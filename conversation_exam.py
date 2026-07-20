"""A six-message, judged use exam that never mutates legislative state."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from rulebook import language_payload, render_language
from state_store import snapshot_hash


def run_conversation(rulebook: dict[str, Any], scenario: dict[str, Any],
                     speaker_call: Callable[[str, str, str], str],
                     judge_call: Callable[[dict[str, Any]], dict[str, Any]],
                     turn: int) -> dict[str, Any]:
    captured = language_payload(rulebook)
    language = render_language(rulebook)
    transcript: list[dict[str, str]] = []
    for index in range(6):
        speaker = "A" if index % 2 == 0 else "B"
        history = "\n".join(f"{m['speaker']}: {m['content']}" for m in transcript) or "(none yet)"
        user = f"SCENARIO:\n{scenario['prompt']}\n\nCONVERSATION SO FAR:\n{history}"
        content = speaker_call(speaker, language, user).strip()
        transcript.append({"speaker": speaker, "content": content})
    judgment = judge_call({"scenario": deepcopy(scenario), "messages": deepcopy(transcript),
                           "language_version": captured["version"], "language_hash": captured["hash"]})
    return {
        "id": f"conversation-{turn}", "turn": turn, "type": "conversation",
        "language_version": captured["version"], "language_hash": captured["hash"],
        "scenario": deepcopy(scenario), "messages": transcript, "judgment": judgment,
        "artifact_hash": snapshot_hash({"scenario": scenario, "messages": transcript, "judgment": judgment}),
    }
