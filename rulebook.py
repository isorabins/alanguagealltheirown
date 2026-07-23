"""Canonical rule views, legislature authority, and exact exam validation."""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, asdict
from typing import Any

from state_store import snapshot_hash

MOTION_RE = re.compile(r"^\s*\**(PROPOSE|REPEAL|ADOPT|REJECT|REVISE|REQUEST(?:-REVISION|-TEST)?)\**\s*:\s*(.+?)\s*$", re.M)
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
        pending = rule.get("pending_repeal")
        if isinstance(pending, dict):
            lines.append(f"  PENDING REPEAL [{pending.get('proposed_turn', '?')}] {pending.get('rationale', '')}")
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
    line: str | None = None

    def dict(self) -> dict[str, Any]:
        return asdict(self)


def _motion_lines(text: str) -> list[tuple[str, str, str]]:
    return [("REQUEST" if m.group(1).upper().startswith("REQUEST") else m.group(1).upper(),
             re.sub(r"[‐‑‒–—]", "-", m.group(2)).strip(" *"), m.group(0).strip())
            for m in MOTION_RE.finditer(text)]


def motion_line(text: str) -> str | None:
    motions = _motion_lines(text)
    return motions[0][2] if len(motions) == 1 else None


def _open_motions(rulebook: dict[str, Any]) -> list[tuple[int, int, str, dict[str, Any]]]:
    open_rows = []
    for index, rule in enumerate(rulebook.get("rules", [])):
        if rule.get("status") == "proposed":
            open_rows.append((int(rule.get("proposed_turn", -1)), index, "add", rule))
        pending = rule.get("pending_repeal")
        if isinstance(pending, dict):
            open_rows.append((int(pending.get("proposed_turn", -1)), index, "repeal", rule))
    return open_rows


