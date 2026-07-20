"""Canonical rule views, legislature authority, and exact exam validation."""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, asdict
from typing import Any

from state_store import snapshot_hash

MOTION_RE = re.compile(r"^\s*\**(PROPOSE|ADOPT|REJECT|REVISE|REQUEST(?:-REVISION|-TEST)?)\**\s*:\s*(.+?)\s*$", re.M)
RULE_ID_RE = re.compile(r"\brule[-‐‑‒–—](\d+)\b", re.I)
VALID_VERDICTS = {"SURVIVED", "CORRUPTED", "MISSING"}


def adopted_rules(rulebook: dict[str, Any]) -> list[dict[str, Any]]:
    return [copy.deepcopy(rule) for rule in rulebook.get("rules", []) if rule.get("status") == "adopted"]


def language_payload(rulebook: dict[str, Any]) -> dict[str, Any]:
    rules = [{"id": r["id"], "text_en": r["text_en"]} for r in adopted_rules(rulebook)]
    payload = {"rules": rules}
    payload["hash"] = snapshot_hash(payload)
    payload["version"] = f"adopted-{payload['hash'][:12]}"
    return payload


def render_language(rulebook: dict[str, Any]) -> str:
    view = language_payload(rulebook)
    if not view["rules"]:
        return f"LANGUAGE {view['version']}\nNo adopted rules. Use plain English."
    lines = [f"LANGUAGE {view['version']} ({len(view['rules'])} adopted rules)"]
    lines.extend(f"{rule['id']}: {rule['text_en']}" for rule in view["rules"])
    return "\n".join(lines)


def render_legislature(rulebook: dict[str, Any]) -> str:
    lines = ["LEGISLATURE — statuses below are history and deliberation, not language law"]
    for rule in rulebook.get("rules", []):
        lines.append(f"{rule['id']} [{rule['status']}] {rule['text_en']}")
    return "\n".join(lines) if len(lines) > 1 else lines[0] + "\n(no motions yet)"


def proposal_trial_payload(rulebook: dict[str, Any], rule_id: str) -> dict[str, Any]:
    """Build the only legal non-adopted test view, explicitly labeled and single-rule."""
    proposal = next((r for r in rulebook.get("rules", [])
                     if r.get("id") == rule_id and r.get("status") == "proposed"), None)
    if not proposal:
        raise ValueError("proposal trial requires one currently proposed rule")
    base = language_payload(rulebook)
    trial = {"kind": "proposal_trial", "proposal_id": rule_id, "base_version": base["version"],
             "base_hash": base["hash"], "rules": [*base["rules"],
             {"id": proposal["id"], "text_en": proposal["text_en"], "trial_only": True}]}
    trial["trial_hash"] = snapshot_hash(trial)
    return trial


def validate_judge_coverage(answer_key: list[str], grade: dict[str, Any]) -> tuple[bool, str]:
    items = grade.get("items")
    if not isinstance(items, list):
        return False, "items_not_array"
    numbers: list[int] = []
    for item in items:
        if not isinstance(item, dict) or isinstance(item.get("n"), bool):
            return False, "item_not_object_or_nonnumeric"
        try:
            n = int(item.get("n"))
        except (TypeError, ValueError):
            return False, "nonnumeric_item_id"
        if str(item.get("n")).strip() not in {str(n), f"{n}."}:
            return False, "nonnumeric_item_id"
        if n < 1 or n > len(answer_key):
            return False, "out_of_range_item_id"
        if item.get("verdict") not in VALID_VERDICTS:
            return False, "invalid_verdict"
        numbers.append(n)
    if len(numbers) != len(set(numbers)):
        return False, "duplicate_item_id"
    if set(numbers) != set(range(1, len(answer_key) + 1)):
        return False, "incomplete_item_coverage"
    if not isinstance(grade.get("invented", []), list):
        return False, "invented_not_array"
    return True, "valid"


def score_judgment(answer_key: list[str], grade: dict[str, Any]) -> dict[str, Any]:
    valid, reason = validate_judge_coverage(answer_key, grade)
    if not valid:
        return {"valid": False, "reason": reason, "fidelity": None}
    items = grade["items"]
    survived = sum(item["verdict"] == "SURVIVED" for item in items)
    invented = grade.get("invented", [])
    fidelity = round(100 * survived / (len(answer_key) + len(invented)))
    if grade.get("mode") == "RESPONDED":
        fidelity = min(fidelity, 15)
    return {"valid": True, "reason": "valid", "fidelity": max(0, min(100, fidelity)),
            "survived": survived, "invented": invented}


@dataclass
class MotionReceipt:
    accepted: bool
    reason: str
    agent: str
    verb: str | None = None
    rule_id: str | None = None
    changed: bool = False

    def dict(self) -> dict[str, Any]:
        return asdict(self)


