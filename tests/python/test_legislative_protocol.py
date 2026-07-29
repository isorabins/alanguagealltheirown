import copy
import unittest

from pydantic import ValidationError

from legislative_protocol import (
    PROTOCOL_VERSION,
    action_request_options,
    build_cutover_receipt,
    build_legislative_request,
    build_post_state_receipt,
    current_open_motion,
    validate_action,
)


def empty_book():
    return {
        "version": "0.0",
        "changes": 0,
        "next_id": 1,
        "rules": [],
    }


def adopted_book():
    return {
        "version": "0.1",
        "changes": 1,
        "next_id": 3,
        "rules": [
            {
                "id": "rule-001",
                "text_en": "Use one stable compact marker.",
                "status": "adopted",
                "history": [],
            },
            {
                "id": "rule-002",
                "text_en": "Keep context in plain text.",
                "status": "adopted",
                "history": [],
            },
        ],
    }


def open_add_book():
    book = adopted_book()
    book["rules"].append(
        {
            "id": "rule-003",
            "text_en": "Use one explicit deadline marker.",
            "status": "proposed",
            "proposed_turn": 12,
            "history": [],
        }
    )
    book["next_id"] = 4
    return book


def open_repeal_book():
    book = adopted_book()
    book["rules"][0]["pending_repeal"] = {
        "kind": "repeal",
        "target_id": "rule-001",
        "rationale": "The marker no longer saves tokens.",
        "proposed_turn": 14,
        "agent": "A",
    }
    return book


def action(motion=None, *, deliberation="One bounded decision.", measurements=None, requests=None):
    return {
        "deliberation": deliberation,
        "motion": motion,
        "measurements": measurements or [],
        "requests": requests or [],
    }


class StateSpecificActionTests(unittest.TestCase):
    def assert_invalid(self, role, rulebook, payload):
        with self.assertRaises(ValidationError):
            validate_action(payload, role, rulebook)

    def test_role_and_state_matrix_accepts_every_legal_motion(self):
        cases = [
            (
                "A",
                empty_book(),
                {"kind": "PROPOSE", "text": "Use one explicit marker after defining it."},
            ),
            (
                "A",
                adopted_book(),
                {
                    "kind": "REPEAL",
                    "target_rule_id": "rule-001",
                    "rationale": "This marker duplicates the plain-text fallback.",
                },
            ),
            (
                "A",
                open_add_book(),
                {
                    "kind": "REVISE",
                    "target_rule_id": "rule-003",
                    "text": "Use one explicit deadline marker only after defining it.",
                },
            ),
            (
                "A",
                open_repeal_book(),
                {
                    "kind": "REVISE",
                    "target_rule_id": "rule-001",
                    "text": "The marker now duplicates the clearer fallback rule.",
                },
            ),
            ("B", open_add_book(), {"kind": "ADOPT", "target_rule_id": "rule-003"}),
            ("B", open_add_book(), {"kind": "REJECT", "target_rule_id": "rule-003"}),
            (
                "B",
                open_add_book(),
                {
                    "kind": "REQUEST",
                    "target_rule_id": "rule-003",
                    "focus": "Test the deadline boundary on hostile prose.",
                },
            ),
        ]
        for role, rulebook, motion in cases:
            with self.subTest(role=role, motion=motion["kind"]):
                parsed = validate_action(action(motion), role, rulebook)
                self.assertEqual(parsed.motion.kind, motion["kind"])

        for role, rulebook in (
            ("A", empty_book()),
            ("A", open_add_book()),
            ("B", adopted_book()),
        ):
            with self.subTest(role=role, no_motion=True):
                self.assertIsNone(validate_action(action(), role, rulebook).motion)
        self.assert_invalid("B", open_add_book(), action())

    def test_wrong_role_wrong_target_and_illegal_state_are_rejected_locally(self):
        self.assert_invalid(
            "A", open_add_book(), action({"kind": "ADOPT", "target_rule_id": "rule-003"})
        )
        self.assert_invalid(
            "B",
            open_add_book(),
            action(
                {
                    "kind": "PROPOSE",
                    "text": "The auditor must not originate a new language rule.",
                }
            ),
        )
        self.assert_invalid(
            "B", open_add_book(), action({"kind": "ADOPT", "target_rule_id": "rule-002"})
        )
        self.assert_invalid(
            "A",
            open_add_book(),
            action(
                {
                    "kind": "REVISE",
                    "target_rule_id": "rule-001",
                    "text": "A stale target must not validate against current state.",
                }
            ),
        )
        self.assert_invalid(
            "B", adopted_book(), action({"kind": "ADOPT", "target_rule_id": "rule-001"})
        )
        self.assert_invalid(
            "A",
            adopted_book(),
            action(
                {
                    "kind": "REPEAL",
                    "target_rule_id": "rule-999",
                    "rationale": "Unknown targets never reach the state machine.",
                }
            ),
        )

    def test_measurements_and_collaboration_requests_are_typed_and_bounded(self):
        payload = action(
            measurements=[{"text": "one compact line"}, {"text": "one plain line"}],
            requests=[
                {"kind": "LOOKUP", "question": "What happened at turn 1163?"},
                {
                    "kind": "RESEARCH",
                    "question": "What public evidence compares compact protocols?",
                },
                {"kind": "ASK", "question": "Which ambiguity should remain?"},
            ],
        )
        parsed = validate_action(payload, "A", empty_book())
        self.assertEqual([request.kind for request in parsed.requests], ["LOOKUP", "RESEARCH", "ASK"])
        self.assert_invalid(
            "A",
            empty_book(),
            action(measurements=[{"text": "one"}, {"text": "two"}, {"text": "three"}]),
        )
        self.assert_invalid(
            "A",
            empty_book(),
            action(
                requests=[
                    {"kind": "LOOKUP", "question": "First?"},
                    {"kind": "LOOKUP", "question": "Duplicate?"},
                ]
            ),
        )
        self.assert_invalid(
            "A",
            empty_book(),
            {
                **action(),
                "invented_field": "provider output may not add keys",
            },
        )

    def test_open_target_is_the_only_target_in_openrouter_schema(self):
        options = action_request_options("B", open_add_book())
        self.assertEqual(options["response_format"]["type"], "json_schema")
        self.assertTrue(options["response_format"]["json_schema"]["strict"])
        self.assertTrue(options["provider"]["require_parameters"])
        schema_text = str(options["response_format"]["json_schema"]["schema"])
        self.assertIn("rule-003", schema_text)
        self.assertNotIn("rule-002", schema_text)

    def test_open_auditor_cannot_return_punctuation_or_skip_the_motion(self):
        self.assert_invalid("B", open_add_book(), action(deliberation=","))
        self.assert_invalid(
            "B",
            open_add_book(),
            action(deliberation="A real audit statement."),
        )

    def test_multiple_open_motions_fail_closed(self):
        book = open_add_book()
        book["rules"][0]["pending_repeal"] = {
            "kind": "repeal",
            "target_id": "rule-001",
            "rationale": "Conflicting open state.",
            "proposed_turn": 13,
        }
        with self.assertRaises(ValueError):
            current_open_motion(book)


