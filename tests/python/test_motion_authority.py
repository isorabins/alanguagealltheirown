import copy
import unittest

from rulebook import apply_authorized_motion


def book():
    return {"version":"0.1","changes":1,"next_id":2,"rules":[{"id":"rule-001","text_en":"Open proposal long enough.","status":"proposed","history":[],"scores":None}]}


class MotionTests(unittest.TestCase):
    def assert_no_change(self, text, agent, reason):
        rb = book(); before = copy.deepcopy(rb)
        receipt = apply_authorized_motion(text, rb, 8, agent)
        self.assertEqual(receipt.reason, reason); self.assertEqual(before, rb)

    def test_a_can_propose_or_revise_but_not_vote(self):
        rb = book(); self.assertTrue(apply_authorized_motion("PROPOSE: Use concise names only after defining them.", rb, 2, "A").changed)
        self.assert_no_change("ADOPT: rule-001", "A", "inventor_cannot_vote")
        self.assertTrue(apply_authorized_motion("REVISE: rule-001 -> Open proposal revised with a clear boundary.", rb, 3, "A").changed)

    def test_b_can_vote_but_not_originate(self):
        rb = book(); self.assertTrue(apply_authorized_motion("ADOPT: rule-001", rb, 2, "B").changed)
        self.assert_no_change("PROPOSE: Auditor invents an unrelated rule.", "B", "auditor_cannot_originate")

    def test_repeated_malformed_and_multiple_are_noops(self):
        rb = book(); apply_authorized_motion("ADOPT: rule-001", rb, 2, "B"); before = copy.deepcopy(rb)
        receipt = apply_authorized_motion("ADOPT: rule-001", rb, 3, "B")
        self.assertEqual(receipt.reason, "settled_or_ineligible_motion"); self.assertEqual(before, rb)
        self.assert_no_change("ADOPT: bananas", "B", "malformed_rule_id")
        self.assert_no_change("ADOPT: rule-001\nREJECT: rule-001", "B", "multiple_motions")


if __name__ == "__main__": unittest.main()
