#!/usr/bin/env python3
"""Scheduled experiment orchestration and provider adapters.

Domain modules own turn recovery, legislative outcomes, exam evidence and public
snapshots. Models still invent and audit the language.
"""
import argparse
import copy
import json
import math
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from collaboration import (
    empty_state,
    escalate_lookup_to_ask,
    import_inbox_spool,
    public_state,
    write_outbox,
)
from cleanup_rulebook import build_applied_rulebook
from conversation_exam import run_conversation
from legislative_protocol import (
    PROTOCOL_VERSION,
    build_cutover_receipt,
    build_post_state_receipt,
    current_open_motion,
    derive_semantic_fault_ledger,
    prompt_receipt_projection,
)
from project_lookup import is_project_question, project_lookup
from rulebook import (
    language_payload,
    render_language,
    score_judgment_v2,
)
from shadow_cleanup import DEFAULT_MAX_SPEND_USD, run_shadow_cleanup
from state_store import atomic_write_json, load_json, snapshot_hash
from turn_store import TurnState, TurnStore
from public_exam_progress import publish_completed_snapshot
import legislature
import exam_evidence
import public_snapshot
from exam_evidence import (
    previous_benchmark_result,
    _materialize_grader_evidence,
)
from legislature import (
    next_legislative_actor,
    latest_post_state_receipt,
)

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_A = "deepseek/deepseek-v3.2"
MODEL_B = "moonshotai/kimi-k2.6"
MODEL_C = "moonshotai/kimi-k3"
MODEL_DECODER = "moonshotai/kimi-k2.6"  # a FOREIGN decoder: the stranger must not share the negotiators' weights
MODEL_GRADER = "deepseek/deepseek-v3.2"

ACTIVE_AGENT_PROMPTS = {
    "A": ("agent-a-v3", ROOT / "prompts" / "agent_a_v3.md"),
    "B": ("agent-b-v3", ROOT / "prompts" / "agent_b_v3.md"),
}
AUTOMATIC_CLEANUP_GROWTH_PERCENT = 10
AUTOMATIC_CLEANUP_MAX_SPEND_USD = DEFAULT_MAX_SPEND_USD
AUTOMATIC_CLEANUP_PROMPT_C = ROOT / "prompts" / "cleanup_c_v4.md"
AUTOMATIC_CLEANUP_PROMPT_B = ROOT / "prompts" / "cleanup_b_v3.md"

TEST_EVERY = 3      # every Nth turn is a test turn
WINDOW = 30         # conversation events each agent sees
MAX_TEST_AUDIT_CATEGORY_CHARS = 320
MAX_TEST_GRADER_LOSS_CHARS = 600
PRIVATE_FAULT_PROMPT_REDACTION = (
    "[private validation-overlapping text withheld from this legislative prompt]"
)
SPEND_CAP = 100.00  # dollars, hard stop across all runs — operator-approved cumulative ceiling
AGENT_TEMP = 0.9
COST_LEDGER_SCHEMA_VERSION = 1
COST_LEDGER_FILENAME = "cost-receipts.local.json"

_key = None
_no_reasoning_field = False
_probe_overhead = None
_probe_cache = {}
_cost_receipt_ledger_path = None
_cost_receipt_ledger = None


class CostAccountingError(RuntimeError):
    pass


def api_key():
    global _key
    if _key is None:
        _key = os.environ.get("OPENROUTER_API_KEY", "").strip() or None
    if _key is None and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                _key = line.split("=", 1)[1].strip()
    if not _key:
        sys.exit("no OPENROUTER_API_KEY in .env")
    return _key


def load(name, default):
    return load_json(STATE / name, default)


def save(name, obj):
    atomic_write_json(STATE / name, obj)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def initialize_exact_cost_accounting(meta, *, cutover_turn):
    """Label the inherited estimate once, then track provider-returned charges."""
    if "spend_usd_historical_estimate" not in meta:
        meta["spend_usd_historical_estimate"] = float(meta.get("spend_usd", 0.0))
        meta["spend_usd_provider_exact_since_cutover"] = 0.0
        meta["cost_accounting_cutover_turn"] = int(cutover_turn)
        meta["cost_accounting_basis"] = "historical_estimate_plus_provider_usage_cost"
    meta["spend_usd"] = round(
        float(meta["spend_usd_historical_estimate"])
        + float(meta["spend_usd_provider_exact_since_cutover"]),
        12,
    )


def _validated_cost(value, *, field):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise CostAccountingError(f"{field} must be a finite non-negative number")
    return float(value)


def _exact_cost_total(meta):
    if "spend_usd_historical_estimate" not in meta:
        raise CostAccountingError("exact cost accounting was not initialized at cutover")
    return round(
        _validated_cost(
            meta.get("spend_usd_provider_exact_since_cutover"),
            field="meta exact provider cost",
        ),
        12,
    )


def _set_meta_exact_cost(meta, exact_total):
    exact_total = round(
        _validated_cost(exact_total, field="exact provider cost total"), 12
    )
    historical = _validated_cost(
        meta.get("spend_usd_historical_estimate"),
        field="historical spend estimate",
    )
    meta["spend_usd_provider_exact_since_cutover"] = exact_total
    meta["spend_usd"] = round(historical + exact_total, 12)


