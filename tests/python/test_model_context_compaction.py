import copy
import json
import unittest
from unittest import mock

import collaboration
import loop
from collaboration import (
    MAX_RESEARCH_DELIVERY_JSON_CHARS,
    deliver_one,
    empty_state,
    project_research_delivery_for_prompt,
    stable_record,
)
from project_lookup import PROJECT_FINDINGS_PREFIX
from legislative_protocol import (
    MAX_SEMANTIC_FAULT_PROMPT_CHARS,
    action_request_options,
    build_legislative_request,
    build_post_state_receipt,
    derive_semantic_fault_ledger,
    prompt_receipt_projection,
    prompt_request_projection,
)
from rulebook import language_payload, render_language, render_legislature
from state_store import snapshot_hash


def production_book():
    rules = []
    for index in range(1, 127):
        status = "adopted" if index <= 23 else (
            "rejected" if index % 4 == 0 else "historical"
        )
        rules.append(
            {
                "id": f"rule-{index:03d}",
                "text_en": (
                    f"Rule {index:03d} preserves one explicit language boundary. "
                    + ("Deterministic historical context remains inspectable. " * 4)
                ),
                "status": status,
                "history": [
                    {
                        "verb": status,
                        "turn": 1000 + index,
                        "agent": "A" if index % 2 else "B",
                    }
                ],
            }
        )
    rules.append(
        {
            "id": "rule-132",
            "text_en": (
                "Use one focused boundary marker only after both agents define "
                "the exact scope it replaces."
            ),
            "status": "proposed",
            "proposed_turn": 1204,
            "history": [{"verb": "proposed", "turn": 1204, "agent": "A"}],
        }
    )
    return {
        "version": "0.132",
        "changes": 132,
        "next_id": 133,
        "rules": rules,
    }


def full_receipt(book, turn, actor):
    language = language_payload(book)
    return {
        "authoritative": True,
        "protocol_version": "structured-legislature-v1",
        "turn": turn,
        "actor": actor,
        "attempted_action": {
            "deliberation": (
                "The motion remains open while the auditor checks a focused "
                "boundary. " * 10
            ),
            "motion": {
                "kind": "REQUEST",
                "target_rule_id": "rule-132",
                "focus": "Test the exact boundary against one hostile transfer.",
            },
            "measurements": [],
            "requests": [],
        },
        "result": "accepted",
        "reason": "focused_work_requested",
        "attempts": 1,
        "changed_rule_ids": [],
        "unchanged_rule_ids": [rule["id"] for rule in book["rules"]],
        "current_open_motion": {
            "kind": "add",
            "target_rule_id": "rule-132",
            "proposed_turn": 1204,
        },
        "adopted_count": len(language["rules"]),
        "adopted_language_hash": language["hash"],
        "rulebook_version": book["version"],
        "rulebook_changes": book["changes"],
        "rulebook_hash": snapshot_hash(book),
        "next_actor": "B",
    }


def production_window(book):
    events = []
    for index in range(15):
        turn = 1180 + index * 2
        events.append(
            {
                "turn": turn,
                "agent": "A",
                "type": "message",
                "content": (
                    "I am restating the same attempted action in agent prose while "
                    "the canonical machine receipt remains authoritative. " * 8
                ),
            }
        )
        events.append(
            {
                "turn": turn,
                "agent": "harness",
                "type": "legislature",
                "post_state_receipt": full_receipt(book, turn, "A"),
            }
        )
    return events


def answered_lookup():
    findings = (
        "Direct answer: rule-132 is the one open add motion and Agent B must "
        "settle it or request focused work. "
    )
    findings += "CANONICAL_LOOKUP_DETAIL " * (
        (14_050 - len(findings)) // len("CANONICAL_LOOKUP_DETAIL ") + 1
    )
    findings = findings[:14_020] + "UNBOUNDED_TAIL_SENTINEL_1202"
    row = stable_record(
        "LOOKUP",
        "B",
        "What is the exact current authority boundary for rule-132?",
        "lookup-1202-b",
    )
    row.update(
        {
            "status": "answered",
            "findings": findings,
            "limitations": [
                "The project corpus cannot establish private intent.",
                "Only canonical state and history were inspected.",
            ],
            "citations": [
                {
                    "title": f"Canonical project source {index}",
                    "url": (
                        "https://github.com/isorabins/alanguagealltheirown/"
                        f"blob/main/evidence/source-{index}.json"
                    ),
                }
                for index in range(10)
            ],
            "route": "project",
            "answer_turn": 1203,
            "evidence_count": 10,
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "web_search_requests": 0,
            },
            "cost_usd": 0,
        }
    )
    return row


