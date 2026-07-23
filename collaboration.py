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
            "processed_inbox_ids": [], "deliveries": []}


def _processed(state: dict[str, Any]) -> list[str]:
    """Read old `processed_ids` state but write only the canonical schema field."""
    current = state.setdefault("processed_inbox_ids", [])
    for record_id in state.pop("processed_ids", []):
        if record_id not in current:
            current.append(record_id)
    return current


class RedisRest:
    """Server-only Upstash command client. Tokens never enter browser responses."""
    def __init__(self, url: str | None = None, token: str | None = None, namespace: str = "alato:v1",
                 timeout: float = 2.0):
        self.url = (url or os.environ.get("UPSTASH_REDIS_REST_URL", "")).rstrip("/")
        self.token = token or os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
        self.namespace = namespace
        self.timeout = timeout
        if not self.url or not self.token:
            raise RuntimeError("missing Upstash REST configuration")

    def command(self, *parts: Any) -> Any:
        response = requests.post(self.url, headers={"Authorization": f"Bearer {self.token}"},
                                 json=list(parts), timeout=self.timeout)
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
                  "if not redis.call('SET',KEYS[2],ARGV[2]..'\\n'..v,'EX',ARGV[1],'NX') then return nil end; return v")
        raw = self.command("EVAL", script, 2, f"{self.namespace}:queue:{queue}",
                           f"{self.namespace}:lease:{queue}", lease_seconds, owner)
        return json.loads(raw) if raw else None

    def ack(self, queue: str, owner: str, record_id: str) -> None:
        script = ("local v=redis.call('GET',KEYS[2]); if not v then return 0 end; "
                  "local p=ARGV[1]..'\\n'; if string.sub(v,1,string.len(p))~=p then return 0 end; "
                  "local raw=string.sub(v,string.len(p)+1); redis.call('LREM',KEYS[1],1,raw); redis.call('DEL',KEYS[2]); "
                  "redis.call('SET',KEYS[3],'1'); return 1")
        self.command("EVAL", script, 3, f"{self.namespace}:queue:{queue}",
                     f"{self.namespace}:lease:{queue}", f"{self.namespace}:done:{record_id}", owner)

    def publish_private(self, state: dict[str, Any]) -> None:
        self.command("SET", f"{self.namespace}:private-state",
                     json.dumps(state, separators=(",", ":"), ensure_ascii=False))

    def load_private(self) -> dict[str, Any] | None:
        raw = self.command("GET", f"{self.namespace}:private-state")
        if not raw:
            return None
        value = json.loads(raw)
        return value if isinstance(value, dict) else None


def stable_record(kind: str, requester: str, text: str, record_id: str | None = None) -> dict[str, Any]:
    clean = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not clean or len(clean) > 1200:
        raise ValueError("text must contain 1-1200 characters")
    return {"id": record_id or f"{kind.lower()}-{secrets.token_hex(12)}", "kind": kind,
            "requester": requester, "question" if kind in {"ASK", "RESEARCH"} else "text": clean,
            "status": "awaiting_iso" if kind == "ASK" else "queued", "created_at": int(time.time())}