def _validated_cost_ledger(ledger, meta):
    required = {
        "schema_version",
        "protocol_version",
        "cutover_turn",
        "base_exact_usd",
        "receipts",
    }
    if not isinstance(ledger, dict) or set(ledger) != required:
        raise CostAccountingError("cost receipt ledger has an invalid shape")
    if ledger["schema_version"] != COST_LEDGER_SCHEMA_VERSION:
        raise CostAccountingError("cost receipt ledger schema version mismatch")
    if ledger["protocol_version"] != PROTOCOL_VERSION:
        raise CostAccountingError("cost receipt ledger protocol version mismatch")
    cutover_turn = ledger["cutover_turn"]
    if isinstance(cutover_turn, bool) or not isinstance(cutover_turn, int):
        raise CostAccountingError("cost receipt ledger cutover turn is invalid")
    if cutover_turn != meta.get("cost_accounting_cutover_turn"):
        raise CostAccountingError("cost receipt ledger cutover turn mismatch")
    base = round(
        _validated_cost(ledger["base_exact_usd"], field="cost ledger base"), 12
    )
    receipts = ledger["receipts"]
    if not isinstance(receipts, dict):
        raise CostAccountingError("cost receipt ledger receipts must be an object")
    costs = []
    for response_id, value in receipts.items():
        if (
            not isinstance(response_id, str)
            or not response_id
            or response_id != response_id.strip()
        ):
            raise CostAccountingError("cost receipt ledger response id is invalid")
        costs.append(
            _validated_cost(value, field="cost receipt ledger response cost")
        )
    return base, round(base + sum(costs), 12)


def disable_cost_receipt_ledger():
    """Disable the process-local ledger binding used only by production run()."""
    global _cost_receipt_ledger_path, _cost_receipt_ledger
    _cost_receipt_ledger_path = None
    _cost_receipt_ledger = None


def configure_cost_receipt_ledger(path, meta):
    """Bind and reconcile the VPS-local response receipt ledger for this process."""
    global _cost_receipt_ledger_path, _cost_receipt_ledger
    disable_cost_receipt_ledger()
    ledger_path = Path(path)
    current_exact = _exact_cost_total(meta)
    cutover_turn = meta.get("cost_accounting_cutover_turn")
    if isinstance(cutover_turn, bool) or not isinstance(cutover_turn, int):
        raise CostAccountingError("meta cost-accounting cutover turn is invalid")
    if ledger_path.exists():
        try:
            ledger = json.loads(ledger_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise CostAccountingError("cost receipt ledger is unreadable") from exc
        base, ledger_total = _validated_cost_ledger(ledger, meta)
        if base > current_exact or ledger_total < current_exact:
            raise CostAccountingError(
                "cost receipt ledger conflicts with persisted exact cost"
            )
        if ledger_total > current_exact:
            _set_meta_exact_cost(meta, ledger_total)
    else:
        ledger = {
            "schema_version": COST_LEDGER_SCHEMA_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "cutover_turn": cutover_turn,
            "base_exact_usd": current_exact,
            "receipts": {},
        }
        atomic_write_json(ledger_path, ledger)
    _cost_receipt_ledger_path = ledger_path
    _cost_receipt_ledger = ledger
    return ledger


def _record_cost_receipt(response_id, cost, meta):
    global _cost_receipt_ledger
    if _cost_receipt_ledger_path is None or _cost_receipt_ledger is None:
        return None
    if (
        not isinstance(response_id, str)
        or not response_id
        or response_id != response_id.strip()
    ):
        raise CostAccountingError("api response missing valid id for cost receipt")
    _, current_total = _validated_cost_ledger(_cost_receipt_ledger, meta)
    existing = _cost_receipt_ledger["receipts"].get(response_id)
    if existing is not None:
        if _validated_cost(existing, field="existing response cost") != cost:
            raise CostAccountingError(
                "api response id has a conflicting provider cost"
            )
        return current_total
    updated = copy.deepcopy(_cost_receipt_ledger)
    updated["receipts"][response_id] = cost
    _validated_cost_ledger(updated, meta)
    atomic_write_json(_cost_receipt_ledger_path, updated)
    _cost_receipt_ledger = updated
    _, updated_total = _validated_cost_ledger(updated, meta)
    return updated_total


def record_provider_cost(meta, usage, *, response_id=None):
    """Accumulate one successful response, durably deduplicated when configured."""
    cost = _validated_cost(
        usage.get("cost") if isinstance(usage, dict) else None,
        field="api response usage.cost",
    )
    current_exact = _exact_cost_total(meta)
    ledger_total = _record_cost_receipt(response_id, cost, meta)
    exact_total = (
        round(current_exact + cost, 12)
        if ledger_total is None
        else ledger_total
    )
    if exact_total < current_exact:
        raise CostAccountingError("cost receipt ledger would reduce exact cost")
    _set_meta_exact_cost(meta, exact_total)


def call(model, system, user, max_tokens=600, temperature=0.7, meta=None,
         request_options=None, transport=None):
    """One chat call. Returns (text, usage). Retries transient failures."""
    global _no_reasoning_field
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": user}
    ]
    body = {"model": model, "messages": messages, "max_tokens": max_tokens,
            "temperature": temperature}
    if model.startswith("deepseek/"):
        # Pin DeepSeek calls so token probes stay on one tokenizer/provider. Foreign
        # decoder calls remain unpinned; every successful call still uses usage.cost.
        body["provider"] = {"order": ["deepseek"]}
    for key, value in (request_options or {}).items():
        if key == "provider":
            body.setdefault("provider", {}).update(value)
        else:
            body[key] = value
    if not _no_reasoning_field:
        body["reasoning"] = {"enabled": False}
    headers = {"Authorization": f"Bearer {api_key()}",
               "HTTP-Referer": "https://alanguagealltheirown.com",
               "X-Title": "a-language-all-their-own"}
    delays = [0, 3, 8, 20, 45]
    for i, d in enumerate(delays):
        if d:
            time.sleep(d)
        try:
            r = (transport or requests.post)(API_URL, headers=headers, json=body, timeout=180)
        except requests.RequestException as e:
            print(f"  ! network {e.__class__.__name__}, retry {i}", flush=True)
            continue
        if r.status_code == 400 and not _no_reasoning_field:
            _no_reasoning_field = True
            body.pop("reasoning", None)
            continue
        if r.status_code in (429, 500, 502, 503, 520, 524):
            print(f"  ! http {r.status_code}, retry {i}", flush=True)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"api {r.status_code}: {r.text[:300]}")
        d = r.json()
        if "error" in d:
            print(f"  ! provider error {str(d['error'])[:120]}, retry {i}", flush=True)
            continue
        choice = d["choices"][0]
        usage = copy.deepcopy(d.get("usage", {}))
        usage["response_receipt"] = {
            "id": d.get("id"),
            "model": d.get("model"),
            "finish_reason": choice.get("finish_reason"),
            "openrouter_metadata": copy.deepcopy(d.get("openrouter_metadata")),
        }
        if meta is not None:
            record_provider_cost(meta, usage, response_id=d.get("id"))
        return choice["message"]["content"] or "", usage
    raise RuntimeError("api: retries exhausted")