class ReceiptTests(unittest.TestCase):
    def test_post_state_receipt_contains_exact_changed_unchanged_open_count_and_hash(self):
        before = open_add_book()
        after = copy.deepcopy(before)
        after["rules"][-1]["status"] = "adopted"
        action_model = validate_action(
            action({"kind": "ADOPT", "target_rule_id": "rule-003"}), "B", before
        )
        receipt = build_post_state_receipt(
            turn=13,
            role="B",
            action=action_model,
            result="accepted",
            reason="motion_applied",
            before_rulebook=before,
            after_rulebook=after,
            next_actor="A",
            attempts=1,
        )
        self.assertEqual(receipt.changed_rule_ids, ["rule-003"])
        self.assertEqual(receipt.unchanged_rule_ids, ["rule-001", "rule-002"])
        self.assertIsNone(receipt.current_open_motion)
        self.assertEqual(receipt.adopted_count, 3)
        self.assertEqual(len(receipt.adopted_language_hash), 64)
        self.assertEqual(receipt.attempted_action.motion.target_rule_id, "rule-003")
        self.assertEqual(receipt.next_actor, "A")

    def test_cutover_receipt_reconciles_state_without_inventing_an_action(self):
        book = open_add_book()
        receipt = build_cutover_receipt(book, turn=12, next_actor="B")
        self.assertEqual(receipt.protocol_version, PROTOCOL_VERSION)
        self.assertEqual(receipt.result, "cutover")
        self.assertIsNone(receipt.attempted_action)
        self.assertEqual(receipt.changed_rule_ids, [])
        self.assertEqual(
            receipt.unchanged_rule_ids, ["rule-001", "rule-002", "rule-003"]
        )
        self.assertEqual(receipt.current_open_motion.target_rule_id, "rule-003")
        self.assertEqual(receipt.adopted_count, 2)

    def test_request_carries_authoritative_state_and_latest_receipt(self):
        book = open_add_book()
        cutover = build_cutover_receipt(book, turn=12, next_actor="B")
        request = build_legislative_request(
            role="B",
            turn=13,
            next_live_test_turn=15,
            rulebook=book,
            latest_receipt=cutover,
            collaboration_input=None,
        )
        self.assertTrue(request.current_state.authoritative)
        self.assertEqual(request.current_state.open_motion.target_rule_id, "rule-003")
        self.assertEqual(request.latest_receipt.result, "cutover")
        self.assertEqual(request.acting_role, "B")

    def test_request_accepts_receipt_written_under_an_older_input_policy(self):
        book = open_add_book()
        prior_receipt = build_cutover_receipt(
            book, turn=12, next_actor="B"
        ).model_dump(mode="json")
        prior_receipt.update(
            {
                "actor": "B",
                "attempted_action": action(deliberation=","),
                "result": "accepted",
                "reason": "no_motion",
                "attempts": 2,
                "next_actor": "A",
            }
        )

        request = build_legislative_request(
            role="A",
            turn=13,
            next_live_test_turn=15,
            rulebook=book,
            latest_receipt=prior_receipt,
            collaboration_input=None,
        )

        self.assertEqual(request.latest_receipt.attempted_action.deliberation, ",")
        self.assertEqual(request.latest_receipt.reason, "no_motion")
        self.assertEqual(request.current_state.open_motion.target_rule_id, "rule-003")


if __name__ == "__main__":
    unittest.main()
