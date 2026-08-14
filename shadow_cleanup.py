#!/usr/bin/env python3
"""Run one manual, non-applying Agent C cleanup with an advisory B review."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from cleanup_rulebook import cleanup_draft_request_options, compile_cleanup_draft, validate_replacement
from rulebook import render_language
from state_store import atomic_write_json, load_json, snapshot_hash

MIN_REDUCTION_PCT = 5.0
MAX_C_TOKENS = 22_000
MAX_B_TOKENS = 1500
MAX_C_CALLS = 2
MAX_B_CALLS = 1
DEFAULT_MAX_SPEND_USD = 1.00
PROMPTS_DIR = Path(__file__).parent / "prompts"
DEFAULT_PROMPT_C_PATH = PROMPTS_DIR / "cleanup_c_v1.md"
DEFAULT_PROMPT_B_PATH = PROMPTS_DIR / "cleanup_b_v1.md"
FINALIZER_PROMPT_PATH = PROMPTS_DIR / "cleanup_c_finalizer_v1.md"
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
FINALIZER_PROMPT = FINALIZER_PROMPT_PATH.read_text()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def prompt_version(path: Path, role: str, sha256: str) -> str:
    """Name repository prompt editions; content-address all other overrides."""
    patterns = {
        "c": r"cleanup_c_(v[1-9][0-9]*)\.md",
        "b": r"cleanup_b_(v[1-9][0-9]*)\.md",
        "c-finalizer": r"cleanup_c_finalizer_(v[1-9][0-9]*)\.md",
    }
    match = re.fullmatch(patterns.get(role, r"$^"), path.name)
    if (
        path.resolve().parent == PROMPTS_DIR.resolve()
        and match
    ):
        return f"cleanup-{role}-{match.group(1)}"
    return f"custom-{role}-{sha256[:12]}"


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
    elif not any(audit[field] for field in ("omissions", "meaning_changes", "operational_text")):
        raise ValueError("Agent B rejection requires at least one actionable finding")


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
    max_spend_usd: float = DEFAULT_MAX_SPEND_USD,
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
    starting_spend = float(meta.get("spend_usd", 0.0))

    def run_spend() -> float:
        return round(float(meta.get("spend_usd", 0.0)) - starting_spend, 12)

    source_bytes = source_path.read_bytes()
    source = load_json(source_path, None)
    if not isinstance(source, dict):
        raise ValueError("source must be one JSON object")
    source_hash = snapshot_hash(source)
    prompt_c_path = Path(prompt_c_path) if prompt_c_path else DEFAULT_PROMPT_C_PATH
    prompt_c = prompt_c_path.read_text()
    prompt_c_hash = hashlib.sha256(prompt_c.encode()).hexdigest()
    prompt_c_version = prompt_version(prompt_c_path, "c", prompt_c_hash)
    prompt_b_path = Path(prompt_b_path) if prompt_b_path else DEFAULT_PROMPT_B_PATH
    prompt_b = prompt_b_path.read_text()
    prompt_b_hash = hashlib.sha256(prompt_b.encode()).hexdigest()
    prompt_b_version = prompt_version(prompt_b_path, "b", prompt_b_hash)
    finalizer_prompt = FINALIZER_PROMPT_PATH.read_text()
    finalizer_prompt_hash = hashlib.sha256(finalizer_prompt.encode()).hexdigest()
    finalizer_prompt_version = prompt_version(
        FINALIZER_PROMPT_PATH, "c-finalizer", finalizer_prompt_hash
    )
    output_dir.mkdir(parents=True)
    atomic_write_json(output_dir / "original.json", source)
    atomic_write_json(output_dir / "c-prompt.json", {
        "version": prompt_c_version,
        "path": str(prompt_c_path.resolve()),
        "sha256": prompt_c_hash,
        "content": prompt_c,
    })
    atomic_write_json(output_dir / "b-prompt.json", {
        "version": prompt_b_version,
        "path": str(prompt_b_path.resolve()),
        "sha256": prompt_b_hash,
        "content": prompt_b,
    })
    atomic_write_json(output_dir / "c-finalizer-prompt.json", {
        "version": finalizer_prompt_version,
        "path": str(FINALIZER_PROMPT_PATH.resolve()),
        "sha256": finalizer_prompt_hash,
        "content": finalizer_prompt,
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
        "prompt_c_version": prompt_c_version,
        "prompt_c_sha256": prompt_c_hash,
        "prompt_b_version": prompt_b_version,
        "prompt_b_sha256": prompt_b_hash,
        "prompt_c_finalizer_version": finalizer_prompt_version,
        "prompt_c_finalizer_sha256": finalizer_prompt_hash,
        "minimum_reduction_pct": min_reduction_pct,
        "source_tokens": None,
        "candidate_tokens": None,
        "reduction_pct": None,
        "provider_calls": [],
        "spend_usd": float(meta.get("spend_usd", 0.0)),
        "run_spend_usd": 0.0,
        "source_unchanged": True,
        "applied": False,
        "decision_authority": "C",
        "b_review_mode": "single_advisory",
        "max_c_calls": MAX_C_CALLS,
        "max_b_calls": MAX_B_CALLS,
        "round_count": 0,
        "rounds": [],
    }
    try:
        adopted = _adopted_rows(source)
        previous_candidate = None
        previous_advisory = None
        source_tokens = None
        for round_number in range(1, MAX_C_CALLS + 1):
            report["round_count"] = round_number
            round_dir = output_dir / "rounds" / f"{round_number:02d}"
            round_dir.mkdir(parents=True)
            c_request: dict[str, Any] = {
                "source_hash": source_hash,
                "adopted_language": adopted,
            }
            c_system = prompt_c
            c_system_version = prompt_c_version
            if previous_candidate is not None:
                c_request.update({
                    "final_decision": True,
                    "previous_candidate": previous_candidate,
                    "b_advisory": previous_advisory,
                })
                c_system = f"{prompt_c}\n\n{finalizer_prompt}"
                c_system_version = (
                    f"{prompt_c_version}+{finalizer_prompt_version}"
                )
            c_system_hash = hashlib.sha256(c_system.encode()).hexdigest()
            atomic_write_json(round_dir / "c-request.json", c_request)
            atomic_write_json(round_dir / "c-system-prompt.json", {
                "version": c_system_version,
                "sha256": c_system_hash,
                "content": c_system,
            })

            report["stage"] = "c_call"
            c_text, c_usage = call_model(
                model_c,
                c_system,
                json.dumps(c_request, ensure_ascii=False),
                max_tokens=MAX_C_TOKENS,
                temperature=0.2,
                meta=meta,
                request_options=cleanup_c_request_options(source),
            )
            report["provider_calls"].append({
                "round": round_number,
                "role": "C",
                "model": model_c,
                "prompt_version": c_system_version,
                "prompt_sha256": c_system_hash,
                "usage": c_usage,
            })
            c_call = {
                "model": model_c,
                "prompt_version": c_system_version,
                "prompt_sha256": c_system_hash,
                "content": c_text,
                "usage": c_usage,
            }
            atomic_write_json(round_dir / "c-call.json", c_call)
            atomic_write_json(output_dir / "c-call.json", c_call)
            if run_spend() > max_spend_usd:
                raise ValueError("shadow spend cap exceeded after Agent C")
            c_response = _parse_object(c_text, "Agent C")
            atomic_write_json(round_dir / "c-response.json", c_response)
            atomic_write_json(output_dir / "c-response.json", c_response)

            report["stage"] = "c_validation"
            candidate, seeds = compile_c_response(source, c_response)
            candidate_hash = snapshot_hash(candidate)
            report["candidate_hash"] = candidate_hash
            atomic_write_json(round_dir / "candidate.json", candidate)
            atomic_write_json(round_dir / "creative-seeds.json", seeds)
            atomic_write_json(output_dir / "candidate.json", candidate)
            atomic_write_json(output_dir / "creative-seeds.json", seeds)
            if not _source_is_unchanged(source_path, source_bytes):
                raise ValueError("source changed during shadow cleanup")

            report["stage"] = "token_gate"
            if source_tokens is None:
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
            if run_spend() > max_spend_usd:
                raise ValueError("shadow spend cap exceeded during token measurement")
            if reduction_pct < min_reduction_pct:
                raise ValueError("candidate did not meet the minimum token reduction")

            round_summary = {
                "round": round_number,
                "candidate_hash": candidate_hash,
                "candidate_changed_from_previous": (
                    None if previous_candidate is None
                    else candidate_hash != snapshot_hash(previous_candidate)
                ),
                "candidate_tokens": candidate_tokens,
                "reduction_pct": reduction_pct,
                "b_verdict": None,
                "finding_counts": None,
            }

            if previous_candidate is not None:
                report["rounds"].append(round_summary)
                atomic_write_json(round_dir / "round-report.json", round_summary)
                report.update({
                    "status": "PASS",
                    "stage": "complete",
                    "reason": "Agent C finalized after one advisory B review",
                })
                break

            report["stage"] = "b_call"
            b_request = {
                "source_hash": source_hash,
                "candidate_hash": candidate_hash,
                "original_adopted_language": adopted,
                "candidate": candidate,
            }
            try:
                b_text, b_usage = call_model(
                    model_b,
                    prompt_b,
                    json.dumps(b_request, ensure_ascii=False),
                    max_tokens=MAX_B_TOKENS,
                    temperature=0,
                    meta=meta,
                    request_options=cleanup_b_request_options(source, candidate),
                )
            except Exception as exc:
                advisory_error = {
                    "status": "unavailable",
                    "error_type": exc.__class__.__name__,
                    "reason": str(exc),
                }
                atomic_write_json(round_dir / "b-advisory-error.json", advisory_error)
                report["b_advisory_error"] = advisory_error
                round_summary["b_verdict"] = "unavailable"
                report["rounds"].append(round_summary)
                atomic_write_json(round_dir / "round-report.json", round_summary)
                report.update({
                    "status": "FAIL",
                    "stage": "b_call",
                    "failure_class": "invalid_advisory",
                    "reason": f"Agent B advisory unavailable: {exc}",
                })
                break
            report["provider_calls"].append({
                "round": round_number,
                "role": "B",
                "model": model_b,
                "prompt_version": prompt_b_version,
                "prompt_sha256": prompt_b_hash,
                "usage": b_usage,
            })
            b_call = {
                "model": model_b,
                "prompt_version": prompt_b_version,
                "prompt_sha256": prompt_b_hash,
                "content": b_text,
                "usage": b_usage,
            }
            atomic_write_json(round_dir / "b-call.json", b_call)
            atomic_write_json(output_dir / "b-call.json", b_call)
            if run_spend() > max_spend_usd:
                raise ValueError("shadow spend cap exceeded after Agent B")
            report["stage"] = "b_audit"
            try:
                audit = _parse_object(b_text, "Agent B")
                validate_b_audit(source, candidate, audit)
            except Exception as exc:
                advisory_error = {
                    "status": "invalid",
                    "error_type": exc.__class__.__name__,
                    "reason": str(exc),
                    "response_receipt": copy.deepcopy(b_call),
                }
                atomic_write_json(round_dir / "b-advisory-error.json", advisory_error)
                report["b_advisory_error"] = advisory_error
                round_summary["b_verdict"] = "invalid"
                report["rounds"].append(round_summary)
                atomic_write_json(round_dir / "round-report.json", round_summary)
                report.update({
                    "status": "FAIL",
                    "stage": "b_audit",
                    "failure_class": "invalid_advisory",
                    "reason": f"Agent B advisory invalid: {exc}",
                })
                break
            atomic_write_json(round_dir / "b-audit.json", audit)
            atomic_write_json(output_dir / "b-audit.json", audit)

            round_summary["b_verdict"] = audit["verdict"]
            round_summary["finding_counts"] = {
                "omissions": len(audit["omissions"]),
                "meaning_changes": len(audit["meaning_changes"]),
                "operational_text": len(audit["operational_text"]),
            }
            report["rounds"].append(round_summary)
            atomic_write_json(round_dir / "round-report.json", round_summary)
            if audit["verdict"] == "pass":
                report.update({
                    "status": "PASS",
                    "stage": "complete",
                    "reason": "Agent C draft passed deterministic gates; B raised no objection",
                })
                break
            previous_candidate = candidate
            previous_advisory = {
                "omissions": copy.deepcopy(audit["omissions"]),
                "meaning_changes": copy.deepcopy(audit["meaning_changes"]),
                "operational_text": copy.deepcopy(audit["operational_text"]),
            }
    except Exception as exc:
        report["error_type"] = exc.__class__.__name__
        report["reason"] = str(exc)
    finally:
        report["source_unchanged"] = _source_is_unchanged(source_path, source_bytes)
        report["spend_usd"] = round(float(meta.get("spend_usd", 0.0)), 12)
        report["run_spend_usd"] = run_spend()
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
    parser.add_argument(
        "--max-spend-usd", type=float, default=DEFAULT_MAX_SPEND_USD
    )
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
