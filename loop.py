#!/usr/bin/env python3
"""A Language All Their Own — the entire engine.

Two agents negotiate an AI-to-AI language; every rule survives (or dies by)
an encode/decode test against a fresh decoder. This file is deliberately all
the code there is: plumbing only, the LLMs do the language.
"""
import argparse
import copy
import json
import math
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from pydantic import ValidationError

from collaboration import (deliver_one, empty_state, escalate_lookup_to_ask,
                           import_inbox_spool, public_state, stable_record, write_outbox)
from conversation_exam import run_conversation
from legislative_protocol import (
    MAX_STRUCTURAL_RETRIES,
    PROTOCOL_VERSION,
    action_request_options,
    build_cutover_receipt,
    build_legislative_request,
    build_post_state_receipt,
    current_open_motion,
    derive_active_legislative_feedback,
    derive_semantic_fault_ledger,
    prompt_receipt_projection,
    prompt_request_projection,
    select_semantic_fault_for_turn,
    semantic_fault_feedback,
    validate_action,
    validate_action_with_deliberation_fallback,
    validation_reason,
)
from project_lookup import is_project_question, project_lookup
from rulebook import (_literal_set_survives, apply_typed_motion, language_payload,
                      render_language, render_legislature, score_judgment_v2)
from state_store import atomic_write_json, load_json

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_A = "deepseek/deepseek-v3.2"
MODEL_B = "moonshotai/kimi-k2.6"
MODEL_DECODER = "moonshotai/kimi-k2.6"  # a FOREIGN decoder: the stranger must not share the negotiators' weights
MODEL_GRADER = "deepseek/deepseek-v3.2"

TEST_EVERY = 3      # every Nth turn is a test turn
WINDOW = 30         # conversation events each agent sees
MAX_TEST_AUDIT_CATEGORY_CHARS = 320
MAX_TEST_GRADER_LOSS_CHARS = 600
SPEND_CAP = 25.00   # dollars, hard stop across all runs — anomaly tripwire, ~50 days at gloves-off burn
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
         request_options=None):
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
            r = requests.post(API_URL, headers=headers, json=body, timeout=180)
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
        usage = d.get("usage", {})
        if meta is not None:
            record_provider_cost(meta, usage, response_id=d.get("id"))
        return d["choices"][0]["message"]["content"] or "", usage
    raise RuntimeError("api: retries exhausted")


def token_count(text, meta):
    """Exact token size of standalone text: probe call, prompt_tokens minus overhead.
    Probe-based so reasoning/completion accounting can never contaminate it."""
    global _probe_overhead
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


def write_viewer_state(conv, rb, meta, collaboration=None, conversations=None):
    # Protocol cutover receipts are canonical harness bookkeeping, not public
    # conversation events. Keep them in the persisted source log and out of the
    # unchanged viewer renderer, which has no cutover event presentation.
    public_conversation = [
        event for event in conv if event.get("type") != "protocol_cutover"
    ]
    (ROOT / "viewer" / "state.js").write_text(
        "window.STATE = " + json.dumps(
            {"conversation": public_conversation, "rulebook": rb,
             "collaboration": public_state(collaboration or empty_state()),
             "conversations": conversations or [],
             "meta": {"spend_usd": meta.get("spend_usd", 0), "model": MODEL_A,
                      "spend_usd_historical_estimate":
                          meta.get("spend_usd_historical_estimate"),
                      "spend_usd_provider_exact_since_cutover":
                          meta.get("spend_usd_provider_exact_since_cutover"),
                      "cost_accounting_basis": meta.get("cost_accounting_basis"),
                      "updated": now_iso(), "run": meta.get("run", "local")}}) + ";\n")


def next_legislative_actor(meta):
    return "B" if meta.get("last_agent") == "A" else "A"


def latest_post_state_receipt(conv):
    for event in reversed(conv):
        if isinstance(event.get("post_state_receipt"), dict):
            return event["post_state_receipt"]
        if event.get("type") == "protocol_cutover" and isinstance(
            event.get("state_receipt"), dict
        ):
            return event["state_receipt"]
    return None


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