def token_count(text, meta, *, call_model=None):
    """Exact token size of standalone text: probe call, prompt_tokens minus overhead.
    Probe-based so reasoning/completion accounting can never contaminate it."""
    global _probe_overhead
    call = call_model or globals()["call"]
    if text in _probe_cache:
        return _probe_cache[text]
    if _probe_overhead is None:
        _, u = call(MODEL_GRADER, None, "x", max_tokens=1, temperature=0, meta=meta)
        _probe_overhead = u["prompt_tokens"] - 1
    _, u = call(MODEL_GRADER, None, text, max_tokens=1, temperature=0, meta=meta)
    n = max(1, u["prompt_tokens"] - _probe_overhead)
    if n <= 2 and len(text) > 12:  # implausible: provider drift broke calibration — recalibrate once
        _probe_overhead = None
        _probe_cache.clear()
        _, u0 = call(MODEL_GRADER, None, "x", max_tokens=1, temperature=0, meta=meta)
        _probe_overhead = u0["prompt_tokens"] - 1
        _, u = call(MODEL_GRADER, None, text, max_tokens=1, temperature=0, meta=meta)
        n = max(1, u["prompt_tokens"] - _probe_overhead)
    _probe_cache[text] = n
    return n


def render_rulebook(rb):
    """Compatibility name for the only ordinary language boundary: adopted rules."""
    return render_language(rb)


DECODE_VIEW_MAX = 6000  # emergency brake only — sized so a 400–600-word decode always renders whole


def render_decode(dec):
    """The stranger's decode, whole — never cut silently: the agents read a mid-word stop
    as decoder data-loss and legislate against it. A bare [:400] slice here became a
    phantom '~100-token decoder limit' (t133-t137) and two of four live rules were built
    to dodge a bug that never existed. If it must elide, say so in the text."""
    if len(dec) <= DECODE_VIEW_MAX:
        return dec
    return (f"{dec[:DECODE_VIEW_MAX]}\n[VIEW ELIDED — this display is hiding "
            f"{len(dec) - DECODE_VIEW_MAX} further chars from you. The decode itself was "
            f"NOT truncated; it arrived complete. Judge fidelity by the grader score, "
            f"never by where this view stops.]")


def render_window(conv):
    out = []
    for e in conv[-WINDOW:]:
        if e["type"] == "protocol_cutover":
            receipt = e.get("state_receipt") or {}
            out.append(
                f"[turn {e['turn']} — AUTHORITATIVE PROTOCOL CUTOVER RECEIPT]\n"
                + json.dumps(
                    prompt_receipt_projection(receipt),
                    sort_keys=True,
                    ensure_ascii=False,
                )
            )
            continue
        if e["type"] == "measure":
            out.append(f"[turn {e['turn']} — MEASUREMENT] \"{e['text']}\" = {e['tokens']} tokens (exact)")
            continue
        if e["type"] == "notice":
            out.append(f"[turn {e['turn']} — HARNESS CORRECTION]\n{e['content']}")
            continue
        if e["type"] == "legislature":
            post_state = e.get("post_state_receipt")
            if isinstance(post_state, dict):
                out.append(
                    f"[turn {e['turn']} — AUTHORITATIVE POST-STATE RECEIPT]\n"
                    + json.dumps(
                        prompt_receipt_projection(post_state),
                        sort_keys=True,
                        ensure_ascii=False,
                    )
                )
                continue
            receipt = e.get("motion_receipt") or {}
            available = {
                key: receipt[key]
                for key in (
                    "accepted", "reason", "agent", "verb", "rule_id", "changed", "line"
                )
                if key in receipt
            }
            out.append(
                f"[turn {e['turn']} — LEGACY MACHINE RECEIPT; AVAILABLE FIELDS ONLY]\n"
                + json.dumps(available, sort_keys=True, ensure_ascii=False)
            )
            continue
        if e["type"] == "test":
            if e.get("scoring_version") == "v2":
                if not e.get("judge_valid"):
                    result = (
                        f"INVALID JUDGE RESULT ({e.get('judge_reason', 'invalid')}); "
                        "this is evaluator failure, not benchmark failure"
                    )
                else:
                    result = (
                        f"meaning {'PASS' if e.get('meaning_pass') else 'FAIL'} | "
                        f"coverage {e.get('semantic_coverage_pct')}% | "
                        f"critical failures {len(e.get('critical_failures', []))} | "
                        f"inventions {len(e.get('inventions', []))} | "
                        f"message-body savings {e.get('message_body_savings_pct')}% | "
                        f"compression {'SUCCESS' if e.get('compression_success') else 'FAIL'}"
                    )
                out.append(
                    f"[turn {e['turn']} — SCORING V2 DEVELOPMENT BENCHMARK | "
                    f"payload: {e['payload']}]\n{result}"
                )
                continue
            audit = ""
            if e.get("total"):
                bits = [f"answer key: {e.get('survived')}/{e['total']} items survived"]
                for lab in ("corrupted", "missing", "invented"):
                    if e.get(lab):
                        rows = e[lab] if isinstance(e[lab], list) else [e[lab]]
                        body = "; ".join(str(x) for x in rows[:4])
                        if len(body) > MAX_TEST_AUDIT_CATEGORY_CHARS:
                            body = (
                                body[:MAX_TEST_AUDIT_CATEGORY_CHARS].rstrip()
                                + "…"
                            )
                        bits.append(
                            f"{lab} ({min(len(rows), 4)}/{len(rows)}): {body}"
                        )
                audit = "\n" + " | ".join(bits)
            score = (f"decode fidelity {e['fidelity']}/100" if e.get("fidelity") is not None
                     else f"no valid score ({e.get('judge_reason', 'invalid')})")
            grader_loss = str(e.get("lost", ""))
            if len(grader_loss) > MAX_TEST_GRADER_LOSS_CHARS:
                grader_loss = (
                    grader_loss[:MAX_TEST_GRADER_LOSS_CHARS].rstrip()
                    + "…"
                )
            comparison = ""
            if e.get("benchmark_id") and e.get("prior_turn") is not None:
                if e.get("fidelity_delta") is None:
                    comparison = (
                        f"\n{e['benchmark_id']} baseline remains turn "
                        f"{e['prior_turn']} because this result is invalid"
                    )
                else:
                    comparison = (
                        f"\nprevious same benchmark: turn {e['prior_turn']} | "
                        f"fidelity {e['prior_fidelity']} -> {e['fidelity']} "
                        f"({e['fidelity_delta']:+d}) | savings "
                        f"{-e['prior_token_delta_pct']}% -> {-e['token_delta_pct']}% "
                        f"({e['savings_delta_pct']:+d} points)"
                    )
            out.append(
                f"[turn {e['turn']} — AUTHORITATIVE LIVE TEST RECEIPT | "
                f"payload: {e['payload']}]\n"
                f"original {e['orig_tokens']} tokens -> encoded {e['enc_tokens']} tokens "
                f"({e['token_delta_pct']:+d}%) | {score}\n"
                f"grader: {grader_loss}" + comparison + audit)
        else:
            out.append(
                f"[turn {e['turn']} — NON-AUTHORITATIVE AGENT DISCUSSION] "
                f"AGENT {e['agent']}:\n{e['content']}"
            )
    return "\n\n".join(out) if out else "(no conversation yet — the rulebook is empty and you speak first)"


