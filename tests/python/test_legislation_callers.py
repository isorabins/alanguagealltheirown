import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import loop
from rule_legislation import RuleLegislation
from rulebook import language_payload
from state_store import atomic_write_json


ROOT = Path(__file__).parents[2]


class LegislativeCallerContractTests(unittest.TestCase):
    def setUp(self):
        self.rulebook = json.loads(
            (ROOT / "tests/fixtures/mixed-rulebook.json").read_text()
        )
        self.module = RuleLegislation.shadow(self.rulebook)
        self.identity = language_payload(self.rulebook)

    def test_legislative_prompt_consumes_the_supplied_module_snapshot(self):
        assembled = loop.assemble_legislative_prompt(
            [], self.rulebook, turn=1, agent="A", collaboration_input=None,
            legislation=self.module,
        )
        self.assertEqual(assembled["legislation_identity"], {
            "version": self.identity["version"], "hash": self.identity["hash"]
        })
        adopted_section = assembled["system"].split(
            "=== ADOPTED LANGUAGE ===\n", 1
        )[1].split("\n\n=== OPEN MOTION ===", 1)[0]
        self.assertIn("Adopted alpha meaning.", adopted_section)
        self.assertNotIn("Proposed beta meaning.", adopted_section)

    def test_project_lookup_receipt_is_bound_to_the_module_identity(self):
        collaboration = {
            "research": [{
                "id": "lookup-1", "kind": "LOOKUP", "route": "project",
                "status": "queued", "question": "What is the current language?",
            }],
            "asks": [], "suggestions": [],
        }
        result = {
            "findings": "Current state found.", "limitations": [], "citations": [],
            "evidence_count": 1, "adequate": True,
        }
        with mock.patch("loop.project_lookup", return_value=result):
            loop.process_one_research(
                collaboration, {"spend_usd": 0.0}, 4, legislation=self.module
            )
        self.assertEqual(
            collaboration["research"][0]["legislation_identity"],
            {"version": self.identity["version"], "hash": self.identity["hash"]},
        )

    def test_automatic_cleanup_eligibility_reads_module_identity_without_calling_provider(self):
        rb = copy.deepcopy(self.rulebook)
        rb["kernel_tokens"] = 100
        meta = {}
        self.assertFalse(loop.maybe_run_automatic_cleanup(
            [], rb, meta, 5, legislation=RuleLegislation.shadow(rb)
        ))
        self.assertEqual(
            meta["automatic_cleanup"]["baseline_language_hash"],
            language_payload(rb)["hash"],
        )

    def test_agent_turn_records_module_identity_and_shadow_authority_result(self):
        rb = copy.deepcopy(self.rulebook)
        collaboration = {"research": [], "asks": [], "suggestions": []}
        meta = {"last_agent": None, "spend_usd": 0.0}
        response = json.dumps({
            "deliberation": "Public proposal: add one focused marker for success.",
            "motion": {"kind": "PROPOSE", "text": "Use !ok for confirmed success."},
            "fault_response": None, "measurements": [], "requests": [],
        })
        with mock.patch("loop.call", return_value=(response, {"completion_tokens": 20})), \
             mock.patch("loop.token_count", return_value=20):
            loop.agent_turn(
                [], rb, meta, collaboration, 1,
                legislation=RuleLegislation.shadow(rb),
            )
        # Re-run with a retained conversation so the receipt is inspectable.
        conv = []
        rb = copy.deepcopy(self.rulebook)
        with mock.patch("loop.call", return_value=(response, {"completion_tokens": 20})), \
             mock.patch("loop.token_count", return_value=20):
            loop.agent_turn(
                conv, rb, meta, collaboration, 2,
                legislation=RuleLegislation.shadow(rb),
            )
        receipt = next(row for row in reversed(conv) if row["type"] == "legislature")
        self.assertEqual(receipt["legislation_identity"]["hash"], self.identity["hash"])
        self.assertEqual(receipt["module_authority"], "shadow_observer")

    def test_stale_supplied_module_snapshot_fails_before_prompt_or_provider(self):
        changed = copy.deepcopy(self.rulebook)
        changed["rules"][0]["text_en"] = "changed adopted meaning"
        with self.assertRaisesRegex(RuntimeError, "legislation_snapshot_identity_mismatch"):
            loop.assemble_legislative_prompt(
                [], changed, turn=1, agent="A", collaboration_input=None,
                legislation=self.module,
            )


if __name__ == "__main__":
    unittest.main()
