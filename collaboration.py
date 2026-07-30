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
MAX_RESEARCH_DELIVERY_JSON_CHARS = 8_000
MAX_RESEARCH_FINDINGS_CHARS = 3_000
MAX_RESEARCH_LIMITATIONS_CHARS = 800
MAX_RESEARCH_QUESTION_CHARS = 600
MAX_RESEARCH_ID_CHARS = 160
MAX_RESEARCH_ROUTE_CHARS = 50
MAX_RESEARCH_CITATIONS = 4
MAX_RESEARCH_CITATION_CHARS = 1_800
MAX_RESEARCH_CITATION_TITLE_CHARS = 120
MAX_RESEARCH_CITATION_URL_CHARS = 450


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
    question_kinds = {"ASK", "RESEARCH", "LOOKUP"}
    record = {"id": record_id or f"{kind.lower()}-{secrets.token_hex(12)}", "kind": kind,
              "requester": requester, "question" if kind in question_kinds else "text": clean,
              "status": "awaiting_iso" if kind == "ASK" else "queued", "created_at": int(time.time())}
    if kind == "LOOKUP":
        record["route"] = "project"
    return record


def reconcile(state_path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    state = load_json(state_path, empty_state())
    processed_list = _processed(state)
    processed = set(processed_list)
    buckets = {"RESEARCH": "research", "LOOKUP": "research",
               "ASK": "asks", "SUGGESTION": "suggestions"}
    for record in records:
        record_id, kind = record.get("id"), record.get("kind")
        if not record_id or record_id in processed or kind not in buckets:
            continue
        state[buckets[kind]].append(deepcopy(record))
        processed_list.append(record_id)
        processed.add(record_id)
    atomic_write_json(state_path, state)
    return state


def _bounded_prefix(value: Any, limit: int) -> tuple[str, int]:
    text = value if isinstance(value, str) else str(value or "")
    return text[:limit].rstrip(), len(text)


def _limitations_text(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value)
    if isinstance(value, str):
        return value
    return str(value or "")


def _bounded_citations(
    value: Any,
) -> tuple[list[dict[str, str]], int, int, int]:
    rows = value if isinstance(value, list) else []
    included: list[dict[str, str]] = []
    used_chars = 0
    original_chars = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = row.get("url")
        title_value = row.get("title", url)
        original_chars += len(str(title_value or "")) + len(str(url or ""))
        if len(included) >= MAX_RESEARCH_CITATIONS:
            continue
        if (
            not isinstance(url, str)
            or not url.lower().startswith(("https://", "http://"))
            or len(url) > MAX_RESEARCH_CITATION_URL_CHARS
        ):
            continue
        title = (
            title_value if isinstance(title_value, str) else str(title_value)
        )[:MAX_RESEARCH_CITATION_TITLE_CHARS].rstrip()
        candidate_chars = len(title) + len(url)
        if used_chars + candidate_chars > MAX_RESEARCH_CITATION_CHARS:
            continue
        included.append({"title": title or url, "url": url})
        used_chars += candidate_chars
    return included, len(rows), original_chars, used_chars


def project_research_delivery_for_prompt(
    delivery: dict[str, Any],
) -> dict[str, Any]:
    """Bound one research delivery without changing its canonical record."""
    record_id, record_id_chars = _bounded_prefix(
        delivery.get("id"), MAX_RESEARCH_ID_CHARS
    )
    question, question_chars = _bounded_prefix(
        delivery.get("question"), MAX_RESEARCH_QUESTION_CHARS
    )
    route, route_chars = _bounded_prefix(
        delivery.get("route"), MAX_RESEARCH_ROUTE_CHARS
    )
    findings, findings_chars = _bounded_prefix(
        delivery.get("findings"), MAX_RESEARCH_FINDINGS_CHARS
    )
    limitations, limitations_chars = _bounded_prefix(
        _limitations_text(delivery.get("limitations")),
        MAX_RESEARCH_LIMITATIONS_CHARS,
    )
    citations, citation_count, citation_chars, citation_included_chars = (
        _bounded_citations(delivery.get("citations"))
    )
    projection = {
        "kind": "RESEARCH",
        "id": record_id,
        "question": question,
        "findings": findings,
        "limitations": limitations,
        "citations": citations,
        "route": route,
        "projection": {
            "type": "bounded_research_delivery_v1",
            "truncated": any(
                (
                    record_id_chars > len(record_id),
                    question_chars > len(question),
                    route_chars > len(route),
                    findings_chars > len(findings),
                    limitations_chars > len(limitations),
                    citation_count > len(citations),
                    citation_chars > citation_included_chars,
                )
            ),
            "id_original_chars": record_id_chars,
            "id_included_chars": len(record_id),
            "id_omitted_chars": record_id_chars - len(record_id),
            "question_original_chars": question_chars,
            "question_included_chars": len(question),
            "question_omitted_chars": question_chars - len(question),
            "route_original_chars": route_chars,
            "route_included_chars": len(route),
            "route_omitted_chars": route_chars - len(route),
            "findings_original_chars": findings_chars,
            "findings_included_chars": len(findings),
            "findings_omitted_chars": findings_chars - len(findings),
            "limitations_original_chars": limitations_chars,
            "limitations_included_chars": len(limitations),
            "limitations_omitted_chars": limitations_chars - len(limitations),
            "citations_original_count": citation_count,
            "citations_included_count": len(citations),
            "citations_omitted_count": citation_count - len(citations),
            "citations_original_chars": citation_chars,
            "citations_included_chars": citation_included_chars,
            "citations_omitted_chars": citation_chars - citation_included_chars,
        },
    }
    rendered_chars = len(
        json.dumps(projection, ensure_ascii=False, separators=(",", ":"))
    )
    if rendered_chars > MAX_RESEARCH_DELIVERY_JSON_CHARS:
        raise RuntimeError("bounded research delivery exceeded its fixed limit")
    return projection


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
                       "limitations": record.get("limitations", ""), "citations": record.get("citations", []),
                       "route": record.get("route")}
        else:
            payload = {"id": record["id"], "optional_suggestion": record["text"]}
        state.setdefault("deliveries", []).append({"kind": kind, **payload})
        canonical_delivery = {"kind": kind, **payload}
        if kind == "RESEARCH":
            return project_research_delivery_for_prompt(canonical_delivery)
        return canonical_delivery
    return None


