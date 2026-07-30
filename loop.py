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
    prompt_receipt_projection,
    prompt_request_projection,
    validate_action,
    validation_reason,
)
from project_lookup import is_project_question, project_lookup
from rulebook import (apply_typed_motion, language_payload, render_language,
                      render_legislature, score_judgment)
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
            out.append(
                f"[turn {e['turn']} — AUTHORITATIVE LIVE TEST RECEIPT | "
                f"payload: {e['payload']}]\n"
                f"original {e['orig_tokens']} tokens -> encoded {e['enc_tokens']} tokens "
                f"({e['token_delta_pct']:+d}%) | {score}\n"
                f"grader: {grader_loss}" + audit)
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
    request = build_legislative_request(
        role=agent,
        turn=turn,
        next_live_test_turn=next_test,
        rulebook=rb,
        latest_receipt=latest_post_state_receipt(conv),
        collaboration_input=collaboration_input,
    )
    prompt_request = prompt_request_projection(request)
    system = (
        f"{constitution}\n\n{role_prompt}\n\n"
        f"=== ADOPTED LANGUAGE ===\n{render_language(rb)}\n\n"
        f"=== COMPLETE LEGISLATURE ===\n{render_legislature(rb)}\n\n"
        f"=== AUTHORITATIVE CURRENT MACHINE STATE AND RECEIPT ===\n"
        f"{json.dumps(prompt_request, ensure_ascii=False, separators=(',', ':'))}"
    )
    user = (
        "=== RECENT EVENT WINDOW ===\n"
        + render_window(conv)
        + f"\n\nIt is turn {turn}. You are Agent {agent}. "
        "The required `deliberation` field is a concise public-facing summary "
        "of your conclusion, not private reasoning; never leave it empty. "
        "Return only the structured response required by the supplied schema."
    )
    return {
        "system": system,
        "user": user,
        "request_options": action_request_options(agent, rb),
        "canonical_request": request,
        "prompt_request": prompt_request,
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
    structured_action = None
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
            structured_action = validate_action(text, agent, rb)
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
    conv.append(
        {
            "turn": turn,
            "agent": agent,
            "type": "message",
            "content": structured_action.deliberation,
            "structured_action": structured_action.model_dump(mode="json"),
            "tokens": usage.get("completion_tokens", 0),
        }
    )
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


DOMAINS = ["logistics", "software operations", "event planning", "food service", "travel",
           "equipment maintenance", "publishing", "customer support", "farming",
           "construction", "lab work", "retail"]


def gen_payload(meta):
    """A fresh, never-seen test message — written blind: the generator sees neither the
    rulebook nor the conversation, so the exam can't be taught to (payloads were a fixed
    set of 13 files until test #24; those files are now the transfer-test battery)."""
    n = meta.get("tests_run", 0)
    kind = ("prose", "task", "data")[n % 3]
    domain = DOMAINS[(n // 3) % len(DOMAINS)]
    prompt = ((ROOT / "prompts" / "payloadgen.md").read_text()
              .replace("{CATEGORY}", kind).replace("{DOMAIN}", domain))
    for _ in range(2):
        raw, _ = call(MODEL_A, prompt, "Write the message now.",
                      max_tokens=2000, temperature=1.0, meta=meta)
        text, _, keyblock = raw.strip().strip('"').partition("===KEY===")
        text = text.strip().strip('"').strip()
        # the answer key is born with the exam, blind to everything downstream —
        # grading checks receipts against it instead of forming one holistic opinion
        key = normalize_answer_key(keyblock)
        if 200 <= len(text) <= 5000 and len(key) >= 6:
            return f"gen-{kind}-{domain.split()[0]}", text, key
    return None, None, None


def normalize_answer_key(raw):
    lines = raw if isinstance(raw, list) else str(raw).splitlines()
    return [re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", str(line)).strip()
            for line in lines
            if re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", str(line)).strip()]


def extract_answer_key(payload, meta):
    """Create the fixed exam key before encoding; failure makes the score invalid."""
    prompt = (ROOT / "prompts" / "answer_key.md").read_text()
    raw, _ = call(MODEL_GRADER, prompt, payload, max_tokens=1200, temperature=0, meta=meta)
    match = re.search(r"\[.*\]", raw, re.S)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return normalize_answer_key(parsed)
        except json.JSONDecodeError:
            pass
    return []


def test_turn(conv, rb, meta, turn):
    pname, payload, key = gen_payload(meta)
    if payload is None:  # generator failed twice — key the fixed payload before either agent sees it
        by_kind = {}
        for f in sorted((ROOT / "payloads").glob("*.txt")):
            by_kind.setdefault(f.name.split("-")[0], []).append(f)
        kinds = sorted(by_kind)  # interleave prose/task/data so no type dominates
        payloads = [ks[i] for i in range(max(len(v) for v in by_kind.values()))
                    for ks in (by_kind[k] for k in kinds) if i < len(ks)]
        p = payloads[meta.get("tests_run", 0) % len(payloads)]
        pname, payload = p.name, p.read_text().strip()
        key = extract_answer_key(payload, meta)
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
    grade_sys = (ROOT / "prompts" / "grader.md").read_text()
    if key:
        key_txt = "\n".join(f"{i + 1}. {k}" for i, k in enumerate(key))
        grade_user = f"ORIGINAL:\n{payload}\n\nANSWER KEY:\n{key_txt}\n\nDECODED:\n{decoded.strip()}"
        graded, _ = call(MODEL_GRADER, grade_sys, grade_user, max_tokens=1200, temperature=0, meta=meta)
        gm = re.search(r"\{.*\}", graded, re.S)
        try:
            g = json.loads(gm.group(0)) if gm else {}
        except json.JSONDecodeError:
            g = {}
    else:
        g = {}
    lost = str(g.get("lost", "answer key unavailable" if not key else "grader output unparseable"))[:300]
    audit = {}
    if key:
        scored = score_judgment(key, g)
        items = g.get("items", []) if scored["valid"] else []
        fidelity = scored["fidelity"]
        audit = {"key": key, "judge_valid": scored["valid"], "judge_reason": scored["reason"],
                 "survived": scored.get("survived", 0), "total": len(key),
                 "corrupted": [f"{i.get('n')}: {i.get('note', '')}" for i in items if i.get("verdict") == "CORRUPTED"],
                 "missing": [f"{i.get('n')}: {i.get('note', '')}" for i in items if i.get("verdict") == "MISSING"],
                 "invented": scored.get("invented", [])}
        if not scored["valid"]:
            lost = f"invalid judge output: {scored['reason']}"
    else:
        fidelity = None
        audit = {"key": [], "judge_valid": False, "judge_reason": "answer_key_unavailable",
                 "survived": 0, "total": 0, "corrupted": [], "missing": [], "invented": []}
    orig_t = token_count(payload, meta)
    enc_t = token_count(encoded.strip(), meta)
    delta = round((enc_t - orig_t) / orig_t * 100)
    meta["tests_run"] = meta.get("tests_run", 0) + 1
    event = {"turn": turn, "agent": "harness", "type": "test", "payload": pname,
             "original": payload, "orig_tokens": orig_t, "enc_tokens": enc_t,
             "token_delta_pct": delta, "fidelity": fidelity, "lost": lost,
             "encoded": encoded.strip(), "decoded": decoded.strip(), "tokens": enc_t,
             "decoder_model": MODEL_DECODER, "language_version": captured["version"],
             "language_hash": captured["hash"]}
    event.update(audit)
    conv.append(event)
    exams = meta.setdefault("corpus_exams", [])
    exams.append({"turn": turn, "language_version": captured["version"],
                  "language_hash": captured["hash"], "fidelity": fidelity,
                  "token_delta_pct": delta, "valid": fidelity is not None})
    meta["corpus_exams"] = exams[-500:]
    print(f"[t{turn} TEST] {pname}  {orig_t}->{enc_t}tok ({delta:+d}%)  fid {fidelity}  "
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