def unprojected_window(events):
    rendered = []
    for event in events[-loop.WINDOW :]:
        if event["type"] == "legislature":
            rendered.append(
                f"[turn {event['turn']} — AUTHORITATIVE POST-STATE RECEIPT]\n"
                + json.dumps(
                    event["post_state_receipt"],
                    sort_keys=True,
                    ensure_ascii=False,
                )
            )
        else:
            rendered.append(
                f"[turn {event['turn']} — NON-AUTHORITATIVE AGENT DISCUSSION] "
                f"AGENT {event['agent']}:\n{event['content']}"
            )
    return "\n\n".join(rendered)


def unprojected_prompt(events, book, delivery):
    request = build_legislative_request(
        role="B",
        turn=1210,
        next_live_test_turn=1212,
        rulebook=book,
        latest_receipt=events[-1]["post_state_receipt"],
        collaboration_input=delivery,
    )
    constitution = (loop.ROOT / "prompts" / "constitution.md").read_text()
    role_prompt = (loop.ROOT / "prompts" / "agent_b.md").read_text()
    system = (
        f"{constitution}\n\n{role_prompt}\n\n"
        f"=== ADOPTED LANGUAGE ===\n{render_language(book)}\n\n"
        f"=== COMPLETE LEGISLATURE ===\n{render_legislature(book)}\n\n"
        "=== AUTHORITATIVE CURRENT MACHINE STATE AND RECEIPT ===\n"
        f"{request.model_dump_json(indent=2)}"
    )
    user = (
        "=== RECENT EVENT WINDOW ===\n"
        + unprojected_window(events)
        + "\n\nIt is turn 1210. You are Agent B. "
        "Return only the structured response required by the supplied schema."
    )
    return system, user