def reconcile(state_path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    state = load_json(state_path, empty_state())
    processed_list = _processed(state)
    processed = set(processed_list)
    buckets = {"RESEARCH": "research", "ASK": "asks", "SUGGESTION": "suggestions"}
    for record in records:
        record_id, kind = record.get("id"), record.get("kind")
        if not record_id or record_id in processed or kind not in buckets:
            continue
        state[buckets[kind]].append(deepcopy(record))
        processed_list.append(record_id)
        processed.add(record_id)
    atomic_write_json(state_path, state)
    return state


def deliver_one(state: dict[str, Any], kind: str, agent: str, turn: int | None = None) -> dict[str, Any] | None:
    bucket = {"ASK": "asks", "SUGGESTION": "suggestions", "RESEARCH": "research"}[kind]
    eligible_status = {"ASK": "answered", "SUGGESTION": "approved", "RESEARCH": "answered"}[kind]
    for record in state.get(bucket, []):
        statuses = {eligible_status}
        if kind == "RESEARCH":
            statuses.update({"no_evidence", "error", "failed"})
        requester = record.get("requester", record.get("asker", agent))
        if record.get("status") not in statuses or requester != agent:
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
    asks = [{k: r.get(k) for k in ("id", "requester", "question", "status", "answer", "request_turn", "answer_turn", "delivery_turn") if r.get(k) is not None}
            for r in state.get("asks", []) if r.get("status") in PUBLIC_STATUSES]
    suggestions = [{k: r.get(k) for k in ("id", "status", "outcome") if r.get(k) is not None}
                   for r in state.get("suggestions", []) if r.get("status") in {"approved", "delivered", "acted", "no_action"}]
    research = []
    for row in state.get("research", []):
        public = {k: row.get(k) for k in ("id", "requester", "question", "status", "findings", "limitations", "no_evidence", "request_turn", "answer_turn", "delivery_turn", "error", "cost_usd")
                  if row.get(k) is not None}
        public["citations"] = [c for c in (row.get("citations") or []) if isinstance(c, dict)
                               and isinstance(c.get("url"), str)
                               and c["url"].lower().startswith(("https://", "http://"))]
        research.append(public)
    return {"asks": asks, "suggestions": suggestions, "research": research}


def _apply_moderation(state: dict[str, Any], command: dict[str, Any], turn: int | None = None) -> None:
    target = command.get("target_id", command.get("id"))
    action = command.get("action")
    if action == "answer_ask":
        record = next((row for row in state.get("asks", []) if row.get("id") == target), None)
        if record and record.get("status") == "awaiting_iso" and isinstance(command.get("answer"), str):
            record.update({"status": "answered", "answer": command["answer"],
                           "answered_at": command.get("created_at"), "answer_turn": turn})
    elif action == "moderate_suggestion":
        record = next((row for row in state.get("suggestions", []) if row.get("id") == target), None)
        if record and record.get("status") == "pending_review" and command.get("decision") in {"approved", "dismissed"}:
            record["status"] = command["decision"]
            record["moderated_at"] = command.get("created_at")


def empty_inbox_spool() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "records": [], "recovery_state": None}


def append_inbox_spool(path: Path, records: list[dict[str, Any]],
                       recovery_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Courier-only atomic receipt. This is transport, never canonical history."""
    spool = load_json(path, empty_inbox_spool())
    if spool.get("schema_version") != SCHEMA_VERSION:
        spool = empty_inbox_spool()
    known = {row.get("id") for row in spool.get("records", []) if isinstance(row, dict)}
    for record in records:
        record_id = record.get("id") if isinstance(record, dict) else None
        if record_id and record_id not in known:
            spool.setdefault("records", []).append(deepcopy(record))
            known.add(record_id)
    if isinstance(recovery_state, dict) and recovery_state.get("schema_version") == SCHEMA_VERSION:
        spool["recovery_state"] = deepcopy(recovery_state)
    atomic_write_json(path, spool)
    return spool


def import_inbox_spool(state: dict[str, Any], path: Path,
                       turn: int | None = None) -> dict[str, Any]:
    """Loop-only reconciliation from durable local transport into canonical memory."""
    spool = load_json(path, empty_inbox_spool())
    has_local = any(state.get(bucket) for bucket in ("research", "asks", "suggestions", "deliveries")) or bool(_processed(state))
    recovered = spool.get("recovery_state")
    if not has_local and isinstance(recovered, dict) and recovered.get("schema_version") == SCHEMA_VERSION:
        state = deepcopy(recovered)
    processed_list = _processed(state)
    processed = set(processed_list)
    for record in spool.get("records", []):
        if not isinstance(record, dict):
            continue
        record_id, kind = record.get("id"), record.get("kind")
        if not record_id or record_id in processed:
            continue
        if kind == "SUGGESTION":
            saved = deepcopy(record)
            saved.setdefault("status", "pending_review")
            state.setdefault("suggestions", []).append(saved)
        elif kind == "MODERATION":
            _apply_moderation(state, record, turn)
        else:
            continue
        processed_list.append(record_id)
        processed.add(record_id)
    return state


def write_outbox(path: Path, state: dict[str, Any]) -> None:
    """Loop-authored private snapshot for best-effort courier publication."""
    atomic_write_json(path, {"schema_version": SCHEMA_VERSION,
                             "private_state": deepcopy(state)})