def apply_authorized_motion(text: str, rulebook: dict[str, Any], turn: int, agent: str,
                            rationale: str = "") -> MotionReceipt:
    motions = _motion_lines(text)
    if not motions:
        return MotionReceipt(False, "no_motion", agent)
    if len(motions) != 1:
        return MotionReceipt(False, "multiple_motions", agent)
    verb, rest, line = motions[0]
    if agent == "A" and verb not in {"PROPOSE", "REVISE", "REPEAL"}:
        return MotionReceipt(False, "inventor_cannot_vote", agent, verb, line=line)
    if agent == "B" and verb not in {"ADOPT", "REJECT", "REQUEST"}:
        return MotionReceipt(False, "auditor_cannot_originate", agent, verb, line=line)
    match = RULE_ID_RE.search(rest)
    if verb == "PROPOSE":
        if _open_motions(rulebook):
            return MotionReceipt(False, "proposal_already_open", agent, verb, line=line)
        proposed = re.sub(r"^rule-\d+\s*[-:]\s*", "", rest, flags=re.I).strip()
        if re.match(r"^(?:PROPOSE|REPEAL|ADOPT|REJECT|REVISE|REQUEST(?:-REVISION|-TEST)?)\s*:", proposed, re.I):
            return MotionReceipt(False, "nested_motion", agent, verb, line=line)
        if len(proposed) < 12:
            return MotionReceipt(False, "proposal_too_short", agent, verb, line=line)
        if any(r.get("text_en", "").strip().casefold() == proposed.casefold()
               and r.get("status") in {"adopted", "proposed"}
               for r in rulebook.get("rules", [])):
            return MotionReceipt(False, "duplicate_proposal", agent, verb, line=line)
        rule_id = f"rule-{int(rulebook.get('next_id', 1)):03d}"
        rulebook["next_id"] = int(rulebook.get("next_id", 1)) + 1
        rulebook.setdefault("rules", []).append({
            "id": rule_id, "text_en": proposed, "status": "proposed", "proposed_turn": turn,
            "scores": None, "history": [{"verb": "proposed", "turn": turn, "agent": agent, "why": rationale}],
        })
        return MotionReceipt(True, "proposal_recorded", agent, verb, rule_id, True, line)
    if not match:
        return MotionReceipt(False, "malformed_rule_id", agent, verb, line=line)
    rule_id = f"rule-{int(match.group(1)):03d}"
    rule = next((r for r in rulebook.get("rules", []) if r.get("id") == rule_id), None)
    if not rule:
        return MotionReceipt(False, "unknown_rule_id", agent, verb, rule_id, line=line)

    if verb == "REPEAL":
        if _open_motions(rulebook):
            return MotionReceipt(False, "proposal_already_open", agent, verb, rule_id, line=line)
        if rule.get("status") != "adopted":
            return MotionReceipt(False, "repeal_target_not_adopted", agent, verb, rule_id, line=line)
        if "->" not in rest:
            return MotionReceipt(False, "missing_repeal_rationale", agent, verb, rule_id, line=line)
        repeal_reason = rest.split("->", 1)[1].strip(" *")
        if len(repeal_reason) < 12:
            return MotionReceipt(False, "repeal_rationale_too_short", agent, verb, rule_id, line=line)
        if re.match(r"^(?:PROPOSE|REPEAL|ADOPT|REJECT|REVISE|REQUEST(?:-REVISION|-TEST)?)\s*:", repeal_reason, re.I):
            return MotionReceipt(False, "nested_motion", agent, verb, rule_id, line=line)
        rule["pending_repeal"] = {"kind": "repeal", "target_id": rule_id,
                                  "rationale": repeal_reason, "proposed_turn": turn,
                                  "agent": agent}
        rule.setdefault("history", []).append({"verb": "repeal_proposed", "turn": turn,
                                                "agent": agent, "why": rationale or repeal_reason})
        return MotionReceipt(True, "repeal_proposed", agent, verb, rule_id, True, line)

    previous = rule.get("status")
    pending_repeal = isinstance(rule.get("pending_repeal"), dict)
    if verb in {"ADOPT", "REJECT"} and previous != "proposed" and not pending_repeal:
        return MotionReceipt(False, "settled_or_ineligible_motion", agent, verb, rule_id, line=line)
    if agent == "B":
        open_rows = _open_motions(rulebook)
        latest = max(open_rows, key=lambda row: (row[0], row[1]), default=None)
        if latest is None or rule_id != latest[3].get("id"):
            return MotionReceipt(False, "not_latest_focused_proposal", agent, verb, rule_id, line=line)
        if verb == "REQUEST":
            focus = re.sub(r"^.*?rule-\d+\s*(?:->|[-:])\s*", "", rest, count=1, flags=re.I).strip(" *")
            if focus == rest.strip(" *") or len(focus) < 12:
                return MotionReceipt(False, "missing_focused_request", agent, verb, rule_id, line=line)
            return MotionReceipt(True, "focused_work_requested", agent, verb, rule_id, False, line)

    if pending_repeal and verb in {"ADOPT", "REJECT"}:
        rule.pop("pending_repeal", None)
        history_verb = "repeal_adopted" if verb == "ADOPT" else "repeal_rejected"
        if verb == "ADOPT":
            rule["status"] = "repealed"
        rule.setdefault("history", []).append({"verb": history_verb, "turn": turn,
                                                "agent": agent, "why": rationale})
        return MotionReceipt(True, f"{history_verb}", agent, verb, rule_id, True, line)
    if verb == "ADOPT":
        rule["status"] = "adopted"
    elif verb == "REJECT":
        rule["status"] = "rejected"
    elif verb == "REVISE":
        if pending_repeal and previous == "adopted":
            if "->" not in rest:
                return MotionReceipt(False, "missing_revision_text", agent, verb, rule_id, line=line)
            replacement = rest.split("->", 1)[1].strip(" *")
            if len(replacement) < 12:
                return MotionReceipt(False, "revision_too_short", agent, verb, rule_id, line=line)
            rule["pending_repeal"].update({"rationale": replacement, "proposed_turn": turn})
            rule.setdefault("history", []).append({"verb": "repeal_revised", "turn": turn,
                                                    "agent": agent, "why": rationale or replacement})
            return MotionReceipt(True, "repeal_revised", agent, verb, rule_id, True, line)
        if previous != "proposed":
            return MotionReceipt(False, "settled_or_ineligible_motion", agent, verb, rule_id, line=line)
        if "->" not in rest:
            return MotionReceipt(False, "missing_revision_text", agent, verb, rule_id, line=line)
        replacement = rest.split("->", 1)[1].strip(" *")
        if re.match(r"^(?:PROPOSE|REPEAL|ADOPT|REJECT|REVISE|REQUEST(?:-REVISION|-TEST)?)\s*:", replacement, re.I):
            return MotionReceipt(False, "nested_motion", agent, verb, rule_id, line=line)
        if len(replacement) < 12:
            return MotionReceipt(False, "revision_too_short", agent, verb, rule_id, line=line)
        rule["text_en"] = replacement
        rule["status"] = "proposed"
        rule["proposed_turn"] = turn
    rule.setdefault("history", []).append({"verb": verb.lower(), "turn": turn, "agent": agent,
                                            "why": rationale})
    return MotionReceipt(True, "motion_applied", agent, verb, rule_id, True, line)
