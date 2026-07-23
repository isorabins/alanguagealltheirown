import copy
import json
import unittest
from pathlib import Path

from conversation_exam import run_conversation

ROOT = Path(__file__).parents[2]


class ConversationTests(unittest.TestCase):
    def test_six_alternating_messages_adopted_only_and_no_rule_mutation(self):
        rb = json.loads((ROOT / "tests/fixtures/mixed-rulebook.json").read_text()); before = copy.deepcopy(rb)
        scenario = json.loads((ROOT / "tests/fixtures/conversation/scenario.json").read_text())
        seen = []
        def speaker(agent, language, user):
            seen.append((agent, language, user)); return {"content":f"{agent} message {len(seen)}",
                                                           "model":f"model-{agent}","usage":{"completion_tokens":3}}
        artifact = run_conversation(rb, scenario, speaker,
                                    lambda payload: {"requirements":[{"id":i+1,"pass":True}
                                                                       for i in range(len(scenario["requirements"]))]}, 96)
        self.assertEqual([m["speaker"] for m in artifact["messages"]], ["A","B","A","B","A","B"])
        self.assertEqual(rb, before)
        for _, language, _ in seen:
            self.assertIn("Adopted alpha", language); self.assertNotIn("Proposed beta", language)
        self.assertTrue(artifact["judgment"]["valid"])
        self.assertEqual(artifact["messages"][0]["model"],"model-A")
        self.assertEqual(artifact["messages"][0]["usage"]["completion_tokens"],3)

    def test_missing_duplicate_or_malformed_requirement_results_are_invalid(self):
        rb = json.loads((ROOT / "tests/fixtures/mixed-rulebook.json").read_text())
        scenario = {"prompt":"real task", "requirements":["first", "second"]}
        speaker = lambda agent, language, user: f"{agent} message"
        for judgment, reason in (
            ({"requirements":[{"id":1,"pass":True}]}, "invalid_requirement_coverage"),
            ({"requirements":[{"id":1,"pass":True},{"id":1,"pass":False}]}, "duplicate_requirement_id"),
            ({"requirements":[{"id":1,"pass":"yes"},{"id":2,"pass":True}]}, "malformed_requirement_result"),
        ):
            artifact = run_conversation(rb, scenario, speaker, lambda payload, j=judgment: j, 96)
            self.assertFalse(artifact["judgment"]["valid"])
            self.assertEqual(artifact["judgment"]["reason"], reason)


if __name__ == "__main__": unittest.main()
