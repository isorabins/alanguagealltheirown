import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import loop
from collaboration import empty_state


def open_book():
    return {
        "version": "0.1",
        "changes": 1,
        "next_id": 2,
        "rules": [
            {
                "id": "rule-001",
                "text_en": "Use one explicit compact marker.",
                "status": "proposed",
                "proposed_turn": 12,
                "history": [],
            }
        ],
    }


class Response:
    status_code = 200
    text = ""

    def __init__(self, content, cost):
        self._content = content
        self._cost = cost

    def json(self):
        return {
            "choices": [{"message": {"content": self._content}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "cost": self._cost,
            },
        }


class StructuredLoopTests(unittest.TestCase):
    def setUp(self):
        loop._no_reasoning_field = False

    def test_structural_exhaustion_retries_twice_keeps_actor_and_rule_state(self):
        conv = []
        rulebook = open_book()
        before = copy.deepcopy(rulebook)
        meta = {"last_agent": "A", "spend_usd": 4.0}
        loop.initialize_exact_cost_accounting(meta, cutover_turn=12)
        bodies = []

        def invalid_post(_url, *, headers, json, timeout):
            bodies.append(json)
            return Response("not-json", 0.1)

        with mock.patch.object(loop, "api_key", return_value="test-key"), mock.patch.object(
            loop.requests, "post", side_effect=invalid_post
        ):
            result = loop.agent_turn(conv, rulebook, meta, empty_state(), 13)

        self.assertEqual(result, "structural_failure")
        self.assertEqual(len(bodies), 3)
        self.assertEqual(rulebook, before)
        self.assertEqual(meta["last_agent"], "A")
        self.assertAlmostEqual(meta["spend_usd_provider_exact_since_cutover"], 0.3)
        self.assertAlmostEqual(meta["spend_usd"], 4.3)
        self.assertTrue(
            all(body["provider"]["require_parameters"] for body in bodies)
        )
        receipts = [
            event["post_state_receipt"]
            for event in conv
            if event.get("type") == "legislature"
        ]
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["result"], "structural_failure")
        self.assertEqual(receipts[0]["attempts"], 3)
        self.assertEqual(receipts[0]["changed_rule_ids"], [])
        self.assertEqual(receipts[0]["unchanged_rule_ids"], ["rule-001"])
        self.assertEqual(receipts[0]["next_actor"], "B")
        failure_event = next(
            event for event in conv if event.get("type") == "legislature"
        )
        self.assertEqual(
            failure_event["motion_receipt"]["reason"],
            "structural_validation_exhausted",
        )

        valid = json.dumps(
            {
                "deliberation": "The proposal needs one more boundary check.",
                "motion": None,
                "measurements": [],
                "requests": [],
            }
        )
        with mock.patch.object(loop, "api_key", return_value="test-key"), mock.patch.object(
            loop.requests, "post", return_value=Response(valid, 0.2)
        ):
            result = loop.agent_turn(conv, rulebook, meta, empty_state(), 14)

        self.assertEqual(result, "accepted")
        self.assertEqual(rulebook, before)
        self.assertEqual(meta["last_agent"], "B")
        self.assertAlmostEqual(meta["spend_usd_provider_exact_since_cutover"], 0.5)
        self.assertAlmostEqual(meta["spend_usd"], 4.5)
        self.assertEqual(conv[-1]["post_state_receipt"]["result"], "accepted")

    def test_missing_provider_cost_fails_closed(self):
        meta = {"spend_usd": 3.5}
        loop.initialize_exact_cost_accounting(meta, cutover_turn=20)
        with self.assertRaises(RuntimeError):
            loop.record_provider_cost(meta, {"prompt_tokens": 2, "completion_tokens": 1})
        self.assertEqual(meta["spend_usd"], 3.5)
        self.assertEqual(meta["spend_usd_provider_exact_since_cutover"], 0.0)

    def test_cutover_appends_one_receipt_without_mutating_pre_cutover_objects(self):
        conversation = [
            {
                "turn": 12,
                "agent": "A",
                "type": "message",
                "content": "Legacy discussion.",
            }
        ]
        rulebook = open_book()
        conversation_before = copy.deepcopy(conversation)
        rulebook_before = copy.deepcopy(rulebook)
        meta = {"last_agent": "A", "spend_usd": 4.137152}

        receipt = loop.ensure_structured_protocol_cutover(
            conversation, rulebook, meta, activation_turn=12
        )
        again = loop.ensure_structured_protocol_cutover(
            conversation, rulebook, meta, activation_turn=12
        )

        self.assertEqual(conversation[:-1], conversation_before)
        self.assertEqual(rulebook, rulebook_before)
        self.assertEqual(receipt, again)
        self.assertEqual(
            [event["type"] for event in conversation].count("protocol_cutover"), 1
        )
        self.assertEqual(receipt["current_open_motion"]["target_rule_id"], "rule-001")
        self.assertEqual(meta["spend_usd_historical_estimate"], 4.137152)
        self.assertEqual(meta["spend_usd_provider_exact_since_cutover"], 0.0)
        self.assertEqual(meta["cost_accounting_basis"], "historical_estimate_plus_provider_usage_cost")

    def test_recent_agent_prose_is_labeled_non_authoritative_and_legacy_receipts_are_sparse(self):
        rendered = loop.render_window(
            [
                {
                    "turn": 10,
                    "agent": "A",
                    "type": "message",
                    "content": "I believe rule-999 is open.",
                },
                {
                    "turn": 10,
                    "agent": "harness",
                    "type": "legislature",
                    "motion_receipt": {"reason": "no_motion", "accepted": False},
                },
            ]
        )
        self.assertIn("NON-AUTHORITATIVE AGENT DISCUSSION", rendered)
        self.assertIn("LEGACY MACHINE RECEIPT", rendered)
        self.assertIn('"reason": "no_motion"', rendered)
        self.assertNotIn('"verb"', rendered)
        self.assertNotIn("no receipt", rendered)

    def test_new_legislative_path_contains_no_prose_or_regex_extraction(self):
        source = inspect.getsource(loop.agent_turn)
        for forbidden in (
            "re.",
            "motion_line",
            "rationale_for",
            "collaboration_directive",
            "apply_authorized_motion",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("validate_action", source)
        self.assertIn("apply_typed_motion", source)

    def test_render_window_keeps_thirty_events_and_labels_every_agent_message(self):
        rendered = loop.render_window(
            [
                {
                    "turn": turn,
                    "agent": "A" if turn % 2 else "B",
                    "type": "message",
                    "content": f"discussion-{turn}",
                }
                for turn in range(1, 36)
            ]
        )
        self.assertNotIn("discussion-5", rendered)
        self.assertIn("discussion-6", rendered)
        self.assertEqual(rendered.count("NON-AUTHORITATIVE AGENT DISCUSSION"), 30)

    def test_viewer_metadata_distinguishes_cost_and_omits_private_cutover_event(self):
        meta = {"spend_usd": 4.137152}
        loop.initialize_exact_cost_accounting(meta, cutover_turn=1165)
        loop.record_provider_cost(meta, {"cost": 0.012345})
        conversation = [
            {
                "turn": 1165,
                "agent": "harness",
                "type": "protocol_cutover",
                "state_receipt": {"result": "cutover"},
            },
            {
                "turn": 1166,
                "agent": "B",
                "type": "message",
                "content": "Public deliberation.",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "viewer").mkdir()
            with mock.patch.object(loop, "ROOT", root):
                loop.write_viewer_state(conversation, open_book(), meta)
            payload = (root / "viewer" / "state.js").read_text()
        self.assertIn('"spend_usd_historical_estimate": 4.137152', payload)
        self.assertIn('"spend_usd_provider_exact_since_cutover": 0.012345', payload)
        self.assertIn(
            '"cost_accounting_basis": "historical_estimate_plus_provider_usage_cost"',
            payload,
        )
        self.assertNotIn('"type": "protocol_cutover"', payload)
        self.assertIn('"content": "Public deliberation."', payload)


if __name__ == "__main__":
    unittest.main()
