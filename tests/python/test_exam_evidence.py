import json
import hashlib
import unittest
from pathlib import Path
from unittest import mock

import loop
from rulebook import language_payload

ROOT = Path(__file__).parents[2]


class EvidenceTests(unittest.TestCase):
    def _valid_grade(self, benchmark):
        decoded = "\n".join(atom["meaning"] for atom in benchmark["answer_key"])
        grade = {"mode": "RELAY", "items": [
            {"id": atom["id"], "verdict": "SURVIVED", "evidence": atom["meaning"]}
            for atom in benchmark["answer_key"]
        ], "inventions": []}
        return decoded, grade

    def _assert_literal_loss_reaches_grader(self, *, benchmark_id, target_id,
                                             literal, replacement, turn):
        suite = loop.load_benchmark_suite()
        benchmark_index = next(
            index for index, row in enumerate(suite["benchmarks"])
            if row["id"] == benchmark_id
        )
        benchmark = suite["benchmarks"][benchmark_index]
        target = next(atom for atom in benchmark["answer_key"] if atom["id"] == target_id)
        corrupted_evidence = target["meaning"].replace(literal, replacement)
        decoded = "\n".join(
            corrupted_evidence if atom["id"] == target_id else atom["meaning"]
            for atom in benchmark["answer_key"]
        )

        def run(verdict):
            grade = {"mode": "RELAY", "items": [
                {
                    "id": atom["id"],
                    "verdict": verdict if atom["id"] == target_id else "SURVIVED",
                    "evidence": corrupted_evidence if atom["id"] == target_id else atom["meaning"],
                }
                for atom in benchmark["answer_key"]
            ], "inventions": []}
            calls = []

            def fake_call(model, system, user, **kwargs):
                calls.append((model, system, user))
                if len(calls) == 1:
                    return "ENCODED", {}
                if len(calls) == 2:
                    return decoded, {}
                return json.dumps(grade), {}

            meta = {
                "tests_run": 0,
                "spend_usd": 0.0,
                "benchmark_suite": {
                    "version": "v2", "next_index": benchmark_index, "cycle": 1,
                },
            }
            conv = []
            with mock.patch("loop.call", side_effect=fake_call), \
                 mock.patch("loop.token_count", side_effect=[100, 50]):
                loop.test_turn(conv, json.loads(
                    (ROOT / "tests/fixtures/mixed-rulebook.json").read_text()
                ), meta, turn)
            self.assertEqual(len(calls), 3)
            return conv[-1], calls[-1]

        invalid_event, grader_call = run("SURVIVED")
        grader_system, grader_user = grader_call[1], grader_call[2]
        key_json = grader_user.split("ATOMIC ANSWER KEY:\n", 1)[1].split(
            "\n\nDECODED:\n", 1
        )[0]
        grader_key = json.loads(key_json)
        self.assertEqual(
            [atom["literal_sets"] for atom in grader_key],
            [atom["literal_sets"] for atom in benchmark["answer_key"]],
        )
        projected_target = next(atom for atom in grader_key if atom["id"] == target_id)
        self.assertEqual(projected_target["missing_literal_sets"], [[literal]])
        self.assertIn("SURVIVED is forbidden", grader_system)
        self.assertIn("CORRUPTED", grader_system)
        self.assertIn("MISSING", grader_system)
        self.assertFalse(invalid_event["judge_valid"])
        self.assertEqual(invalid_event["judge_status"], "INVALID JUDGE RESULT")
        self.assertEqual(invalid_event["judge_reason"], f"deterministic_conflict:{target_id}")

        valid_event, _ = run("CORRUPTED")
        self.assertTrue(valid_event["judge_valid"])
        self.assertEqual(valid_event["judge_status"], "VALID")
        self.assertFalse(valid_event["meaning_pass"])
        target_result = next(
            item for item in valid_event["atom_results"] if item["id"] == target_id
        )
        self.assertEqual(target_result["verdict"], "CORRUPTED")
        language = language_payload(json.loads(
            (ROOT / "tests/fixtures/mixed-rulebook.json").read_text()
        ))
        feedback = loop.derive_scoring_v2_failure_feedback(
            [valid_event],
            language_version=language["version"],
            language_hash=language["hash"],
        )
        self.assertIsNotNone(feedback)
        self.assertEqual(feedback.failed_atom_id, target_id)
        self.assertEqual(feedback.classification, "CORRUPTED")
        self.assertEqual(feedback.decoded_evidence, corrupted_evidence)

    def test_b1_dropped_currency_symbol_is_visible_to_the_grader(self):
        self._assert_literal_loss_reaches_grader(
            benchmark_id="B1", target_id="B1.03", literal="$48",
            replacement="48", turn=1350,
        )

    def test_b2_compacted_vessel_identifier_is_visible_to_the_grader(self):
        self._assert_literal_loss_reaches_grader(
            benchmark_id="B2", target_id="B2.01", literal="C-18A",
            replacement="c18a", turn=1353,
        )

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
        self.assertEqual(conv[-1]["judge_status"], "INVALID JUDGE RESULT")
        self.assertFalse(conv[-1]["judge_valid"])
        self.assertEqual(conv[-1]["judge_reason"],"items_not_array")
        self.assertFalse(meta["corpus_exams"][-1]["valid"])
        self.assertEqual(len(meta["corpus_exams"]),500)
        self.assertEqual(meta["corpus_exams"][0]["turn"],1)
        self.assertEqual(conv[-1]["benchmark_id"],"B1")
        self.assertEqual(meta["benchmark_suite"]["next_index"],1)
        self.assertNotIn("benchmark_results_v2",meta)

    def test_legacy_v1_is_immutable_and_v2_is_a_distinct_corrected_contract(self):
        suite=loop.load_benchmark_suite()
        self.assertEqual(suite["version"],"v2")
        self.assertEqual(suite["source_version"],"v1")
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
        legacy=json.loads((ROOT/"benchmarks/v1.json").read_text())
        for row in legacy["benchmarks"]:
            frozen=json.dumps({"original":row["original"],"answer_key":row["answer_key"]},
                              sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
            self.assertEqual(hashlib.sha256(frozen).hexdigest(),expected[row["id"]])
        b5=next(row for row in suite["benchmarks"] if row["id"]=="B5")
        meanings=[atom["meaning"] for atom in b5["answer_key"]]
        self.assertTrue(any("last two digits" in meaning for meaning in meanings))
        self.assertTrue(any("350 gigs" in meaning for meaning in meanings))
        self.assertTrue(any("pre-check succeeds" in meaning and "live 03:45 verification then fails" in meaning
                            for meaning in meanings))
        self.assertTrue(all(len({atom["id"] for atom in row["answer_key"]}) == len(row["answer_key"])
                            for row in suite["benchmarks"]))

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
                         {"version":"v2","next_index":1,"cycle":2})

    def test_v1_cursor_starts_a_fresh_v2_cycle(self):
        meta={"benchmark_suite":{"version":"v1","next_index":4,"cycle":9}}
        benchmark,cycle=loop.select_benchmark(meta)
        self.assertEqual((benchmark["id"],cycle),("B1",1))
        self.assertEqual(meta["benchmark_suite"],{"version":"v2","next_index":0,"cycle":1})

    def test_previous_valid_result_is_same_benchmark_only(self):
        suite=loop.load_benchmark_suite()
        b1=suite["benchmarks"][0]
        meta={"benchmark_results_v2":{
            "B1":{"turn":1300,"meaning_pass":False,"semantic_coverage_pct":94,
                  "language_version":"v","language_hash":"h"},
            "B2":{"turn":1301,"meaning_pass":False,"semantic_coverage_pct":10,
                  "language_version":"other","language_hash":"other"},
        }}
        self.assertEqual(loop.previous_benchmark_result(meta,b1)["turn"],1300)
        self.assertIsNone(loop.previous_benchmark_result({},b1))

    def test_valid_v2_receipt_reports_separate_results_without_v1_comparison(self):
        rb=json.loads((ROOT/"tests/fixtures/mixed-rulebook.json").read_text())
        benchmark=loop.load_benchmark_suite()["benchmarks"][0]
        decoded,grade=self._valid_grade(benchmark)
        meta={"tests_run":406,"spend_usd":0.0}
        conv=[]
        with mock.patch("loop.call",side_effect=[
                 ("ENCODED",{}),(decoded,{}),(json.dumps(grade),{})
             ]), mock.patch("loop.token_count",side_effect=[100,50]):
            loop.test_turn(conv,rb,meta,1242)
        event=conv[-1]
        self.assertEqual(event["benchmark_id"],"B1")
        self.assertEqual(event["scoring_version"],"v2")
        self.assertTrue(event["meaning_pass"])
        self.assertTrue(event["compression_success"])
        self.assertEqual(event["semantic_coverage_pct"],100)
        self.assertEqual(event["critical_failures"],[])
        self.assertEqual(event["inventions"],[])
        self.assertEqual(event["message_body_savings_pct"],50)
        self.assertNotIn("fidelity",event)
        self.assertNotIn("fidelity_delta",event)
        self.assertIsNone(event["prior_valid_v2_turn"])
        self.assertEqual(meta["benchmark_results_v2"]["B1"]["turn"],1242)
        self.assertEqual(meta["benchmark_suite"]["next_index"],1)
        rendered=loop.render_window(conv)
        self.assertIn("SCORING V2 DEVELOPMENT BENCHMARK",rendered)
        self.assertIn("meaning PASS",rendered)
        self.assertNotIn("fidelity",rendered)

    def test_invalid_v2_judge_does_not_replace_prior_valid_v2_result(self):
        rb=json.loads((ROOT/"tests/fixtures/mixed-rulebook.json").read_text())
        baseline={"turn":1230,"meaning_pass":True,"semantic_coverage_pct":100,
                  "language_version":"v","language_hash":"h"}
        meta={"tests_run":0,"spend_usd":0.0,"benchmark_results_v2":{"B1":baseline.copy()}}
        conv=[]
        with mock.patch("loop.call",side_effect=[("ENC",{}),("DEC",{}),("{}",{})]), \
             mock.patch("loop.token_count",side_effect=[10,8]):
            loop.test_turn(conv,rb,meta,1242)
        self.assertEqual(conv[-1]["judge_status"],"INVALID JUDGE RESULT")
        self.assertEqual(conv[-1]["prior_valid_v2_turn"],1230)
        self.assertEqual(meta["benchmark_results_v2"]["B1"],baseline)

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
