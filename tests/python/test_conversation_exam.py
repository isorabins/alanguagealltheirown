import copy
import json
import unittest
from pathlib import Path

from conversation_exam import run_conversation

ROOT = Path(__file__).parents[2]


class ConversationTests(unittest.TestCase):
    def test_six_alternating_messages_adopted_only_and_no_rule_mutation(self):
        rb = json.loads((ROOT / "tests/fixtures/mixed-rulebook.json").read_text()); before = copy.deepcopy(rb)
        seen = []
        def speaker(agent, language, user):
            seen.append((agent, language, user)); return f"{agent} message {len(seen)}"
        artifact = run_conversation(rb, {"prompt":"real task","requirements":["done"]}, speaker,
                                    lambda payload: {"valid":True,"requirements":[{"id":1,"pass":True}]}, 96)
        self.assertEqual([m["speaker"] for m in artifact["messages"]], ["A","B","A","B","A","B"])
        self.assertEqual(rb, before)
        for _, language, _ in seen:
            self.assertIn("Adopted alpha", language); self.assertNotIn("Proposed beta", language)


if __name__ == "__main__": unittest.main()
