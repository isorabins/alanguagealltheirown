"""Non-applying local C rehearsal with a reservation before every HTTP attempt.

No production state, quarantine, model choice or prompt is changed by this tool.
Text-only requests use a conservative byte bound plus framing allowance, capped
at the advertised context limit. Other requests reserve the full context.
An uncertain charge keeps its reservation and stops the run; it is never retried.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from functools import partial
import json
from pathlib import Path
import re
import time

import requests

from state_store import atomic_write_json, snapshot_hash


class LocalBudgetError(RuntimeError):
    pass


class ReservedTransport:
    """Give a budget/catalog/receipt path; get a fail-closed HTTP callable.

Reserve bounded input plus requested output at uncached prices before dispatch,
including retries; enforce those token prices with provider.max_price.
Release unused reservation only on an exact
nonnegative cost receipt. The receipt file contains no headers or prompt content.
"""

    def __init__(self, limit, models, receipt_path, *, post=requests.post, max_output_tokens=None):
        self.limit = self._amount(limit)
        if self.limit <= 0:
            raise LocalBudgetError("local spend limit must be positive")
        self.models = models
        self.path = Path(receipt_path)
        self.post = post
        if max_output_tokens is not None and (type(max_output_tokens) is not int or max_output_tokens <= 0):
            raise LocalBudgetError("output ceiling must be a positive integer")
        self.max_output_tokens = max_output_tokens
        self.used = Decimal(0)
        self.attempts = []
        self.stopped = False
        if self.path.exists():
            saved = json.loads(self.path.read_text())
            if self._amount(saved["limit_usd"]) != self.limit:
                raise LocalBudgetError("cannot change an existing run's allowance")
            self.used = self._amount(saved["charged_or_reserved_usd"])
            self.attempts = saved["attempts"]
            self.stopped = saved["stopped"]

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

    def reconcile_context_rejection(self, request_path):
        """Release one proven pre-generation rejection under documented billing.

        The original uncertain receipt is retained. This is a policy-supported
        zero charge, never represented as a returned provider usage receipt.
        No other missing-cost response or timeout is eligible.
        """
        if not self.attempts:
            raise LocalBudgetError('no request to reconcile')
        attempt = self.attempts[-1]
        if attempt.get('reconciliation'):
            return False
        response_path = self.path.parent / f'provider-response-{len(self.attempts):02d}.json'
        response = json.loads(response_path.read_text())
        request = json.loads(Path(request_path).read_text())
        error = response.get('error') or {}
        metadata = error.get('metadata') or {}
        bound_request = (attempt.get('request_hash') == snapshot_hash(request)
                         and attempt.get('text_only_no_aux') is True)
        if (attempt.get('status') != 'uncertain' or not self.stopped
                or any(a.get('status') == 'uncertain' and not a.get('reconciliation') for a in self.attempts[:-1])
                or response.get('http_status') != 400 or error.get('code') != 400
                or not str(error.get('message', '')).startswith("This endpoint's maximum context length is ")
                or 'provider_name' not in metadata or metadata['provider_name'] is not None
                or any(response.get(k) is not None for k in ('id', 'model', 'provider', 'choices', 'usage'))
                or not bound_request or request.get('model') != attempt.get('model')
                or self._amount(self.models[attempt['model']]['pricing'].get('request', 0)) != 0):
            raise LocalBudgetError('response is not a proven text-only pre-generation context rejection')
        attempt['reconciliation'] = {
            'kind': 'documented_zero_charge', 'charge_usd': '0',
            'released_reservation_usd': attempt['reserved_usd'],
            'response_hash': snapshot_hash(response), 'request_hash': snapshot_hash(request),
            'request_path': str(Path(request_path).resolve()),
            'basis': 'Context validation failed before provider assignment; no output or auxiliary services.',
            'billing_policy': 'https://openrouter.ai/docs/guides/features/zero-completion-insurance',
        }
        self.used -= self._amount(attempt['reserved_usd'])
        self.stopped = False
        self._save()
        return True

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
        if self.max_output_tokens is not None:
            output = body["max_tokens"] = min(output, self.max_output_tokens)
        prices = model.get("pricing", {})
        # Local text-only rehearsals need not reserve a million empty tokens.
        # For the experiment's byte-tokenized models, use twice the entire JSON
        # payload's UTF-8 size plus 8192 tokens for chat/schema framing. Fall back
        # to the full model context for all other request shapes and models.
        messages = body.get("messages", [])
        if (body["model"] in {"moonshotai/kimi-k3", "moonshotai/kimi-k2.6", "deepseek/deepseek-v3.2"}
                and messages and all(isinstance(m.get("content"), str) for m in messages)
                and not any(k in body for k in ("tools", "plugins", "audio", "images"))):
            context = min(context, 2 * len(json.dumps(body, ensure_ascii=False).encode()) + 8192)
        body.setdefault("provider", {})["max_price"] = {
            "prompt": float(self._amount(prices.get("prompt")) * 1_000_000),
            "completion": float(self._amount(prices.get("completion")) * 1_000_000),
        }
        # Include output separately, conservatively even when the advertised
        # context already includes the completion tokens.
        reserve = (context * self._amount(prices.get("prompt")) +
                   output * self._amount(prices.get("completion")) +
                   self._amount(prices.get("request", 0)))
        if self.used + reserve > self.limit:
            raise LocalBudgetError("next request exceeds remaining local spend reservation")
        wire_keys = {'model', 'messages', 'max_tokens', 'temperature', 'provider',
                     'response_format', 'reasoning'}
        text_only = (bool(messages) and all(isinstance(m.get('content'), str)
                     and m.get('role') in {'system', 'user'} and set(m) <= {'role','content'}
                     for m in messages) and not (set(body) - wire_keys)
                     and not body['model'].endswith(':online'))
        attempt = {"model": body["model"], "reserved_usd": str(reserve), "input_token_bound": context,
                   "output_token_limit": output,
                   "status": "uncertain", "request_hash": snapshot_hash(body),
                   "text_only_no_aux": text_only}
        self.attempts.append(attempt)
        self.used += reserve
        self.stopped = True
        self._save()  # Durable before dispatch; a crash cannot erase the reservation.
        atomic_write_json(self.path.parent / f"provider-request-{len(self.attempts):02d}.json", body)
        stage = "request"
        started = time.monotonic()
        response = None
        data = None
        try:
            response = self.post(url, **kwargs)
            stage = "response_json"
            data = response.json()
            # Preserve diagnosis evidence locally, including provider choice
            # errors that the ordinary text/usage adapter does not return.
            # Never persist request headers or the transport's credential.
            stage = "response_receipt"
            atomic_write_json(self.path.parent / f"provider-response-{len(self.attempts):02d}.json", {
                "http_status": response.status_code,
                **{key: data.get(key) for key in
                   ("id", "model", "provider", "choices", "usage", "error")},
            })
            stage = "cost"
            cost = self._amount(data.get("usage", {}).get("cost"))
        except Exception as error:
            # Keep diagnostics separate from billing: no raw exception, headers,
            # prompt, or model output; uncertainty still retains the full reserve.
            failure = {"stage": stage, "exception_type": type(error).__name__,
                       "elapsed_seconds": round(time.monotonic() - started, 3)}
            status = getattr(response, "status_code", None)
            if type(status) is int:
                failure["http_status"] = status
            response_id = data.get("id") if isinstance(data, dict) else None
            if isinstance(response_id, str) and re.fullmatch(r"gen-[A-Za-z0-9_-]{1,150}", response_id):
                failure["response_id"] = response_id
            attempt["failure"] = failure
            try:
                self._save()
            except Exception:
                # A filesystem failure cannot undo the pre-dispatch reservation
                # or replace the fail-closed error with unsafe exception details.
                pass
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
