import unittest

from collaboration import deliver_one, empty_state, stable_record


class AskTests(unittest.TestCase):
    def test_unanswered_stays_open_and_answer_is_verbatim_exactly_once(self):
        state=empty_state(); ask=stable_record("ASK","B","Keep punctuation?","ask-7"); state["asks"].append(ask)
        self.assertIsNone(deliver_one(state,"ASK","B")); self.assertEqual(ask["status"],"awaiting_iso")
        answer="Yes — keep it exactly as written.\n  <not markup>"; ask.update({"status":"answered","answer":answer})
        delivered=deliver_one(state,"ASK","B"); self.assertEqual(delivered,{"kind":"ASK","id":"ask-7","question":"Keep punctuation?","answer":answer})
        self.assertIsNone(deliver_one(state,"ASK","B"))

    def test_requester_only(self):
        state=empty_state(); ask=stable_record("ASK","A","Question?","ask-a"); ask.update({"status":"answered","answer":"Answer"}); state["asks"].append(ask)
        self.assertIsNone(deliver_one(state,"ASK","B")); self.assertIsNotNone(deliver_one(state,"ASK","A"))


if __name__ == "__main__": unittest.main()