def assemble_legislative_prompt(
    conv,
    rb,
    *,
    turn,
    agent,
    collaboration_input,
):
    """Assemble the one deterministic model-facing legislative projection."""
    role_prompt = (ROOT / "prompts" / f"agent_{agent.lower()}.md").read_text()
    constitution = (ROOT / "prompts" / "constitution.md").read_text()
    next_test = ((turn // TEST_EVERY) + 1) * TEST_EVERY
    active_feedback = derive_active_legislative_feedback(
        conv, current_open_motion(rb)
    )
    semantic_fault = select_semantic_fault_for_turn(
        derive_semantic_fault_ledger(conv),
        role=agent,
        open_motion=current_open_motion(rb),
    )
    fault_feedback = semantic_fault_feedback(semantic_fault)
    required_fault_token = (
        semantic_fault.fault_token
        if semantic_fault is not None
        and semantic_fault.status == "UNRESOLVED"
        and agent == "A"
        and current_open_motion(rb) is None
        else None
    )
    request = build_legislative_request(
        role=agent,
        turn=turn,
        next_live_test_turn=next_test,
        rulebook=rb,
        latest_receipt=latest_post_state_receipt(conv),
        active_legislative_feedback=active_feedback,
        semantic_fault_feedback=fault_feedback,
        collaboration_input=collaboration_input,
    )
    open_motion = request.current_state.open_motion
    target = (
        open_motion.target_rule_id
        if open_motion is not None
        else "the authoritative current state"
    )
    audit_focus = (
        f"open {target}"
        if open_motion is not None
        else target
    )
    public_stem = "Public audit:" if agent == "B" else "Public proposal:"
    example_deliberation = (
        f"Public audit: {target} needs a focused verification before adoption."
        if agent == "B"
        else "Public proposal: the current idea needs one focused revision."
    )
    if agent == "B":
        example_motion = (
            {
                "kind": "REQUEST",
                "target_rule_id": target,
                "focus": "Verify one exact boundary before adoption.",
            }
            if open_motion is not None
            else None
        )
    else:
        example_motion = (
            {
                "kind": "REVISE",
                "target_rule_id": target,
                "text": "Preserve the idea with one exact boundary.",
            }
            if open_motion is not None
            else {
                "kind": "PROPOSE",
                "text": "Use one exact marker for one repeated meaning.",
            }
        )
    example = json.dumps(
        {
            "deliberation": example_deliberation,
            "motion": example_motion,
            "fault_response": (
                {
                    "status": "REPAIR_PROPOSED",
                    "fault_token": required_fault_token,
                }
                if required_fault_token is not None
                else None
            ),
            "measurements": [],
            "requests": [],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    output_contract = (
        "=== MANDATORY PUBLIC OUTPUT CONTRACT ===\n"
        "`deliberation` is required public output, not private reasoning. It "
        f"must be a complete sentence beginning exactly \"{public_stem}\". "
        "Return the exact object key and value types required by the schema; "
        "never substitute prose strings or differently named request fields. "
        f"Valid non-operative shape example: {example}\n"
        "Never return an empty, whitespace-only, or punctuation-only "
        "`deliberation` value.\n"
        + (
            "The supplied abstract semantic fault is mandatory now. Return "
            "one focused `PROPOSE` motion and the exact schema-bound "
            "`fault_response`; prompt presence or free prose is not attention. "
            "Generalize the repair from its invariant and do not seek the "
            "private benchmark source.\n\n"
            if required_fault_token is not None
            else "\n"
        )
    )
    prompt_request = prompt_request_projection(request)
    system = (
        f"{output_contract}{constitution}\n\n{role_prompt}\n\n"
        f"=== ADOPTED LANGUAGE ===\n{render_language(rb)}\n\n"
        f"=== COMPLETE LEGISLATURE ===\n{render_legislature(rb)}\n\n"
        f"=== AUTHORITATIVE CURRENT MACHINE STATE AND RECEIPT ===\n"
        f"{json.dumps(prompt_request, ensure_ascii=False, separators=(',', ':'))}"
    )
    user = (
        f"It is turn {turn}. You are Agent B. Audit only {audit_focus} using "
        "the complete legislature, authoritative current state, and "
        "collaboration input above. Set `deliberation` to one public sentence "
        "beginning exactly \"Public audit:\". Return only the required "
        "structured response."
        if agent == "B"
        else (
            f"It is turn {turn}. You are Agent A. Use the complete legislature, "
            "authoritative current state, and collaboration input above. Set "
            "`deliberation` to one public sentence beginning exactly "
            "\"Public proposal:\". Return only the required structured response."
        )
    )
    return {
        "system": system,
        "user": user,
        "request_options": action_request_options(
            agent, rb, required_fault_token=required_fault_token
        ),
        "canonical_request": request,
        "prompt_request": prompt_request,
        "required_fault_token": required_fault_token,
        "total_chars": len(system) + len(user),
    }


def agent_turn(conv, rb, meta, collaboration, turn):
    agent = next_legislative_actor(meta)
    model = MODEL_A if agent == "A" else MODEL_B
    collaboration_before_delivery = copy.deepcopy(collaboration)
    delivery = (deliver_one(collaboration, "RESEARCH", agent, turn) or
                deliver_one(collaboration, "ASK", agent, turn) or
                deliver_one(collaboration, "SUGGESTION", agent, turn))
    assembled = assemble_legislative_prompt(
        conv,
        rb,
        turn=turn,
        agent=agent,
        collaboration_input=delivery,
    )
    system = assembled["system"]
    base_user = assembled["user"]
    request_options = assembled["request_options"]
    required_fault_token = assembled["required_fault_token"]
    structured_action = None
    deliberation_fallback = None
    usage = {}
    last_structural_reason = "unknown structural validation error"
    attempts = 0
    for attempts in range(1, MAX_STRUCTURAL_RETRIES + 2):
        retry_note = (
            ""
            if attempts == 1
            else "\n\nYour previous response failed local structural validation. "
            "Regenerate from the unchanged authoritative state. "
            f"Error: {last_structural_reason}"
        )
        text, usage = call(
            model,
            system,
            base_user + retry_note,
            max_tokens=2000,
            temperature=AGENT_TEMP,
            meta=meta,
            request_options=request_options,
        )
        try:
            structured_action, deliberation_fallback = (
                validate_action_with_deliberation_fallback(text, agent, rb)
                if required_fault_token is None
                else validate_action_with_deliberation_fallback(
                    text,
                    agent,
                    rb,
                    required_fault_token=required_fault_token,
                )
            )
            break
        except ValidationError as exc:
            last_structural_reason = validation_reason(exc)

    if structured_action is None:
        collaboration.clear()
        collaboration.update(collaboration_before_delivery)
        receipt = build_post_state_receipt(
            turn=turn,
            role=agent,
            action=None,
            result="structural_failure",
            reason=f"structural_validation_exhausted: {last_structural_reason}",
            before_rulebook=rb,
            after_rulebook=rb,
            next_actor=agent,
            attempts=attempts,
        )
        conv.append(
            {
                "turn": turn,
                "agent": "harness",
                "type": "legislature",
                "protocol": PROTOCOL_VERSION,
                # Compatibility projection for the unchanged public viewer.
                # The full authoritative result remains post_state_receipt.
                "motion_receipt": {
                    "accepted": False,
                    "reason": "structural_validation_exhausted",
                    "agent": agent,
                    "verb": None,
                    "rule_id": None,
                    "changed": False,
                    "line": None,
                },
                "post_state_receipt": receipt.model_dump(mode="json"),
            }
        )
        print(
            f"[t{turn} {agent}] structural validation exhausted; same actor retained  "
            f"${meta['spend_usd']:.3f}",
            flush=True,
        )
        return "structural_failure"

    before_rulebook = copy.deepcopy(rb)
    message_event = {
        "turn": turn,
        "agent": agent,
        "type": "message",
        "content": structured_action.deliberation,
        "structured_action": structured_action.model_dump(mode="json"),
        "tokens": usage.get("completion_tokens", 0),
    }
    if deliberation_fallback is not None:
        message_event["deliberation_fallback"] = deliberation_fallback
    conv.append(message_event)
    for measurement in structured_action.measurements:
        probe_text = measurement.text
        n = token_count(probe_text, meta)
        conv.append({"turn": turn, "agent": "harness", "type": "measure",
                     "text": probe_text[:120], "tokens": n})
        print(f"[t{turn} MEASURE] \"{probe_text[:40]}\" = {n}tok", flush=True)
    motion_receipt = apply_typed_motion(
        structured_action.motion,
        rb,
        turn,
        agent,
        structured_action.deliberation[:280],
    )
    if motion_receipt.changed:
        rb["version"] = f"0.{rb['changes'] + 1}"
        rb["changes"] += 1
        rb["kernel_tokens"] = token_count(render_language(rb), meta)
    result = "accepted" if motion_receipt.accepted else "rejected"
    next_actor = "A" if agent == "B" else "B"
    receipt = build_post_state_receipt(
        turn=turn,
        role=agent,
        action=structured_action,
        result=result,
        reason=motion_receipt.reason,
        before_rulebook=before_rulebook,
        after_rulebook=rb,
        next_actor=next_actor,
        attempts=attempts,
    )
    conv.append(
        {
            "turn": turn,
            "agent": "harness",
            "type": "legislature",
            "protocol": PROTOCOL_VERSION,
            "motion_receipt": motion_receipt.dict(),
            "post_state_receipt": receipt.model_dump(mode="json"),
        }
    )
    if delivery and delivery.get("kind") == "SUGGESTION":
        suggestion = next((row for row in collaboration.get("suggestions", [])
                           if row.get("id") == delivery.get("id")), None)
        if suggestion:
            suggestion["status"] = "acted" if motion_receipt.changed else "no_action"
            suggestion["outcome"] = motion_receipt.reason
            suggestion["outcome_turn"] = turn
    for typed_request in structured_action.requests:
        kind = typed_request.kind
        question = typed_request.question
        if question:
            record_id = f"{kind.lower()}-{turn}-{agent.lower()}"
            bucket = "research" if kind in {"LOOKUP", "RESEARCH"} else "asks"
            if not any(r.get("id") == record_id for r in collaboration[bucket]):
                record = stable_record(kind, agent, question, record_id)
                record["request_turn"] = turn
                collaboration[bucket].append(record)
    meta["last_agent"] = agent
    print(f"[t{turn} {agent}] {usage.get('completion_tokens', 0)}tok  "
          f"rules:{len(rb['rules'])}  ${meta['spend_usd']:.3f}", flush=True)
    return result


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


def select_benchmark(meta, suite=None):
    """Return the next benchmark without advancing its durable cursor."""
    suite = suite or load_benchmark_suite()
    state = meta.get("benchmark_suite")
    if state is None or state.get("version") != suite["version"]:
        state = {"version": suite["version"], "next_index": 0, "cycle": 1}
        meta["benchmark_suite"] = state
    index = state.get("next_index")
    cycle = state.get("cycle")
    if not isinstance(index, int) or not 0 <= index < len(suite["benchmarks"]):
        raise ValueError("benchmark_cursor_invalid")
    if not isinstance(cycle, int) or cycle < 1:
        raise ValueError("benchmark_cycle_invalid")
    return copy.deepcopy(suite["benchmarks"][index]), cycle


def advance_benchmark(meta, benchmark, suite=None):
    """Advance exactly once after an exam receipt has been constructed."""
    suite = suite or load_benchmark_suite()
    state = meta["benchmark_suite"]
    index = state["next_index"]
    if suite["benchmarks"][index]["id"] != benchmark["id"]:
        raise ValueError("benchmark_cursor_drift")
    next_index = (index + 1) % len(suite["benchmarks"])
    state["next_index"] = next_index
    if next_index == 0:
        state["cycle"] += 1


def previous_benchmark_result(meta, benchmark):
    """Return only a prior valid Scoring V2 result; V1 is never a comparison baseline."""
    return copy.deepcopy(meta.get("benchmark_results_v2", {}).get(benchmark["id"]))


def normalize_answer_key(raw):
    lines = raw if isinstance(raw, list) else str(raw).splitlines()
    return [re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", str(line)).strip()
            for line in lines
            if re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", str(line)).strip()]


def _numbered_decoded(decoded):
    """Return a stable one-based view of decoded lines for the judge."""
    lines = decoded.splitlines()
    return "\n".join(
        f"{line_number:04d}: {line}"
        for line_number, line in enumerate(lines, start=1)
    )


def _grader_answer_key(answer_key, decoded):
    """Expose exact-literal requirements and deterministic decode preflight."""
    decoded_lines = decoded.splitlines()
    projected = []
    for atom in answer_key:
        literal_sets = copy.deepcopy(atom["literal_sets"])
        projected.append({
            "id": atom["id"],
            "meaning": atom["meaning"],
            "literal_sets": literal_sets,
            "missing_literal_sets": [
                alternatives for alternatives in literal_sets
                if not _literal_set_survives(decoded, alternatives)
            ],
            "literal_set_lines": [
                [
                    line_number
                    for line_number, line in enumerate(decoded_lines, start=1)
                    if _literal_set_survives(line, alternatives)
                ]
                for alternatives in literal_sets
            ],
        })
    return projected


def _materialize_grader_evidence(grade, decoded):
    """Resolve judge-selected line ranges into exact spans owned by the harness."""
    if not isinstance(grade, dict):
        return grade, None
    items = grade.get("items")
    inventions = grade.get("inventions")
    if not isinstance(items, list) or not isinstance(inventions, list):
        return grade, None

    decoded_lines = decoded.splitlines()
    materialized = copy.deepcopy(grade)

    def resolve(entry, *, identity, missing_allowed):
        if not isinstance(entry, dict):
            return f"invalid_evidence_line_range:{identity}"
        evidence_lines = entry.pop("evidence_lines", None)
        if missing_allowed and evidence_lines == []:
            entry["evidence"] = ""
            return None
        if (
            not isinstance(evidence_lines, list)
            or len(evidence_lines) != 2
            or any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in evidence_lines
            )
        ):
            return f"invalid_evidence_line_range:{identity}"
        start, end = evidence_lines
        if start < 1 or end < start or end > len(decoded_lines):
            return f"invalid_evidence_line_range:{identity}"
        entry["evidence"] = "\n".join(decoded_lines[start - 1:end])
        return None

    for item in materialized["items"]:
        identity = item.get("id", "unknown") if isinstance(item, dict) else "unknown"
        missing_allowed = isinstance(item, dict) and item.get("verdict") == "MISSING"
        reason = resolve(item, identity=identity, missing_allowed=missing_allowed)
        if reason:
            return grade, reason
    for index, invention in enumerate(materialized["inventions"], start=1):
        reason = resolve(
            invention,
            identity=f"invention-{index}",
            missing_allowed=False,
        )
        if reason:
            return grade, reason
    return materialized, None


def _invalid_judge_diagnostic(grade, reason):
    """Retain only the rejected reference needed to explain an invalid result."""
    diagnostic = {"reason": reason}
    atom_id = reason.split(":", 1)[1] if ":" in reason else None
    items = grade.get("items") if isinstance(grade, dict) else None
    if atom_id and isinstance(items, list):
        item = next(
            (
                candidate for candidate in items
                if isinstance(candidate, dict) and candidate.get("id") == atom_id
            ),
            None,
        )
        if item:
            diagnostic.update({
                "atom_id": atom_id,
                "verdict": item.get("verdict"),
                "evidence_lines": copy.deepcopy(item.get("evidence_lines")),
            })
    return diagnostic


def test_turn(conv, rb, meta, turn):
    suite = load_benchmark_suite()
    benchmark, benchmark_cycle = select_benchmark(meta, suite)
    pname = f"{benchmark['id']} · {benchmark['name']}"
    payload = benchmark["original"]
    key = copy.deepcopy(benchmark["answer_key"])
    previous = previous_benchmark_result(meta, benchmark)
    captured = language_payload(rb)
    rbook = render_language(rb)
    enc_sys = ("You are the encoder. Encode the message below into the project language "
               "using ONLY this rulebook. Where the rulebook is silent, fall back to plain "
               "English for that part. Output ONLY the encoded message, nothing else.\n\n" + rbook)
    encoded, _ = call(MODEL_A, enc_sys, payload, max_tokens=4000, temperature=0.3, meta=meta)
    dec_sys = ("You are a fresh agent. You have never seen any prior conversation. Below is the "
               "complete rulebook of a constructed language. Decode the message you receive: "
               "reconstruct the original content as faithfully as you can. Do not invent anything "
               "the message does not encode. Output ONLY the reconstruction.\n\n" + rbook)
    decoded, _ = call(MODEL_DECODER, dec_sys, encoded.strip(), max_tokens=4000, temperature=0.1, meta=meta)
    orig_t = token_count(payload, meta)
    enc_t = token_count(encoded.strip(), meta)
    delta = round((enc_t - orig_t) / orig_t * 100)
    savings_pct = -delta
    grade_sys = (ROOT / "prompts" / "grader_v2.md").read_text()
    if key:
        numbered_decoded = _numbered_decoded(decoded.strip())
        key_txt = json.dumps(_grader_answer_key(key, decoded.strip()), ensure_ascii=False)
        grade_user = (
            f"ORIGINAL:\n{payload}\n\nATOMIC ANSWER KEY:\n{key_txt}"
            f"\n\nNUMBERED DECODED:\n{numbered_decoded}"
        )
        graded, _ = call(MODEL_GRADER, grade_sys, grade_user, max_tokens=4000, temperature=0, meta=meta)
        gm = re.search(r"\{.*\}", graded, re.S)
        try:
            g = json.loads(gm.group(0)) if gm else {}
        except json.JSONDecodeError:
            g = {}
    else:
        g = {}
    audit = {}
    if key:
        materialized_grade, evidence_reason = _materialize_grader_evidence(
            g, decoded.strip()
        )
        if evidence_reason:
            scored = {
                "valid": False,
                "status": "INVALID JUDGE RESULT",
                "reason": evidence_reason,
                "scoring_version": "v2",
            }
        else:
            scored = score_judgment_v2(
                key, materialized_grade, decoded.strip(), savings_pct
            )
        audit = {
            "judge_valid": scored["valid"], "judge_status": scored["status"],
            "judge_reason": scored["reason"], "atom_results": scored.get("items", []),
            "survived": scored.get("survived"), "total": scored.get("total", len(key)),
            "meaning_pass": scored.get("meaning_pass"),
            "compression_success": scored.get("compression_success"),
            "semantic_coverage_pct": scored.get("semantic_coverage_pct"),
            "critical_failures": scored.get("critical_failures", []),
            "inventions": scored.get("inventions", []),
        }
        if not scored["valid"]:
            audit["judge_diagnostic"] = _invalid_judge_diagnostic(
                g, scored["reason"]
            )
    else:
        scored = {"valid": False, "status": "INVALID JUDGE RESULT", "reason": "answer_key_unavailable"}
        audit = {"judge_valid": False, "judge_status": scored["status"],
                 "judge_reason": scored["reason"], "atom_results": [], "survived": None,
                 "total": 0, "meaning_pass": None, "compression_success": None,
                 "semantic_coverage_pct": None, "critical_failures": [], "inventions": []}
    meta["tests_run"] = meta.get("tests_run", 0) + 1
    event = {"turn": turn, "agent": "harness", "type": "test", "payload": pname,
             "original": payload, "orig_tokens": orig_t, "enc_tokens": enc_t,
             "token_delta_pct": delta, "message_body_savings_pct": savings_pct,
             "encoded": encoded.strip(), "decoded": decoded.strip(), "tokens": enc_t,
             "decoder_model": MODEL_DECODER, "language_version": captured["version"],
             "language_hash": captured["hash"], "era": "benchmark-v2",
             "scoring_version": "v2",
             "benchmark_id": benchmark["id"], "benchmark_name": benchmark["name"],
             "benchmark_version": suite["version"], "benchmark_cycle": benchmark_cycle,
             "benchmark_source_turn": benchmark["source_turn"],
             "answer_key": [{"id": atom["id"], "meaning": atom["meaning"],
                              "critical": atom["critical"]} for atom in key],
             "prior_valid_v2_turn": previous.get("turn") if previous else None}
    event.update(audit)
    conv.append(event)
    exams = meta.setdefault("corpus_exams", [])
    exams.append({"turn": turn, "language_version": captured["version"],
                  "language_hash": captured["hash"], "scoring_version": "v2",
                  "meaning_pass": audit["meaning_pass"],
                  "compression_success": audit["compression_success"],
                  "semantic_coverage_pct": audit["semantic_coverage_pct"],
                  "critical_failures": copy.deepcopy(audit["critical_failures"]),
                  "inventions": copy.deepcopy(audit["inventions"]),
                  "message_body_savings_pct": savings_pct,
                  "token_delta_pct": delta, "valid": scored["valid"],
                  "judge_status": audit["judge_status"],
                  "era": "benchmark-v2", "benchmark_id": benchmark["id"],
                  "benchmark_name": benchmark["name"],
                  "benchmark_version": suite["version"],
                  "benchmark_cycle": benchmark_cycle,
                  "prior_valid_v2_turn": previous.get("turn") if previous else None})
    meta["corpus_exams"] = exams[-500:]
    if scored["valid"]:
        meta.setdefault("benchmark_results_v2", {})[benchmark["id"]] = {
            "turn": turn, "meaning_pass": audit["meaning_pass"],
            "compression_success": audit["compression_success"],
            "semantic_coverage_pct": audit["semantic_coverage_pct"],
            "critical_failures": copy.deepcopy(audit["critical_failures"]),
            "inventions": copy.deepcopy(audit["inventions"]),
            "message_body_savings_pct": savings_pct,
            "language_version": captured["version"], "language_hash": captured["hash"],
        }
    advance_benchmark(meta, benchmark, suite)
    print(f"[t{turn} TEST] {pname}  {orig_t}->{enc_t}tok ({delta:+d}%)  "
          f"{audit['judge_status']} coverage {audit['semantic_coverage_pct']}  "
          f"${meta['spend_usd']:.3f}", flush=True)


def consume_notice(conv, turn):
    """Notice inbox: if state/pending-notice.txt exists, deliver it as a harness notice
    this turn and remove the file. Lets notices travel via git without racing the
    VPS's own state commits (a direct conversation.json edit would)."""
    f = STATE / "pending-notice.txt"
    if not f.exists():
        return
    text = f.read_text().strip()
    if text:
        conv.append({"turn": turn, "agent": "harness", "type": "notice", "content": text})
        print(f"[t{turn} NOTICE] delivered ({len(text)} chars)", flush=True)
    f.unlink()


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


def run(turns):
    STATE.mkdir(exist_ok=True)
    conv = load("conversation.json", [])
    rb = load("rulebook.json", {"version": "0.0", "kernel_tokens": 0, "changes": 0,
                                "next_id": 1, "rules": []})
    meta = load("meta.json", {"spend_usd": 0.0, "last_agent": None, "tests_run": 0,
                              "started": now_iso()})
    collaboration = load("collaboration.json", empty_state())
    conversations = load("conversations.json", [])
    start_turn = (conv[-1]["turn"] + 1) if conv else 1
    ensure_structured_protocol_cutover(
        conv, rb, meta, activation_turn=start_turn - 1
    )
    configure_cost_receipt_ledger(STATE / COST_LEDGER_FILENAME, meta)
    for turn in range(start_turn, start_turn + turns):
        if meta["spend_usd"] >= SPEND_CAP:
            print(f"SPEND CAP hit (${meta['spend_usd']:.2f}) — stopping.", flush=True)
            break
        consume_notice(conv, turn)
        collaboration = import_inbox_spool(
            collaboration, STATE / "collaboration-inbox.json", turn=turn)
        save("collaboration.json", collaboration)
        process_one_research(collaboration, meta, turn)
        if turn % TEST_EVERY == 0:
            test_turn(conv, rb, meta, turn)
            maybe_run_conversation(rb, meta, turn, conversations)
        else:
            agent_turn(conv, rb, meta, collaboration, turn)
        save("conversation.json", conv)
        save("rulebook.json", rb)
        save("meta.json", meta)
        save("collaboration.json", collaboration)
        write_outbox(STATE / "collaboration-outbox.json", collaboration)
        save("public-collaboration.json", public_state(collaboration))
        save("conversations.json", conversations)
        write_viewer_state(conv, rb, meta, collaboration, conversations)
    print(f"done. turns {start_turn}..{turn}  rules {len(rb['rules'])}  "
          f"spend ${meta['spend_usd']:.3f}", flush=True)


def archive(name):
    dest = STATE / "tuning-runs" / name
    dest.mkdir(parents=True, exist_ok=True)
    for f in ("conversation.json", "rulebook.json", "meta.json", COST_LEDGER_FILENAME):
        if (STATE / f).exists():
            shutil.move(str(STATE / f), str(dest / f))
    for pf in (ROOT / "prompts").glob("*.md"):
        shutil.copy(str(pf), str(dest / pf.name))
    print(f"archived state + prompt snapshot -> state/tuning-runs/{name}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", type=int, default=6)
    ap.add_argument("--archive", help="archive current state under this name and reset")
    args = ap.parse_args()
    if args.archive:
        archive(args.archive)
    else:
        run(args.turns)
