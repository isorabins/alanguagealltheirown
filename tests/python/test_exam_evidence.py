import json
import unittest
from pathlib import Path
from unittest import mock

import loop
from rulebook import language_payload

ROOT = Path(__file__).parents[2]


class EvidenceTests(unittest.TestCase):
    def test_corpus_receipt_does_not_mutate_legacy_rule_scores(self):
        rb = json.loads((ROOT / "tests/fixtures/mixed-rulebook.json").read_text())
        before = json.dumps(rb, sort_keys=True)
        receipt = {"language_hash": language_payload(rb)["hash"], "fidelity": 100, "token_delta_pct": -20}
        self.assertIn("language_hash", receipt)
        self.assertEqual(before, json.dumps(rb, sort_keys=True))

    def test_fixed_fallback_without_precomputed_key_is_invalid_not_holistic(self):
        rb = json.loads((ROOT / "tests/fixtures/mixed-rulebook.json").read_text())
        conv=[]; meta={"tests_run":0,"spend_usd":0.0}
        responses=[("not a JSON key",{}),("ENCODED",{}),("DECODED",{})]
        with mock.patch("loop.gen_payload",return_value=(None,None,None)), \
             mock.patch("loop.call",side_effect=responses) as call, \
             mock.patch("loop.token_count",side_effect=lambda text, meta: max(1,len(text.split()))):
            loop.test_turn(conv,rb,meta,3)
        self.assertEqual(call.call_count,3)
        self.assertIsNone(conv[-1]["fidelity"])
        self.assertFalse(conv[-1]["judge_valid"])
        self.assertEqual(conv[-1]["judge_reason"],"answer_key_unavailable")
        self.assertFalse(meta["corpus_exams"][-1]["valid"])

    def test_answer_key_numbering_is_normalized_before_grading(self):
        self.assertEqual(loop.normalize_answer_key("1. first fact\n- second fact\n* third fact"),
                         ["first fact","second fact","third fact"])


if __name__ == "__main__": unittest.main()
