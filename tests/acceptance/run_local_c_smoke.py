"""Opt-in real-provider smoke: 12 frozen real rules, C/B, apply, restart, A.

Requires OPENROUTER_API_KEY in process. Run output is isolated; the shared budget
file survives failed attempts. This deliberately does not test the full archive.
"""
import argparse
import copy
from functools import partial
import json
import shutil
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import loop
from collaboration import empty_state
from local_cleanup import ReservedTransport
from rulebook import render_language, language_payload
from state_store import atomic_write_json, snapshot_hash
from turn_store import TurnState, TurnStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--budget", required=True, type=Path)
    parser.add_argument("--max-spend-usd", default="1.00")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    args.budget.parent.mkdir(parents=True, exist_ok=True)
    original_path = ROOT / "state/rulebook.json"
    original_bytes = original_path.read_bytes()
    original = json.loads(original_bytes)
    rb = copy.deepcopy(original)
    rb["rules"] = [r for r in rb["rules"] if r["status"] == "adopted"][:12]
    atomic_write_json(args.output / "fixture.json", rb)
    atomic_write_json(args.output / "fixture-provenance.json", {
        "source_hash": snapshot_hash(original), "source_path": str(original_path),
        "selected_ids": [r["id"] for r in rb["rules"]],
        "scope": "first 12 adopted records, preserved verbatim; historical archive excluded",
    })
    response = loop.requests.get("https://openrouter.ai/api/v1/models", timeout=30)
    response.raise_for_status()
    needed = {loop.MODEL_C, loop.MODEL_B, loop.MODEL_GRADER, loop.MODEL_A}
    models = {m["id"]: m for m in response.json()["data"] if m["id"] in needed}
    atomic_write_json(args.output / "model-preflight.json", models)
    transport = ReservedTransport(args.max_spend_usd, models, args.budget, max_output_tokens=6000)
    loop.call = partial(loop.call, transport=transport)
    loop.token_count = partial(loop.token_count, call_model=loop.call)
    loop.STATE = args.output / "state"
    loop.STATE.mkdir()
    meta = {"spend_usd": 0.0, "last_agent": "B", "tests_run": 0}
    conv = []
    loop.initialize_exact_cost_accounting(meta, cutover_turn=0)
    loop.configure_cost_receipt_ledger(loop.STATE / loop.COST_LEDGER_FILENAME, meta)
    rb["kernel_tokens"] = loop.token_count(render_language(rb), meta)
    meta["automatic_cleanup"] = {
        "schema_version": 2, "baseline_tokens": int(rb["kernel_tokens"] / 1.2),
        "baseline_language_hash": "local-test-trigger", "baseline_turn": 0,
        "last_status": "quarantined", "last_attempt_language_hash": None,
        "quarantine": {"edition": "automatic-cleanup-v5-structured-context",
                       "reason": "structural_output", "entered_turn": 0},
    }
    loop.reset_automatic_cleanup_quarantine(meta["automatic_cleanup"],
        reviewed_edition=loop.AUTOMATIC_CLEANUP_EDITION, operator="Iso: local test approval")
    loop.ensure_structured_protocol_cutover(conv, rb, meta, activation_turn=0)
    original_shadow = loop.run_shadow_cleanup
    def retained_shadow(source, _temporary_output, **kwargs):
        report = original_shadow(source, _temporary_output, **kwargs)
        shutil.copytree(_temporary_output, args.output / "shadow")
        return report
    loop.run_shadow_cleanup = retained_shadow
    state = TurnState(conv, rb, meta, empty_state(), [])
    result = {"status": "FAIL", "scope": "12-rule real-provider local smoke"}
    try:
        with TurnStore(loop.STATE).writer() as store:
            store.commit(state)
            assert loop.maybe_run_automatic_cleanup(conv, rb, meta, 1), "cleanup did not apply"
            store.commit(state)
        applied_hash = language_payload(rb)["hash"]
        with TurnStore(loop.STATE).writer() as store:
            restarted = store.load(TurnState([], {}, {}, empty_state(), []))
            assert language_payload(restarted.rulebook)["hash"] == applied_hash
            outcome = loop.agent_turn(restarted.conversation, restarted.rulebook,
                restarted.meta, restarted.collaboration, 2)
            assert outcome in {"accepted", "rejected"}, "ordinary turn did not complete lawfully"
            assert any(e.get("agent") == "A" and e.get("type") == "message"
                       for e in restarted.conversation), "A did not continue after cleanup"
            store.commit(restarted)
        result.update(status="PASS", cleanup_applied=True, restart_preserved_language=True,
                      next_turn_outcome=outcome, applied_language_hash=applied_hash)
    finally:
        result["source_unchanged"] = original_path.read_bytes() == original_bytes
        result["charged_or_reserved_usd"] = str(transport.used)
        atomic_write_json(args.output / "acceptance.json", result)
        print(json.dumps(result, indent=2))
    assert result["source_unchanged"]


if __name__ == "__main__":
    main()
