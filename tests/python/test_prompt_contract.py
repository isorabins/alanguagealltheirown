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
        self.assertIn("Never `PROPOSE` or `REVISE`", b)


if __name__ == "__main__": unittest.main()
