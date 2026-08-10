import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import loop
from collaboration import empty_state, stable_record


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

    def __init__(self, content, cost, response_id="generation-test"):
        self._content = content
        self._cost = cost
        self._response_id = response_id

    def json(self):
        return {
            "id": self._response_id,
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
        loop.disable_cost_receipt_ledger()

    def tearDown(self):
        loop.disable_cost_receipt_ledger()

    def _assert_delivery_restored_and_redelivered(self, kind):
        collaboration = empty_state()
        if kind == "RESEARCH":
            record = stable_record(
                "RESEARCH", "B", "What public evidence supports this?", "research-retry"
            )
            record.update(
                {
                    "status": "answered",
                    "findings": "One cited result.",
                    "limitations": [],
                    "citations": [{"url": "https://example.test/source"}],
                }
            )
            collaboration["research"].append(record)
        elif kind == "ASK":
            record = stable_record(
                "ASK", "B", "Should this boundary remain?", "ask-retry"
            )
            record.update({"status": "answered", "answer": "Keep it bounded."})
            collaboration["asks"].append(record)
        else:
            record = stable_record(
                "SUGGESTION", "visitor", "Try the shorter marker.", "suggestion-retry"
            )
            record.update({"status": "approved", "requester": "B"})
            collaboration["suggestions"].append(record)

        before = copy.deepcopy(collaboration)
        conv = []
        rulebook = open_book()
        meta = {"last_agent": "A", "spend_usd": 4.0}
        loop.initialize_exact_cost_accounting(meta, cutover_turn=12)
        valid = json.dumps(
            {
                "deliberation": "The queued input remains advisory.",
                "motion": {
                    "kind": "REQUEST",
                    "target_rule_id": "rule-001",
                    "focus": "Test the proposal against one hostile boundary.",
                },
                "measurements": [],
                "requests": [],
            }
        )
        responses = [
            Response("not-json", 0.01, f"{kind.lower()}-invalid-{index}")
            for index in range(3)
        ]
        responses.append(Response(valid, 0.01, f"{kind.lower()}-valid"))
        bodies = []

        def post(_url, *, headers, json, timeout):
            bodies.append(json)
            return responses[len(bodies) - 1]

        with mock.patch.object(loop, "api_key", return_value="test-key"), mock.patch.object(
            loop.requests, "post", side_effect=post
        ):
            self.assertEqual(
                loop.agent_turn(conv, rulebook, meta, collaboration, 13),
                "structural_failure",
            )
            self.assertEqual(collaboration, before)
            self.assertEqual(
                loop.agent_turn(conv, rulebook, meta, collaboration, 16),
                "accepted",
            )

        delivered_request = bodies[-1]["messages"][0]["content"]
        self.assertIn(record["id"], delivered_request)
        self.assertEqual(len(collaboration["deliveries"]), 1)
        if kind == "SUGGESTION":
            self.assertEqual(before["suggestions"][0]["status"], "approved")
            self.assertEqual(collaboration["suggestions"][0]["status"], "no_action")
        else:
            bucket = "research" if kind == "RESEARCH" else "asks"
            self.assertEqual(collaboration[bucket][0]["status"], "delivered")

    def test_structural_failure_restores_research_for_same_actor_redelivery(self):
        self._assert_delivery_restored_and_redelivered("RESEARCH")

    def test_structural_failure_restores_ask_for_same_actor_redelivery(self):
        self._assert_delivery_restored_and_redelivered("ASK")

    def test_structural_failure_restores_suggestion_without_status_drift(self):
        self._assert_delivery_restored_and_redelivered("SUGGESTION")

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
                "motion": {
                    "kind": "REQUEST",
                    "target_rule_id": "rule-001",
                    "focus": "Test the proposal against one hostile boundary.",
                },
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

    def test_cost_ledger_reconciles_after_crash_between_receipt_and_meta(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger_path = Path(directory) / "cost-receipts.local.json"
            meta = {"spend_usd": 3.5}
            loop.initialize_exact_cost_accounting(meta, cutover_turn=20)
            loop.configure_cost_receipt_ledger(ledger_path, meta)
            with mock.patch.object(
                loop, "_set_meta_exact_cost", side_effect=RuntimeError("crash")
            ):
                with self.assertRaisesRegex(RuntimeError, "crash"):
                    loop.record_provider_cost(
                        meta,
                        {"cost": 0.125},
                        response_id="generation-crash",
                    )
            self.assertEqual(meta["spend_usd_provider_exact_since_cutover"], 0.0)
            persisted = json.loads(ledger_path.read_text())
            self.assertEqual(persisted["receipts"], {"generation-crash": 0.125})

            loop.disable_cost_receipt_ledger()
            restarted_meta = copy.deepcopy(meta)
            loop.configure_cost_receipt_ledger(ledger_path, restarted_meta)
            self.assertEqual(
                restarted_meta["spend_usd_provider_exact_since_cutover"], 0.125
            )
            self.assertEqual(restarted_meta["spend_usd"], 3.625)

    def test_cost_ledger_deduplicates_and_rejects_conflict_or_missing_id(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger_path = Path(directory) / "cost-receipts.local.json"
            meta = {"spend_usd": 2.0}
            loop.initialize_exact_cost_accounting(meta, cutover_turn=30)
            loop.configure_cost_receipt_ledger(ledger_path, meta)
            loop.record_provider_cost(
                meta, {"cost": 0.05}, response_id="generation-one"
            )
            loop.record_provider_cost(
                meta, {"cost": 0.05}, response_id="generation-one"
            )
            self.assertEqual(meta["spend_usd_provider_exact_since_cutover"], 0.05)
            persisted = json.loads(ledger_path.read_text())
            self.assertEqual(persisted["receipts"], {"generation-one": 0.05})

            with self.assertRaisesRegex(
                loop.CostAccountingError, "conflicting provider cost"
            ):
                loop.record_provider_cost(
                    meta, {"cost": 0.06}, response_id="generation-one"
                )
            with self.assertRaisesRegex(
                loop.CostAccountingError, "missing valid id"
            ):
                loop.record_provider_cost(meta, {"cost": 0.01})
            self.assertEqual(meta["spend_usd_provider_exact_since_cutover"], 0.05)
            self.assertEqual(
                json.loads(ledger_path.read_text())["receipts"],
                {"generation-one": 0.05},
            )

    def test_call_persists_openrouter_response_id_before_returning(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger_path = Path(directory) / "cost-receipts.local.json"
            meta = {"spend_usd": 2.0}
            loop.initialize_exact_cost_accounting(meta, cutover_turn=31)
            loop.configure_cost_receipt_ledger(ledger_path, meta)
            with mock.patch.object(
                loop, "api_key", return_value="test-key"
            ), mock.patch.object(
                loop.requests,
                "post",
                return_value=Response("valid response", 0.075, "generation-call"),
            ):
                text, _usage = loop.call(
                    loop.MODEL_A, "system", "user", meta=meta
                )

            self.assertEqual(text, "valid response")
            self.assertEqual(
                json.loads(ledger_path.read_text())["receipts"],
                {"generation-call": 0.075},
            )
            self.assertEqual(meta["spend_usd_provider_exact_since_cutover"], 0.075)

    def test_existing_cost_ledger_inconsistent_with_meta_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger_path = Path(directory) / "cost-receipts.local.json"
            meta = {"spend_usd": 1.0}
            loop.initialize_exact_cost_accounting(meta, cutover_turn=40)
            loop.record_provider_cost(meta, {"cost": 0.2})
            loop.configure_cost_receipt_ledger(ledger_path, meta)
            loop.disable_cost_receipt_ledger()

            advanced_meta = copy.deepcopy(meta)
            advanced_meta["spend_usd_provider_exact_since_cutover"] = 0.3
            advanced_meta["spend_usd"] = 1.3
            with self.assertRaisesRegex(
                loop.CostAccountingError, "conflicts with persisted exact cost"
            ):
                loop.configure_cost_receipt_ledger(ledger_path, advanced_meta)

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

    def test_viewer_bootstrap_is_small_and_contains_immediate_headline_state(self):
        conversation = [
            {
                "turn": 20,
                "agent": "harness",
                "type": "test",
                "scoring_version": "v2",
                "judge_valid": True,
                "meaning_pass": True,
                "semantic_coverage_pct": 100,
                "message_body_savings_pct": 31,
            },
            {
                "turn": 21,
                "agent": "harness",
                "type": "test",
                "scoring_version": "v2",
                "judge_valid": False,
                "message_body_savings_pct": 38,
            },
            {
                "turn": 22,
                "agent": "B",
                "type": "message",
                "content": "Public deliberation.",
            },
        ]
        rulebook = open_book()
        rulebook["version"] = "0.9"
        rulebook["rules"][0]["status"] = "adopted"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "viewer").mkdir()
            with mock.patch.object(loop, "ROOT", root), mock.patch.object(
                loop, "now_iso", return_value="2026-08-10T08:30:00Z"
            ):
                loop.write_viewer_state(conversation, rulebook, {"spend_usd": 0})
            payload = (root / "viewer" / "bootstrap.js").read_text()

        self.assertLess(len(payload.encode()), 2048)
        self.assertTrue(payload.startswith("window.PUBLIC_BOOTSTRAP = "))
        bootstrap = json.loads(payload.removeprefix("window.PUBLIC_BOOTSTRAP = ").removesuffix(";\n"))
        self.assertEqual(bootstrap["turn"], 22)
        self.assertEqual(bootstrap["updated"], "2026-08-10T08:30:00Z")
        self.assertEqual(
            bootstrap["metrics"],
            [
                ["rulebook revisions", "9"],
                ["turns", "22"],
                ["rules adopted", "1"],
                ["latest meaning pass · V2", "PASS"],
                ["latest semantic coverage · V2", "100%"],
                ["best message-body savings · V2", "+38%"],
            ],
        )

    def test_archive_moves_local_cost_ledger_with_the_matching_meta(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            prompts = root / "prompts"
            state.mkdir()
            prompts.mkdir()
            (prompts / "constitution.md").write_text("test")
            (state / "conversation.json").write_text("[]")
            (state / "rulebook.json").write_text("{}")
            (state / "meta.json").write_text("{}")
            (state / loop.COST_LEDGER_FILENAME).write_text('{"receipts": {}}')
            with mock.patch.object(loop, "ROOT", root), mock.patch.object(
                loop, "STATE", state
            ):
                loop.archive("receipt-test")

            archive = state / "tuning-runs" / "receipt-test"
            self.assertFalse((state / loop.COST_LEDGER_FILENAME).exists())
            self.assertEqual(
                (archive / loop.COST_LEDGER_FILENAME).read_text(),
                '{"receipts": {}}',
            )
            self.assertTrue((archive / "meta.json").exists())


if __name__ == "__main__":
    unittest.main()
