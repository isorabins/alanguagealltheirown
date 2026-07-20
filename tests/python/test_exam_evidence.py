import json
import unittest
from pathlib import Path

from rulebook import language_payload

ROOT = Path(__file__).parents[2]


class EvidenceTests(unittest.TestCase):
    def test_corpus_receipt_does_not_mutate_legacy_rule_scores(self):
        rb = json.loads((ROOT / "tests/fixtures/mixed-rulebook.json").read_text())
        before = json.dumps(rb, sort_keys=True)
        receipt = {"language_hash": language_payload(rb)["hash"], "fidelity": 100, "token_delta_pct": -20}
        self.assertIn("language_hash", receipt)
        self.assertEqual(before, json.dumps(rb, sort_keys=True))


if __name__ == "__main__": unittest.main()