def rationale_for(text, line):
    """The paragraph around the exact matched motion line, minus verb lines — the 'why'."""
    paras = text.split("\n\n")
    idx = next((i for i, p in enumerate(paras) if line in p), 0)
    for cand in (paras[idx], paras[idx - 1] if idx else ""):
        why = " ".join(l for l in cand.splitlines()
                       if not re.match(r"\s*\**(PROPOSE|REPEAL|ADOPT|REJECT|REVISE|REQUEST(?:-REVISION|-TEST)?)", l)).strip()
        if len(why) > 20:
            return why[:280]
    return ""


def collaboration_directive(text, kind):
    """Read one plain, bold, or code-formatted collaboration directive."""
    match = re.search(
        rf"^\s*[*`]*{re.escape(kind)}[*`]*\s*:\s*(.+?)\s*[*`]*$",
        text,
        re.M,
    )
    return match.group(1).strip().strip("*`").strip() if match else None








def _public_policy():
    return public_snapshot.PublicPolicy(SPEND_CAP, TEST_EVERY, AUTOMATIC_CLEANUP_GROWTH_PERCENT, MODEL_A)


def _public_agent_c_state(rb, meta):
    return public_snapshot._public_agent_c_state(rb, meta, AUTOMATIC_CLEANUP_GROWTH_PERCENT)


def _public_runtime_state(turn, meta, rb):
    return public_snapshot._public_runtime_state(turn, meta, rb, _public_policy())


def write_viewer_state(conv, rb, meta, collaboration=None, conversations=None):
    public_snapshot.write_snapshot(
        TurnState(conv, rb, meta, collaboration or empty_state(), conversations or []),
        ROOT, updated=meta.get("last_completed_turn_at"), policy=_public_policy(),
    )


def ensure_structured_protocol_cutover(conv, rb, meta, *, activation_turn):
    """Append one authoritative boundary receipt while leaving old records untouched."""
    existing = meta.get("structured_protocol")
    if isinstance(existing, dict):
        if existing.get("version") != PROTOCOL_VERSION:
            raise RuntimeError("unknown structured protocol state")
        receipt = latest_post_state_receipt(conv)
        if not receipt:
            raise RuntimeError("structured protocol metadata has no persisted receipt")
        initialize_exact_cost_accounting(
            meta, cutover_turn=int(existing["cutover_turn"])
        )
        return receipt

    next_actor = next_legislative_actor(meta)
    receipt = build_cutover_receipt(
        rb, turn=int(activation_turn), next_actor=next_actor
    ).model_dump(mode="json")
    conv.append(
        {
            "turn": int(activation_turn),
            "agent": "harness",
            "type": "protocol_cutover",
            "state_receipt": receipt,
        }
    )
    meta["structured_protocol"] = {
        "version": PROTOCOL_VERSION,
        "cutover_turn": int(activation_turn),
    }
    initialize_exact_cost_accounting(meta, cutover_turn=int(activation_turn))
    return receipt


AUTOMATIC_CLEANUP_STATE_SCHEMA_VERSION = 2
AUTOMATIC_CLEANUP_EDITION = "automatic-cleanup-v6-provider-failure-classification"
MAX_POST_CHECKPOINT_CHANGES = 64
MAX_STRUCTURED_PROMPT_CHARS = 120_000


def build_structured_cleanup_snapshot(candidate, *, checkpoint_turn, source_hash):
    """Bind one accepted C artifact to the automatic-cleanup checkpoint."""
    structured_rulebook = candidate.get("structured_rulebook")
    legislative_memory = candidate.get("legislative_memory")
    if not isinstance(structured_rulebook, dict) or not isinstance(legislative_memory, dict):
        raise ValueError("accepted cleanup candidate lacks structured context")
    if isinstance(checkpoint_turn, bool) or not isinstance(checkpoint_turn, int) or checkpoint_turn < 0:
        raise ValueError("structured snapshot checkpoint_turn is invalid")
    if not isinstance(source_hash, str) or len(source_hash) != 64:
        raise ValueError("structured snapshot source_hash is invalid")
    snapshot = {
        "checkpoint_turn": checkpoint_turn,
        "source_hash": source_hash,
        "rulebook": copy.deepcopy(structured_rulebook),
        "legislative_memory": copy.deepcopy(legislative_memory),
    }
    if len(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))) > 25_000:
        raise ValueError("structured snapshot exceeds the deterministic size budget")
    return snapshot


