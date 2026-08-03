import copy
import json
import hashlib
import unittest
from pathlib import Path
from unittest import mock

import loop
from legislative_protocol import (
    build_post_state_receipt,
    current_open_motion,
    derive_semantic_fault_ledger,
    select_semantic_fault_for_turn,
    validate_action,
)
from rulebook import apply_typed_motion, language_payload
from state_store import snapshot_hash

ROOT = Path(__file__).parents[2]


class EvidenceTests(unittest.TestCase):
    def _valid_grade(self, benchmark):
        decoded = "\n".join(atom["meaning"] for atom in benchmark["answer_key"])
        grade = {"mode": "RELAY", "items": [
            {
                "id": atom["id"],
                "verdict": "SURVIVED",
                "evidence_lines": [line_number, line_number],
            }
            for line_number, atom in enumerate(benchmark["answer_key"], start=1)
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
                    "evidence_lines": [line_number, line_number],
                }
                for line_number, atom in enumerate(benchmark["answer_key"], start=1)
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
            "\n\nNUMBERED DECODED:\n", 1
        )[0]
        grader_key = json.loads(key_json)
        self.assertEqual(
            [atom["literal_sets"] for atom in grader_key],
            [atom["literal_sets"] for atom in benchmark["answer_key"]],
        )
        projected_target = next(atom for atom in grader_key if atom["id"] == target_id)
        self.assertEqual(projected_target["missing_literal_sets"], [[literal]])
        self.assertEqual(projected_target["literal_set_lines"], [[]])
        self.assertIn("SURVIVED is forbidden", grader_system)
        self.assertIn("CORRUPTED", grader_system)
        self.assertIn("MISSING", grader_system)
        self.assertFalse(invalid_event["judge_valid"])
        self.assertEqual(invalid_event["judge_status"], "INVALID JUDGE RESULT")
        self.assertEqual(invalid_event["judge_reason"], f"deterministic_conflict:{target_id}")
        self.assertEqual(invalid_event["judge_diagnostic"]["atom_id"], target_id)

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
        ledger = loop.derive_semantic_fault_ledger([valid_event])
        fault = next(
            entry for entry in ledger if entry.latest_source.atom_id == target_id
        )
        self.assertEqual(fault.classification, "CORRUPTED")
        self.assertEqual(fault.latest_source.decoded_evidence, corrupted_evidence)

    def test_production_evidence_patterns_use_harness_owned_contiguous_spans(self):
        cases = (
            (
                "B2.12",
                "Weld-Series Gamma is the longitudinal seam.",
                [["Weld-Series Gamma"]],
                "Before re-test, inspect Weld-Series Gamma.\n"
                "This is the longitudinal seam fabricated by Arclight.",
                [1, 2],
            ),
            (
                "B4.28",
                "The perishables in Bay 3 are confirmed intact.",
                [["Bay 3"]],
                "Temperature in Bay 3 held steady at 34°F; perishables are intact.",
                [1, 1],
            ),
            (
                "B4.26",
                "The final summary to Erica includes the action taken on each unit.",
                [["Erica"]],
                "Final summary to Erica: include action taken on each freezer-coil unit.",
                [1, 1],
            ),
        )
        for atom_id, meaning, literal_sets, decoded, evidence_lines in cases:
            with self.subTest(atom_id=atom_id):
                raw_grade = {
                    "mode": "RELAY",
                    "items": [{
                        "id": atom_id,
                        "verdict": "SURVIVED",
                        "evidence_lines": evidence_lines,
                    }],
                    "inventions": [],
                }
                materialized, reason = loop._materialize_grader_evidence(
                    raw_grade, decoded
                )
                self.assertIsNone(reason)
                result = loop.score_judgment_v2(
                    [{
                        "id": atom_id,
                        "meaning": meaning,
                        "critical": True,
                        "literal_sets": literal_sets,
                    }],
                    materialized,
                    decoded,
                    20,
                )
                self.assertTrue(result["valid"])
                self.assertTrue(result["meaning_pass"])
                self.assertIn(
                    literal_sets[0][0],
                    result["items"][0]["evidence"],
                )

    def test_malformed_or_legacy_evidence_references_fail_closed(self):
        decoded = "Line one.\nLine two."
        for evidence_lines in (
            None, [0, 1], [2, 1], [1, 3], [True, 1], ["1", 1], [1], [1, 2, 3]
        ):
            with self.subTest(evidence_lines=evidence_lines):
                item = {"id": "B1.01", "verdict": "SURVIVED"}
                if evidence_lines is None:
                    item["evidence"] = "Line one."
                else:
                    item["evidence_lines"] = evidence_lines
                _, reason = loop._materialize_grader_evidence(
                    {"mode": "RELAY", "items": [item], "inventions": []},
                    decoded,
                )
                self.assertEqual(reason, "invalid_evidence_line_range:B1.01")

    def test_deterministic_evidence_keeps_real_language_losses_failed(self):
        decoded = (
            "Use prescription map.\n"
            "If TX-88773 is over 475 gigabits, pause env:staging dataflows."
        )
        raw_grade = {
            "mode": "RELAY",
            "items": [
                {"id": "B3.10", "verdict": "MISSING", "evidence_lines": []},
                {"id": "B5.26", "verdict": "CORRUPTED", "evidence_lines": [2, 2]},
            ],
            "inventions": [],
        }
        materialized, reason = loop._materialize_grader_evidence(raw_grade, decoded)
        self.assertIsNone(reason)
        result = loop.score_judgment_v2(
            [
                {
                    "id": "B3.10", "meaning": "Use tag v4_final.",
                    "critical": True, "literal_sets": [["v4_final"]],
                },
                {
                    "id": "B5.26", "meaning": "Pause dataflows tagged env: staging.",
                    "critical": True, "literal_sets": [["env: staging"]],
                },
            ],
            materialized,
            decoded,
            20,
        )
        self.assertTrue(result["valid"])
        self.assertFalse(result["meaning_pass"])
        self.assertEqual(result["semantic_coverage_pct"], 0)
        self.assertEqual(
            [failure["atom_id"] for failure in result["critical_failures"]],
            ["B3.10", "B5.26"],
        )

    def test_b1_dropped_currency_symbol_is_visible_to_the_grader(self):
        self._assert_literal_loss_reaches_grader(
            benchmark_id="B1", target_id="B1.03", literal="$48",
            replacement="48", turn=1506,
        )

    def test_b2_compacted_vessel_identifier_is_visible_to_the_grader(self):
        self._assert_literal_loss_reaches_grader(
            benchmark_id="B2", target_id="B2.01", literal="C-18A",
            replacement="c18a", turn=1509,
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


class SemanticFaultLedgerTests(unittest.TestCase):
    def _fault_event(self, *, turn=1506, verdict="MISSING", evidence=""):
        return {
            "turn": turn,
            "agent": "harness",
            "type": "test",
            "era": "benchmark-v2",
            "benchmark_id": "B2",
            "benchmark_version": "v2",
            "scoring_version": "v2",
            "language_version": "adopted-a",
            "language_hash": "a" * 64,
            "judge_valid": True,
            "judge_status": "VALID",
            "meaning_pass": verdict == "SURVIVED",
            "answer_key": [
                {
                    "id": "B2.04",
                    "meaning": "Use routing token ref_8.delta.",
                    "critical": True,
                    "literal_sets": [["ref_8.delta"]],
                }
            ],
            "atom_results": [
                {"id": "B2.04", "verdict": verdict, "evidence": evidence}
            ],
            "critical_failures": (
                []
                if verdict == "SURVIVED"
                else [
                    {
                        "atom_id": "B2.04",
                        "decoded_evidence": evidence,
                        "expected_meaning": "Use routing token ref_8.delta.",
                        "verdict": verdict,
                    }
                ]
            ),
            "original": "PRIVATE ORIGINAL",
            "encoded": "PRIVATE ENCODED",
            "decoded": "PRIVATE DECODED",
        }

    def _book(self):
        return {"version": "0.0", "changes": 0, "next_id": 1, "rules": []}

    def _legislative_event(
        self,
        book,
        *,
        turn,
        role,
        payload,
        required_fault_token=None,
    ):
        before = copy.deepcopy(book)
        action = validate_action(
            payload,
            role,
            book,
            required_fault_token=required_fault_token,
        )
        motion_receipt = apply_typed_motion(
            action.motion, book, turn, role, action.deliberation
        )
        if motion_receipt.changed:
            book["version"] = f"0.{book['changes'] + 1}"
            book["changes"] += 1
        post_state = build_post_state_receipt(
            turn=turn,
            role=role,
            action=action,
            result="accepted" if motion_receipt.accepted else "rejected",
            reason=motion_receipt.reason,
            before_rulebook=before,
            after_rulebook=book,
            next_actor="A" if role == "B" else "B",
            attempts=1,
        )
        return {
            "turn": turn,
            "agent": "harness",
            "type": "legislature",
            "protocol": "structured-legislature-v1",
            "motion_receipt": motion_receipt.dict(),
            "post_state_receipt": post_state.model_dump(mode="json"),
        }

    def _linked_proposal(self):
        exam = self._fault_event()
        token = derive_semantic_fault_ledger([exam])[0].fault_token
        book = self._book()
        proposal = self._legislative_event(
            book,
            turn=1507,
            role="A",
            required_fault_token=token,
            payload={
                "deliberation": "Public proposal: preserve this general invariant.",
                "motion": {
                    "kind": "PROPOSE",
                    "text": "Preserve opaque identifiers exactly, including punctuation and case.",
                },
                "fault_response": {
                    "status": "REPAIR_PROPOSED",
                    "fault_token": token,
                },
                "measurements": [],
                "requests": [],
            },
        )
        return exam, proposal, book

    def test_proposal_request_reject_and_adopt_follow_canonical_receipts(self):
        exam, proposal, request_book = self._linked_proposal()
        proposed = derive_semantic_fault_ledger([exam, proposal])[0]
        self.assertEqual(proposed.status, "REPAIR_PROPOSED")
        self.assertEqual(proposed.linked_motion_rule_id, "rule-001")

        request = self._legislative_event(
            request_book,
            turn=1508,
            role="B",
            payload={
                "deliberation": "Public audit: verify the punctuation boundary.",
                "motion": {
                    "kind": "REQUEST",
                    "target_rule_id": "rule-001",
                    "focus": "Test punctuation and case on one hostile opaque identifier.",
                },
                "measurements": [],
                "requests": [],
            },
        )
        requested = derive_semantic_fault_ledger([exam, proposal, request])[0]
        self.assertEqual(requested.status, "REPAIR_PROPOSED")
        self.assertEqual(requested.linked_motion_rule_id, "rule-001")

        refreshed_failure = self._fault_event(turn=1509)
        refreshed = derive_semantic_fault_ledger(
            [exam, proposal, request, refreshed_failure]
        )[0]
        self.assertEqual(refreshed.status, "REPAIR_PROPOSED")
        self.assertEqual(refreshed.last_failure_turn, 1509)
        self.assertEqual(
            select_semantic_fault_for_turn(
                [refreshed],
                role="A",
                open_motion=current_open_motion(request_book),
            ).fault_token,
            refreshed.fault_token,
        )
        revision = self._legislative_event(
            request_book,
            turn=1510,
            role="A",
            payload={
                "deliberation": "Public proposal: tighten the identifier boundary.",
                "motion": {
                    "kind": "REVISE",
                    "target_rule_id": "rule-001",
                    "text": "Preserve opaque identifiers and all internal punctuation exactly.",
                },
                "measurements": [],
                "requests": [],
            },
        )
        adopt_after_revision = self._legislative_event(
            request_book,
            turn=1511,
            role="B",
            payload={
                "deliberation": "Public audit: adopt the revised general boundary.",
                "motion": {"kind": "ADOPT", "target_rule_id": "rule-001"},
                "measurements": [],
                "requests": [],
            },
        )
        after_interleaving = derive_semantic_fault_ledger(
            [
                exam,
                proposal,
                request,
                refreshed_failure,
                revision,
                adopt_after_revision,
            ]
        )[0]
        self.assertEqual(after_interleaving.status, "PENDING_RETEST")
        self.assertEqual(after_interleaving.adoption_turn, 1511)

        exam, proposal, reject_book = self._linked_proposal()
        rejected_event = self._legislative_event(
            reject_book,
            turn=1508,
            role="B",
            payload={
                "deliberation": "Public audit: reject the proposed boundary.",
                "motion": {"kind": "REJECT", "target_rule_id": "rule-001"},
                "measurements": [],
                "requests": [],
            },
        )
        rejected = derive_semantic_fault_ledger(
            [exam, proposal, rejected_event]
        )[0]
        self.assertEqual(rejected.status, "UNRESOLVED")

        exam, proposal, adopt_book = self._linked_proposal()
        adopted_event = self._legislative_event(
            adopt_book,
            turn=1508,
            role="B",
            payload={
                "deliberation": "Public audit: adopt the general identifier boundary.",
                "motion": {"kind": "ADOPT", "target_rule_id": "rule-001"},
                "measurements": [],
                "requests": [],
            },
        )
        adopted = derive_semantic_fault_ledger(
            [exam, proposal, adopted_event]
        )[0]
        self.assertEqual(adopted.status, "PENDING_RETEST")
        self.assertEqual(adopted.adoption_turn, 1508)

    def test_only_later_valid_same_atom_retest_can_resolve_or_reactivate(self):
        exam, proposal, book = self._linked_proposal()
        adopted_event = self._legislative_event(
            book,
            turn=1508,
            role="B",
            payload={
                "deliberation": "Public audit: adopt the general identifier boundary.",
                "motion": {"kind": "ADOPT", "target_rule_id": "rule-001"},
                "measurements": [],
                "requests": [],
            },
        )
        base = [exam, proposal, adopted_event]

        invalid = self._fault_event(turn=1509, verdict="SURVIVED", evidence="ref_8.delta")
        invalid.update({"judge_valid": False, "judge_status": "INVALID JUDGE RESULT"})
        self.assertEqual(
            derive_semantic_fault_ledger(base + [invalid])[0].status,
            "PENDING_RETEST",
        )

        other = self._fault_event(turn=1509, verdict="SURVIVED", evidence="ref_8.delta")
        other["benchmark_id"] = "B3"
        other["answer_key"][0]["id"] = "B3.04"
        other["atom_results"][0]["id"] = "B3.04"
        self.assertEqual(
            derive_semantic_fault_ledger(base + [other])[0].status,
            "PENDING_RETEST",
        )

        survived = self._fault_event(
            turn=1509, verdict="SURVIVED", evidence="ref_8.delta"
        )
        resolved = derive_semantic_fault_ledger(base + [survived])[0]
        self.assertEqual(resolved.status, "RESOLVED")
        self.assertEqual(resolved.resolved_turn, 1509)

        failed = self._fault_event(turn=1512)
        reactivated = derive_semantic_fault_ledger(base + [failed])[0]
        self.assertEqual(reactivated.status, "UNRESOLVED")
        self.assertEqual(reactivated.last_failure_turn, 1512)

    def test_state_machine_noop_cannot_claim_repair_proposed(self):
        exam = self._fault_event()
        token = derive_semantic_fault_ledger([exam])[0].fault_token
        duplicate_text = (
            "Preserve opaque identifiers exactly, including punctuation and case."
        )
        book = {
            "version": "0.1",
            "changes": 1,
            "next_id": 2,
            "rules": [
                {
                    "id": "rule-001",
                    "text_en": duplicate_text,
                    "status": "adopted",
                    "history": [],
                }
            ],
        }
        noop = self._legislative_event(
            book,
            turn=1507,
            role="A",
            required_fault_token=token,
            payload={
                "deliberation": "Public proposal: repeat the existing identifier rule.",
                "motion": {"kind": "PROPOSE", "text": duplicate_text},
                "fault_response": {
                    "status": "REPAIR_PROPOSED",
                    "fault_token": token,
                },
                "measurements": [],
                "requests": [],
            },
        )
        self.assertEqual(noop["post_state_receipt"]["result"], "rejected")
        ledger = derive_semantic_fault_ledger([exam, noop])
        self.assertEqual(ledger[0].status, "UNRESOLVED")
        self.assertIsNone(ledger[0].linked_motion_rule_id)

    def test_turn_1506_to_1510_production_trace_keeps_critical_queue_private(self):
        canonical = json.loads((ROOT / "state/conversation.json").read_text())
        events = [
            copy.deepcopy(event)
            for event in canonical
            if 1506 <= int(event.get("turn", -1)) <= 1510
        ]
        events_hash = snapshot_hash(events)
        first_exam = next(
            event for event in events
            if event.get("turn") == 1506 and event.get("type") == "test"
        )
        later_exam = next(
            event for event in events
            if event.get("turn") == 1509 and event.get("type") == "test"
        )
        first_critical_ids = {
            failure["atom_id"] for failure in first_exam["critical_failures"]
        }

        # Reproduce the broken reader: the first failed atom is noncritical.
        old_choice = next(
            item for item in later_exam["atom_results"]
            if item["verdict"] in {"MISSING", "CORRUPTED"}
        )
        key_row = next(
            atom for atom in later_exam["answer_key"] if atom["id"] == old_choice["id"]
        )
        self.assertFalse(key_row["critical"])
        self.assertEqual(old_choice["id"], "B4.01")
        turn_1510_message = next(
            event for event in events
            if event.get("turn") == 1510 and event.get("type") == "message"
        )
        turn_1510_receipt = next(
            event for event in events
            if event.get("turn") == 1510 and event.get("type") == "legislature"
        )
        self.assertIn(old_choice["id"], turn_1510_message["content"])
        self.assertEqual(
            turn_1510_message["structured_action"]["motion"]["kind"], "PROPOSE"
        )
        self.assertEqual(
            turn_1510_receipt["post_state_receipt"]["current_open_motion"]["target_rule_id"],
            turn_1510_receipt["motion_receipt"]["rule_id"],
        )

        suite = loop.load_benchmark_suite()
        ledger = derive_semantic_fault_ledger(events, benchmark_suite=suite)
        ledger_ids = {entry.latest_source.atom_id for entry in ledger}
        self.assertTrue(first_critical_ids.issubset(ledger_ids))
        self.assertNotIn(old_choice["id"], ledger_ids)
        self.assertTrue(all(entry.status == "UNRESOLVED" for entry in ledger))
        self.assertEqual(
            ledger[0].latest_source.atom_id,
            first_exam["critical_failures"][0]["atom_id"],
        )
        self.assertEqual(
            ledger[1].latest_source.atom_id,
            first_exam["critical_failures"][1]["atom_id"],
        )
        suite_atoms = {
            atom["id"]: atom
            for row in suite["benchmarks"]
            if row["id"] == first_exam["benchmark_id"]
            for atom in row["answer_key"]
        }
        for entry in ledger[:2]:
            self.assertEqual(
                entry.latest_source.required_literal_sets,
                suite_atoms[entry.latest_source.atom_id]["literal_sets"],
            )
        selected = select_semantic_fault_for_turn(
            ledger, role="A", open_motion=None
        )
        self.assertEqual(selected.fault_token, ledger[0].fault_token)
        self.assertEqual(
            [entry.model_dump(mode="json") for entry in ledger],
            [
                entry.model_dump(mode="json")
                for entry in derive_semantic_fault_ledger(
                    json.loads(json.dumps(events)), benchmark_suite=suite
                )
            ],
        )
        self.assertEqual(snapshot_hash(events), events_hash)

        # The eligible prompt uses the exact production B3 source internally,
        # but none of its answer material crosses the model boundary.
        settled_book = json.loads((ROOT / "state/rulebook.json").read_text())
        open_rule = next(rule for rule in settled_book["rules"] if rule["id"] == "rule-176")
        open_rule["status"] = "rejected"
        assembled = loop.assemble_legislative_prompt(
            [event for event in events if event.get("turn") <= 1509],
            settled_book,
            turn=1513,
            agent="A",
            collaboration_input=None,
        )
        self.assertIsNotNone(
            assembled["prompt_request"]["semantic_fault_feedback"]
        )
        private_values = {
            first_exam["benchmark_id"],
            first_exam["original"],
            first_exam["encoded"],
            first_exam["decoded"],
        }
        for failure in first_exam["critical_failures"]:
            private_values.add(failure["atom_id"])
            private_values.add(failure["expected_meaning"])
            if failure["decoded_evidence"]:
                private_values.add(failure["decoded_evidence"])
            for group in suite_atoms[failure["atom_id"]]["literal_sets"]:
                private_values.update(group)
        new_fault_surface = json.dumps(
            {
                "feedback": assembled["prompt_request"]["semantic_fault_feedback"],
                "schema": assembled["request_options"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        for private_value in private_values:
            self.assertNotIn(private_value, new_fault_surface)


if __name__ == "__main__": unittest.main()
