import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import loop
from collaboration import deliver_one, empty_state, public_state, stable_record


class Response:
    def raise_for_status(self): return None
    def json(self):
        return {"choices":[{"message":{"content":"{\"findings\":\"supported\",\"limitations\":[\"one source\"],\"citations\":[]}",
                                         "annotations":[{"url_citation":{"title":"Primary","url":"https://example.test/source"}}]}}],
                "usage":{"prompt_tokens":100,"completion_tokens":50,
                         "cost":0.0123,
                         "server_tool_use":{"web_search_requests":1}}}


class ResearchTests(unittest.TestCase):
    def test_plain_bold_and_code_formatted_directives_parse(self):
        self.assertEqual(
            loop.collaboration_directive("LOOKUP: What happened at turn 636?", "LOOKUP"),
            "What happened at turn 636?",
        )
        self.assertEqual(
            loop.collaboration_directive(
                "**RESEARCH:** What public evidence supports prompt caching?",
                "RESEARCH",
            ),
            "What public evidence supports prompt caching?",
        )
        self.assertEqual(
            loop.collaboration_directive(
                "`ASK: Which project goal matters most?`",
                "ASK",
            ),
            "Which project goal matters most?",
        )

    def test_oldest_one_per_turn_citations_restart_and_no_rule_mutation(self):
        state=empty_state(); state["research"]=[
            stable_record("RESEARCH","A","What current public research compares prompt caching across LLM APIs?","r1"),
            stable_record("RESEARCH","B","What public evidence compares inference pricing?","r2"),
        ]
        rules={"rules":[{"id":"rule-1","status":"adopted","text_en":"x"}]}; before=copy.deepcopy(rules)
        meta={}
        with mock.patch("loop.api_key",return_value="test"), mock.patch("loop.requests.post",return_value=Response()) as post:
            loop.process_one_research(state,meta,9)
        self.assertEqual(state["research"][0]["status"],"answered"); self.assertEqual(state["research"][1]["status"],"queued")
        self.assertEqual(state["research"][0]["route"],"web")
        self.assertEqual(state["research"][0]["question"],"What current public research compares prompt caching across LLM APIs?")
        self.assertEqual(state["research"][0]["citations"][0]["url"],"https://example.test/source")
        self.assertEqual(rules,before)
        self.assertEqual(meta["spend_usd"], 0.0123)
        self.assertEqual(state["research"][0]["usage"]["web_search_requests"],1)
        self.assertEqual(state["research"][0]["cost_usd"],0.0123)
        self.assertEqual(post.call_count, 1)

    def test_no_evidence_and_provider_error_are_explicit(self):
        state=empty_state(); state["research"]=[stable_record("RESEARCH","A","unknown?","r1")]
        with mock.patch("loop.api_key",return_value="test"), mock.patch("loop.requests.post",side_effect=RuntimeError("down")):
            loop.process_one_research(state,{},10)
        self.assertEqual(state["research"][0]["status"],"error"); self.assertEqual(state["research"][0]["citations"],[])
        self.assertIn("unavailable",state["research"][0]["limitations"][0]); self.assertTrue(state["research"][0]["no_evidence"])
        self.assertEqual(state["research"][0]["error"],"RuntimeError")

    def test_no_citation_is_deliverable_honest_no_evidence(self):
        state=empty_state(); state["research"]=[stable_record("RESEARCH","A","unsupported?","r1")]
        class NoEvidence(Response):
            def json(self): return {"choices":[{"message":{"content":"{\"findings\":\"\",\"limitations\":[\"no source\"],\"citations\":[]}","annotations":[]}}],"usage":{"cost":0.001}}
        with mock.patch("loop.api_key",return_value="test"), mock.patch("loop.requests.post",return_value=NoEvidence()):
            loop.process_one_research(state,{},11)
        self.assertEqual(state["research"][0]["status"],"no_evidence")
        delivered=deliver_one(state,"RESEARCH","A",12)
        self.assertEqual(delivered["question"],"unsupported?"); self.assertEqual(delivered["citations"],[])

    def test_unsafe_citation_scheme_is_not_published_or_delivered(self):
        state=empty_state(); row=stable_record("RESEARCH","A","unsafe?","r1")
        row.update({"status":"answered","findings":"claim","limitations":[],
                    "citations":[{"title":"bad","url":"javascript:alert(1)"}]}); state["research"].append(row)
        self.assertEqual(loop.public_state(state)["research"][0]["citations"],[])

    def test_known_internal_questions_use_project_corpus_and_never_web(self):
        questions = [
            "What was the actual harness state of rule-072 at turn 1120?",
            "Is rule-054-revised proposed or settled internally?",
            "Why does every motion return settled_or_ineligible_motion since turn 636?",
            "Is proposal_already_open caused by dual-track proposals in the current legislature?",
            "How many aliases in turn 1137 were used in directive lines versus plain text lines?",
            "Does the current rulebook have a pending repeal?",
            "Why has the harness blocked new proposals while the visible project keeps testing?",
        ]
        for index, question in enumerate(questions):
            with self.subTest(question=question):
                state = empty_state()
                state["research"] = [
                    stable_record("RESEARCH", "A", question, f"internal-{index}")
                ]
                with mock.patch("loop.requests.post") as post:
                    loop.process_one_research(state, {}, 1200 + index)
                row = state["research"][0]
                self.assertEqual(row["route"], "project")
                self.assertEqual(row["status"], "answered")
                self.assertGreater(row["evidence_count"], 0)
                self.assertEqual(row["usage"]["web_search_requests"], 0)
                self.assertEqual(row["cost_usd"], 0)
                self.assertLessEqual(len(row["findings"]), 24_000)
                self.assertTrue(row["citations"])
                self.assertTrue(all(
                    citation["url"].startswith("https://github.com/isorabins/alanguagealltheirown/")
                    for citation in row["citations"]
                ))
                post.assert_not_called()

    def test_explicit_lookup_miss_creates_one_correlated_ask_without_web(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "state").mkdir()
            (root / "state" / "conversation.json").write_text("[]")
            (root / "state" / "rulebook.json").write_text(
                json.dumps({"version": "0.0", "changes": 0, "next_id": 1, "rules": []})
            )
            (root / "state" / "conversations.json").write_text("[]")
            state = empty_state()
            state["research"] = [
                stable_record(
                    "LOOKUP",
                    "B",
                    "What private intention did Iso have before beginning this experiment?",
                    "lookup-miss",
                )
            ]
            with mock.patch("loop.ROOT", root), mock.patch("loop.requests.post") as post:
                loop.process_one_research(state, {}, 20)
                loop.process_one_research(state, {}, 21)
            lookup = state["research"][0]
            self.assertEqual(lookup["status"], "escalated_to_iso")
            self.assertEqual(lookup["route"], "project")
            self.assertEqual(len(state["asks"]), 1)
            self.assertEqual(state["asks"][0]["id"], "ask-from-lookup-miss")
            self.assertEqual(state["asks"][0]["requester"], "B")
            self.assertEqual(state["asks"][0]["question"], lookup["question"])
            self.assertEqual(state["asks"][0]["source_lookup_id"], "lookup-miss")
            post.assert_not_called()

    def test_malformed_web_prose_is_no_evidence_even_with_annotation(self):
        state = empty_state()
        state["research"] = [
            stable_record("RESEARCH", "A", "What public studies compare compact AI protocols?", "web-malformed")
        ]

        class Malformed(Response):
            def json(self):
                return {
                    "choices": [{
                        "message": {
                            "content": "A plausible but unstructured answer.",
                            "annotations": [{
                                "url_citation": {
                                    "title": "Irrelevant",
                                    "url": "https://example.test/irrelevant",
                                }
                            }],
                        }
                    }],
                    "usage": {"cost": 0.001, "server_tool_use": {"web_search_requests": 1}},
                }

        with mock.patch("loop.api_key", return_value="test"), mock.patch(
            "loop.requests.post", return_value=Malformed()
        ):
            loop.process_one_research(state, {}, 30)
        row = state["research"][0]
        self.assertEqual(row["route"], "web")
        self.assertEqual(row["status"], "no_evidence")
        self.assertEqual(row["findings"], "")
        self.assertIn("malformed", row["limitations"][0])

    def test_project_route_is_visible_and_delivered_with_evidence(self):
        state = empty_state()
        state["research"] = [
            stable_record("LOOKUP", "A", "What is the current status of rule-054?", "lookup-1")
        ]
        with mock.patch("loop.requests.post") as post:
            loop.process_one_research(state, {}, 40)
        public = public_state(state)["research"][0]
        self.assertEqual(public["route"], "project")
        delivered = deliver_one(state, "RESEARCH", "A", 41)
        self.assertEqual(delivered["route"], "project")
        self.assertIn("Project corpus evidence", delivered["findings"])
        post.assert_not_called()


if __name__ == "__main__": unittest.main()
