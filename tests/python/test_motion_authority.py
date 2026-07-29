import copy
import unittest

import loop
from legislative_protocol import build_post_state_receipt
from rulebook import apply_authorized_motion, apply_typed_motion, language_payload, motion_line
from state_store import snapshot_hash


def book():
    return {"version":"0.1","changes":1,"next_id":2,"rules":[{"id":"rule-001","text_en":"Open proposal long enough.","status":"proposed","history":[],"scores":None}]}


def adopted_book():
    return {"version":"0.1","changes":1,"next_id":2,"rules":[{"id":"rule-001","text_en":"Use one stable compact marker.","status":"adopted","history":[],"scores":None}]}


def extracted_turn_1165_book():
    """Small record-shaped slice of the historical 072/083–085/128/129 state."""
    return {
        "version": "0.124",
        "changes": 124,
        "next_id": 130,
        "kernel_tokens": 901,
        "rules": [
            {
                "id": "rule-072",
                "text_en": "Within a message, the sender may define a local alias.",
                "status": "repealed",
                "proposed_turn": 406,
                "scores": {"fidelity_pct": 100, "token_delta_pct": -22},
                "history": [
                    {"agent": "A", "turn": 406, "verb": "proposed", "why": "Lock aliasing."},
                    "tested turn 648: fid 100, -22%",
                    {"agent": "B", "turn": 1163, "verb": "repeal_adopted", "why": "Clean ratification."},
                ],
            },
            {
                "id": "rule-083",
                "text_en": "Alias only when the measured savings are positive.",
                "status": "adopted",
                "proposed_turn": 434,
                "scores": {"fidelity_pct": 100, "token_delta_pct": -22},
                "history": [
                    {"agent": "B", "turn": 434, "verb": "proposed", "why": "Revise the guideline."},
                    "tested turn 648: fid 100, -22%",
                ],
            },
            {
                "id": "rule-084",
                "text_en": "Use the repeat threshold only with bounded definition overhead.",
                "status": "adopted",
                "proposed_turn": 437,
                "scores": {"fidelity_pct": 100, "token_delta_pct": -22},
                "history": [{"agent": "B", "turn": 473, "verb": "adopt", "why": ""}],
            },
            {
                "id": "rule-085",
                "text_en": "Keep one minimal alias example in the language.",
                "status": "adopted",
                "proposed_turn": 437,
                "scores": {"fidelity_pct": 100, "token_delta_pct": -22},
                "history": [{"agent": "B", "turn": 482, "verb": "adopt", "why": ""}],
            },
            {
                "id": "rule-128",
                "text_en": "A stale legacy proposal that is already terminal.",
                "status": "historical",
                "proposed_turn": 1147,
                "scores": None,
                "history": [
                    {
                        "agent": "harness",
                        "turn": 1148,
                        "verb": "archived_legacy_motion",
                        "prior_status": "proposed",
                    }
                ],
            },
            {
                "id": "rule-129",
                "text_en": "A directive line must contain only an actionable instruction.",
                "status": "proposed",
                "proposed_turn": 1165,
                "scores": None,
                "history": [
                    {
                        "agent": "A",
                        "turn": 1165,
                        "verb": "proposed",
                        "why": "Restate the directive boundary.",
                    }
                ],
            },
        ],
    }


def extracted_turn_1162_repeal_book():
    rb = extracted_turn_1165_book()
    rb["rules"] = [
        rule for rule in rb["rules"] if rule["id"] in {"rule-072", "rule-083", "rule-084", "rule-085"}
    ]
    rule_072 = rb["rules"][0]
    rule_072["status"] = "adopted"
    rule_072["pending_repeal"] = {
        "kind": "repeal",
        "target_id": "rule-072",
        "rationale": "Aliasing produced repeated measured bloat.",
        "proposed_turn": 1150,
        "agent": "A",
    }
    rule_072["history"] = [
        entry
        for entry in rule_072["history"]
        if not (isinstance(entry, dict) and entry.get("verb") == "repeal_adopted")
    ]
    rule_072["history"].append(
        {
            "agent": "A",
            "turn": 1153,
            "verb": "repeal_revised",
            "why": "Agent prose claimed the dependent cluster would also repeal.",
        }
    )
    return rb


