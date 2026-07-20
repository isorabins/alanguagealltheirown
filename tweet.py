#!/usr/bin/env python3
"""Confirmed, idempotent X changelog delivery; never blocks the experiment loop."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from state_store import atomic_write_json, load_json

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
PAGE = "alanguagealltheirown.com"
MAX_LEN = 250
MAX_ATTEMPTS = 3
NOTES_PER_DAY = 2
TWEET_VERBS = ("adopted", "rejected", "reverted")
REFRAIN = "Two AIs are inventing a language, one tested rule at a time."
LABEL = {"adopted": "New rule adopted", "rejected": "Rule rejected", "reverted": "Rule un-adopted"}


def env(name: str) -> str:
    if (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip()
    return os.environ.get(name, "")


def log(message: str) -> None:
    print(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {message}", flush=True)


def stable_id(kind: str, source_id: str, text: str) -> str:
    return "x-" + hashlib.sha256(f"{kind}\0{source_id}\0{text}".encode()).hexdigest()[:32]


def adopted_count(rulebook: dict[str, Any]) -> int:
    return sum(rule.get("status") == "adopted" for rule in rulebook.get("rules", []))


def compose(rulebook: dict[str, Any], rule: dict[str, Any]) -> str:
    head = f"{LABEL[rule['status']]}: "
    tail = f"\n\n{adopted_count(rulebook)} rules in force. {PAGE}"
    body = " ".join(rule.get("text_en", "").replace("**", "").split())
    room = MAX_LEN - len(head) - len(tail) - 2
    if len(body) > room:
        body = body[: max(1, room - 1)].rstrip() + "…"
    return f'{head}"{body}"{tail}'


def _x_receipt(data: Any) -> dict[str, Any] | None:
    """Accept only an explicit X success carrying a durable post or job id."""
    candidates: list[dict[str, Any]] = []
    if isinstance(data, dict):
        if isinstance(data.get("results"), dict) and isinstance(data["results"].get("x"), dict):
            candidates.append({"platform": "x", **data["results"]["x"]})
        for key in ("results", "result", "posts", "data"):
            value = data.get(key)
            if isinstance(value, list):
                candidates.extend(item for item in value if isinstance(item, dict))
            elif isinstance(value, dict):
                candidates.append(value)
        candidates.append(data)
    for item in candidates:
        platform = str(item.get("platform") or item.get("provider") or "").lower()
        success = item.get("success") is True or str(item.get("status", "")).lower() in {
            "success", "posted", "published", "completed", "queued", "processing"
        }
        receipt_id = item.get("post_id") or item.get("id") or item.get("url")
        if platform in {"x", "twitter"} and success and receipt_id:
            return {"platform": "x", "status": str(item.get("status", "confirmed")).lower(),
                    "receipt_id": str(receipt_id), "url": item.get("url")}
    return None


def poll_receipt(delivery: dict[str, Any], key: str) -> tuple[str, dict[str, Any] | None]:
    request_id = delivery.get("request_id")
    if not request_id:
        return "not_found", None
    response = requests.get("https://api.upload-post.com/api/uploadposts/status",
                            headers={"Authorization": f"Apikey {key}"},
                            params={"request_id": request_id}, timeout=20)
    try:
        data = response.json()
    except ValueError:
        data = {}
    receipt = _x_receipt(data) if response.ok else None
    if receipt:
        return "confirmed", receipt
    status = str(data.get("status") or data.get("state") or "").lower()
    if response.status_code == 404 or status in {"failed", "error", "cancelled", "not_found"}:
        return "not_found", None
    return "pending", None


def attempt_post(text: str, delivery: dict[str, Any], state_path: Path) -> dict[str, Any]:
    if len(text) > MAX_LEN:
        raise ValueError(f"X copy exceeds {MAX_LEN} characters")
    key, user = env("UPLOAD_POST_API_KEY"), env("UPLOAD_POST_USER")
    if env("TWEET_ENABLE") != "1" or not key or not user:
        return {"status": "dry", "confirmed": False}
    if delivery.get("status") in {"posted", "blocked"}:
        return delivery
    if delivery.get("request_id"):
        try:
            poll_state, receipt = poll_receipt(delivery, key)
        except requests.RequestException:
            delivery["status"] = "pending_confirmation"
            return delivery
        if poll_state == "confirmed":
            delivery.update({"status": "posted", "confirmed": True, "receipt": receipt})
        elif poll_state == "pending":
            delivery["status"] = "pending_confirmation"
        else:
            delivery.pop("request_id", None)
            if int(delivery.get("attempts", 0)) >= MAX_ATTEMPTS:
                delivery["status"] = "blocked"
            else:
                delivery["status"] = "failed"
        state = load_json(state_path, {})
        state.setdefault("deliveries", {})[delivery["id"]] = delivery
        atomic_write_json(state_path, state)
        if poll_state != "not_found" or delivery["status"] == "blocked":
            return delivery
    delivery["attempts"] = int(delivery.get("attempts", 0)) + 1
    delivery["status"] = "attempting"
    delivery["last_attempt_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    state = load_json(state_path, {})
    state.setdefault("deliveries", {})[delivery["id"]] = delivery
    atomic_write_json(state_path, state)  # persist id + attempt before the network side effect
    try:
        response = requests.post("https://api.upload-post.com/api/upload_text",
                                 headers={"Authorization": f"Apikey {key}", "Idempotency-Key": delivery["id"]},
                                 data={"user": user, "platform[]": ["x"], "title": text, "x_title": text,
                                       "request_id": delivery["id"], "async_upload": "false"}, timeout=20)
        try:
            data = response.json()
        except ValueError:
            data = {}
        receipt = _x_receipt(data) if response.ok else None
        if receipt:
            delivery.update({"status": "posted", "confirmed": True, "receipt": receipt})
        elif response.ok and data.get("success") is True and data.get("request_id"):
            delivery.update({"status": "pending_confirmation", "confirmed": False,
                             "request_id": str(data["request_id"])})
        else:
            delivery.update({"status": "failed", "confirmed": False,
                             "last_error": f"unconfirmed_http_{response.status_code}"})
    except requests.RequestException as error:
        delivery.update({"status": "pending_confirmation", "confirmed": False,
                         "request_id": delivery["id"],
                         "last_error": f"ambiguous_{error.__class__.__name__}"})
    if not delivery.get("confirmed") and delivery["attempts"] >= MAX_ATTEMPTS:
        delivery["status"] = "blocked"
    state = load_json(state_path, {})
    state.setdefault("deliveries", {})[delivery["id"]] = delivery
    atomic_write_json(state_path, state)
    return delivery


def deliver(kind: str, source_id: str, text: str, state: dict[str, Any], state_path: Path) -> dict[str, Any]:
    delivery_id = stable_id(kind, source_id, text)
    delivery = state.setdefault("deliveries", {}).setdefault(delivery_id, {
        "id": delivery_id, "kind": kind, "source_id": source_id, "text": text,
        "attempts": 0, "status": "pending", "confirmed": False,
    })
    return attempt_post(text, delivery, state_path)


def main() -> None:
    rulebook = load_json(STATE / "rulebook.json", {"rules": []})
    state_path = STATE / "tweet-state.json"
    state = load_json(state_path, {"statuses": None, "tweets_sent": 0, "deliveries": {},
                                   "notes_posted": [], "blocked_count": 0})
    current = {rule["id"]: rule["status"] for rule in rulebook.get("rules", [])}
    previous = state.get("statuses")
    if previous is None:
        state["statuses"] = current
        atomic_write_json(state_path, state)
        log(f"bootstrap: snapshot of {len(current)} rule statuses, nothing posted")
        return
    events = [rule for rule in rulebook.get("rules", [])
              if rule.get("status") in TWEET_VERBS and previous.get(rule["id"]) != rule["status"]]
    for rule in events:
        text = compose(rulebook, rule)
        result = deliver("rule", f"{rule['id']}:{rule['status']}", text, state, state_path)
        if result.get("confirmed"):
            state["statuses"][rule["id"]] = rule["status"]
            state["tweets_sent"] = int(state.get("tweets_sent", 0)) + 1
        log(f"{result['status']} {result['id']}: {text}")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("notes_day") != today:
        state["notes_day"], state["notes_day_count"] = today, 0
    budget = max(0, NOTES_PER_DAY - int(state.get("notes_day_count", 0)))
    notes = load_json(ROOT / "notes.json", [])
    prior_notes = state.get("notes_posted", [])
    if isinstance(prior_notes, int):
        prior_notes = [str(notes[i].get("id") or i) for i in range(min(prior_notes, len(notes)))]
        state["notes_posted"] = prior_notes
    posted = set(prior_notes)
    for index, note in enumerate(notes):
        note_id = str(note.get("id") or index)
        if note_id in posted or budget <= 0:
            continue
        text = note.get("tweet") or (" ".join(note.get("note", "").split())[: MAX_LEN - len(PAGE) - 2] + " " + PAGE)
        result = deliver("note", note_id, text[:MAX_LEN], state, state_path)
        if result.get("confirmed"):
            state.setdefault("notes_posted", []).append(note_id)
            state["notes_day_count"] = int(state.get("notes_day_count", 0)) + 1
            budget -= 1
        # A blocked note never consumes budget and cannot stop later notes.
    state["blocked_count"] = sum(row.get("status") == "blocked" for row in state.get("deliveries", {}).values())
    atomic_write_json(state_path, state)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # posting must never take the experiment turn down
        log(f"tweet.py error: {error}")
