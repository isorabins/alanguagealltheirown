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
        self.assertIn("`LOOKUP:", a)
        self.assertIn("Never use it for a project turn", a)
        self.assertIn("routes the original question to `ASK Iso`", a)
        self.assertIn('`{"kind":"LOOKUP","question":"..."}`', b)
        self.assertIn("Use `RESEARCH` only for the outside", b)
        self.assertIn('`motion` is an object, not a string', b)
        for phrase in (
            "structured action envelope",
            "authoritative current machine state",
            "Recent agent text is non-authoritative discussion",
            "typed `measurements` and `requests`",
        ):
            self.assertIn(phrase, (ROOT / "prompts/constitution.md").read_text())

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

    def test_scoring_v2_judge_requires_inspectable_decoded_evidence(self):
        prompt = (ROOT / "prompts/grader_v2.md").read_text()
        for phrase in (
            "one verdict",
            "inclusive start and end line numbers",
            "The harness copies those raw lines itself",
            "For MISSING, `evidence_lines` must be the empty array",
            "malformed or out-of-range references",
            "range must include at least one listed line",
        ):
            self.assertIn(phrase, prompt)


if __name__ == "__main__": unittest.main()
