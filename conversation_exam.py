"""A six-message, judged use exam that never mutates legislative state."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from rulebook import language_payload, render_language
from state_store import snapshot_hash


def validate_judgment(requirements: list[str], judgment: Any) -> dict[str, Any]:
    if not isinstance(judgment, dict) or not isinstance(judgment.get("requirements"), list):
        return {"valid": False, "reason": "requirements_not_array", "raw": judgment}
    rows = judgment["requirements"]
    ids: list[int] = []
    for row in rows:
        if (not isinstance(row, dict) or isinstance(row.get("id"), bool)
                or not isinstance(row.get("pass"), bool)):
            return {"valid": False, "reason": "malformed_requirement_result", "raw": judgment}
        try:
            requirement_id = int(row["id"])
        except (TypeError, ValueError):
            return {"valid": False, "reason": "malformed_requirement_id", "raw": judgment}
        if str(row["id"]).strip() != str(requirement_id):
            return {"valid": False, "reason": "malformed_requirement_id", "raw": judgment}
        ids.append(requirement_id)
    expected = set(range(1, len(requirements) + 1))
    if len(ids) != len(set(ids)):
        return {"valid": False, "reason": "duplicate_requirement_id", "raw": judgment}
    if set(ids) != expected:
        return {"valid": False, "reason": "invalid_requirement_coverage", "raw": judgment}
    validated = deepcopy(judgment)
    validated["valid"] = True
    validated["reason"] = "valid"
    return validated


def run_conversation(rulebook: dict[str, Any], scenario: dict[str, Any],
                     speaker_call: Callable[[str, str, str], str],
                     judge_call: Callable[[dict[str, Any]], dict[str, Any]],
                     turn: int, models: dict[str, str] | None = None) -> dict[str, Any]:
    captured = language_payload(rulebook)
    language = render_language(rulebook)
    transcript: list[dict[str, Any]] = []
    for index in range(6):
        speaker = "A" if index % 2 == 0 else "B"
        history = "\n".join(f"{m['speaker']}: {m['content']}" for m in transcript) or "(none yet)"
        user = f"SCENARIO:\n{scenario['prompt']}\n\nCONVERSATION SO FAR:\n{history}"
        response = speaker_call(speaker, language, user)
        if isinstance(response, dict):
            content = str(response.get("content", "")).strip()
            model = response.get("model") or (models or {}).get(speaker)
            usage = deepcopy(response.get("usage", {}))
        else:
            content = str(response).strip()
            model = (models or {}).get(speaker)
            usage = {}
        transcript.append({"speaker": speaker, "content": content, "model": model, "usage": usage})
    raw_judgment = judge_call({"scenario": deepcopy(scenario), "messages": deepcopy(transcript),
                               "language_version": captured["version"], "language_hash": captured["hash"]})
    judge_receipt = raw_judgment.pop("_receipt", {}) if isinstance(raw_judgment, dict) else {}
    judgment = validate_judgment(scenario.get("requirements", []), raw_judgment)
    artifact = {
        "id": f"conversation-{turn}", "turn": turn, "type": "conversation",
        "language_version": captured["version"], "language_hash": captured["hash"],
        "scenario": deepcopy(scenario), "messages": transcript, "judgment": judgment,
        "models": deepcopy(models or {}), "judge_receipt": deepcopy(judge_receipt),
    }
    artifact["artifact_hash"] = snapshot_hash(artifact)
    return artifact
