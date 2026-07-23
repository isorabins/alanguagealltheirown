import json
import unittest
from pathlib import Path

from rulebook import language_payload, proposal_trial_payload, render_language, render_legislature

ROOT = Path(__file__).parents[2]


class RulebookViewTests(unittest.TestCase):
    def setUp(self): self.rb = json.loads((ROOT / "tests/fixtures/mixed-rulebook.json").read_text())

    def test_language_contains_every_adopted_and_no_other_status(self):
        text = render_language(self.rb)
        self.assertIn("Adopted alpha meaning", text)
        for forbidden in ("Proposed beta", "Rejected gamma", "Reverted delta"):
            self.assertNotIn(forbidden, text)

    def test_legislature_preserves_every_status(self):
        text = render_legislature(self.rb)
        for status in ("adopted", "proposed", "rejected", "reverted"):
            self.assertIn(f"[{status}]", text)

    def test_version_changes_only_with_adopted_meaning(self):
        first = language_payload(self.rb)
        self.rb["rules"][1]["text_en"] = "changed proposal"
        self.assertEqual(first, language_payload(self.rb))
        self.rb["rules"][0]["text_en"] = "changed adopted"
        self.assertNotEqual(first["hash"], language_payload(self.rb)["hash"])

    def test_only_explicit_single_proposal_trial_can_add_proposed_text(self):
        trial = proposal_trial_payload(self.rb, "rule-002")
        self.assertEqual(trial["kind"], "proposal_trial")
        self.assertEqual([r["id"] for r in trial["rules"]], ["rule-001", "rule-002"])
        self.assertTrue(trial["rules"][-1]["trial_only"])
        with self.assertRaises(ValueError): proposal_trial_payload(self.rb, "rule-003")


if __name__ == "__main__": unittest.main()