def _structural_cleanup_failure(report):
    reason = str(report.get("reason", ""))
    return (
        report.get("error_type") == "ValueError"
        and report.get("stage") in {"c_call", "c_validation"}
        and reason.startswith("Agent C ")
    )


def _upgrade_automatic_cleanup_state(state, turn):
    """Upgrade the pre-quarantine state without buying another known-bad call."""
    if state.get("schema_version") != 1:
        return state
    state["schema_version"] = AUTOMATIC_CLEANUP_STATE_SCHEMA_VERSION
    reason = str(state.get("last_reason", ""))
    if state.get("last_status") == "failed" and reason.startswith("Agent C "):
        state["last_status"] = "quarantined"
        state["quarantine"] = {
            "reason": "structural_output",
            "edition": "pre-quarantine-edition",
            "entered_turn": state.get("last_attempt_turn", turn),
            "failure_reason": reason[:500],
        }
    return state


def reset_automatic_cleanup_quarantine(state, *, reviewed_edition, operator):
    """Explicitly re-arm C only after an operator reviews a different edition."""
    quarantine = state.get("quarantine")
    if not isinstance(quarantine, dict) or state.get("last_status") != "quarantined":
        raise ValueError("automatic cleanup is not quarantined")
    if not isinstance(reviewed_edition, str) or not reviewed_edition.strip():
        raise ValueError("reset requires a reviewed cleanup edition")
    if reviewed_edition == quarantine.get("edition"):
        raise ValueError("reset requires a different reviewed cleanup edition")
    if reviewed_edition != AUTOMATIC_CLEANUP_EDITION:
        raise ValueError("reset requires the current reviewed cleanup edition")
    if not isinstance(operator, str) or not operator.strip():
        raise ValueError("reset requires explicit operator action")
    state["reset"] = {
        "reviewed_edition": reviewed_edition,
        "operator": operator.strip(),
        "prior_quarantine": copy.deepcopy(quarantine),
    }
    state["last_status"] = "armed"
    state["last_reason"] = "explicit operator reset for reviewed edition"
    state["last_attempt_language_hash"] = None
    state.pop("quarantine")


def maybe_run_automatic_cleanup(conv, rb, meta, turn):
    """Apply the proven shadow workflow after 10% adopted-language growth."""
    current_tokens = rb.get("kernel_tokens")
    if (
        isinstance(current_tokens, bool)
        or not isinstance(current_tokens, int)
        or current_tokens <= 0
    ):
        raise RuntimeError("automatic cleanup requires a positive kernel token count")
    language = language_payload(rb)
    state = meta.get("automatic_cleanup")
    if state is None:
        meta["automatic_cleanup"] = {
            "schema_version": AUTOMATIC_CLEANUP_STATE_SCHEMA_VERSION,
            "baseline_tokens": current_tokens,
            "baseline_language_hash": language["hash"],
            "baseline_turn": turn,
            "last_attempt_language_hash": None,
            "last_status": "armed",
        }
        return False
    if not isinstance(state, dict):
        raise RuntimeError("automatic cleanup state is invalid")
    state = _upgrade_automatic_cleanup_state(state, turn)
    if state.get("schema_version") != AUTOMATIC_CLEANUP_STATE_SCHEMA_VERSION:
        raise RuntimeError("automatic cleanup state is invalid")
    baseline_tokens = state.get("baseline_tokens")
    if (
        isinstance(baseline_tokens, bool)
        or not isinstance(baseline_tokens, int)
        or baseline_tokens <= 0
    ):
        raise RuntimeError("automatic cleanup baseline is invalid")
    cleanup_threshold = (
        baseline_tokens * (100 + AUTOMATIC_CLEANUP_GROWTH_PERCENT) + 99
    ) // 100
    if current_tokens < cleanup_threshold:
        return False
    if current_open_motion(rb) is not None:
        return False
    if state.get("last_status") == "quarantined":
        quarantine = state.get("quarantine")
        if not isinstance(quarantine, dict):
            raise RuntimeError("automatic cleanup quarantine is invalid")
        conv.append({
            "turn": turn,
            "agent": "harness",
            "type": "cleanup",
            "status": "quarantined",
            "failure_class": quarantine.get("reason"),
            "quarantined_edition": quarantine.get("edition"),
            "language_hash": language["hash"],
            "reason": "automatic Agent C cleanup remains quarantined",
            "run_spend_usd": 0.0,
        })
        return False
    if state.get("last_attempt_language_hash") == language["hash"]:
        return False

    state["last_attempt_language_hash"] = language["hash"]
    state["last_attempt_turn"] = turn
    source_path = STATE / "rulebook.json"
    source = load_json(source_path, None)
    if not isinstance(source, dict) or snapshot_hash(source) != snapshot_hash(rb):
        raise RuntimeError("automatic cleanup source does not match loaded rulebook")

    with tempfile.TemporaryDirectory(prefix="alato-cleanup-") as directory:
        output = Path(directory) / "result"
        report = run_shadow_cleanup(
            source_path,
            output,
            model_c=MODEL_C,
            model_b=MODEL_B,
            call_model=call,
            token_counter=token_count,
            meta=meta,
            prompt_c_path=AUTOMATIC_CLEANUP_PROMPT_C,
            prompt_b_path=AUTOMATIC_CLEANUP_PROMPT_B,
            max_spend_usd=AUTOMATIC_CLEANUP_MAX_SPEND_USD,
        )
        if report.get("error_type") == "CostAccountingError":
            raise CostAccountingError(str(report.get("reason")))
        if report.get("status") != "PASS":
            structural_failure = _structural_cleanup_failure(report)
            invalid_advisory = report.get("failure_class") == "invalid_advisory"
            quarantine_class = (
                "structural_output" if structural_failure
                else "invalid_advisory" if invalid_advisory
                else None
            )
            state.update({
                "last_status": "quarantined" if quarantine_class else "failed",
                "last_reason": str(report.get("reason", "cleanup failed"))[:500],
            })
            if quarantine_class:
                state["quarantine"] = {
                    "reason": quarantine_class,
                    "edition": AUTOMATIC_CLEANUP_EDITION,
                    "entered_turn": turn,
                    "failure_reason": state["last_reason"],
                }
            conv.append({
                "turn": turn,
                "agent": "harness",
                "type": "cleanup",
                "status": "failed",
                "failure_class": quarantine_class or report.get("failure_class") or "other",
                "source_hash": report.get("source_hash"),
                "candidate_hash": report.get("candidate_hash"),
                "source_tokens": report.get("source_tokens"),
                "candidate_tokens": report.get("candidate_tokens"),
                "reduction_pct": report.get("reduction_pct"),
                "reason": state["last_reason"],
                "models": report.get("models"),
                "provider_calls": copy.deepcopy(report.get("provider_calls")),
                "rounds": copy.deepcopy(report.get("rounds")),
                "b_advisory_error": copy.deepcopy(
                    report.get("b_advisory_error")
                ),
                "run_spend_usd": report.get("run_spend_usd"),
            })
            print(f"[t{turn} CLEANUP] failed: {state['last_reason']}", flush=True)
            return False

        candidate = load_json(output / "candidate.json", None)
        seeds = load_json(output / "creative-seeds.json", None)
        if not isinstance(candidate, dict) or not isinstance(seeds, list):
            raise RuntimeError("automatic cleanup output is incomplete")
        structured_snapshot = build_structured_cleanup_snapshot(
            candidate,
            checkpoint_turn=turn,
            source_hash=str(report.get("source_hash", "")),
        )
        before_rulebook = copy.deepcopy(rb)
        applied = build_applied_rulebook(before_rulebook, candidate)
        applied_tokens = token_count(render_language(applied), meta)
        applied["kernel_tokens"] = applied_tokens
        after_language = language_payload(applied)
        receipt = build_post_state_receipt(
            turn=turn,
            role="harness",
            action=None,
            result="cutover",
            reason="automatic_cleanup_c_final_authority",
            before_rulebook=before_rulebook,
            after_rulebook=applied,
            next_actor=next_legislative_actor(meta),
            attempts=0,
        )
        rb.clear()
        rb.update(applied)
        state.update({
            "baseline_tokens": applied_tokens,
            "baseline_language_hash": after_language["hash"],
            "baseline_turn": turn,
            "last_status": "applied",
            "last_reason": report.get("reason"),
            "structured_snapshot": structured_snapshot,
            "pending_creative_seeds": {
                "cleanup_turn": turn,
                "seeds": seeds,
                "delivered_roles": [],
            },
        })
        conv.append({
            "turn": turn,
            "agent": "harness",
            "type": "cleanup",
            "status": "applied",
            "source_hash": report.get("source_hash"),
            "candidate_hash": report.get("candidate_hash"),
            "source_tokens": report.get("source_tokens"),
            "candidate_tokens": report.get("candidate_tokens"),
            "applied_tokens": applied_tokens,
            "reduction_pct": report.get("reduction_pct"),
            "models": report.get("models"),
            "prompt_versions": {
                "c": report.get("prompt_c_version"),
                "b": report.get("prompt_b_version"),
                "c_finalizer": report.get("prompt_c_finalizer_version"),
            },
            "rounds": report.get("rounds"),
            "run_spend_usd": report.get("run_spend_usd"),
            "creative_seeds": seeds,
            "post_state_receipt": receipt.model_dump(mode="json"),
        })
        print(
            f"[t{turn} CLEANUP] applied {current_tokens}->{applied_tokens}tok  "
            f"{report.get('reduction_pct')}% candidate reduction",
            flush=True,
        )
        return True








