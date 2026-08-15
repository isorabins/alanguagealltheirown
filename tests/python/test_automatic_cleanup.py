import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import loop
from state_store import atomic_write_json


def source_rulebook(kernel_tokens=100):
    return {
        "version": "0.2",
        "kernel_tokens": kernel_tokens,
        "changes": 2,
        "next_id": 3,
        "rules": [
            {"id": "rule-001", "text_en": "Mark deadlines once.", "status": "adopted", "history": []},
            {"id": "rule-002", "text_en": "Keep identifiers exact.", "status": "adopted", "history": []},
        ],
    }


class AutomaticCleanupTests(unittest.TestCase):
    def test_invalid_b_advisory_quarantines_with_permanent_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            rb = source_rulebook(110)
            original = copy.deepcopy(rb)
            meta = {
                "last_agent": "B",
                "spend_usd": 4.0,
                "automatic_cleanup": {
                    "schema_version": 2,
                    "baseline_tokens": 100,
                    "baseline_language_hash": "x" * 64,
                    "baseline_turn": 1,
                    "last_attempt_language_hash": None,
                    "last_status": "armed",
                    "structured_snapshot": {
                        "checkpoint_turn": 4,
                        "source_hash": "z" * 64,
                        "rulebook": {"rules": []},
                        "legislative_memory": {
                            "retired_mechanisms": [],
                            "failure_modes": [],
                            "unresolved_questions": [],
                        },
                    },
                },
            }
            previous_snapshot = copy.deepcopy(meta["automatic_cleanup"]["structured_snapshot"])
            conv = []
            error = {
                "status": "invalid",
                "error_type": "ValueError",
                "reason": "Agent B did not return valid JSON",
                "response_receipt": {
                    "model": loop.MODEL_B,
                    "prompt_version": "cleanup-b-v2",
                    "prompt_sha256": "b" * 64,
                    "content": "not json",
                    "usage": {"cost": 0.02},
                },
            }
            rounds = [{"round": 1, "b_verdict": "invalid"}]
            atomic_write_json(state_dir / "rulebook.json", rb)

            with patch.object(loop, "STATE", state_dir), patch.object(
                loop, "run_shadow_cleanup"
            ) as cleanup:
                cleanup.return_value = {
                    "status": "FAIL",
                    "stage": "b_audit",
                    "failure_class": "invalid_advisory",
                    "reason": "Agent B advisory invalid: Agent B did not return valid JSON",
                    "source_hash": "a" * 64,
                    "candidate_hash": "c" * 64,
                    "models": {"c": loop.MODEL_C, "b": loop.MODEL_B},
                    "rounds": rounds,
                    "b_advisory_error": error,
                    "run_spend_usd": 0.18,
                }
                self.assertFalse(loop.maybe_run_automatic_cleanup(conv, rb, meta, 10))
                self.assertEqual(cleanup.call_count, 1)
                self.assertEqual(meta["automatic_cleanup"]["last_status"], "quarantined")
                self.assertEqual(
                    meta["automatic_cleanup"]["quarantine"]["reason"],
                    "invalid_advisory",
                )
                event = conv[-1]
                self.assertEqual(event["failure_class"], "invalid_advisory")
                self.assertEqual(event["candidate_hash"], "c" * 64)
                self.assertEqual(event["rounds"], rounds)
                self.assertEqual(event["b_advisory_error"], error)
                self.assertEqual(rb, original)
                self.assertEqual(
                    meta["automatic_cleanup"]["structured_snapshot"], previous_snapshot
                )

                starting_spend = meta["spend_usd"]
                for turn in (11, 12):
                    rb["version"] = f"0.{turn}"
                    atomic_write_json(state_dir / "rulebook.json", rb)
                    self.assertFalse(
                        loop.maybe_run_automatic_cleanup(conv, rb, meta, turn)
                    )

                self.assertEqual(cleanup.call_count, 1)
                self.assertEqual(meta["spend_usd"], starting_spend)
                self.assertEqual([row["run_spend_usd"] for row in conv[-2:]], [0.0, 0.0])

    def test_structural_failure_quarantines_changed_hashes_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            rb = source_rulebook(110)
            original = copy.deepcopy(rb)
            meta = {
                "last_agent": "B",
                "spend_usd": 4.0,
                "automatic_cleanup": {
                    "schema_version": 2,
                    "baseline_tokens": 100,
                    "baseline_language_hash": "x" * 64,
                    "baseline_turn": 1,
                    "last_attempt_language_hash": None,
                    "last_status": "armed",
                },
            }
            conv = []
            atomic_write_json(state_dir / "rulebook.json", rb)

            with patch.object(loop, "STATE", state_dir), patch.object(
                loop, "run_shadow_cleanup"
            ) as cleanup:
                cleanup.return_value = {
                    "status": "FAIL",
                    "stage": "c_call",
                    "error_type": "ValueError",
                    "reason": "Agent C did not return valid JSON",
                    "source_hash": "a" * 64,
                    "models": {"c": loop.MODEL_C, "b": loop.MODEL_B},
                    "provider_calls": [{
                        "round": 1,
                        "role": "C",
                        "usage": {
                            "response_receipt": {
                                "id": "generation-truncated",
                                "finish_reason": "length",
                            },
                        },
                    }],
                    "run_spend_usd": 0.08,
                }
                self.assertFalse(loop.maybe_run_automatic_cleanup(conv, rb, meta, 10))
                self.assertEqual(cleanup.call_count, 1)
                self.assertEqual(
                    cleanup.call_args.kwargs["max_spend_usd"],
                    loop.AUTOMATIC_CLEANUP_MAX_SPEND_USD,
                )
                self.assertEqual(loop.AUTOMATIC_CLEANUP_MAX_SPEND_USD, 1.00)
                self.assertEqual(meta["automatic_cleanup"]["last_status"], "quarantined")
                self.assertEqual(
                    meta["automatic_cleanup"]["quarantine"]["edition"],
                    loop.AUTOMATIC_CLEANUP_EDITION,
                )
                self.assertEqual(conv[-1]["status"], "failed")
                self.assertEqual(conv[-1]["failure_class"], "structural_output")
                self.assertEqual(
                    conv[-1]["provider_calls"][0]["usage"]["response_receipt"],
                    {
                        "id": "generation-truncated",
                        "finish_reason": "length",
                    },
                )
                self.assertEqual(rb, original)

                restarted_meta = copy.deepcopy(meta)
                starting_spend = restarted_meta["spend_usd"]
                for turn in (11, 12, 13):
                    rb["version"] = f"0.{turn}"
                    atomic_write_json(state_dir / "rulebook.json", rb)
                    self.assertFalse(
                        loop.maybe_run_automatic_cleanup(conv, rb, restarted_meta, turn)
                    )

                self.assertEqual(cleanup.call_count, 1)
                self.assertEqual(restarted_meta["spend_usd"], starting_spend)
                self.assertEqual([row["status"] for row in conv[-3:]], [
                    "quarantined", "quarantined", "quarantined"
                ])
                self.assertEqual(rb["rules"], original["rules"])

    def test_quarantine_reset_requires_new_reviewed_edition_and_operator_action(self):
        state = {
            "schema_version": 2,
            "last_status": "quarantined",
            "quarantine": {
                "reason": "structural_output",
                "edition": "cleanup-edition-v1",
            },
        }
        with self.assertRaises(ValueError):
            loop.reset_automatic_cleanup_quarantine(
                state, reviewed_edition="cleanup-edition-v1", operator="Iso"
            )
        with self.assertRaises(ValueError):
            loop.reset_automatic_cleanup_quarantine(
                state, reviewed_edition="cleanup-edition-v2", operator=""
            )
        with self.assertRaisesRegex(ValueError, "current reviewed cleanup edition"):
            loop.reset_automatic_cleanup_quarantine(
                state, reviewed_edition="invented-future-edition", operator="Iso"
            )
        loop.reset_automatic_cleanup_quarantine(
            state, reviewed_edition=loop.AUTOMATIC_CLEANUP_EDITION, operator="Iso"
        )
        self.assertEqual(state["last_status"], "armed")
        self.assertEqual(
            state["reset"]["reviewed_edition"], loop.AUTOMATIC_CLEANUP_EDITION
        )
        self.assertNotIn("quarantine", state)

    def test_arms_then_applies_at_ten_percent_growth(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            rb = source_rulebook()
            meta = {"last_agent": "B"}
            conv = []
            atomic_write_json(state_dir / "rulebook.json", rb)

            with patch.object(loop, "STATE", state_dir), patch.object(
                loop, "run_shadow_cleanup"
            ) as cleanup:
                self.assertFalse(loop.maybe_run_automatic_cleanup(conv, rb, meta, 10))
                cleanup.assert_not_called()

                rb["kernel_tokens"] = 110
                atomic_write_json(state_dir / "rulebook.json", rb)

                def passing_cleanup(_source, output, **_kwargs):
                    candidate = {
                        "version": "cleanup-candidate",
                        "rules": [{
                            "id": "rule-c001",
                            "text_en": "Mark deadlines once and keep identifiers exact.",
                            "status": "adopted",
                            "source_ids": ["rule-001", "rule-002"],
                            "history": [],
                        }],
                        "excluded_sources": [],
                        "structured_rulebook": {"rules": [{
                            "id": "deadlines",
                            "trigger": "A message contains a deadline.",
                            "encoder": ["Mark the deadline once."],
                            "decoder": ["Restore the marked deadline."],
                            "invalid_if": ["The deadline changes."],
                            "overrides": [],
                            "source_ids": ["rule-001", "rule-002"],
                        }]},
                        "legislative_memory": {
                            "retired_mechanisms": [],
                            "failure_modes": [],
                            "unresolved_questions": [],
                        },
                    }
                    seeds = [
                        {"idea": f"idea {n}", "experiment": f"test {n}", "risk": f"risk {n}"}
                        for n in range(1, 4)
                    ]
                    atomic_write_json(output / "candidate.json", candidate)
                    atomic_write_json(output / "creative-seeds.json", seeds)
                    return {
                        "status": "PASS",
                        "reason": "C finalized",
                        "source_hash": "a" * 64,
                        "candidate_hash": "b" * 64,
                        "source_tokens": 110,
                        "candidate_tokens": 60,
                        "reduction_pct": 45.45,
                        "models": {"c": loop.MODEL_C, "b": loop.MODEL_B},
                        "prompt_c_version": "cleanup-c-v3",
                        "prompt_b_version": "cleanup-b-v3",
                        "prompt_c_finalizer_version": "cleanup-c-finalizer-v2",
                        "rounds": [],
                        "run_spend_usd": 0.08,
                    }

                cleanup.side_effect = passing_cleanup
                with patch.object(loop, "token_count", return_value=65):
                    self.assertTrue(loop.maybe_run_automatic_cleanup(conv, rb, meta, 11))

            self.assertEqual(rb["kernel_tokens"], 65)
            self.assertEqual([r["status"] for r in rb["rules"]],
                             ["historical", "historical", "adopted"])
            self.assertEqual(meta["automatic_cleanup"]["baseline_tokens"], 65)
            self.assertEqual(
                meta["automatic_cleanup"]["structured_snapshot"]["checkpoint_turn"], 11
            )
            self.assertEqual(
                meta["automatic_cleanup"]["structured_snapshot"]["source_hash"], "a" * 64
            )
            self.assertEqual(len(meta["automatic_cleanup"]["pending_creative_seeds"]["seeds"]), 3)
            self.assertEqual(
                meta["automatic_cleanup"]["pending_creative_seeds"]["delivered_roles"], []
            )
            self.assertEqual(conv[-1]["status"], "applied")
            self.assertEqual(conv[-1]["post_state_receipt"]["actor"], "harness")

    def test_open_motion_blocks_due_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            rb = source_rulebook(110)
            rb["rules"].append({
                "id": "rule-003",
                "text_en": "An unresolved proposal.",
                "status": "proposed",
                "proposed_turn": 9,
                "history": [],
            })
            meta = {
                "last_agent": "A",
                "automatic_cleanup": {
                    "schema_version": 2,
                    "baseline_tokens": 100,
                    "baseline_language_hash": "x" * 64,
                    "baseline_turn": 1,
                    "last_attempt_language_hash": None,
                    "last_status": "armed",
                },
            }
            atomic_write_json(state_dir / "rulebook.json", rb)
            with patch.object(loop, "STATE", state_dir), patch.object(
                loop, "run_shadow_cleanup"
            ) as cleanup:
                self.assertFalse(loop.maybe_run_automatic_cleanup([], rb, meta, 10))
                cleanup.assert_not_called()

    def test_active_regular_prompts_are_versioned_v3(self):
        rb = source_rulebook()
        assembled = loop.assemble_legislative_prompt(
            [], rb, turn=10, agent="A", collaboration_input=None
        )
        self.assertEqual(assembled["prompt_receipt"]["role_version"], "agent-a-v3")
        self.assertIn("The goal is not to create more rules", assembled["system"])
        self.assertEqual(len(assembled["prompt_receipt"]["assembled_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
