import copy
import unittest

import loop
from rulebook import apply_authorized_motion, language_payload, motion_line


def book():
    return {"version":"0.1","changes":1,"next_id":2,"rules":[{"id":"rule-001","text_en":"Open proposal long enough.","status":"proposed","history":[],"scores":None}]}


def adopted_book():
    return {"version":"0.1","changes":1,"next_id":2,"rules":[{"id":"rule-001","text_en":"Use one stable compact marker.","status":"adopted","history":[],"scores":None}]}


class MotionTests(unittest.TestCase):
    def assert_no_change(self, text, agent, reason):
        rb = book(); before = copy.deepcopy(rb)
        receipt = apply_authorized_motion(text, rb, 8, agent)
        self.assertEqual(receipt.reason, reason); self.assertEqual(before, rb)

    def test_a_can_propose_or_revise_but_not_vote(self):
        rb = {"version":"0.0","changes":0,"next_id":1,"rules":[]}
        self.assertTrue(apply_authorized_motion("PROPOSE: Use concise names only after defining them.", rb, 2, "A").changed)
        self.assert_no_change("ADOPT: rule-001", "A", "inventor_cannot_vote")
        self.assertTrue(apply_authorized_motion("REVISE: rule-001 -> Open proposal revised with a clear boundary.", rb, 3, "A").changed)

    def test_b_can_vote_but_not_originate(self):
        rb = book(); self.assertTrue(apply_authorized_motion("ADOPT: rule-001", rb, 2, "B").changed)
        self.assert_no_change("PROPOSE: Auditor invents an unrelated rule.", "B", "auditor_cannot_originate")

    def test_b_can_only_act_on_latest_focused_proposal(self):
        rb = book()
        rb["rules"][0]["proposed_turn"] = 1
        rb["rules"].append({"id":"rule-002","text_en":"A newer focused proposal with adequate detail.",
                            "status":"proposed","history":[],"proposed_turn":4})
        rb["next_id"] = 3
        before = copy.deepcopy(rb)
        receipt = apply_authorized_motion("ADOPT: rule-001", rb, 5, "B")
        self.assertEqual(receipt.reason, "not_latest_focused_proposal"); self.assertEqual(before, rb)
        request = apply_authorized_motion("REQUEST: rule-002 -> Test the deadline boundary explicitly.", rb, 5, "B")
        self.assertTrue(request.accepted); self.assertFalse(request.changed)
        self.assertEqual(request.rule_id, "rule-002")
        request = apply_authorized_motion("REQUEST-TEST: rule-002 — Test one hostile boundary.", rb, 5, "B")
        self.assertTrue(request.accepted); self.assertFalse(request.changed)

    def test_a_revision_becomes_the_latest_focused_idea(self):
        rb = book(); rb["rules"][0]["proposed_turn"] = 1
        rb["rules"].append({"id":"rule-002","text_en":"A newer proposal that was latest before revision.",
                            "status":"proposed","history":[],"proposed_turn":4})
        revised = apply_authorized_motion("REVISE: rule-001 -> The older proposal is now newly focused.", rb, 6, "A")
        self.assertTrue(revised.changed); self.assertEqual(rb["rules"][0]["proposed_turn"],6)
        self.assertTrue(apply_authorized_motion("ADOPT: rule-001", rb, 7, "B").changed)

    def test_repeated_malformed_and_multiple_are_noops(self):
        rb = book(); apply_authorized_motion("ADOPT: rule-001", rb, 2, "B"); before = copy.deepcopy(rb)
        receipt = apply_authorized_motion("ADOPT: rule-001", rb, 3, "B")
        self.assertEqual(receipt.reason, "settled_or_ineligible_motion"); self.assertEqual(before, rb)
        self.assert_no_change("ADOPT: bananas", "B", "malformed_rule_id")
        empty={"version":"0.0","changes":0,"next_id":1,"rules":[]}; before=copy.deepcopy(empty)
        self.assertEqual(apply_authorized_motion("PROPOSE: REJECT: rule-001",empty,3,"A").reason,"nested_motion")
        self.assertEqual(before,empty)
        self.assert_no_change("ADOPT: rule-001\nREJECT: rule-001", "B", "multiple_motions")

    def test_one_open_motion_blocks_add_and_repeal_origination(self):
        rb = book(); before = copy.deepcopy(rb)
        add = apply_authorized_motion("PROPOSE: Another complete focused rule for testing.", rb, 8, "A")
        self.assertEqual(add.reason, "proposal_already_open"); self.assertEqual(before, rb)
        rb["rules"].append({"id":"rule-002","text_en":"An adopted target rule.","status":"adopted","history":[]})
        before = copy.deepcopy(rb)
        repeal = apply_authorized_motion("REPEAL: rule-002 -> It duplicates the open proposal.", rb, 9, "A")
        self.assertEqual(repeal.reason, "proposal_already_open"); self.assertEqual(before, rb)

    def test_repeal_lifecycle_preserves_history_and_leaves_language(self):
        rb = adopted_book(); before_hash = language_payload(rb)["hash"]
        proposed = apply_authorized_motion(
            "REPEAL: rule-001 -> The marker is now redundant and increases cost.", rb, 10, "A")
        self.assertTrue(proposed.changed); self.assertEqual(proposed.reason, "repeal_proposed")
        self.assertEqual(rb["rules"][0]["pending_repeal"]["target_id"], "rule-001")
        self.assertEqual(language_payload(rb)["hash"], before_hash)
        request = apply_authorized_motion(
            "REQUEST-TEST: rule-001 -> Show that plain wording stays unambiguous.", rb, 11, "B")
        self.assertTrue(request.accepted); self.assertFalse(request.changed)
        revised = apply_authorized_motion(
            "REVISE: rule-001 -> Remove it because the marker costs tokens without reducing ambiguity.", rb, 12, "A")
        self.assertTrue(revised.changed); self.assertEqual(revised.reason, "repeal_revised")
        adopted = apply_authorized_motion("ADOPT: rule-001", rb, 13, "B")
        self.assertTrue(adopted.changed); self.assertEqual(rb["rules"][0]["status"], "repealed")
        self.assertNotIn("pending_repeal", rb["rules"][0])
        self.assertEqual(language_payload(rb)["rules"], [])
        self.assertEqual([h["verb"] for h in rb["rules"][0]["history"]],
                         ["repeal_proposed", "repeal_revised", "repeal_adopted"])
        reproposed = apply_authorized_motion(
            "PROPOSE: Use one stable compact marker.", rb, 14, "A")
        self.assertTrue(reproposed.changed); self.assertNotEqual(reproposed.rule_id, "rule-001")

    def test_repeal_authority_and_terminal_guards(self):
        rb = adopted_book(); before = copy.deepcopy(rb)
        self.assertEqual(apply_authorized_motion(
            "REPEAL: rule-001 -> Auditor cannot originate this repeal.", rb, 2, "B").reason,
            "auditor_cannot_originate")
        self.assertEqual(before, rb)
        proposed = adopted_book(); proposed["rules"][0]["status"]="rejected"; before = copy.deepcopy(proposed)
        self.assertEqual(apply_authorized_motion(
            "REPEAL: rule-001 -> This target is not adopted yet.", proposed, 2, "A").reason,
            "repeal_target_not_adopted")
        self.assertEqual(before, proposed)
        rb["rules"][0]["status"] = "repealed"; before = copy.deepcopy(rb)
        self.assertEqual(apply_authorized_motion(
            "REPEAL: rule-001 -> A repealed id is terminal forever.", rb, 3, "A").reason,
            "repeal_target_not_adopted")
        self.assertEqual(before, rb)

    def test_receipt_exposes_exact_motion_line_for_rationale(self):
        text = "This is the actual reason before the motion.\n\n**PROPOSE: Use one exact marker for every deadline.**\n\nClosing text that is not the reason."
        line = motion_line(text)
        self.assertEqual(line, "**PROPOSE: Use one exact marker for every deadline.**")
        rb = {"version":"0.0","changes":0,"next_id":1,"rules":[]}
        receipt = apply_authorized_motion(text, rb, 2, "A", loop.rationale_for(text, line))
        self.assertEqual(receipt.line, line)
        self.assertEqual(rb["rules"][0]["history"][0]["why"], "This is the actual reason before the motion.")
        request_text = "Audit evidence describes this boundary clearly.\n\nREQUEST-TEST: rule-001 -> Try a hostile boundary."
        request_line = motion_line(request_text)
        self.assertEqual(loop.rationale_for(request_text, request_line),
                         "Audit evidence describes this boundary clearly.")


if __name__ == "__main__": unittest.main()