def _legislative_resources():
    return legislature.LegislativeResources(
        ROOT, ACTIVE_AGENT_PROMPTS, load_benchmark_suite(),
        {"A": MODEL_A, "B": MODEL_B}, TEST_EVERY, AGENT_TEMP,
    )


def assemble_legislative_prompt(conv, rb, *, turn, agent, collaboration_input,
                                structured_snapshot=None):
    return legislature.assemble_request(
        conv, rb, turn=turn, agent=agent, collaboration_input=collaboration_input,
        structured_snapshot=structured_snapshot, resources=_legislative_resources(),
    )


def agent_turn(conv, rb, meta, collaboration, turn):
    return legislature.take_turn(
        TurnState(conv, rb, meta, collaboration, []), turn,
        resources=_legislative_resources(), provider=call,
        count_tokens=lambda text: token_count(text, meta),
    )

BENCHMARK_PATH = ROOT / "benchmarks" / "v2.json"
LEGACY_BENCHMARK_PATH = ROOT / "benchmarks" / "v1.json"
BENCHMARK_IDS = ("B1", "B2", "B3", "B4", "B5")


def load_benchmark_suite(path=BENCHMARK_PATH):
    """Load Scoring V2 atoms and join them to the immutable V1 source messages."""
    suite = load_json(Path(path), {})
    rows = suite.get("benchmarks", [])
    ids = tuple(row.get("id") for row in rows if isinstance(row, dict))
    if suite.get("version") != "v2" or suite.get("source_version") != "v1" or ids != BENCHMARK_IDS:
        raise ValueError("benchmark_v2_registry_invalid")
    source_suite = load_json(LEGACY_BENCHMARK_PATH, {})
    source_rows = {row.get("id"): row for row in source_suite.get("benchmarks", [])}
    for row in rows:
        source = source_rows.get(row.get("id"), {})
        atoms = row.get("answer_key", [])
        atom_ids = [atom.get("id") for atom in atoms if isinstance(atom, dict)]
        valid_atoms = (
            len(atoms) >= 6 and len(atom_ids) == len(atoms)
            and len(atom_ids) == len(set(atom_ids))
            and all(
                isinstance(atom.get("meaning"), str) and atom["meaning"].strip()
                and isinstance(atom.get("critical"), bool)
                and isinstance(atom.get("literal_sets"), list)
                and all(isinstance(group, list) and group
                        and all(isinstance(value, str) and value for value in group)
                        for group in atom["literal_sets"])
                for atom in atoms if isinstance(atom, dict)
            )
        )
        if (not str(row.get("name", "")).strip() or not valid_atoms
                or not str(source.get("original", "")).strip()
                or source.get("source_turn") != row.get("source_turn")):
            raise ValueError(f"benchmark_v2_row_invalid:{row.get('id')}")
        row["original"] = source["original"]
    return suite