def public_state(state: dict[str, Any]) -> dict[str, Any]:
    asks = [{k: r.get(k) for k in ("id", "requester", "question", "status", "answer", "request_turn", "answer_turn", "delivery_turn") if r.get(k) is not None}
            for r in state.get("asks", []) if r.get("status") in PUBLIC_STATUSES]
    suggestions = [{k: r.get(k) for k in ("id", "status", "outcome") if r.get(k) is not None}
                   for r in state.get("suggestions", []) if r.get("status") in {"approved", "delivered", "acted", "no_action"}]
    research = []
    for row in state.get("research", []):
        public = {k: row.get(k) for k in ("id", "requester", "question", "status", "route", "findings", "limitations", "no_evidence", "evidence_count", "ask_id", "request_turn", "answer_turn", "delivery_turn", "error", "cost_usd")
                  if row.get(k) is not None}
        public["citations"] = [c for c in (row.get("citations") or []) if isinstance(c, dict)
                               and isinstance(c.get("url"), str)
                               and c["url"].lower().startswith(("https://", "http://"))]
        research.append(public)
    return {"asks": asks, "suggestions": suggestions, "research": research}


def escalate_lookup_to_ask(state: dict[str, Any], record: dict[str, Any],
                           turn: int) -> dict[str, Any]:
    """Correlate one evidence miss to the human lane without duplicating retries."""
    ask_id = f"ask-from-{record['id']}"
    ask = next((row for row in state.get("asks", []) if row.get("id") == ask_id), None)
    if ask is None:
        ask = stable_record("ASK", record["requester"], record["question"], ask_id)
        ask.update({"request_turn": turn, "source_lookup_id": record["id"]})
        state.setdefault("asks", []).append(ask)
    record.update({
        "status": "escalated_to_iso",
        "route": "project",
        "ask_id": ask_id,
        "answer_turn": turn,
        "no_evidence": True,
    })
    return ask


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