def expected_language_receipt_fields(rulebook):
    rules = [
        {"id": rule["id"], "text_en": rule["text_en"]}
        for rule in rulebook["rules"]
        if rule["status"] == "adopted"
    ]
    return len(rules), snapshot_hash({"rules": rules})


def independently_changed_rule_ids(before, after):
    before_by_id = {rule["id"]: rule for rule in before["rules"]}
    return [
        rule["id"]
        for rule in after["rules"]
        if rule != before_by_id.get(rule["id"])
    ]


def apply_with_post_state(rulebook, motion, *, turn, agent, deliberation):
    before = copy.deepcopy(rulebook)
    motion_receipt = apply_typed_motion(
        motion, rulebook, turn, agent, deliberation
    )
    if motion_receipt.changed:
        rulebook["changes"] += 1
        rulebook["version"] = f"0.{rulebook['changes']}"
    result = "accepted" if motion_receipt.accepted else "rejected"
    action = {
        "deliberation": deliberation,
        "motion": motion,
        "measurements": [],
        "requests": [],
    }
    post_state = build_post_state_receipt(
        turn=turn,
        role=agent,
        action=action,
        result=result,
        reason=motion_receipt.reason,
        before_rulebook=before,
        after_rulebook=rulebook,
        next_actor="A" if agent == "B" else "B",
        attempts=1,
    )
    return before, motion_receipt, post_state


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

    def test_full_line_inline_code_motion_is_recognized_exactly(self):
        rb = book()
        receipt = apply_authorized_motion("Decision follows.\n\n`ADOPT: rule-001`", rb, 2, "B")
        self.assertTrue(receipt.changed)
        self.assertEqual(receipt.reason, "motion_applied")
        self.assertEqual(receipt.line, "`ADOPT: rule-001`")
        self.assertEqual(rb["rules"][0]["status"], "adopted")

    def test_inline_code_motion_must_occupy_the_entire_line(self):
        self.assert_no_change("Decision: `ADOPT: rule-001`", "B", "no_motion")
        self.assert_no_change("`ADOPT: rule-001``", "B", "no_motion")
        self.assert_no_change(
            "`ADOPT: rule-001`\nREJECT: rule-001", "B", "multiple_motions")

    def test_exact_duplicate_motion_lines_are_one_idempotent_decision(self):
        rb = book()
        receipt = apply_authorized_motion(
            "`ADOPT: rule-001`\n\nSupporting analysis.\n\n`ADOPT: rule-001`", rb, 2, "B")
        self.assertTrue(receipt.changed)
        self.assertEqual(receipt.reason, "motion_applied")
        self.assertEqual(receipt.line, "`ADOPT: rule-001`")
        self.assertEqual(rb["rules"][0]["status"], "adopted")

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

    def test_typed_motion_path_replays_inline_duplicate_without_parsing_prose(self):
        historical_record = {
            "turn": 1160,
            "agent": "B",
            "type": "message",
            "content": (
                "`ADOPT: rule-072`\nEvidence and a typed measurement request.\n"
                "`ADOPT: rule-072`\n`MEASURE: turn 1158 encoded tokens`"
            ),
        }
        self.assertEqual(historical_record["content"].count("ADOPT: rule-072"), 2)
        rb = extracted_turn_1162_repeal_book()
        before, receipt, post_state = apply_with_post_state(
            rb,
            {"kind": "ADOPT", "target_rule_id": "rule-072"},
            turn=1160,
            agent="B",
            deliberation="The structured envelope carries one unambiguous vote.",
        )
        self.assertTrue(receipt.changed)
        self.assertEqual(receipt.reason, "repeal_adopted")
        self.assertEqual(rb["rules"][0]["status"], "repealed")
        self.assertIsNone(receipt.line)
        self.assertEqual(post_state.changed_rule_ids, ["rule-072"])
        self.assertEqual(independently_changed_rule_ids(before, rb), ["rule-072"])
        self.assertIsNone(post_state.current_open_motion)
        expected_count, expected_hash = expected_language_receipt_fields(rb)
        self.assertEqual(expected_count, 3)
        self.assertEqual(post_state.adopted_count, expected_count)
        self.assertEqual(post_state.adopted_language_hash, expected_hash)

    def test_typed_motion_path_rejects_stale_target_without_mutation(self):
        historical_record = {
            "turn": 1149,
            "agent": "B",
            "type": "message",
            "content": "`ADOPT: rule-128`",
        }
        rb = extracted_turn_1165_book()
        before, receipt, post_state = apply_with_post_state(
            rb,
            {"kind": "ADOPT", "target_rule_id": "rule-128"},
            turn=1166,
            agent="B",
            deliberation=historical_record["content"],
        )
        self.assertEqual(receipt.reason, "settled_or_ineligible_motion")
        self.assertEqual(before, rb)
        self.assertEqual(post_state.changed_rule_ids, [])
        self.assertEqual(
            post_state.unchanged_rule_ids,
            [rule["id"] for rule in before["rules"]],
        )
        self.assertEqual(post_state.current_open_motion.target_rule_id, "rule-129")
        expected_count, expected_hash = expected_language_receipt_fields(rb)
        self.assertEqual(post_state.adopted_count, expected_count)
        self.assertEqual(post_state.adopted_language_hash, expected_hash)

    def test_typed_repeal_revision_uses_canonical_state_not_agent_belief(self):
        historical_belief = {
            "turn": 1153,
            "agent": "A",
            "type": "message",
            "content": (
                "Revise the pending repeal to encompass the entire aliasing "
                "cluster in one motion: 072, 083, 084, and 085."
            ),
        }
        rb = extracted_turn_1162_repeal_book()
        rb["rules"][0]["pending_repeal"].update(
            {
                "rationale": "Initial repeal targets rule-072 only.",
                "proposed_turn": 1150,
            }
        )
        rb["rules"][0]["history"] = [
            entry
            for entry in rb["rules"][0]["history"]
            if not (
                isinstance(entry, dict)
                and entry.get("verb") == "repeal_revised"
            )
        ]
        before_language_count, before_language_hash = expected_language_receipt_fields(
            rb
        )
        before, revised, post_state = apply_with_post_state(
            rb,
            {
                "kind": "REVISE",
                "target_rule_id": "rule-072",
                "text": (
                    "Remove rule-072 and, according to deliberation only, "
                    "dependent rules 083, 084, and 085."
                ),
            },
            turn=1153,
            agent="A",
            deliberation=historical_belief["content"],
        )
        self.assertEqual(revised.reason, "repeal_revised")
        self.assertEqual(post_state.changed_rule_ids, ["rule-072"])
        self.assertEqual(independently_changed_rule_ids(before, rb), ["rule-072"])
        self.assertEqual(post_state.current_open_motion.target_rule_id, "rule-072")
        self.assertEqual(rb["rules"][0]["status"], "adopted")
        self.assertEqual(
            [rule["status"] for rule in rb["rules"][1:]],
            ["adopted", "adopted", "adopted"],
        )
        expected_count, expected_hash = expected_language_receipt_fields(rb)
        self.assertEqual(expected_count, 4)
        self.assertEqual(expected_count, before_language_count)
        self.assertEqual(expected_hash, before_language_hash)
        self.assertEqual(post_state.adopted_count, expected_count)
        self.assertEqual(post_state.adopted_language_hash, expected_hash)


if __name__ == "__main__": unittest.main()
