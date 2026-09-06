"""Public snapshots derived from one completed experiment state.

write_snapshot owns sanitization, current metrics, compact startup, preview and
full archive. These are rebuildable projections, never canonical inputs. Startup
is capped at 2 KB; full rule text and history load asynchronously.
"""
from __future__ import annotations
import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path
from collaboration import public_state, empty_state
from legislative_protocol import current_open_motion
from rulebook import language_payload, render_language
from state_store import atomic_write_json, load_json
from turn_store import TurnState

@dataclass(frozen=True)
class PublicPolicy:
    spend_cap: float
    test_every: int
    cleanup_growth_percent: int
    model: str

def _strict_scoring_success(event):
    return (
        event.get("scoring_version") == "v2"
        and event.get("judge_valid") is True
        and event.get("meaning_pass") is True
        and event.get("compression_success") is True
    )


def _public_agent_c_state(rb, meta, growth_percent=10):
    """Project the bounded, non-operative Agent C cleanup status."""
    current_tokens = rb.get("kernel_tokens")
    if isinstance(current_tokens, bool) or not isinstance(current_tokens, int):
        current_tokens = 0
    cleanup = meta.get("automatic_cleanup")
    cleanup = cleanup if isinstance(cleanup, dict) else {}
    baseline_tokens = cleanup.get("baseline_tokens")
    if isinstance(baseline_tokens, bool) or not isinstance(baseline_tokens, int):
        baseline_tokens = current_tokens
    if baseline_tokens > 0:
        threshold_tokens = (
            baseline_tokens * (100 + growth_percent) + 99
        ) // 100
        growth_pct = round(
            (current_tokens - baseline_tokens) / baseline_tokens * 100, 1
        )
        progress_pct = round(max(0.0, min(100.0, growth_pct * 10)), 1)
    else:
        threshold_tokens = 0
        growth_pct = 0.0
        progress_pct = 0.0

    last_status = cleanup.get("last_status")
    if last_status not in {"armed", "failed", "quarantined", "applied"}:
        last_status = None
    open_motion = current_open_motion(rb)
    blocker = None
    if last_status == "quarantined":
        public_state = "quarantined"
        quarantine = cleanup.get("quarantine")
        if isinstance(quarantine, dict) and quarantine.get("reason") in {
            "structural_output", "invalid_advisory"
        }:
            blocker = quarantine["reason"]
    elif baseline_tokens <= 0 or current_tokens < threshold_tokens:
        public_state = "growing"
    elif open_motion is not None:
        public_state = "blocked_motion"
        blocker = open_motion.target_rule_id
    elif (
        last_status == "failed"
        and cleanup.get("last_attempt_language_hash") == language_payload(rb)["hash"]
    ):
        public_state = "blocked_attempt"
        blocker = "prior_failure_same_language"
    else:
        public_state = "eligible"
    last_attempt_turn = cleanup.get("last_attempt_turn")
    if isinstance(last_attempt_turn, bool) or not isinstance(last_attempt_turn, int):
        last_attempt_turn = None
    return {
        "state": public_state,
        "current_tokens": current_tokens,
        "baseline_tokens": baseline_tokens,
        "threshold_tokens": threshold_tokens,
        "growth_pct": growth_pct,
        "trigger_pct": growth_percent,
        "progress_pct": progress_pct,
        "blocker": blocker,
        "last_attempt_turn": last_attempt_turn,
        "last_status": last_status,
    }


def _public_runtime_state(turn, meta, rb, policy):
    agent_c = _public_agent_c_state(rb, meta, policy.cleanup_growth_percent)
    if float(meta.get("spend_usd", 0.0)) >= policy.spend_cap:
        return {
            "status": "paused",
            "turn": turn,
            "message": (
                f"Experiment paused at turn {turn}. No new turn or exam is running. "
                "The public record remains available."
            ),
            "next_exam_turn": None,
            "next_conversation_turn": None,
            "agent_c": agent_c,
        }
    next_exam_turn = turn + (policy.test_every - (turn % policy.test_every))
    tests_run = meta.get("tests_run")
    next_conversation_turn = None
    if isinstance(tests_run, int) and not isinstance(tests_run, bool):
        exams_remaining = 32 - (tests_run % 32)
        next_conversation_turn = next_exam_turn + (exams_remaining - 1) * policy.test_every
    return {
        "status": "active",
        "turn": turn,
        "message": "The experiment is active.",
        "next_exam_turn": next_exam_turn,
        "next_conversation_turn": next_conversation_turn,
        "agent_c": agent_c,
    }


