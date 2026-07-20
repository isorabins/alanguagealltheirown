"""Minimal durable collaboration inbox and canonical loop-owned history."""
from __future__ import annotations

import json
import os
import secrets
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

import requests

from state_store import atomic_write_json, load_json

SCHEMA_VERSION = 1
PUBLIC_STATUSES = {"awaiting_iso", "answered", "delivered", "approved", "dismissed", "acted", "no_action"}


def empty_state() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "research": [], "asks": [], "suggestions": [],
            "processed_ids": [], "deliveries": []}


class RedisRest:
    """Server-only Upstash command client. Tokens never enter browser responses."""
    def __init__(self, url: str | None = None, token: str | None = None, namespace: str = "alato:v1"):
        self.url = (url or os.environ.get("UPSTASH_REDIS_REST_URL", "")).rstrip("/")
        self.token = token or os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
        self.namespace = namespace
        if not self.url or not self.token:
            raise RuntimeError("missing Upstash REST configuration")

    def command(self, *parts: Any) -> Any:
        response = requests.post(self.url, headers={"Authorization": f"Bearer {self.token}"},
                                 json=list(parts), timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(f"redis command failed: {data['error']}")
        return data.get("result")

    def enqueue(self, queue: str, record: dict[str, Any]) -> bool:
        record_id = record["id"]
        marker = f"{self.namespace}:id:{record_id}"
        script = ("if redis.call('SET',KEYS[1],'1','NX') then "
                  "redis.call('RPUSH',KEYS[2],ARGV[1]); return 1 else return 0 end")
        result = self.command("EVAL", script, 2, marker, f"{self.namespace}:queue:{queue}",
                              json.dumps(record, separators=(",", ":")))
        return int(result or 0) == 1

    def claim(self, queue: str, owner: str, lease_seconds: int = 120) -> dict[str, Any] | None:
        # Peek + lease leaves the record in the queue. A crash only expires the lease;
        # ack is the sole operation that removes the leased value.
        script = ("local v=redis.call('LINDEX',KEYS[1],0); if not v then return nil end; "
                  "if not redis.call('SET',KEYS[2],v,'EX',ARGV[1],'NX') then return nil end; return v")
        raw = self.command("EVAL", script, 2, f"{self.namespace}:queue:{queue}",
                           f"{self.namespace}:lease:{queue}", lease_seconds)
        return json.loads(raw) if raw else None

    def ack(self, queue: str, owner: str, record_id: str) -> None:
        script = ("local v=redis.call('GET',KEYS[2]); if not v then return 0 end; "
                  "redis.call('LREM',KEYS[1],1,v); redis.call('DEL',KEYS[2]); "
                  "redis.call('SET',KEYS[3],'1'); return 1")
        self.command("EVAL", script, 3, f"{self.namespace}:queue:{queue}",
                     f"{self.namespace}:lease:{queue}", f"{self.namespace}:done:{record_id}")

    def publish_private(self, state: dict[str, Any]) -> None:
        self.command("SET", f"{self.namespace}:private-state",
                     json.dumps(state, separators=(",", ":"), ensure_ascii=False))


def stable_record(kind: str, asker: str, text: str, record_id: str | None = None) -> dict[str, Any]:
    clean = " ".join(text.split()).strip()
    if not clean or len(clean) > 1200:
        raise ValueError("text must contain 1-1200 characters")
    return {"id": record_id or f"{kind.lower()}-{secrets.token_hex(12)}", "kind": kind,
            "asker": asker, "question" if kind in {"ASK", "RESEARCH"} else "text": clean,
            "status": "awaiting_iso" if kind == "ASK" else "queued", "created_at": int(time.time())}


def reconcile(state_path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    state = load_json(state_path, empty_state())
    processed = set(state.get("processed_ids", []))
    buckets = {"RESEARCH": "research", "ASK": "asks", "SUGGESTION": "suggestions"}
    for record in records:
        record_id, kind = record.get("id"), record.get("kind")
        if not record_id or record_id in processed or kind not in buckets:
            continue
        state[buckets[kind]].append(deepcopy(record))
        state["processed_ids"].append(record_id)
        processed.add(record_id)
    atomic_write_json(state_path, state)
    return state


def deliver_one(state: dict[str, Any], kind: str, agent: str, turn: int | None = None) -> dict[str, Any] | None:
    bucket = {"ASK": "asks", "SUGGESTION": "suggestions", "RESEARCH": "research"}[kind]
    eligible_status = {"ASK": "answered", "SUGGESTION": "approved", "RESEARCH": "answered"}[kind]
    for record in state.get(bucket, []):
        if record.get("status") != eligible_status or record.get("asker", agent) != agent:
            continue
        record["status"] = "delivered"
        record["delivered_to"] = agent
        if turn is not None:
            record["delivery_turn"] = turn
        if kind == "ASK":
            payload = {"id": record["id"], "question": record["question"], "answer": record["answer"]}
        elif kind == "RESEARCH":
            payload = {"id": record["id"], "question": record["question"], "findings": record.get("findings", ""),
                       "limitations": record.get("limitations", ""), "citations": record.get("citations", [])}
        else:
            payload = {"id": record["id"], "optional_suggestion": record["text"]}
        state.setdefault("deliveries", []).append({"kind": kind, **payload})
        return {"kind": kind, **payload}
    return None


def public_state(state: dict[str, Any]) -> dict[str, Any]:
    asks = [{k: r.get(k) for k in ("id", "asker", "question", "status", "answer", "request_turn", "answer_turn", "delivery_turn") if r.get(k) is not None}
            for r in state.get("asks", []) if r.get("status") in PUBLIC_STATUSES]
    suggestions = [{k: r.get(k) for k in ("id", "status", "outcome") if r.get(k) is not None}
                   for r in state.get("suggestions", []) if r.get("status") in {"approved", "delivered", "acted", "no_action"}]
    research = [{k: r.get(k) for k in ("id", "asker", "question", "status", "findings", "limitations", "citations", "request_turn", "answer_turn", "delivery_turn", "error")
                 if r.get(k) is not None} for r in state.get("research", [])]
    return {"asks": asks, "suggestions": suggestions, "research": research}


def _apply_moderation(state: dict[str, Any], command: dict[str, Any], turn: int | None = None) -> None:
    target = command.get("id")
    action = command.get("action")
    if action == "answer_ask":
        record = next((row for row in state.get("asks", []) if row.get("id") == target), None)
        if record and record.get("status") == "awaiting_iso" and isinstance(command.get("answer"), str):
            record.update({"status": "answered", "answer": command["answer"],
                           "answered_at": command.get("created_at"), "answer_turn": turn})
    elif action in {"approve_suggestion", "dismiss_suggestion"}:
        record = next((row for row in state.get("suggestions", []) if row.get("id") == target), None)
        if record and record.get("status") == "pending_review":
            record["status"] = "approved" if action == "approve_suggestion" else "dismissed"
            record["moderated_at"] = command.get("created_at")


def sync_remote(state: dict[str, Any], owner: str = "loop", limit: int = 20,
                turn: int | None = None) -> dict[str, Any]:
    """Claim transport records, reconcile once, and publish the private loop-owned view."""
    try:
        redis = RedisRest()
    except RuntimeError:
        return state
    processed = set(state.get("processed_ids", []))
    for queue in ("suggestion", "moderation"):
        for index in range(limit):
            lease_owner = f"{owner}-{queue}-{index}"
            record = redis.claim(queue, lease_owner)
            if not record:
                break
            record_id = record.get("id")
            if record_id and record_id not in processed:
                if queue == "suggestion":
                    record.setdefault("status", "pending_review")
                    state.setdefault("suggestions", []).append(record)
                else:
                    _apply_moderation(state, record, turn)
                state.setdefault("processed_ids", []).append(record_id)
                processed.add(record_id)
            redis.ack(queue, lease_owner, record_id or "malformed")
    redis.publish_private({"asks": state.get("asks", []), "suggestions": state.get("suggestions", []),
                           "cleanup": state.get("cleanup", [])})
    return state
