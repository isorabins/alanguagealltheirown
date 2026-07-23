import json
import unittest
from pathlib import Path

from rulebook import score_judgment

ROOT = Path(__file__).parents[2]


class JudgeTests(unittest.TestCase):
    def test_only_exact_coverage_scores(self):
        cases = json.loads((ROOT / "tests/fixtures/judgments.json").read_text())
        key = ["one", "two"]
        self.assertTrue(score_judgment(key, cases["complete"])["valid"])
        self.assertEqual(score_judgment(key, cases["complete"])["fidelity"], 50)
        for name in ("missing", "duplicate", "nonnumeric", "out_of_range"):
            result = score_judgment(key, cases[name])
            self.assertFalse(result["valid"], name)
            self.assertIsNone(result["fidelity"])


if __name__ == "__main__": unittest.main()
