"""Deterministic, bounded retrieval from the project's canonical local corpus."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from state_store import load_json


GITHUB_BLOB = "https://github.com/isorabins/alanguagealltheirown/blob/main/"
PROJECT_MARKER = re.compile(
    r"(?:\bturn\s*[-:#]?\s*\d+\b"
    r"|\brule[-‐‑‒–—]\d+\b"
    r"|\b(?:this|current|visible|live)\s+(?:project|experiment|harness|rulebook|legislature)\b"
    r"|\b(?:harness|legislature|rulebook|motion_receipt|proposal_already_open"
    r"|settled_or_ineligible_motion|pending_repeal|language_hash|conversation-\d+)\b)",
    re.I,
)
TURN_RE = re.compile(r"\bturn\s*[-:#]?\s*(\d+)\b", re.I)
RULE_RE = re.compile(r"\brule[-‐‑‒–—](\d+)\b", re.I)
ERROR_RE = re.compile(r"\b[a-z]+(?:_[a-z]+)+\b")
STOP_WORDS = {
    "about", "actual", "after", "again", "before", "being", "could", "current",
    "does", "from", "have", "into", "project", "should", "that", "their", "there",
    "these", "they", "this", "turn", "visible", "what", "when", "where", "which",
    "while", "with", "would",
}
DOC_PATHS = (
    "README.md",
    "MECHANICS.md",
    "specs/001-experiment-repair/spec.md",
    "specs/001-experiment-repair/plan.md",
)
MAX_FINDINGS_CHARS = 24_000


def is_project_question(question: str) -> bool:
    return bool(PROJECT_MARKER.search(question or ""))


def _words(text: str) -> set[str]:
    return {
        word for word in re.findall(r"[a-z0-9_]+", text.casefold())
        if len(word) >= 4 and word not in STOP_WORDS
    }


def _score(query_words: set[str], value: Any) -> int:
    haystack = json.dumps(value, ensure_ascii=False).casefold()
    return sum(word in haystack for word in query_words)


def _trim(value: Any, limit: int = 6000) -> Any:
    if not isinstance(value, str) or len(value) <= limit:
        return value
    return value[:limit] + f"\n[bounded: {len(value) - limit} characters omitted]"


def _compact_event(event: dict[str, Any]) -> dict[str, Any]:
    compact = {
        key: event.get(key)
        for key in (
            "turn", "type", "agent", "payload", "fidelity", "judge_reason",
            "token_delta_pct", "orig_tokens", "enc_tokens", "language_version",
            "language_hash",
        )
        if event.get(key) is not None
    }
    for key in ("content", "original", "encoded", "decoded", "lost"):
        if event.get(key) is not None:
            compact[key] = _trim(event[key])
    if isinstance(event.get("motion_receipt"), dict):
        compact["motion_receipt"] = event["motion_receipt"]
    return compact


def _compact_rule(rule: dict[str, Any]) -> dict[str, Any]:
    compact = {
        key: rule.get(key)
        for key in ("id", "status", "proposed_turn", "text_en", "pending_repeal")
        if rule.get(key) is not None
    }
    history = rule.get("history")
    if isinstance(history, list):
        compact["recent_history"] = history[-8:]
        compact["history_entries"] = len(history)
    return compact


def collect_project_evidence(
    root: Path,
    question: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return only question-matched, bounded evidence with stable source locators."""
    conversation = load_json(root / "state/conversation.json", [])
    rulebook = load_json(root / "state/rulebook.json", {})
    conversations = load_json(root / "state/conversations.json", [])
    conversation = conversation if isinstance(conversation, list) else []
    rules = rulebook.get("rules", []) if isinstance(rulebook, dict) else []
    conversations = conversations if isinstance(conversations, list) else []
    query_words = _words(question)
    turns = {int(value) for value in TURN_RE.findall(question)}
    rule_ids = {f"rule-{int(value):03d}" for value in RULE_RE.findall(question)}
    error_reasons = set(ERROR_RE.findall(question.casefold()))
    evidence: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(source_id: str, title: str, path: str, locator: str, data: Any) -> None:
        if source_id in seen or len(evidence) >= limit:
            return
        seen.add(source_id)
        evidence.append({
            "source_id": source_id,
            "title": title,
            "path": path,
            "locator": locator,
            "data": data,
        })

    state_terms = re.search(
        r"\b(?:harness|legislature|rulebook|proposal|repeal|motion|blocked|state|status)\b",
        question,
        re.I,
    )
    if state_terms and isinstance(rulebook, dict) and rules:
        counts: dict[str, int] = {}
        for rule in rules:
            status = str(rule.get("status", "unknown"))
            counts[status] = counts.get(status, 0) + 1
        open_proposals = [
            rule.get("id") for rule in rules if rule.get("status") == "proposed"
        ]
        pending_repeals = [
            rule.get("id") for rule in rules
            if isinstance(rule.get("pending_repeal"), dict)
        ]
        add(
            "rulebook-current-state",
            "Canonical rulebook current state",
            "state/rulebook.json",
            "current status summary",
            {
                "version": rulebook.get("version"),
                "changes": rulebook.get("changes"),
                "next_id": rulebook.get("next_id"),
                "status_counts": counts,
                "open_proposal_count": len(open_proposals),
                "open_proposal_ids": open_proposals[-12:],
                "pending_repeal_count": len(pending_repeals),
                "pending_repeal_ids": pending_repeals,
                "latest_turn": conversation[-1].get("turn") if conversation else None,
            },
        )

    for turn in sorted(turns):
        rows = [_compact_event(row) for row in conversation if row.get("turn") == turn]
        if rows:
            add(
                f"conversation-turn-{turn}",
                f"Canonical conversation turn {turn}",
                "state/conversation.json",
                f"turn {turn}",
                rows,
            )
        artifact = next(
            (row for row in conversations if row.get("turn") == turn),
            None,
        )
        if artifact:
            add(
                f"conversation-exam-{turn}",
                f"Conversation exam at turn {turn}",
                "state/conversations.json",
                f"turn {turn}",
                artifact,
            )

    for rule_id in sorted(rule_ids):
        rule = next((row for row in rules if row.get("id") == rule_id), None)
        if rule:
            add(
                f"rulebook-{rule_id}",
                f"Canonical rule record {rule_id}",
                "state/rulebook.json",
                rule_id,
                _compact_rule(rule),
            )

    for reason in sorted(error_reasons):
        rows = [
            _compact_event(row)
            for row in conversation
            if isinstance(row.get("motion_receipt"), dict)
            and str(row["motion_receipt"].get("reason", "")).casefold() == reason
        ][-6:]
        if rows:
            add(
                f"legislature-reason-{reason}",
                f"Recent legislature receipts: {reason}",
                "state/conversation.json",
                f"motion_receipt.reason={reason}",
                rows,
            )

    scored_events = sorted(
        (
            (_score(query_words, row), index, row)
            for index, row in enumerate(conversation[-500:])
        ),
        key=lambda item: (item[0], item[1]),
        reverse=True,
    )
    for score, _, row in scored_events[:4]:
        if score < 2:
            continue
        turn = row.get("turn")
        row_type = row.get("type", "event")
        add(
            f"conversation-match-{turn}-{row_type}",
            f"Matched canonical conversation evidence at turn {turn}",
            "state/conversation.json",
            f"turn {turn}, type {row_type}",
            _compact_event(row),
        )

    scored_rules = sorted(
        ((_score(query_words, rule), index, rule) for index, rule in enumerate(rules)),
        key=lambda item: (item[0], item[1]),
        reverse=True,
    )
    for score, _, rule in scored_rules[:3]:
        if score < 2:
            continue
        rule_id = str(rule.get("id"))
        add(
            f"rulebook-match-{rule_id}",
            f"Matched canonical rule record {rule_id}",
            "state/rulebook.json",
            rule_id,
            _compact_rule(rule),
        )

    for relative in DOC_PATHS:
        path = root / relative
        if not path.exists():
            continue
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", path.read_text())
            if paragraph.strip()
        ]
        ranked = sorted(
            ((_score(query_words, paragraph), index, paragraph)
             for index, paragraph in enumerate(paragraphs)),
            key=lambda item: (item[0], -item[1]),
            reverse=True,
        )
        if ranked and ranked[0][0] >= 2:
            score, index, paragraph = ranked[0]
            add(
                f"doc-{relative}-{index}",
                f"Matched project documentation: {relative}",
                relative,
                f"paragraph {index + 1}",
                _trim(paragraph, 3000),
            )

    return evidence


