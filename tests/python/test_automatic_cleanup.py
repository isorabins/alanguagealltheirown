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
                        "prompt_c_version": "cleanup-c-v2",
                        "prompt_b_version": "cleanup-b-v2",
                        "prompt_c_finalizer_version": "cleanup-c-finalizer-v1",
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
            self.assertEqual(len(meta["automatic_cleanup"]["pending_creative_seeds"]["seeds"]), 3)
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
                    "schema_version": 1,
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

    def test_active_regular_prompts_are_versioned_v2(self):
        rb = source_rulebook()
        assembled = loop.assemble_legislative_prompt(
            [], rb, turn=10, agent="A", collaboration_input=None
        )
        self.assertEqual(assembled["prompt_receipt"]["role_version"], "agent-a-v2")
        self.assertIn("The goal is not to create more rules", assembled["system"])
        self.assertEqual(len(assembled["prompt_receipt"]["assembled_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
