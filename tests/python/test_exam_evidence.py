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
        conv=[]; meta={"tests_run":0,"spend_usd":0.0,
                      "corpus_exams":[{"turn":n} for n in range(500)]}
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
        self.assertEqual(len(meta["corpus_exams"]),500)
        self.assertEqual(meta["corpus_exams"][0]["turn"],1)

    def test_invalid_exam_window_never_renders_none_as_score(self):
        event={"turn":3,"agent":"harness","type":"test","payload":"fixture",
               "orig_tokens":10,"enc_tokens":8,"token_delta_pct":-20,"fidelity":None,
               "judge_reason":"duplicate_item_id","encoded":"x","decoded":"y","lost":"invalid"}
        rendered=loop.render_window([event])
        self.assertIn("no valid score (duplicate_item_id)",rendered)
        self.assertNotIn("None/100",rendered)

    def test_dead_economics_stub_is_removed(self):
        self.assertNotIn("def econ_line", (ROOT / "loop.py").read_text())

    def test_answer_key_numbering_is_normalized_before_grading(self):
        self.assertEqual(loop.normalize_answer_key("1. first fact\n- second fact\n* third fact"),
                         ["first fact","second fact","third fact"])


if __name__ == "__main__": unittest.main()
