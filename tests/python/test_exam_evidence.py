import json
import hashlib
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

    def test_frozen_benchmark_with_invalid_judge_is_invalid_not_holistic(self):
        rb = json.loads((ROOT / "tests/fixtures/mixed-rulebook.json").read_text())
        conv=[]; meta={"tests_run":0,"spend_usd":0.0,
                      "corpus_exams":[{"turn":n} for n in range(500)]}
        responses=[("ENCODED",{}),("DECODED",{}),("not a judgment",{})]
        with mock.patch("loop.call",side_effect=responses) as call, \
             mock.patch("loop.token_count",side_effect=lambda text, meta: max(1,len(text.split()))):
            loop.test_turn(conv,rb,meta,3)
        self.assertEqual(call.call_count,3)
        self.assertIsNone(conv[-1]["fidelity"])
        self.assertFalse(conv[-1]["judge_valid"])
        self.assertEqual(conv[-1]["judge_reason"],"items_not_array")
        self.assertFalse(meta["corpus_exams"][-1]["valid"])
        self.assertEqual(len(meta["corpus_exams"]),500)
        self.assertEqual(meta["corpus_exams"][0]["turn"],1)
        self.assertEqual(conv[-1]["benchmark_id"],"B1")
        self.assertEqual(meta["benchmark_suite"]["next_index"],1)
        self.assertNotIn("benchmark_results",meta)

    def test_benchmark_registry_is_frozen_and_versioned(self):
        suite=loop.load_benchmark_suite()
        self.assertEqual(suite["version"],"v1")
        self.assertEqual([row["id"] for row in suite["benchmarks"]],
                         ["B1","B2","B3","B4","B5"])
        self.assertEqual([row["source_turn"] for row in suite["benchmarks"]],
                         [1119,1149,1179,1200,1221])
        expected={
            "B1":"63f1fad5c9f47b858a3e6e484df331db48e0131ed74d965f475edbcb0567a224",
            "B2":"4b29fb55056b40b909bf96d26fb6e3681a45461122f3c5290923bc34ee68736c",
            "B3":"de7063025ab8428177aa78406a665d8cd212182465ba4dc208ab92acb035cb20",
            "B4":"c39e3227c48fc6e22cc487d345eae4fee3e31a42a56f3ce9ecd21d35450fb78d",
            "B5":"c40691a111abd785e4f9414063ca3d03e2e98e4f493be6efaf73ecd3a9df8b8d",
        }
        for row in suite["benchmarks"]:
            frozen=json.dumps({"original":row["original"],"answer_key":row["answer_key"]},
                              sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
            self.assertEqual(hashlib.sha256(frozen).hexdigest(),expected[row["id"]])

    def test_round_robin_cursor_survives_serialized_restart(self):
        meta={}
        seen=[]
        for _ in range(3):
            benchmark,cycle=loop.select_benchmark(meta)
            seen.append((benchmark["id"],cycle))
            loop.advance_benchmark(meta,benchmark)
        restarted=json.loads(json.dumps(meta))
        for _ in range(3):
            benchmark,cycle=loop.select_benchmark(restarted)
            seen.append((benchmark["id"],cycle))
            loop.advance_benchmark(restarted,benchmark)
        self.assertEqual(seen,[("B1",1),("B2",1),("B3",1),("B4",1),("B5",1),("B1",2)])
        self.assertEqual(restarted["benchmark_suite"],
                         {"version":"v1","next_index":1,"cycle":2})

    def test_previous_valid_result_is_same_benchmark_only(self):
        suite=loop.load_benchmark_suite()
        b1=suite["benchmarks"][0]
        meta={"benchmark_results":{
            "B1":{"turn":1300,"fidelity":94,"token_delta_pct":-40,
                  "language_version":"v","language_hash":"h"},
            "B2":{"turn":1301,"fidelity":10,"token_delta_pct":99,
                  "language_version":"other","language_hash":"other"},
        }}
        self.assertEqual(loop.previous_benchmark_result(meta,b1)["turn"],1300)
        self.assertEqual(loop.previous_benchmark_result({},b1)["turn"],1119)

    def test_live_receipt_compares_only_with_same_benchmark_baseline(self):
        rb=json.loads((ROOT/"tests/fixtures/mixed-rulebook.json").read_text())
        key=loop.load_benchmark_suite()["benchmarks"][0]["answer_key"]
        grade={"mode":"RELAY","items":[
            {"n":index+1,"verdict":"SURVIVED"} for index in range(len(key))
        ],"invented":[],"lost":"nothing material"}
        meta={"tests_run":406,"spend_usd":0.0}
        conv=[]
        with mock.patch("loop.call",side_effect=[
                 ("ENCODED",{}),("DECODED",{}),(json.dumps(grade),{})
             ]), mock.patch("loop.token_count",side_effect=[100,50]):
            loop.test_turn(conv,rb,meta,1242)
        event=conv[-1]
        self.assertEqual(event["benchmark_id"],"B1")
        self.assertEqual(event["prior_turn"],1119)
        self.assertEqual(event["fidelity_delta"],17)
        self.assertEqual(event["savings_delta_pct"],-9)
        self.assertEqual(meta["benchmark_results"]["B1"]["turn"],1242)
        self.assertEqual(meta["benchmark_suite"]["next_index"],1)
        rendered=loop.render_window(conv)
        self.assertIn("previous same benchmark: turn 1119",rendered)
        self.assertIn("fidelity 83 -> 100 (+17)",rendered)

    def test_invalid_exam_window_never_renders_none_as_score(self):
        event={"turn":3,"agent":"harness","type":"test","payload":"fixture",
               "orig_tokens":10,"enc_tokens":8,"token_delta_pct":-20,"fidelity":None,
               "judge_reason":"duplicate_item_id","encoded":"x","decoded":"y","lost":"invalid"}
        rendered=loop.render_window([event])
        self.assertIn("no valid score (duplicate_item_id)",rendered)
        self.assertNotIn("None/100",rendered)

    def test_legislature_receipt_renders_without_message_content(self):
        event={"turn":4,"agent":"harness","type":"legislature",
               "motion_receipt":{"verb":"PROPOSE","accepted":False,
                                 "reason":"proposal_already_open"}}
        rendered=loop.render_window([event])
        self.assertIn("LEGACY MACHINE RECEIPT; AVAILABLE FIELDS ONLY", rendered)
        self.assertIn('"reason": "proposal_already_open"', rendered)
        self.assertIn('"verb": "PROPOSE"', rendered)
        self.assertNotIn('"rule_id"', rendered)

    def test_dead_economics_stub_is_removed(self):
        self.assertNotIn("def econ_line", (ROOT / "loop.py").read_text())

    def test_answer_key_numbering_is_normalized_before_grading(self):
        self.assertEqual(loop.normalize_answer_key("1. first fact\n- second fact\n* third fact"),
                         ["first fact","second fact","third fact"])


if __name__ == "__main__": unittest.main()