class ProjectionUnitTests(unittest.TestCase):
    def test_receipt_and_request_projections_are_prompt_only(self):
        book = production_book()
        receipt = full_receipt(book, 1209, "A")
        request = build_legislative_request(
            role="B",
            turn=1210,
            next_live_test_turn=1212,
            rulebook=book,
            latest_receipt=receipt,
            collaboration_input=None,
        )
        canonical_json = request.model_dump_json()
        receipt_projection = prompt_receipt_projection(receipt)
        request_projection = prompt_request_projection(request)

        self.assertEqual(
            set(receipt_projection),
            {
                "turn",
                "actor",
                "result",
                "reason",
                "attempts",
                "changed_rule_ids",
                "current_open_motion",
                "adopted_count",
                "adopted_language_hash",
                "rulebook_version",
                "rulebook_hash",
                "next_actor",
            },
        )
        self.assertNotIn("rule_states", request_projection["current_state"])
        self.assertIn("rule_states", request.current_state.model_dump())
        self.assertIn("attempted_action", request.latest_receipt.model_dump())
        self.assertIn("unchanged_rule_ids", request.latest_receipt.model_dump())
        self.assertEqual(request.model_dump_json(), canonical_json)
        self.assertIsNone(request_projection["active_legislative_feedback"])
        self.assertIsNone(request_projection["semantic_fault_feedback"])

    def test_schema_describes_the_unchanged_substantive_deliberation_boundary(self):
        schema = action_request_options("B", production_book())["response_format"][
            "json_schema"
        ]["schema"]
        deliberation = schema["properties"]["deliberation"]

        self.assertEqual(deliberation["minLength"], 12)
        self.assertEqual(deliberation["pattern"], "[A-Za-z0-9]")
        self.assertIn("public-facing summary", deliberation["description"])
        self.assertIn("not private reasoning", deliberation["description"])

    def test_research_projection_is_bounded_deterministic_and_preserves_full_delivery(self):
        state = empty_state()
        row = answered_lookup()
        state["research"].append(row)
        original = copy.deepcopy(row)
        canonical_delivery = {
            "kind": "RESEARCH",
            "id": original["id"],
            "question": original["question"],
            "findings": original["findings"],
            "limitations": original["limitations"],
            "citations": original["citations"],
            "route": original["route"],
        }
        row_hash = snapshot_hash(row)
        direct_projection = project_research_delivery_for_prompt(
            canonical_delivery
        )
        self.assertEqual(snapshot_hash(row), row_hash)

        delivered = deliver_one(state, "RESEARCH", "B", 1210)
        repeated = project_research_delivery_for_prompt(
            {"kind": "RESEARCH", **state["deliveries"][0]}
        )
        expected_state = empty_state()
        expected_row = copy.deepcopy(original)
        expected_row.update(
            {
                "status": "delivered",
                "delivered_to": "B",
                "delivery_turn": 1210,
            }
        )
        expected_state["research"].append(expected_row)
        expected_state["deliveries"].append(canonical_delivery)

        self.assertEqual(delivered, direct_projection)
        self.assertEqual(delivered, repeated)
        self.assertEqual(state, expected_state)
        self.assertLessEqual(
            len(json.dumps(delivered, ensure_ascii=False)),
            MAX_RESEARCH_DELIVERY_JSON_CHARS,
        )
        self.assertTrue(delivered["projection"]["truncated"])
        self.assertGreater(delivered["projection"]["findings_omitted_chars"], 0)
        self.assertEqual(delivered["projection"]["citations_original_count"], 10)
        self.assertLess(
            delivered["projection"]["citations_included_count"],
            delivered["projection"]["citations_original_count"],
        )
        self.assertEqual(state["research"][0]["findings"], original["findings"])
        self.assertEqual(state["research"][0]["citations"], original["citations"])
        self.assertEqual(state["deliveries"][0]["findings"], original["findings"])
        self.assertEqual(state["deliveries"][0]["citations"], original["citations"])

    def test_projection_preserves_exact_correlation_fields(self):
        delivery = {
            "kind": "RESEARCH",
            "id": "lookup-" + ("correlation-" * 20),
            "question": "Which exact source applies? " + ("context " * 100),
            "findings": "Direct answer.",
            "limitations": [],
            "citations": [],
            "route": "project-corpus-authoritative",
        }

        projected = project_research_delivery_for_prompt(delivery)

        for field in ("id", "question", "route"):
            self.assertEqual(projected[field], delivery[field])
            self.assertEqual(
                projected["projection"][f"{field}_omitted_chars"],
                0,
            )

    def test_quote_heavy_projection_fits_serialized_cap(self):
        delivery = {
            "kind": "RESEARCH",
            "id": "lookup-hostile-escaping",
            "question": 'What does the quoted "\\\\" evidence establish?',
            "findings": ('Direct answer: "\\\\quoted". ' * 500),
            "limitations": ['"\\\\' * 500],
            "citations": [
                {
                    "title": '"\\\\' * 60,
                    "url": f"https://example.test/{index}/" + ("%22" * 100),
                }
                for index in range(10)
            ],
            "route": "project",
        }

        projected = project_research_delivery_for_prompt(delivery)

        self.assertLessEqual(
            len(json.dumps(projected, ensure_ascii=False, separators=(",", ":"))),
            MAX_RESEARCH_DELIVERY_JSON_CHARS,
        )
        self.assertTrue(projected["findings"].startswith("Direct answer:"))
        self.assertTrue(projected["projection"]["truncated"])

    def test_project_findings_projection_keeps_complete_evidence_records(self):
        evidence = [
            {
                "source_id": f"source-{index}",
                "title": f"Canonical source {index}",
                "data": {"answer": f"complete answer {index}"},
            }
            for index in range(5)
        ]
        findings = PROJECT_FINDINGS_PREFIX + json.dumps(
            evidence,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        delivery = {
            "kind": "RESEARCH",
            "id": "lookup-complete-records",
            "question": "Which canonical records answer the question?",
            "findings": findings,
            "limitations": [],
            "citations": [],
            "route": "project",
        }

        projected = project_research_delivery_for_prompt(delivery)
        rendered_records, bounded_note = projected["findings"].split(
            "\n[bounded projection:", 1
        )
        included = json.loads(rendered_records[len(PROJECT_FINDINGS_PREFIX):])

        self.assertEqual(included, evidence[:2])
        self.assertIn("2 of 5 evidence records included", bounded_note)
        self.assertIn("3 omitted", bounded_note)
        self.assertGreater(
            projected["projection"]["findings_omitted_chars"],
            0,
        )

    def test_oversized_project_record_never_becomes_partial_json(self):
        evidence = [
            {
                "source_id": "oversized-source",
                "data": {"answer": "x" * 5_000},
            },
            {"source_id": "small-source", "data": {"answer": "complete"}},
        ]
        findings = PROJECT_FINDINGS_PREFIX + json.dumps(
            evidence,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        delivery = {
            "kind": "RESEARCH",
            "id": "lookup-oversized-record",
            "question": "Which complete evidence records fit?",
            "findings": findings,
            "limitations": [],
            "citations": [],
            "route": "project",
        }

        projected = project_research_delivery_for_prompt(delivery)
        rendered_records, bounded_note = projected["findings"].split(
            "\n[bounded projection:", 1
        )
        included = json.loads(rendered_records[len(PROJECT_FINDINGS_PREFIX):])

        self.assertEqual(included, [])
        self.assertIn("0 of 2 evidence records included", bounded_note)
        self.assertIn("2 omitted", bounded_note)
        self.assertLessEqual(
            len(json.dumps(projected, ensure_ascii=False, separators=(",", ":"))),
            MAX_RESEARCH_DELIVERY_JSON_CHARS,
        )

    def test_projection_failure_cannot_consume_delivery(self):
        state = empty_state()
        row = answered_lookup()
        state["research"].append(row)
        before = copy.deepcopy(state)

        with mock.patch.object(
            collaboration,
            "project_research_delivery_for_prompt",
            side_effect=RuntimeError("projection failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "projection failed"):
                collaboration.deliver_one(state, "RESEARCH", "B", 1210)

        self.assertEqual(state, before)


class ActiveLegislativeFeedbackPromptTests(unittest.TestCase):
    def _request_receipt(self, book, turn, focus):
        receipt = full_receipt(book, turn, "B")
        receipt["attempted_action"]["motion"]["focus"] = focus
        return {"turn": turn, "agent": "harness", "type": "legislature", "post_state_receipt": receipt}

    def _assemble(self, events, book, agent):
        return loop.assemble_legislative_prompt(
            events, book, turn=1220, agent=agent, collaboration_input=None
        )

    def test_current_exact_request_reaches_agent_a_without_mutating_canonical_inputs(self):
        book = production_book()
        focus = "Test the exact boundary against one hostile transfer."
        events = [self._request_receipt(book, 1209, focus)]
        book_hash, event_hash = snapshot_hash(book), snapshot_hash(events)

        assembled = self._assemble(events, book, "A")

        self.assertEqual(
            assembled["prompt_request"]["active_legislative_feedback"],
            {"kind": "REQUEST", "target_rule_id": "rule-132", "focus": focus, "request_turn": 1209},
        )
        self.assertIn(focus, assembled["system"])
        self.assertNotIn("RECENT EVENT WINDOW", assembled["system"])
        self.assertEqual(snapshot_hash(book), book_hash)
        self.assertEqual(snapshot_hash(events), event_hash)

    def test_request_survives_revision_structural_failure_and_reconstruction_to_agent_b(self):
        book = production_book()
        focus = "Test the exact boundary against one hostile transfer."
        events = [self._request_receipt(book, 1209, focus)]
        before_revision = copy.deepcopy(book)
        book["rules"][-1]["text_en"] = "Use the boundary marker only after its hostile scope is explicit."
        book["rules"][-1]["proposed_turn"] = 1210
        revision = build_post_state_receipt(
            turn=1210, role="A", result="accepted", reason="motion_applied",
            action={"deliberation": "The focused revision preserves the open boundary.", "motion": {"kind": "REVISE", "target_rule_id": "rule-132", "text": book["rules"][-1]["text_en"]}, "measurements": [], "requests": []},
            before_rulebook=before_revision, after_rulebook=book, next_actor="B", attempts=1,
        ).model_dump(mode="json")
        failure = build_post_state_receipt(
            turn=1211, role="B", action=None, result="structural_failure",
            reason="structural_validation_exhausted: invalid JSON", before_rulebook=book,
            after_rulebook=book, next_actor="B", attempts=3,
        ).model_dump(mode="json")
        events.extend([
            {"turn": 1210, "agent": "harness", "type": "legislature", "post_state_receipt": revision},
            {"turn": 1211, "agent": "harness", "type": "legislature", "post_state_receipt": failure},
        ])

        assembled = self._assemble(copy.deepcopy(events), book, "B")

        self.assertEqual(assembled["prompt_request"]["active_legislative_feedback"]["focus"], focus)
        self.assertIn(focus, assembled["system"])

    def test_newer_request_supersedes_the_older_request(self):
        book = production_book()
        older = "Test the first exact boundary before adoption."
        newer = "Test the replacement boundary against mixed conditional lists."
        events = [self._request_receipt(book, 1209, older), self._request_receipt(book, 1212, newer)]

        assembled = self._assemble(events, book, "A")

        self.assertEqual(assembled["prompt_request"]["active_legislative_feedback"]["focus"], newer)
        self.assertIn(newer, assembled["system"])
        self.assertNotIn(older, assembled["system"])

    def test_matching_adoption_or_rejection_clears_feedback(self):
        focus = "Test the exact boundary against one hostile transfer."
        for terminal_status in ("adopted", "rejected"):
            with self.subTest(terminal_status=terminal_status):
                book = production_book()
                events = [self._request_receipt(book, 1209, focus)]
                book["rules"][-1]["status"] = terminal_status

                assembled = self._assemble(events, book, "A")

                self.assertIsNone(assembled["prompt_request"]["active_legislative_feedback"])
                self.assertNotIn(focus, assembled["system"])

    def test_no_motion_preserves_feedback_but_unrelated_motion_does_not_receive_it(self):
        book = production_book()
        focus = "Test the exact boundary against one hostile transfer."
        events = [self._request_receipt(book, 1209, focus)]
        no_motion = build_post_state_receipt(
            turn=1210, role="A", action={"deliberation": "The open motion needs no additional action now.", "motion": None, "measurements": [], "requests": []},
            result="accepted", reason="no_motion", before_rulebook=book, after_rulebook=book,
            next_actor="B", attempts=1,
        ).model_dump(mode="json")
        events.append({"turn": 1210, "agent": "harness", "type": "legislature", "post_state_receipt": no_motion})
        self.assertEqual(self._assemble(events, book, "B")["prompt_request"]["active_legislative_feedback"]["focus"], focus)

        unrelated = self._request_receipt(book, 1211, "Test an unrelated target boundary.")
        unrelated["post_state_receipt"]["attempted_action"]["motion"]["target_rule_id"] = "rule-126"
        unrelated["post_state_receipt"]["current_open_motion"]["target_rule_id"] = "rule-126"
        events.append(unrelated)
        assembled = self._assemble(events, book, "A")
        self.assertEqual(assembled["prompt_request"]["active_legislative_feedback"]["focus"], focus)
        self.assertNotIn("Test an unrelated target boundary.", assembled["system"])

    def test_settled_repeal_request_does_not_resurface_on_a_later_repeal_of_same_rule(self):
        first_repeal = production_book()
        target = first_repeal["rules"][-1]
        target["status"] = "adopted"
        target["pending_repeal"] = {
            "kind": "repeal",
            "target_id": target["id"],
            "rationale": "Remove the first version after one focused audit.",
            "proposed_turn": 1205,
            "agent": "A",
        }
        stale_focus = "Test the first repeal against one exact downstream dependency."
        stale_request = self._request_receipt(first_repeal, 1206, stale_focus)

        settled = copy.deepcopy(first_repeal)
        settled["rules"][-1].pop("pending_repeal")
        current = copy.deepcopy(settled)
        current["rules"][-1]["pending_repeal"] = {
            "kind": "repeal",
            "target_id": target["id"],
            "rationale": "Open a later independent repeal after the first settled.",
            "proposed_turn": 1215,
            "agent": "A",
        }
        creation = build_post_state_receipt(
            turn=1215,
            role="A",
            action={
                "deliberation": "A later independent repeal is now open for audit.",
                "motion": {
                    "kind": "REPEAL",
                    "target_rule_id": target["id"],
                    "rationale": "Open a later independent repeal after the first settled.",
                },
                "measurements": [],
                "requests": [],
            },
            result="accepted",
            reason="repeal_proposed",
            before_rulebook=settled,
            after_rulebook=current,
            next_actor="B",
            attempts=1,
        ).model_dump(mode="json")
        events = [stale_request, {
            "turn": 1215,
            "agent": "harness",
            "type": "legislature",
            "post_state_receipt": creation,
        }]

        assembled = self._assemble(events, current, "B")

        self.assertIsNone(assembled["prompt_request"]["active_legislative_feedback"])
        self.assertNotIn(stale_focus, assembled["system"])


class SemanticFaultFeedbackPromptTests(unittest.TestCase):
    def _failure_event(
        self,
        book,
        turn=1506,
        *,
        benchmark_id="B2",
        atom_id="B2.04",
        verdict="MISSING",
        evidence="",
        language_version=None,
        language_hash=None,
    ):
        language = language_payload(book)
        return {
            "turn": turn,
            "agent": "harness",
            "type": "test",
            "era": "benchmark-v2",
            "benchmark_id": benchmark_id,
            "benchmark_version": "v2",
            "scoring_version": "v2",
            "language_version": language_version or language["version"],
            "language_hash": language_hash or language["hash"],
            "judge_valid": True,
            "judge_status": "VALID",
            "meaning_pass": False,
            "answer_key": [
                {
                    "id": f"{benchmark_id}.01",
                    "meaning": "A noncritical location must not preempt repair work.",
                    "critical": False,
                    "literal_sets": [],
                },
                {
                    "id": atom_id,
                    "meaning": "Use routing token ref_8.delta.",
                    "critical": True,
                    "literal_sets": [["ref_8.delta"]],
                },
                {
                    "id": f"{benchmark_id}.19",
                    "meaning": "The allocation is 2.7 liters of batch QX-41.",
                    "critical": True,
                    "literal_sets": [["2.7"], ["liters"], ["QX-41"]],
                },
            ],
            "atom_results": [
                {
                    "id": f"{benchmark_id}.01",
                    "verdict": "CORRUPTED",
                    "evidence": "A noncritical location was normalized.",
                },
                {"id": atom_id, "verdict": verdict, "evidence": evidence},
                {
                    "id": f"{benchmark_id}.19",
                    "verdict": "MISSING",
                    "evidence": "",
                },
            ],
            "critical_failures": [
                {
                    "atom_id": atom_id,
                    "decoded_evidence": evidence,
                    "expected_meaning": "Use routing token ref_8.delta.",
                    "verdict": verdict,
                },
                {
                    "atom_id": f"{benchmark_id}.19",
                    "decoded_evidence": "",
                    "expected_meaning": "The allocation is 2.7 liters of batch QX-41.",
                    "verdict": "MISSING",
                },
            ],
            "original": "RAW_BENCHMARK_SENTINEL " * 100,
            "encoded": "RAW_ENCODED_SENTINEL " * 100,
            "decoded": "RAW_DECODED_SENTINEL " * 100,
            "grader_prompt": "RAW_GRADER_PROMPT_SENTINEL " * 100,
            "grader_deliberation": "RAW_GRADER_DELIBERATION_SENTINEL " * 100,
        }

    def _eligible_book(self):
        book = production_book()
        book["rules"][-1]["status"] = "rejected"
        return book

    def _assemble(self, events, book, agent, *, turn=1513):
        exam = next(event for event in events if event.get("type") == "test")
        suite = {
            "version": "v2",
            "benchmarks": [
                {
                    "id": exam["benchmark_id"],
                    "answer_key": copy.deepcopy(exam["answer_key"]),
                }
            ],
        }
        with mock.patch("loop.load_benchmark_suite", return_value=suite):
            return loop.assemble_legislative_prompt(
                events, book, turn=turn, agent=agent, collaboration_input=None
            )

    def test_eligible_agent_a_gets_one_abstract_schema_bound_fault(self):
        book = self._eligible_book()
        events = [self._failure_event(book)]
        book_hash, events_hash = snapshot_hash(book), snapshot_hash(events)

        assembled_a = self._assemble(events, book, "A")
        projection = assembled_a["prompt_request"]["semantic_fault_feedback"]
        self.assertEqual(
            set(projection),
            {"fault_token", "status", "classification", "failure_class", "invariant"},
        )
        self.assertEqual(projection["status"], "UNRESOLVED")
        self.assertEqual(projection["classification"], "MISSING")
        self.assertEqual(projection["failure_class"], "OPAQUE_IDENTIFIER")
        self.assertEqual(assembled_a["required_fault_token"], projection["fault_token"])
        schema = json.dumps(assembled_a["request_options"], sort_keys=True)
        self.assertIn(projection["fault_token"], schema)
        self.assertIn("REPAIR_PROPOSED", schema)
        self.assertLessEqual(
            len(json.dumps(projection, separators=(",", ":"))),
            MAX_SEMANTIC_FAULT_PROMPT_CHARS,
        )
        for private_value in (
            "B2.04",
            "B2.19",
            "ref_8.delta",
            "2.7",
            "liters",
            "QX-41",
            "RAW_BENCHMARK_SENTINEL",
            "RAW_ENCODED_SENTINEL",
            "RAW_DECODED_SENTINEL",
            "RAW_GRADER_PROMPT_SENTINEL",
            "RAW_GRADER_DELIBERATION_SENTINEL",
        ):
            self.assertNotIn(private_value, assembled_a["system"])
        self.assertEqual(snapshot_hash(book), book_hash)
        self.assertEqual(snapshot_hash(events), events_hash)

    def test_unrelated_open_motion_settles_without_fault_preemption(self):
        book = production_book()
        assembled = self._assemble([self._failure_event(book)], book, "B", turn=1511)
        self.assertIsNone(assembled["prompt_request"]["semantic_fault_feedback"])
        self.assertIsNone(assembled["required_fault_token"])

    def test_invalid_legacy_and_malformed_correlations_fail_closed(self):
        book = self._eligible_book()
        invalid = self._failure_event(book, 1506)
        invalid.update({"judge_valid": False, "judge_status": "INVALID JUDGE RESULT"})
        legacy = self._failure_event(book, 1507)
        legacy.update({"era": "benchmark-v1", "benchmark_version": "v1", "scoring_version": "v1"})
        malformed = self._failure_event(book, 1508)
        malformed["critical_failures"][0]["atom_id"] = "B3.99"

        assembled = self._assemble([invalid, legacy, malformed], book, "A")

        self.assertIsNone(assembled["prompt_request"]["semantic_fault_feedback"])
        self.assertNotIn("INVALID JUDGE RESULT", assembled["system"])
        self.assertNotIn("RAW_BENCHMARK_SENTINEL", assembled["system"])

    def test_language_hash_change_does_not_drop_private_queue(self):
        book = self._eligible_book()
        event = self._failure_event(
            book, 1506, language_version="adopted-before", language_hash="a" * 64
        )
        ledger = derive_semantic_fault_ledger([event])
        assembled = self._assemble([event], book, "A")
        self.assertEqual(len(ledger), 2)
        self.assertIsNotNone(assembled["prompt_request"]["semantic_fault_feedback"])


class ProductionShapedPromptTests(unittest.TestCase):
    def test_live_test_projection_keeps_outcome_not_duplicate_payloads(self):
        event = {
            "turn": 1209,
            "type": "test",
            "agent": "harness",
            "payload": "gen-prose-logistics",
            "orig_tokens": 553,
            "enc_tokens": 322,
            "token_delta_pct": -42,
            "fidelity": 76,
            "judge_reason": "valid",
            "lost": "one binding relationship was ambiguous",
            "total": 4,
            "survived": 3,
            "corrupted": ["binding relationship"],
            "missing": [],
            "invented": [],
            "encoded": "ENCODED_PAYLOAD_SENTINEL " * 200,
            "decoded": "DECODED_PAYLOAD_SENTINEL " * 200,
        }
        event_hash = snapshot_hash(event)

        rendered = loop.render_window([event])

        self.assertIn("AUTHORITATIVE LIVE TEST RECEIPT", rendered)
        self.assertIn("553 tokens -> encoded 322 tokens (-42%)", rendered)
        self.assertIn("decode fidelity 76/100", rendered)
        self.assertIn("binding relationship was ambiguous", rendered)
        self.assertIn("corrupted (1/1): binding relationship", rendered)
        self.assertNotIn("ENCODED_PAYLOAD_SENTINEL", rendered)
        self.assertNotIn("DECODED_PAYLOAD_SENTINEL", rendered)
        self.assertEqual(snapshot_hash(event), event_hash)

    def test_live_test_audit_details_are_size_bounded(self):
        event = {
            "turn": 1209,
            "type": "test",
            "agent": "harness",
            "payload": "gen-prose-logistics",
            "orig_tokens": 553,
            "enc_tokens": 322,
            "token_delta_pct": -42,
            "fidelity": 76,
            "judge_reason": "valid",
            "lost": "loss " * 30_000,
            "total": 12,
            "survived": 3,
            "corrupted": ["corrupted " * 20_000],
            "missing": ["missing " * 20_000],
            "invented": ["invented " * 20_000],
            "encoded": "ENCODED_PAYLOAD_SENTINEL " * 200,
            "decoded": "DECODED_PAYLOAD_SENTINEL " * 200,
        }
        event_hash = snapshot_hash(event)

        rendered = loop.render_window([event])

        self.assertLess(len(rendered), 2_000)
        for label in ("corrupted (1/1)", "missing (1/1)", "invented (1/1)"):
            self.assertIn(label, rendered)
        self.assertNotIn("ENCODED_PAYLOAD_SENTINEL", rendered)
        self.assertNotIn("DECODED_PAYLOAD_SENTINEL", rendered)
        self.assertEqual(snapshot_hash(event), event_hash)

    def test_127_rule_30_event_14k_lookup_prompt_is_materially_smaller_and_exact(self):
        book = production_book()
        events = production_window(book)
        state = empty_state()
        row = answered_lookup()
        state["research"].append(row)
        book_hash = snapshot_hash(book)
        event_hash = snapshot_hash(events)
        canonical_lookup = copy.deepcopy(row)
        full_delivery = {
            "kind": "RESEARCH",
            "id": row["id"],
            "question": row["question"],
            "findings": row["findings"],
            "limitations": row["limitations"],
            "citations": row["citations"],
            "route": row["route"],
        }
        legacy_system, legacy_user = unprojected_prompt(
            events, book, full_delivery
        )

        with mock.patch.object(loop.requests, "post") as web:
            delivery = deliver_one(state, "RESEARCH", "B", 1210)
            assembled = loop.assemble_legislative_prompt(
                events,
                book,
                turn=1210,
                agent="B",
                collaboration_input=delivery,
            )
        web.assert_not_called()

        compact_chars = len(assembled["system"]) + len(assembled["user"])
        legacy_chars = len(legacy_system) + len(legacy_user)
        self.assertLessEqual(compact_chars, int(legacy_chars * 0.70))
        self.assertEqual(assembled["total_chars"], compact_chars)
        self.assertEqual(snapshot_hash(book), book_hash)
        self.assertEqual(snapshot_hash(events), event_hash)
        self.assertEqual(state["research"][0]["findings"], canonical_lookup["findings"])
        self.assertEqual(state["research"][0]["citations"], canonical_lookup["citations"])
        self.assertIn("rule-132 [proposed]", assembled["system"])
        self.assertNotIn('"rule_states"', assembled["system"])
        self.assertNotIn('"attempted_action"', assembled["system"])
        self.assertNotIn('"unchanged_rule_ids"', assembled["system"])
        self.assertTrue(
            assembled["system"].startswith(
                "=== MANDATORY PUBLIC OUTPUT CONTRACT ==="
            )
        )
        self.assertIn(
            'beginning exactly "Public audit:"',
            assembled["user"],
        )
        self.assertNotIn("RECENT EVENT WINDOW", assembled["user"])
        self.assertNotIn("AUTHORITATIVE LIVE TEST RECEIPT", assembled["user"])
        self.assertNotIn("NON-AUTHORITATIVE AGENT DISCUSSION", assembled["user"])
        schema = json.dumps(assembled["request_options"], sort_keys=True)
        self.assertIn("rule-132", schema)
        self.assertNotIn("rule-126", schema)
        self.assertEqual(
            assembled["canonical_request"].current_state.rule_states[-1].rule_id,
            "rule-132",
        )

    def test_legislative_output_contract_covers_a_open_and_b_no_open(self):
        book = production_book()
        events = production_window(book)

        assembled_a = loop.assemble_legislative_prompt(
            events,
            book,
            turn=1214,
            agent="A",
            collaboration_input=None,
        )
        self.assertTrue(
            assembled_a["system"].startswith(
                "=== MANDATORY PUBLIC OUTPUT CONTRACT ==="
            )
        )
        self.assertIn(
            'beginning exactly "Public proposal:"',
            assembled_a["user"],
        )
        self.assertIn(
            '"deliberation":"Public proposal: the current idea needs one '
            'focused revision."',
            assembled_a["system"],
        )
        self.assertIn(
            '"motion":{"kind":"REVISE","target_rule_id":"rule-132"',
            assembled_a["system"],
        )

        book["rules"][-1]["status"] = "rejected"
        assembled_b = loop.assemble_legislative_prompt(
            events,
            book,
            turn=1215,
            agent="B",
            collaboration_input=None,
        )
        self.assertIn(
            "Audit only the authoritative current state",
            assembled_b["user"],
        )
        self.assertIn(
            '"deliberation":"Public audit: the authoritative current state '
            'needs a focused verification before adoption."',
            assembled_b["system"],
        )
        self.assertIn('"motion":null', assembled_b["system"])
        self.assertIn(
            "Never put legacy prose such as `ADOPT: rule-NNN`",
            assembled_b["system"],
        )

    def test_structural_failure_restores_full_state_and_redelivers_bounded_once(self):
        book = production_book()
        events = production_window(book)
        state = empty_state()
        row = answered_lookup()
        state["research"].append(row)
        before = copy.deepcopy(state)
        meta = {"last_agent": "A", "spend_usd": 0.0}
        valid = json.dumps(
            {
                "deliberation": "The proposal needs one focused boundary test.",
                "motion": {
                    "kind": "REQUEST",
                    "target_rule_id": "rule-132",
                    "focus": "Test the exact boundary against one hostile transfer.",
                },
                "measurements": [],
                "requests": [],
            }
        )
        outputs = iter(
            [
                ("not-json", {}),
                ("not-json", {}),
                ("not-json", {}),
                (valid, {"completion_tokens": 30}),
            ]
        )
        systems = []

        def fake_call(_model, system, _user, **_kwargs):
            systems.append(system)
            return next(outputs)

        with mock.patch.object(loop, "call", side_effect=fake_call), mock.patch.object(
            loop.requests, "post"
        ) as web:
            self.assertEqual(
                loop.agent_turn(events, book, meta, state, 1210),
                "structural_failure",
            )
            self.assertEqual(state, before)
            self.assertEqual(loop.agent_turn(events, book, meta, state, 1211), "accepted")
        web.assert_not_called()

        self.assertEqual(len(state["deliveries"]), 1)
        self.assertEqual(state["research"][0]["findings"], row["findings"])
        self.assertEqual(state["research"][0]["citations"], row["citations"])
        self.assertEqual(state["research"][0]["status"], "delivered")
        for system in systems:
            self.assertNotIn("UNBOUNDED_TAIL_SENTINEL_1202", system)
            self.assertIn('"findings_omitted_chars"', system)
            self.assertNotIn('"unchanged_rule_ids"', system)

    def test_agent_turn_repairs_only_deliberation_and_records_public_receipt(self):
        book = production_book()
        events = production_window(book)
        state = empty_state()
        row = answered_lookup()
        state["research"].append(row)
        meta = {"last_agent": "A", "spend_usd": 0.0}
        provider_output = json.dumps(
            {
                "deliberation": "I",
                "motion": {
                    "kind": "REQUEST",
                    "target_rule_id": "rule-132",
                    "focus": "Test the exact boundary against one hostile transfer.",
                },
                "measurements": [],
                "requests": [],
            }
        )

        with mock.patch.object(
            loop,
            "call",
            return_value=(provider_output, {"completion_tokens": 17}),
        ):
            self.assertEqual(
                loop.agent_turn(events, book, meta, state, 1214),
                "accepted",
            )

        message = next(
            event
            for event in reversed(events)
            if event.get("type") == "message"
        )
        receipt = events[-1]["post_state_receipt"]
        self.assertEqual(
            message["content"],
            "Public audit: Agent B requested focused work on rule-132.",
        )
        self.assertEqual(
            message["structured_action"]["motion"],
            {
                "kind": "REQUEST",
                "target_rule_id": "rule-132",
                "focus": "Test the exact boundary against one hostile transfer.",
            },
        )
        self.assertEqual(
            message["deliberation_fallback"],
            {
                "applied": True,
                "source": "harness_deterministic_deliberation",
                "provider_error": "string_too_short at deliberation",
            },
        )
        self.assertEqual(receipt["attempts"], 1)
        self.assertEqual(
            receipt["attempted_action"]["deliberation"],
            message["content"],
        )
        self.assertEqual(state["research"][0]["status"], "delivered")
        self.assertEqual(len(state["deliveries"]), 1)


if __name__ == "__main__":
    unittest.main()
