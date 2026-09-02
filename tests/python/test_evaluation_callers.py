import copy
import json
import unittest
from pathlib import Path
from unittest import mock

import loop
from conversation_exam import run_conversation
from rule_legislation import RuleLegislation
from rulebook import language_payload


ROOT = Path(__file__).parents[2]


class EvaluationCallerContractTests(unittest.TestCase):
    def setUp(self):
        self.rulebook = json.loads(
            (ROOT / "tests/fixtures/mixed-rulebook.json").read_text()
        )

    def test_development_exam_uses_supplied_identity_and_reports_complete_call_tokens(self):
        conv = []
        benchmark = loop.load_benchmark_suite()["benchmarks"][0]
        decoded = "\n".join(atom["meaning"] for atom in benchmark["answer_key"])
        grade = {
            "mode": "RELAY",
            "items": [
                {"id": atom["id"], "verdict": "SURVIVED", "evidence_lines": [n, n]}
                for n, atom in enumerate(benchmark["answer_key"], start=1)
            ],
            "inventions": [],
        }
        responses = [
            ("ENCODED", {"prompt_tokens": 30, "completion_tokens": 10}),
            (decoded, {"prompt_tokens": 25, "completion_tokens": 15}),
            (json.dumps(grade), {"prompt_tokens": 20, "completion_tokens": 5}),
        ]
        with mock.patch("loop.call", side_effect=responses), mock.patch(
            "loop.token_count", side_effect=[100, 50]
        ):
            loop.test_turn(
                conv, self.rulebook, {"tests_run": 0, "spend_usd": 0.0}, 3,
                legislation=RuleLegislation.shadow(self.rulebook),
            )
        event = conv[-1]
        self.assertEqual(event["total_successful_system_tokens"], 105)
        self.assertEqual(event["system_token_components"], {
            "agent_a": 40, "agent_b": 40, "judge": 25,
        })
        self.assertEqual(event["message_body_savings_pct"], 50)
        self.assertNotEqual(event["total_successful_system_tokens"], 50)
        self.assertEqual(
            event["legislation_identity"]["hash"], language_payload(self.rulebook)["hash"]
        )

    def test_stale_exam_snapshot_fails_before_provider(self):
        module = RuleLegislation.shadow(self.rulebook)
        changed = copy.deepcopy(self.rulebook)
        changed["rules"][0]["text_en"] = "changed adopted meaning"
        with mock.patch("loop.call") as provider:
            with self.assertRaisesRegex(RuntimeError, "legislation_snapshot_identity_mismatch"):
                loop.test_turn(
                    [], changed, {"tests_run": 0, "spend_usd": 0.0}, 3,
                    legislation=module,
                )
        provider.assert_not_called()

    def test_conversation_uses_one_snapshot_and_counts_all_speakers_and_judge(self):
        scenario = json.loads(
            (ROOT / "tests/fixtures/conversation/scenario.json").read_text()
        )

        def speaker(name, language, user):
            return {
                "content": f"{name} message", "model": f"fixture/{name}",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }

        def judge(payload):
            return {
                "requirements": [
                    {"id": index, "pass": True}
                    for index in range(1, len(scenario["requirements"]) + 1)
                ],
                "_receipt": {"usage": {"prompt_tokens": 20, "completion_tokens": 5}},
            }

        snapshot = RuleLegislation.shadow(self.rulebook).snapshot()
        artifact = run_conversation(
            self.rulebook, scenario, speaker, judge, 96,
            legislation_snapshot=snapshot,
        )
        self.assertEqual(artifact["total_successful_system_tokens"], 115)
        self.assertEqual(artifact["system_token_components"]["agent_a"], 45)
        self.assertEqual(artifact["system_token_components"]["agent_b"], 45)
        self.assertEqual(artifact["system_token_components"]["judge"], 25)
        self.assertEqual(artifact["language_hash"], snapshot.adopted_language.hash)


if __name__ == "__main__":
    unittest.main()
