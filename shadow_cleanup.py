#!/usr/bin/env python3
"""Run one manual, non-applying Agent C cleanup and Agent B edition audit."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from cleanup_rulebook import cleanup_draft_request_options, compile_cleanup_draft, validate_replacement
from rulebook import render_language
from state_store import atomic_write_json, load_json, snapshot_hash

MIN_REDUCTION_PCT = 5.0
MAX_C_TOKENS = 10000
MAX_B_TOKENS = 5000
SEED_FIELDS = {"idea", "experiment", "risk"}
AUDIT_FIELD_ORDER = (
    "verdict",
    "reviewed_source_hash",
    "reviewed_candidate_hash",
    "covered_source_ids",
    "omissions",
    "meaning_changes",
    "operational_text",
    "notes",
)
AUDIT_FIELDS = set(AUDIT_FIELD_ORDER)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _adopted_rows(source: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for rule in source.get("rules", []):
        if rule.get("status") == "adopted":
            rule_id = rule.get("id")
            text = rule.get("text_en")
            if not isinstance(rule_id, str) or not isinstance(text, str) or not text.strip():
                raise ValueError("every adopted rule requires a non-empty id and text_en")
            rows.append({"id": rule_id, "text_en": text})
    if not rows:
        raise ValueError("source requires at least one adopted rule")
    return rows


def cleanup_c_request_options(source: dict[str, Any]) -> dict[str, Any]:
    """Extend the proven cleanup schema with three non-operative creative seeds."""
    options = copy.deepcopy(cleanup_draft_request_options(source))
    schema = options["response_format"]["json_schema"]["schema"]
    schema["properties"]["creative_seeds"] = {
        "type": "array",
        "minItems": 3,
        "maxItems": 3,
        "items": {
            "type": "object",
            "properties": {
                "idea": {"type": "string", "minLength": 1, "maxLength": 1000},
                "experiment": {"type": "string", "minLength": 1, "maxLength": 1000},
                "risk": {"type": "string", "minLength": 1, "maxLength": 1000},
            },
            "required": ["idea", "experiment", "risk"],
            "additionalProperties": False,
        },
    }
    schema["required"].append("creative_seeds")
    options["response_format"]["json_schema"]["name"] = "shadow_cleanup_c"
    return options


def cleanup_b_request_options(source: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    adopted_ids = [row["id"] for row in _adopted_rows(source)]
    source_hash = snapshot_hash(source)
    candidate_hash = snapshot_hash(candidate)
    finding = {
        "type": "object",
        "properties": {
            "location": {"type": "string", "minLength": 1, "maxLength": 256},
            "issue": {"type": "string", "minLength": 1, "maxLength": 2000},
        },
        "required": ["location", "issue"],
        "additionalProperties": False,
    }
    operational = {
        "type": "object",
        "properties": {
            "location": {"type": "string", "minLength": 1, "maxLength": 256},
            "text": {"type": "string", "minLength": 1, "maxLength": 2000},
            "assessment": {"type": "string", "minLength": 1, "maxLength": 2000},
        },
        "required": ["location", "text", "assessment"],
        "additionalProperties": False,
    }
    schema = {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["pass", "REJECT"]},
            "reviewed_source_hash": {"type": "string", "enum": [source_hash]},
            "reviewed_candidate_hash": {"type": "string", "enum": [candidate_hash]},
            "covered_source_ids": {
                "type": "array",
                "minItems": len(adopted_ids),
                "maxItems": len(adopted_ids),
                "items": {"type": "string", "enum": adopted_ids},
            },
            "omissions": {"type": "array", "items": {"type": "string", "enum": adopted_ids}},
            "meaning_changes": {"type": "array", "items": finding},
            "operational_text": {"type": "array", "items": operational},
            "notes": {"type": "array", "items": {"type": "string", "maxLength": 2000}},
        },
        "required": list(AUDIT_FIELD_ORDER),
        "additionalProperties": False,
    }
    return {
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "shadow_cleanup_b_audit", "strict": True, "schema": schema},
        },
        "provider": {"require_parameters": True},
    }


def _parse_object(text: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} did not return valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must return one JSON object")
    return value


def compile_c_response(source: dict[str, Any], response: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    expected = {"assignments", "groups", "exclusions", "creative_seeds"}
    if set(response) != expected:
        raise ValueError("Agent C response has an invalid top-level shape")
    seeds = response["creative_seeds"]
    if not isinstance(seeds, list) or len(seeds) != 3:
        raise ValueError("Agent C must return exactly three creative seeds")
    for seed in seeds:
        if not isinstance(seed, dict) or set(seed) != SEED_FIELDS:
            raise ValueError("every creative seed requires idea, experiment, and risk")
        if any(not isinstance(seed[field], str) or not seed[field].strip() for field in SEED_FIELDS):
            raise ValueError("creative seed fields must be non-empty strings")
    draft = {key: copy.deepcopy(response[key]) for key in ("assignments", "groups", "exclusions")}
    return compile_cleanup_draft(source, draft), copy.deepcopy(seeds)


def validate_b_audit(source: dict[str, Any], candidate: dict[str, Any], audit: dict[str, Any]) -> None:
    if set(audit) != AUDIT_FIELDS:
        raise ValueError("Agent B audit has an invalid top-level shape")
    if audit.get("verdict") not in {"pass", "REJECT"}:
        raise ValueError("Agent B audit verdict is invalid")
    adopted_ids = [row["id"] for row in _adopted_rows(source)]
    covered = audit.get("covered_source_ids")
    if not isinstance(covered, list) or set(covered) != set(adopted_ids) or len(covered) != len(set(covered)):
        raise ValueError("Agent B audit must cover every adopted source exactly once")
    if audit.get("reviewed_source_hash") != snapshot_hash(source):
        raise ValueError("Agent B audit is not bound to the source")
    if audit.get("reviewed_candidate_hash") != snapshot_hash(candidate):
        raise ValueError("Agent B audit is not bound to the candidate")
    for field in ("omissions", "meaning_changes", "operational_text", "notes"):
        if not isinstance(audit.get(field), list):
            raise ValueError(f"Agent B audit {field} must be a list")
    if audit["verdict"] == "pass":
        validate_replacement(source, candidate, audit)
    elif not any(audit[field] for field in ("omissions", "meaning_changes", "operational_text", "notes")):
        raise ValueError("Agent B rejection requires at least one finding")


def _source_is_unchanged(source_path: Path, original: bytes) -> bool:
    try:
        return source_path.read_bytes() == original
    except FileNotFoundError:
        return False


def run_shadow_cleanup(
    source_path: Path,
    output_dir: Path,
    *,
    model_c: str,
    model_b: str,
    call_model: Callable[..., tuple[str, dict[str, Any]]],
    token_counter: Callable[[str, dict[str, Any]], int],
    meta: dict[str, Any],
    prompt_c_path: Path | None = None,
    prompt_b_path: Path | None = None,
    min_reduction_pct: float = MIN_REDUCTION_PCT,
    max_spend_usd: float = 0.25,
) -> dict[str, Any]:
    """Create evidence only. This function has no active-state or apply argument."""
    source_path = Path(source_path)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise ValueError("shadow output directory already exists")
    if min_reduction_pct <= 0 or max_spend_usd <= 0:
        raise ValueError("reduction and spend limits must be positive")
    if not model_c.strip() or not model_b.strip() or model_c == model_b:
        raise ValueError("Agent C and Agent B require different non-empty models")
    source_bytes = source_path.read_bytes()
    source = load_json(source_path, None)
    if not isinstance(source, dict):
        raise ValueError("source must be one JSON object")
    source_hash = snapshot_hash(source)
    prompt_c_path = Path(prompt_c_path) if prompt_c_path else Path(__file__).parent / "prompts" / "cleanup_c.md"
    prompt_c = prompt_c_path.read_text()
    prompt_c_hash = hashlib.sha256(prompt_c.encode()).hexdigest()
    prompt_b_path = Path(prompt_b_path) if prompt_b_path else Path(__file__).parent / "prompts" / "cleanup_b.md"
    prompt_b = prompt_b_path.read_text()
    prompt_b_hash = hashlib.sha256(prompt_b.encode()).hexdigest()
    output_dir.mkdir(parents=True)
    atomic_write_json(output_dir / "original.json", source)
    atomic_write_json(output_dir / "c-prompt.json", {
        "path": str(prompt_c_path.resolve()),
        "sha256": prompt_c_hash,
        "content": prompt_c,
    })
    atomic_write_json(output_dir / "b-prompt.json", {
        "path": str(prompt_b_path.resolve()),
        "sha256": prompt_b_hash,
        "content": prompt_b,
    })
    report: dict[str, Any] = {
        "kind": "shadow_cleanup",
        "status": "FAIL",
        "stage": "source",
        "reason": "shadow did not complete",
        "created_at": _now(),
        "source_path": str(source_path.resolve()),
        "source_hash": source_hash,
        "candidate_hash": None,
        "models": {"c": model_c, "b": model_b},
        "prompt_c_sha256": prompt_c_hash,
        "prompt_b_sha256": prompt_b_hash,
        "minimum_reduction_pct": min_reduction_pct,
        "source_tokens": None,
        "candidate_tokens": None,
        "reduction_pct": None,
        "provider_calls": [],
        "spend_usd": float(meta.get("spend_usd", 0.0)),
        "source_unchanged": True,
        "applied": False,
    }
    try:
        adopted = _adopted_rows(source)
        report["stage"] = "c_call"
        c_user = json.dumps({"source_hash": source_hash, "adopted_language": adopted}, ensure_ascii=False)
        c_text, c_usage = call_model(
            model_c,
            prompt_c,
            c_user,
            max_tokens=MAX_C_TOKENS,
            temperature=0.2,
            meta=meta,
            request_options=cleanup_c_request_options(source),
        )
        report["provider_calls"].append({"role": "C", "model": model_c, "usage": c_usage})
        atomic_write_json(output_dir / "c-call.json", {
            "model": model_c,
            "content": c_text,
            "usage": c_usage,
        })
        if float(meta.get("spend_usd", 0.0)) > max_spend_usd:
            raise ValueError("shadow spend cap exceeded after Agent C")
        c_response = _parse_object(c_text, "Agent C")
        atomic_write_json(output_dir / "c-response.json", c_response)

        report["stage"] = "c_validation"
        candidate, seeds = compile_c_response(source, c_response)
        report["candidate_hash"] = snapshot_hash(candidate)
        atomic_write_json(output_dir / "candidate.json", candidate)
        atomic_write_json(output_dir / "creative-seeds.json", seeds)
        if not _source_is_unchanged(source_path, source_bytes):
            raise ValueError("source changed during shadow cleanup")

        report["stage"] = "token_gate"
        source_tokens = token_counter(render_language(source), meta)
        candidate_tokens = token_counter(render_language(candidate), meta)
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0
               for value in (source_tokens, candidate_tokens)):
            raise ValueError("token measurements must be positive integers")
        reduction_pct = round((source_tokens - candidate_tokens) / source_tokens * 100, 2)
        report.update({
            "source_tokens": source_tokens,
            "candidate_tokens": candidate_tokens,
            "reduction_pct": reduction_pct,
        })
        if float(meta.get("spend_usd", 0.0)) > max_spend_usd:
            raise ValueError("shadow spend cap exceeded during token measurement")
        if reduction_pct < min_reduction_pct:
            raise ValueError("candidate did not meet the minimum token reduction")

        report["stage"] = "b_call"
        candidate_hash = snapshot_hash(candidate)
        b_user = json.dumps({
            "source_hash": source_hash,
            "candidate_hash": candidate_hash,
            "original_adopted_language": adopted,
            "candidate": candidate,
        }, ensure_ascii=False)
        b_text, b_usage = call_model(
            model_b,
            prompt_b,
            b_user,
            max_tokens=MAX_B_TOKENS,
            temperature=0,
            meta=meta,
            request_options=cleanup_b_request_options(source, candidate),
        )
        report["provider_calls"].append({"role": "B", "model": model_b, "usage": b_usage})
        atomic_write_json(output_dir / "b-call.json", {
            "model": model_b,
            "content": b_text,
            "usage": b_usage,
        })
        if float(meta.get("spend_usd", 0.0)) > max_spend_usd:
            raise ValueError("shadow spend cap exceeded after Agent B")
        audit = _parse_object(b_text, "Agent B")
        atomic_write_json(output_dir / "b-audit.json", audit)

        report["stage"] = "b_audit"
        validate_b_audit(source, candidate, audit)
        if audit["verdict"] != "pass":
            report["reason"] = "Agent B rejected the proposed edition"
        else:
            report.update({"status": "PASS", "stage": "complete", "reason": "all shadow gates passed"})
    except Exception as exc:
        report["error_type"] = exc.__class__.__name__
        report["reason"] = str(exc)
    finally:
        report["source_unchanged"] = _source_is_unchanged(source_path, source_bytes)
        report["spend_usd"] = round(float(meta.get("spend_usd", 0.0)), 12)
        if not report["source_unchanged"]:
            report.update({"status": "FAIL", "stage": "source_integrity", "reason": "source changed during shadow cleanup"})
        atomic_write_json(output_dir / "report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one non-applying shadow cleanup")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-c", required=True)
    parser.add_argument("--model-b", default=None)
    parser.add_argument("--prompt-c", type=Path, default=None)
    parser.add_argument("--prompt-b", type=Path, default=None)
    parser.add_argument("--min-reduction-pct", type=float, default=MIN_REDUCTION_PCT)
    parser.add_argument("--max-spend-usd", type=float, default=0.25)
    args = parser.parse_args()

    from loop import MODEL_B, call, initialize_exact_cost_accounting, token_count

    meta: dict[str, Any] = {"spend_usd": 0.0}
    initialize_exact_cost_accounting(meta, cutover_turn=0)
    report = run_shadow_cleanup(
        args.source,
        args.output,
        model_c=args.model_c,
        model_b=args.model_b or MODEL_B,
        call_model=call,
        token_counter=token_count,
        meta=meta,
        prompt_c_path=args.prompt_c,
        prompt_b_path=args.prompt_b,
        min_reduction_pct=args.min_reduction_pct,
        max_spend_usd=args.max_spend_usd,
    )
    print(json.dumps({
        "status": report["status"],
        "stage": report["stage"],
        "reason": report["reason"],
        "reduction_pct": report["reduction_pct"],
        "spend_usd": report["spend_usd"],
        "source_unchanged": report["source_unchanged"],
        "output": str(args.output.resolve()),
    }, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
