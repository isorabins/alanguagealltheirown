import copy
import unittest
from unittest import mock

import loop
from collaboration import deliver_one, empty_state, stable_record


class Response:
    def raise_for_status(self): return None
    def json(self):
        return {"choices":[{"message":{"content":"{\"findings\":\"supported\",\"limitations\":\"one source\"}",
                                         "annotations":[{"url_citation":{"title":"Primary","url":"https://example.test/source"}}]}}],
                "usage":{"prompt_tokens":100,"completion_tokens":50,
                         "server_tool_use":{"web_search_requests":1}}}


class ResearchTests(unittest.TestCase):
    def test_oldest_one_per_turn_citations_restart_and_no_rule_mutation(self):
        state=empty_state(); state["research"]=[stable_record("RESEARCH","A","first?","r1"),stable_record("RESEARCH","B","second?","r2")]
        rules={"rules":[{"id":"rule-1","status":"adopted","text_en":"x"}]}; before=copy.deepcopy(rules)
        meta={}
        with mock.patch("loop.api_key",return_value="test"), mock.patch("loop.requests.post",return_value=Response()):
            loop.process_one_research(state,meta,9)
        self.assertEqual(state["research"][0]["status"],"answered"); self.assertEqual(state["research"][1]["status"],"queued")
        self.assertEqual(state["research"][0]["question"],"first?"); self.assertEqual(state["research"][0]["citations"][0]["url"],"https://example.test/source")
        self.assertEqual(rules,before)
        self.assertGreaterEqual(meta["spend_usd"], loop.WEB_SEARCH_PRICE)
        self.assertEqual(state["research"][0]["usage"]["web_search_requests"],1)
        self.assertGreaterEqual(state["research"][0]["cost_usd"],loop.WEB_SEARCH_PRICE)

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
            def json(self): return {"choices":[{"message":{"content":"{\"findings\":\"\",\"limitations\":\"no source\"}","annotations":[]}}],"usage":{}}
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


if __name__ == "__main__": unittest.main()
