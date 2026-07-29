import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]


class PromptContractTests(unittest.TestCase):
    def test_shared_constitution_and_distinct_roles(self):
        constitution = (ROOT / "prompts/constitution.md").read_text().lower()
        for phrase in ("50%", "fresh model", "affordable access", "public"):
            self.assertIn(phrase, constitution)
        forbidden = ("dumb-script", "mindless script", "gigawatt", "power-grid", "traffic growth", "unprecedented")
        for phrase in forbidden: self.assertNotIn(phrase, constitution)
        a = (ROOT / "prompts/agent_a.md").read_text(); b = (ROOT / "prompts/agent_b.md").read_text()
        self.assertIn("Never `ADOPT` or `REJECT`", a)
        self.assertIn("Never `PROPOSE`, `REPEAL`, or `REVISE`", b)
        for prompt in (a, b):
            self.assertIn("`LOOKUP:", prompt)
            self.assertIn("Never use it for a project turn", prompt)
            self.assertIn("routes the original question to `ASK Iso`", prompt)

    def test_conversation_judge_documents_the_validator_schema(self):
        prompt = (ROOT / "prompts/conversation_judge.md").read_text()
        for phrase in (
            "numbered_requirements",
            "integer field `id`",
            "boolean field `pass`",
            "exactly once",
            "harness validator owns validity",
        ):
            self.assertIn(phrase, prompt)
        self.assertIn("Do not rename these fields to `requirement` or `verdict`", prompt)


if __name__ == "__main__": unittest.main()
