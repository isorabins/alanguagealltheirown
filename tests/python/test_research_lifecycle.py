import copy
import unittest
from unittest import mock

import loop
from collaboration import empty_state, stable_record


class Response:
    def raise_for_status(self): return None
    def json(self):
        return {"choices":[{"message":{"content":"{\"findings\":\"supported\",\"limitations\":\"one source\"}",
                                         "annotations":[{"url_citation":{"title":"Primary","url":"https://example.test/source"}}]}}]}


class ResearchTests(unittest.TestCase):
    def test_oldest_one_per_turn_citations_restart_and_no_rule_mutation(self):
        state=empty_state(); state["research"]=[stable_record("RESEARCH","A","first?","r1"),stable_record("RESEARCH","B","second?","r2")]
        rules={"rules":[{"id":"rule-1","status":"adopted","text_en":"x"}]}; before=copy.deepcopy(rules)
        with mock.patch("loop.api_key",return_value="test"), mock.patch("loop.requests.post",return_value=Response()):
            loop.process_one_research(state,{},9)
        self.assertEqual(state["research"][0]["status"],"answered"); self.assertEqual(state["research"][1]["status"],"queued")
        self.assertEqual(state["research"][0]["question"],"first?"); self.assertEqual(state["research"][0]["citations"][0]["url"],"https://example.test/source")
        self.assertEqual(rules,before)

    def test_no_evidence_and_provider_error_are_explicit(self):
        state=empty_state(); state["research"]=[stable_record("RESEARCH","A","unknown?","r1")]
        with mock.patch("loop.api_key",return_value="test"), mock.patch("loop.requests.post",side_effect=RuntimeError("down")):
            loop.process_one_research(state,{},10)
        self.assertEqual(state["research"][0]["status"],"error"); self.assertEqual(state["research"][0]["citations"],[])
        self.assertIn("unavailable",state["research"][0]["limitations"])


if __name__ == "__main__": unittest.main()