def project_lookup(root: Path, question: str) -> dict[str, Any]:
    evidence = collect_project_evidence(root, question)
    bounded: list[dict[str, Any]] = []
    remaining = MAX_FINDINGS_CHARS - 1000
    for item in evidence:
        candidate = dict(item)
        encoded = json.dumps(candidate, ensure_ascii=False)
        if len(encoded) > remaining:
            candidate["data"] = _trim(
                json.dumps(candidate["data"], ensure_ascii=False),
                max(256, remaining - 800),
            )
            encoded = json.dumps(candidate, ensure_ascii=False)
        if len(encoded) > remaining:
            break
        bounded.append(candidate)
        remaining -= len(encoded)
    evidence_was_bounded = len(bounded) < len(evidence)
    evidence = bounded
    citations = [
        {
            "source_id": item["source_id"],
            "title": item["title"],
            "url": GITHUB_BLOB + item["path"],
            "locator": item["locator"],
        }
        for item in evidence
    ]
    if not evidence:
        return {
            "adequate": False,
            "findings": "",
            "limitations": [
                "No question-matched evidence was found in the bounded project corpus."
            ],
            "citations": [],
            "evidence_count": 0,
        }
    findings = (
        "Project corpus evidence (not a web result):\n"
        + json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
    )
    limitations = [
        "Evidence is bounded to canonical state and core project documentation; "
        "the requesting agent must distinguish recorded facts from prior agent claims."
    ]
    if evidence_was_bounded:
        limitations.append("Additional matched project evidence was omitted by the size bound.")
    return {
        "adequate": True,
        "findings": findings,
        "limitations": limitations,
        "citations": citations,
        "evidence_count": len(evidence),
    }