def _public_cleanup_event(event):
    """Whitelist the bounded cleanup receipt safe for the public viewer."""
    public = {
        key: copy.deepcopy(event[key])
        for key in (
            "turn", "agent", "type", "status", "failure_class",
            "source_tokens", "candidate_tokens", "applied_tokens",
            "reduction_pct", "run_spend_usd",
        )
        if key in event
    }
    public["rounds"] = []
    for round_item in event.get("rounds", []):
        if not isinstance(round_item, dict):
            continue
        public_round = {
            key: copy.deepcopy(round_item[key])
            for key in (
                "round", "b_verdict", "candidate_tokens", "reduction_pct",
                "candidate_changed_from_previous", "finding_counts",
            )
            if key in round_item
        }
        public["rounds"].append(public_round)
    return public


def write_snapshot(state: TurnState, root: Path, *, updated: str | None, policy: PublicPolicy) -> None:
    """Write matching current/public archive views without mutating canonical state."""
    conv, rb, meta = state.conversation, state.rulebook, state.meta
    collaboration, conversations = state.collaboration, state.conversations
    # Protocol cutover receipts are canonical harness bookkeeping, not public
    # conversation events. Keep them in the persisted source log and out of the
    # unchanged viewer renderer, which has no cutover event presentation.
    public_conversation = []
    for event in conv:
        if event.get("type") == "protocol_cutover":
            continue
        public_conversation.append(
            _public_cleanup_event(event)
            if event.get("type") == "cleanup"
            else event
        )
    tests = [event for event in public_conversation if event.get("type") == "test"]
    latest_valid_v2 = next(
        (
            event
            for event in reversed(tests)
            if event.get("scoring_version") == "v2"
            and event.get("judge_valid") is True
        ),
        None,
    )
    savings = [event.get("message_body_savings_pct") for event in tests
               if _strict_scoring_success(event)
               and isinstance(event.get("message_body_savings_pct"), (int, float))
               and not isinstance(event.get("message_body_savings_pct"), bool)
               and math.isfinite(event["message_body_savings_pct"])]
    best_savings = max(savings) if savings else None
    revision_parts = str(rb.get("version", "0.0")).split(".", 1)
    revisions = revision_parts[1] if len(revision_parts) == 2 else "0"
    turn = public_conversation[-1].get("turn", 0) if public_conversation else 0
    runtime = _public_runtime_state(turn, meta, rb, policy)
    if isinstance(meta.get("runtime_models"), dict):
        runtime["models"] = {role: meta["runtime_models"].get(role) for role in ("A", "B", "C")}
        runtime["reasoning"] = {role: meta.get("runtime_reasoning", {}).get(role) for role in ("A", "C")}
    runtime_path = root / "state" / "public-runtime.json"
    runtime_path.parent.mkdir(exist_ok=True)
    atomic_write_json(runtime_path, runtime)
    language = language_payload(rb)
    public_language = {
        "version": language["version"],
        "hash": language["hash"],
        "rules": language["rules"],
        "text": render_language(rb),
    }
    atomic_write_json(root / "state" / "public-language.json", public_language)
    notes = load_json(root / "notes.json", [])
    adopted_count = sum(rule.get("status") == "adopted" for rule in rb.get("rules", []))
    pct = lambda value: ("+" if value > 0 else "") + f"{value}%"
    latest_conversation = (conversations or [])[-1] if conversations else None
    conversation_judgment = (
        latest_conversation.get("judgment", {}) if latest_conversation else {}
    )
    conversation_rows = conversation_judgment.get("requirements", [])
    conversation_passes = sum(
        row.get("pass") is True for row in conversation_rows if isinstance(row, dict)
    )
    conversation_metric = (
        f"{conversation_passes} / {len(conversation_rows)} pass"
        if conversation_judgment.get("valid") is True and conversation_rows
        else "unavailable"
    )
    metrics = [
        ["rulebook revisions", str(revisions)],
        ["turns", str(turn)],
        ["rules adopted", str(adopted_count)],
        [
            "best strict savings · V2",
            pct(best_savings) if best_savings is not None else "—",
        ],
        [
            "latest coverage · V2",
            (
                f'{latest_valid_v2.get("semantic_coverage_pct")}% · '
                f'{"pass" if latest_valid_v2.get("meaning_pass") else "fail"}'
                if latest_valid_v2
                else "awaiting V2"
            ),
        ],
        ["latest Conversation", conversation_metric],
    ]
    preview_rules = [
        rule for rule in rb.get("rules", [])
        if rule.get("status") in {"adopted", "proposed"}
        or rule.get("pending_repeal")
    ]
    terminal_rules = [
        rule for rule in rb.get("rules", []) if rule not in preview_rules
    ][-10:]
    # A bounded preview must preserve the same headline evidence as the archive.
    highlights = [latest_valid_v2]
    if best_savings is not None:
        highlights.append(next(event for event in tests if _strict_scoring_success(event)
                               and event.get("message_body_savings_pct") == best_savings))
    for actor in ("A", "B"):
        highlights.append(next((event for event in reversed(public_conversation)
                                if event.get("type") == "message" and event.get("agent") == actor), None))
    required = {index for index, event in enumerate(public_conversation)
                if any(event is highlight for highlight in highlights)}
    selected = set(range(max(0, len(public_conversation) - 30), len(public_conversation))) | required
    for index in sorted(selected - required):
        if len(selected) <= 30:
            break
        selected.remove(index)
    preview_conversation = [public_conversation[index] for index in sorted(selected)]
    bootstrap = {
        "turn": turn,
        "updated": updated,
        "runtime": runtime,
        "metrics": metrics,
        "preview": {
            "conversation": preview_conversation,
            "rulebook": {
                "version": rb.get("version", "0.0"),
                "rules": preview_rules + terminal_rules,
            },
            "collaboration": {},
            "conversations": (conversations or [])[-1:],
            "language": public_language,
            "notes": notes[-1:] if isinstance(notes, list) else [],
            "meta": {"updated": updated, "runtime": runtime},
            "metrics": metrics,
        },
    }
    preview = bootstrap.pop("preview")
    atomic_write_json(root / "viewer" / "preview.json", preview)
    startup_bytes = len(("window.PUBLIC_BOOTSTRAP = " + json.dumps(bootstrap, separators=(",", ":")) + ";\n").encode())
    if startup_bytes > 2048:
        raise ValueError("public startup exceeds the 2 KB behavior contract")
    (root / "viewer" / "bootstrap.js").write_text(
        "window.PUBLIC_BOOTSTRAP = "
        + json.dumps(bootstrap, separators=(",", ":"))
        + ";\n"
    )
    (root / "viewer" / "state.js").write_text(
        "window.STATE = " + json.dumps(
            {"conversation": public_conversation, "rulebook": rb,
             "collaboration": public_state(collaboration or empty_state()),
             "conversations": conversations or [], "language": public_language,
             "notes": notes if isinstance(notes, list) else [],
             "meta": {"spend_usd": meta.get("spend_usd", 0), "model": policy.model,
                      "spend_usd_historical_estimate":
                          meta.get("spend_usd_historical_estimate"),
                      "spend_usd_provider_exact_since_cutover":
                          meta.get("spend_usd_provider_exact_since_cutover"),
                      "cost_accounting_basis": meta.get("cost_accounting_basis"),
                      "updated": updated, "run": meta.get("run", "local"),
                      "runtime": runtime}}) + ";\n")
