import copy
import json
import unittest
from pathlib import Path
from unittest import mock

import loop
from rule_legislation import RuleLegislation, WorkOutcome
from rulebook import language_payload


ROOT = Path(__file__).parents[2]


class ShadowLegislationInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.rulebook = json.loads(
            (ROOT / "tests/fixtures/mixed-rulebook.json").read_text()
        )

    def test_shadow_snapshot_matches_canonical_language_without_mutation(self):
        before = copy.deepcopy(self.rulebook)
        module = RuleLegislation.shadow(self.rulebook)

        snapshot = module.snapshot()
        canonical = language_payload(self.rulebook)

        self.assertEqual(snapshot.adopted_language.version, canonical["version"])
        self.assertEqual(snapshot.adopted_language.hash, canonical["hash"])
        self.assertEqual(
            [rule.as_dict() for rule in snapshot.adopted_language.rules],
            canonical["rules"],
        )
        self.assertEqual(snapshot.classifications, {})
        self.assertEqual(snapshot.budget.mode, "shadow")
        self.assertEqual(snapshot.budget.monthly_ceiling_usd, "30.00")
        self.assertEqual(snapshot.public_read_model["legislation_identity"], {
            "version": canonical["version"], "hash": canonical["hash"]
        })
        self.assertEqual(self.rulebook, before)

        self.assertEqual(
            module.submit_change(None).outcome, WorkOutcome.DEFERRED
        )
        self.assertEqual(module.advance().outcome, WorkOutcome.DEFERRED)
        self.assertEqual(self.rulebook, before)

    def test_development_exam_uses_the_same_shadow_snapshot_identity_and_rules(self):
        canonical = language_payload(self.rulebook)
        calls = []

        def fake_call(model, system, user, **kwargs):
            calls.append((model, system, user))
            if len(calls) == 1:
                return "ENCODED", {}
            if len(calls) == 2:
                return "DECODED", {}
            return "{}", {}

        conv = []
        meta = {"tests_run": 0, "spend_usd": 0.0}
        with mock.patch("loop.call", side_effect=fake_call), mock.patch(
            "loop.token_count", side_effect=[10, 5]
        ):
            loop.test_turn(conv, self.rulebook, meta, 3)

        self.assertEqual(conv[-1]["language_version"], canonical["version"])
        self.assertEqual(conv[-1]["language_hash"], canonical["hash"])
        self.assertIn("Adopted alpha meaning.", calls[0][1])
        self.assertNotIn("Proposed beta meaning.", calls[0][1])
        self.assertNotIn("Rejected gamma meaning.", calls[0][1])


if __name__ == "__main__":
    unittest.main()