def _motion_lines(text: str) -> list[tuple[str, str]]:
    return [("REQUEST" if m.group(1).upper().startswith("REQUEST") else m.group(1).upper(),
             re.sub(r"[‐‑‒–—]", "-", m.group(2)).strip(" *"))
            for m in MOTION_RE.finditer(text)]


def apply_authorized_motion(text: str, rulebook: dict[str, Any], turn: int, agent: str,
                            rationale: str = "") -> MotionReceipt:
    motions = _motion_lines(text)
    if not motions:
        return MotionReceipt(False, "no_motion", agent)
    if len(motions) != 1:
        return MotionReceipt(False, "multiple_motions", agent)
    verb, rest = motions[0]
    if agent == "A" and verb not in {"PROPOSE", "REVISE"}:
        return MotionReceipt(False, "inventor_cannot_vote", agent, verb)
    if agent == "B" and verb not in {"ADOPT", "REJECT", "REQUEST"}:
        return MotionReceipt(False, "auditor_cannot_originate", agent, verb)
    match = RULE_ID_RE.search(rest)
    if verb == "PROPOSE":
        proposed = re.sub(r"^rule-\d+\s*[-:]\s*", "", rest, flags=re.I).strip()
        if re.match(r"^(?:PROPOSE|ADOPT|REJECT|REVISE|REQUEST(?:-REVISION|-TEST)?)\s*:", proposed, re.I):
            return MotionReceipt(False, "nested_motion", agent, verb)
        if len(proposed) < 12:
            return MotionReceipt(False, "proposal_too_short", agent, verb)
        if any(r.get("text_en", "").strip().casefold() == proposed.casefold()
               for r in rulebook.get("rules", [])):
            return MotionReceipt(False, "duplicate_proposal", agent, verb)
        rule_id = f"rule-{int(rulebook.get('next_id', 1)):03d}"
        rulebook["next_id"] = int(rulebook.get("next_id", 1)) + 1
        rulebook.setdefault("rules", []).append({
            "id": rule_id, "text_en": proposed, "status": "proposed", "proposed_turn": turn,
            "scores": None, "history": [{"verb": "proposed", "turn": turn, "agent": agent, "why": rationale}],
        })
        return MotionReceipt(True, "proposal_recorded", agent, verb, rule_id, True)
    if not match:
        return MotionReceipt(False, "malformed_rule_id", agent, verb)
    rule_id = f"rule-{int(match.group(1)):03d}"
    rule = next((r for r in rulebook.get("rules", []) if r.get("id") == rule_id), None)
    if not rule:
        return MotionReceipt(False, "unknown_rule_id", agent, verb, rule_id)

    previous = rule.get("status")
    if verb in {"ADOPT", "REJECT"} and previous != "proposed":
        return MotionReceipt(False, "settled_or_ineligible_motion", agent, verb, rule_id)
    if agent == "B":
        proposed = [r for r in rulebook.get("rules", []) if r.get("status") == "proposed"]
        latest = max(proposed, key=lambda r: (int(r.get("proposed_turn", -1)),
                                              rulebook.get("rules", []).index(r)), default=None)
        if latest is None or rule_id != latest.get("id"):
            return MotionReceipt(False, "not_latest_focused_proposal", agent, verb, rule_id)
        if verb == "REQUEST":
            focus = re.sub(r"^.*?rule-\d+\s*(?:->|[-:])\s*", "", rest, count=1, flags=re.I).strip(" *")
            if focus == rest.strip(" *") or len(focus) < 12:
                return MotionReceipt(False, "missing_focused_request", agent, verb, rule_id)
            return MotionReceipt(True, "focused_work_requested", agent, verb, rule_id, False)

    if verb == "ADOPT":
        rule["status"] = "adopted"
    elif verb == "REJECT":
        rule["status"] = "rejected"
    elif verb == "REVISE":
        if previous not in {"proposed", "reverted"}:
            return MotionReceipt(False, "settled_or_ineligible_motion", agent, verb, rule_id)
        if "->" not in rest:
            return MotionReceipt(False, "missing_revision_text", agent, verb, rule_id)
        replacement = rest.split("->", 1)[1].strip(" *")
        if re.match(r"^(?:PROPOSE|ADOPT|REJECT|REVISE|REQUEST(?:-REVISION|-TEST)?)\s*:", replacement, re.I):
            return MotionReceipt(False, "nested_motion", agent, verb, rule_id)
        if len(replacement) < 12:
            return MotionReceipt(False, "revision_too_short", agent, verb, rule_id)
        rule["text_en"] = replacement
        rule["status"] = "proposed"
        rule["proposed_turn"] = turn
    rule.setdefault("history", []).append({"verb": verb.lower(), "turn": turn, "agent": agent,
                                            "why": rationale})
    return MotionReceipt(True, "motion_applied", agent, verb, rule_id, True)
