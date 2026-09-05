"""Non-applying local C rehearsal with a reservation before every HTTP attempt.

No production state, quarantine, model choice or prompt is changed by this tool.
The provider's advertised context limit and token prices bound each reservation.
An uncertain charge keeps its reservation and stops the run; it is never retried.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from functools import partial
import json
from pathlib import Path

import requests

from state_store import atomic_write_json


class LocalBudgetError(RuntimeError):
    pass


class ReservedTransport:
    """Give a budget/catalog/receipt path; get a fail-closed HTTP callable.

Reserve the full advertised context plus requested output at uncached prices
before dispatch, including retries. Release unused reservation only on an exact
nonnegative cost receipt. The receipt file contains no headers or prompt content.
"""

    def __init__(self, limit, models, receipt_path, *, post=requests.post):
        self.limit = self._amount(limit)
        if self.limit <= 0:
            raise LocalBudgetError("local spend limit must be positive")
        self.models = models
        self.path = Path(receipt_path)
        self.post = post
        self.used = Decimal(0)
        self.attempts = []
        self.stopped = False

    @staticmethod
    def _amount(value):
        try:
            if isinstance(value, bool):
                raise ValueError()
            result = Decimal(str(value))
            if not result.is_finite() or result < 0:
                raise ValueError()
            return result
        except (InvalidOperation, ValueError):
            raise LocalBudgetError("missing or invalid provider price/cost") from None

    def _save(self):
        atomic_write_json(self.path, {
            "limit_usd": str(self.limit), "charged_or_reserved_usd": str(self.used),
            "stopped": self.stopped, "attempts": self.attempts,
        })

    def __call__(self, url, **kwargs):
        if self.stopped:
            raise LocalBudgetError("local provider run already stopped")
        body = kwargs["json"]
        model = self.models.get(body["model"])
        if not model:
            raise LocalBudgetError("model absent from preflight catalog")
        context = model.get("context_length")
        output = body.get("max_tokens")
        if (type(context) is not int or context <= 0 or
                type(output) is not int or output <= 0):
            raise LocalBudgetError("provider token limits must be positive integers")
        prices = model.get("pricing", {})
        # Include every advertised context token, conservatively even when the
        # advertised context already includes the reserved completion tokens.
        reserve = (context * self._amount(prices.get("prompt")) +
                   output * self._amount(prices.get("completion")) +
                   self._amount(prices.get("request", 0)))
        if self.used + reserve > self.limit:
            raise LocalBudgetError("next request exceeds remaining local spend reservation")
        attempt = {"model": body["model"], "reserved_usd": str(reserve),
                   "status": "uncertain"}
        self.attempts.append(attempt)
        self.used += reserve
        self.stopped = True
        self._save()  # Durable before dispatch; a crash cannot erase the reservation.
        try:
            response = self.post(url, **kwargs)
            data = response.json()
            # Preserve diagnosis evidence locally, including provider choice
            # errors that the ordinary text/usage adapter does not return.
            # Never persist request headers or the transport's credential.
            atomic_write_json(self.path.parent / f"provider-response-{len(self.attempts):02d}.json", {
                "http_status": response.status_code,
                **{key: data.get(key) for key in
                   ("id", "model", "provider", "choices", "usage", "error")},
            })
            cost = self._amount(data.get("usage", {}).get("cost"))
        except Exception:
            raise LocalBudgetError("provider charge uncertain; reservation retained, no retry") from None
        attempt.update({"response_id": data.get("id"), "http_status": response.status_code,
                        "cost_usd": str(cost), "status": "received"})
        self.used += cost - reserve
        if cost > reserve:
            self._save()
            raise LocalBudgetError("provider charge exceeded advertised reservation; stopped")
        self.stopped = False
        self._save()
        return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-spend-usd", required=True)
    args = parser.parse_args()
    # Output ownership is explicit; never reuse a previous run's budget or state.
    args.output.mkdir(parents=True, exist_ok=False)
    import loop
    from shadow_cleanup import run_shadow_cleanup
    response = requests.get("https://openrouter.ai/api/v1/models", timeout=30)
    response.raise_for_status()
    needed = {loop.MODEL_C, loop.MODEL_B, loop.MODEL_GRADER}
    models = {m["id"]: m for m in response.json()["data"] if m["id"] in needed}
    atomic_write_json(args.output / "model-preflight.json", models)
    transport = ReservedTransport(args.max_spend_usd, models, args.output / "budget.json")
    call = partial(loop.call, transport=transport)
    meta = {"spend_usd": 0.0}
    loop.initialize_exact_cost_accounting(meta, cutover_turn=0)
    loop.configure_cost_receipt_ledger(args.output / "cost-receipts.json", meta)
    report = run_shadow_cleanup(
        args.source, args.output / "shadow", model_c=loop.MODEL_C, model_b=loop.MODEL_B,
        call_model=call, token_counter=partial(loop.token_count, call_model=call),
        meta=meta, max_spend_usd=float(transport.limit),
    )
    print(json.dumps({k: report.get(k) for k in (
        "status", "stage", "reason", "reduction_pct", "run_spend_usd", "source_unchanged"
    )}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
