import json
import unittest
from pathlib import Path

from rulebook import score_judgment, score_judgment_v2

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

    def test_v2_separates_coverage_critical_failure_inventions_and_compression(self):
        key = [
            {"id":"B2.01","meaning":"Vessel is C-18A.","critical":True,
             "literal_sets":[["C-18A"]]},
            {"id":"B2.02","meaning":"Use potable water.","critical":False,
             "literal_sets":[]},
        ]
        decoded = "Vessel C-18A is not named. Use potable water. Also use steam."
        grade = {"mode":"RELAY","items":[
            {"id":"B2.01","verdict":"CORRUPTED","evidence":"Vessel C-18A is not named."},
            {"id":"B2.02","verdict":"SURVIVED","evidence":"Use potable water."},
        ],"inventions":[{"claim":"Use steam.","evidence":"Also use steam."}]}
        result = score_judgment_v2(key, grade, decoded, 35)
        self.assertTrue(result["valid"])
        self.assertFalse(result["meaning_pass"])
        self.assertFalse(result["compression_success"])
        self.assertEqual(result["semantic_coverage_pct"],50)
        self.assertEqual(result["critical_failures"],[{
            "atom_id":"B2.01","verdict":"CORRUPTED",
            "expected_meaning":"Vessel is C-18A.",
            "decoded_evidence":"Vessel C-18A is not named.",
        }])
        self.assertEqual(len(result["inventions"]),1)
        self.assertEqual(result["message_body_savings_pct"],35)

    def test_v2_requires_zero_inventions_and_positive_savings_for_compression_success(self):
        key=[{"id":"B1.01","meaning":"Use Tier A.","critical":True,
              "literal_sets":[["Tier A"]]}]
        decoded="Use Tier A."
        grade={"mode":"RELAY","items":[{"id":"B1.01","verdict":"SURVIVED","evidence":decoded}],
               "inventions":[]}
        self.assertTrue(score_judgment_v2(key,grade,decoded,1)["compression_success"])
        zero=score_judgment_v2(key,grade,decoded,0)
        self.assertTrue(zero["meaning_pass"])
        self.assertFalse(zero["compression_success"])

    def test_v2_invalidates_structural_absent_fabricated_and_conflicting_evidence(self):
        key=[{"id":"B2.01","meaning":"Pressure is 22.5 MPa.","critical":True,
              "literal_sets":[["22.5"],["MPa"]]}]
        cases={
            "invalid_atom_coverage_or_order":{"mode":"RELAY","items":[],"inventions":[]},
            "absent_evidence":{"mode":"RELAY","items":[{"id":"B2.01","verdict":"SURVIVED","evidence":""}],"inventions":[]},
            "fabricated_evidence":{"mode":"RELAY","items":[{"id":"B2.01","verdict":"SURVIVED","evidence":"22.5 MPa"}],"inventions":[]},
            "deterministic_conflict":{"mode":"RELAY","items":[{"id":"B2.01","verdict":"SURVIVED","evidence":"Pressure is 225 MPa."}],"inventions":[]},
        }
        decoded="Pressure is 225 MPa."
        for expected_reason,grade in cases.items():
            with self.subTest(expected_reason=expected_reason):
                result=score_judgment_v2(key,grade,decoded,10)
                self.assertFalse(result["valid"])
                self.assertEqual(result["status"],"INVALID JUDGE RESULT")
                self.assertTrue(result["reason"].startswith(expected_reason),result)


if __name__ == "__main__": unittest.main()