def normalize_answer_key(raw):
    lines = raw if isinstance(raw, list) else str(raw).splitlines()
    return [re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", str(line)).strip()
            for line in lines
            if re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", str(line)).strip()]







def select_benchmark(meta, suite=None):
    return exam_evidence.select_benchmark(meta, suite or load_benchmark_suite())


def advance_benchmark(meta, benchmark, suite=None):
    return exam_evidence.advance_benchmark(meta, benchmark, suite or load_benchmark_suite())


def test_turn(conv, rb, meta, turn, *, progress_path=None):
    return exam_evidence.run_exam(
        TurnState(conv, rb, meta, {}, []), turn,
        resources=exam_evidence.ExamResources(
            ROOT, load_benchmark_suite(), MODEL_A, MODEL_DECODER, MODEL_GRADER),
        provider=call, count_tokens=lambda text: token_count(text, meta),
        progress_path=progress_path,
    )


def consume_notice(conv, turn):
    """Notice inbox: if state/pending-notice.txt exists, deliver it as a harness notice
    this turn; TurnStore acknowledges it only with the completed turn. Lets notices travel via git without racing the
    VPS's own state commits (a direct conversation.json edit would)."""
    f = STATE / "pending-notice.txt"
    if not f.exists():
        return
    original = f.read_text()
    text = original.strip()
    if text:
        conv.append({"turn": turn, "agent": "harness", "type": "notice", "content": text})
        print(f"[t{turn} NOTICE] delivered ({len(text)} chars)", flush=True)
    return original


def process_one_research(collaboration, meta, turn):
    """Resolve at most the oldest queued request; evidence cannot alter rule state."""
    record = next((r for r in collaboration.get("research", []) if r.get("status") == "queued"), None)
    if not record:
        return
    question = str(record.get("question", ""))
    route = (
        "project"
        if record.get("kind") == "LOOKUP"
        or record.get("route") == "project"
        or is_project_question(question)
        else "web"
    )
    record["route"] = route
    if route == "project":
        record["status"] = "looking_up"
        result = project_lookup(ROOT, question)
        record.update({
            "findings": result["findings"],
            "limitations": result["limitations"],
            "citations": result["citations"],
            "evidence_count": result["evidence_count"],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "web_search_requests": 0,
            },
            "cost_usd": 0,
            "no_evidence": not result["adequate"],
            "answer_turn": turn,
        })
        if result["adequate"]:
            record["status"] = "answered"
        else:
            escalate_lookup_to_ask(collaboration, record, turn)
        return

    record["status"] = "researching"
    if "spend_usd_historical_estimate" not in meta:
        initialize_exact_cost_accounting(meta, cutover_turn=turn)
    spend_before = float(meta.get("spend_usd", 0.0))
    body = {"model": MODEL_A,
            "messages": [{"role": "system", "content": (ROOT / "prompts" / "research.md").read_text()},
                         {"role": "user", "content": record["question"]}],
            "tools": [{"type": "openrouter:web_search", "parameters": {"max_total_results": 5}}],
            "max_tokens": 1000, "temperature": 0}
    try:
        response = requests.post(API_URL, headers={"Authorization": f"Bearer {api_key()}",
                                                   "Content-Type": "application/json"},
                                 json=body, timeout=180)
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage", {})
        usage = usage if isinstance(usage, dict) else {}
        record_provider_cost(meta, usage, response_id=data.get("id"))
        message = data["choices"][0]["message"]
        tool_use = usage.get("server_tool_use", {})
        tool_use = tool_use if isinstance(tool_use, dict) else {}
        structured = True
        try:
            parsed = json.loads(message.get("content") or "{}")
        except json.JSONDecodeError:
            parsed = {}
            structured = False
        if not isinstance(parsed, dict) or not {
            "findings", "limitations", "citations"
        }.issubset(parsed):
            parsed = {}
            structured = False
        citations = []
        for annotation in message.get("annotations", []):
            citation = annotation.get("url_citation", {})
            if citation.get("url"):
                citations.append({"title": citation.get("title", citation["url"]), "url": citation["url"]})
        findings_value = parsed.get("findings", "")
        if not isinstance(findings_value, str):
            structured = False
        findings = findings_value.strip() if isinstance(findings_value, str) else ""
        limitations = parsed.get("limitations", [])
        if isinstance(limitations, str):
            limitations = [limitations] if limitations.strip() else []
        if not isinstance(limitations, list):
            limitations = ["research response had malformed limitations"]
            structured = False
        if not structured:
            findings = ""
            limitations = ["research response was malformed; required structured JSON was not returned"]
        resolved_citations = citations or parsed.get("citations", [])
        resolved_citations = resolved_citations if isinstance(resolved_citations, list) else []
        resolved_citations = [c for c in resolved_citations if isinstance(c, dict)
                              and isinstance(c.get("url"), str)
                              and c["url"].lower().startswith(("https://", "http://"))]
        no_evidence = not findings or not resolved_citations
        if no_evidence and not limitations:
            limitations = ["no usable cited evidence returned"]
        record.update({"status": "no_evidence" if no_evidence else "answered", "findings": findings,
                       "limitations": limitations, "citations": resolved_citations,
                       "no_evidence": no_evidence, "answer_turn": turn,
                       "usage": {"prompt_tokens": usage.get("prompt_tokens", 0),
                                 "completion_tokens": usage.get("completion_tokens", 0),
                                 "web_search_requests": int(tool_use.get("web_search_requests", 0) or 0)},
                       "cost_usd": round(float(meta.get("spend_usd", 0.0)) - spend_before, 12)})
    except CostAccountingError:
        raise
    except Exception as exc:
        record.update({"status": "error", "findings": "", "citations": [], "no_evidence": True,
                       "limitations": [f"research unavailable: {exc.__class__.__name__}"],
                       "error": exc.__class__.__name__, "cost_usd": round(float(meta.get("spend_usd", 0.0)) - spend_before, 12),
                       "answer_turn": turn})


def maybe_run_conversation(rb, meta, turn, conversations):
    if not meta.get("tests_run") or meta["tests_run"] % 32 != 0:
        return
    if conversations and conversations[-1].get("ordinary_exam_count") == meta["tests_run"]:
        return
    scenario = {"prompt": "Plan a handoff of order AL-204: Mira packs 12 units by 15:00 UTC; Ken verifies count and ships by 16:00 UTC.",
                "requirements": ["Mira packs 12 units", "packing deadline is 15:00 UTC",
                                 "Ken verifies the count", "shipping deadline is 16:00 UTC"]}
    def speaker(speaker_name, language, user):
        prompt = (ROOT / "prompts" / "conversation.md").read_text() + "\n\n" + language
        model = MODEL_A if speaker_name == "A" else MODEL_B
        text, usage = call(model, prompt, user, max_tokens=500, temperature=0.3, meta=meta)
        return {"content": text, "model": model, "usage": usage}
    def judge(artifact):
        raw, usage = call(MODEL_GRADER, (ROOT / "prompts" / "conversation_judge.md").read_text(),
                          json.dumps(artifact), max_tokens=700, temperature=0, meta=meta)
        match = re.search(r"\{.*\}", raw, re.S)
        try:
            result = json.loads(match.group(0)) if match else {"valid": False, "summary": "unparseable"}
        except json.JSONDecodeError:
            result = {"valid": False, "summary": "unparseable"}
        result["_receipt"] = {"model": MODEL_GRADER, "usage": usage}
        return result
    artifact = run_conversation(rb, scenario, speaker, judge, turn,
                                models={"A": MODEL_A, "B": MODEL_B, "judge": MODEL_GRADER})
    artifact["ordinary_exam_count"] = meta["tests_run"]
    conversations.append(artifact)


def publish_turn(state: TurnState) -> None:
    """Rebuild projections; an optional trace failure cannot cancel a real turn."""
    write_outbox(STATE / "collaboration-outbox.json", state.collaboration)
    save("public-collaboration.json", public_state(state.collaboration))
    write_viewer_state(state.conversation, state.rulebook, state.meta,
                       state.collaboration, state.conversations)
    if state.public_exam_progress is not None:
        try:
            publish_completed_snapshot(STATE / "public-exam-progress.json", state.public_exam_progress)
        except Exception as error:
            print(f"[PUBLIC EXAM] completed snapshot unavailable · {error.__class__.__name__}", flush=True)


def run(turns):
    with TurnStore(STATE).writer() as store:
        return _run_turns(turns, store)


def _run_turns(turns, store):
    state = store.load(TurnState(
        [], {"version": "0.0", "kernel_tokens": 0, "changes": 0,
             "next_id": 1, "rules": []},
        {"spend_usd": 0.0, "last_agent": None, "tests_run": 0, "started": now_iso()},
        empty_state(), [],
    ))
    conv, rb, meta = state.conversation, state.rulebook, state.meta
    collaboration, conversations = state.collaboration, state.conversations
    start_turn = state.next_turn
    ensure_structured_protocol_cutover(
        conv, rb, meta, activation_turn=start_turn - 1
    )
    configure_cost_receipt_ledger(STATE / COST_LEDGER_FILENAME, meta)
    # Projections can fail after a fully committed turn (with no redo left).
    # Repair them before cap checks or provider work on every runner entry.
    publish_turn(state)
    turn = start_turn - 1
    for turn in range(start_turn, start_turn + turns):
        if meta["spend_usd"] >= SPEND_CAP:
            print(f"SPEND CAP hit (${meta['spend_usd']:.2f}) — stopping.", flush=True)
            break
        consumed_notice = consume_notice(conv, turn)
        collaboration = import_inbox_spool(
            collaboration, STATE / "collaboration-inbox.json", turn=turn)
        save("collaboration.json", collaboration)
        process_one_research(collaboration, meta, turn)
        maybe_run_automatic_cleanup(conv, rb, meta, turn)
        if turn % TEST_EVERY == 0:
            completed_public_exam = test_turn(
                conv, rb, meta, turn,
                progress_path=STATE / "public-exam-progress.local.json",
            )
            maybe_run_conversation(rb, meta, turn, conversations)
        else:
            completed_public_exam = None
            agent_turn(conv, rb, meta, collaboration, turn)
        meta["last_completed_turn_at"] = now_iso()
        if completed_public_exam is not None:
            state.public_exam_progress = completed_public_exam
        state = TurnState(conv, rb, meta, collaboration, conversations, state.public_exam_progress, consumed_notice)
        store.commit(state)
        publish_turn(state)
    print(f"done. turns {start_turn}..{turn}  rules {len(rb['rules'])}  "
          f"spend ${meta['spend_usd']:.3f}", flush=True)


def archive(name):
    if not name or Path(name).name != name or name in {".", ".."}:
        raise ValueError("archive name must be one directory name")
    with TurnStore(STATE).writer() as store:
        # Recover first so no abandoned journal can resurrect archived work.
        store.load(TurnState([], {}, {}, {}, []))
        dest = store.archive(name)
        for pf in (ROOT / "prompts").glob("*.md"):
            shutil.copy(str(pf), str(dest / pf.name))
    print(f"archived state + prompt snapshot -> state/tuning-runs/{name}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", type=int, default=6)
    ap.add_argument("--recover", action="store_true", help="recover and rebuild saved state without a model turn")
    ap.add_argument("--archive", help="archive current state under this name and reset")
    args = ap.parse_args()
    if args.archive:
        archive(args.archive)
    else:
        run(0 if args.recover else args.turns)
