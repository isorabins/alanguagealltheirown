#!/usr/bin/env python3
"""One-time frozen-English controls and deterministic paired projections.

This module is deliberately absent from the scheduled turn path. Its CLI previews
by default and requires an explicit live flag plus a bounded spend cap before it
can call the existing provider seam.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from rulebook import score_judgment_v2
from state_store import atomic_write_json, load_json


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "baselines" / "frozen-english-contract-v2.json"
REGISTRY_PATH = ROOT / "baselines" / "frozen-english-v2.json"
PROGRESS_PATH = ROOT / "baselines" / "frozen-english-progress.local.json"
BENCHMARK_IDS = ("B1", "B2", "B3", "B4", "B5")
BASELINE_VERSION = "frozen-english-v2"
SCHEMA_VERSION = 1
MAX_APPROVED_SPEND_USD = 0.25
CONTROL_ARTIFACT_MAX_CHARS = 128_000
MAX_JUDGE_ATTEMPTS = 2

MODEL_ENCODER = "deepseek/deepseek-v3.2"
MODEL_DECODER = "moonshotai/kimi-k2.6"
MODEL_JUDGE = "deepseek/deepseek-v3.2"
TOKENIZER_MODEL = "deepseek/deepseek-v3.2"
MAX_TOKENS = 4000
ENCODER_TEMPERATURE = 0.3
DECODER_TEMPERATURE = 0.1
JUDGE_TEMPERATURE = 0
TOKENIZER_TEMPERATURE = 0

ENGLISH_PROMPT_PATH = ROOT / "prompts" / "frozen_english.md"
DECODER_PROMPT_PATH = ROOT / "prompts" / "frozen_english_decoder.md"
GRADER_PROMPT_PATH = ROOT / "prompts" / "grader_v2.md"

PROJECTION_ASSUMPTIONS = {
    "reference_model": "Claude Sonnet 4.6",
    "exchanges": 20,
    "messages": 40,
    "english_tokens_per_message": 1000,
    "history_message_copies": 780,
    "rulebook_cache_writes": 2,
    "rulebook_cache_reads": 38,
    "input_usd_per_million": 3.0,
    "output_usd_per_million": 15.0,
    "cache_write_usd_per_million": 3.75,
    "cache_read_usd_per_million": 0.30,
}


class FrozenEnglishError(RuntimeError):
    pass


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execution_inputs() -> dict[str, Any]:
    """The complete named invalidation boundary for frozen controls."""
    return {
        "encoder_model": MODEL_ENCODER,
        "decoder_model": MODEL_DECODER,
        "judge_model": MODEL_JUDGE,
        "tokenizer_model": TOKENIZER_MODEL,
        "compression_instruction_sha256": _file_hash(ENGLISH_PROMPT_PATH),
        "decoder_instruction_sha256": _file_hash(DECODER_PROMPT_PATH),
        "grader_instruction_sha256": _file_hash(GRADER_PROMPT_PATH),
        "encoder_temperature": ENCODER_TEMPERATURE,
        "decoder_temperature": DECODER_TEMPERATURE,
        "judge_temperature": JUDGE_TEMPERATURE,
        "tokenizer_temperature": TOKENIZER_TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }


def expected_contract(suite: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for benchmark in suite["benchmarks"]:
        frozen = {
            "id": benchmark["id"],
            "name": benchmark["name"],
            "source_turn": benchmark["source_turn"],
            "original": benchmark["original"],
            "answer_key": benchmark["answer_key"],
        }
        rows.append({
            "id": benchmark["id"],
            "benchmark_digest": _canonical_hash(frozen),
        })
    if tuple(row["id"] for row in rows) != BENCHMARK_IDS:
        raise FrozenEnglishError("benchmark_registry_invalid")
    return {
        "schema_version": SCHEMA_VERSION,
        "baseline_version": BASELINE_VERSION,
        "benchmark_version": suite["version"],
        "execution_inputs": execution_inputs(),
        "benchmarks": rows,
    }


def load_checked_contract(suite: dict[str, Any], path: Path = CONTRACT_PATH) -> dict[str, Any]:
    expected = expected_contract(suite)
    actual = load_json(path, {})
    if actual != expected:
        raise FrozenEnglishError("frozen_english_contract_drift")
    return actual


def baseline_status(
    registry: dict[str, Any], contract: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Classify each expected record without inventing extra stale inputs."""
    records = {
        row.get("benchmark_id"): row
        for row in registry.get("records", [])
        if isinstance(row, dict)
    }
    expected_digests = {
        row["id"]: row["benchmark_digest"] for row in contract["benchmarks"]
    }
    status = {}
    for benchmark_id in BENCHMARK_IDS:
        record = records.get(benchmark_id)
        if record is None:
            status[benchmark_id] = {"state": "missing", "record": None}
            continue
        current = (
            registry.get("schema_version") == SCHEMA_VERSION
            and registry.get("baseline_version") == BASELINE_VERSION
            and record.get("benchmark_version") == contract["benchmark_version"]
            and record.get("benchmark_digest") == expected_digests[benchmark_id]
            and record.get("execution_inputs") == contract["execution_inputs"]
        )
        status[benchmark_id] = {
            "state": "current" if current else "stale",
            "record": record,
        }
    return status


def latest_qualifying_cycle(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the newest complete meaning-safe, compressed Scoring V2 B1-B5 cycle."""
    cycles: dict[int, dict[str, dict[str, Any]]] = {}
    for event in events:
        if (
            not isinstance(event, dict)
            or event.get("scoring_version") != "v2"
            or event.get("era") != "benchmark-v2"
            or event.get("benchmark_version") != "v2"
            or event.get("benchmark_id") not in BENCHMARK_IDS
            or isinstance(event.get("benchmark_cycle"), bool)
            or not isinstance(event.get("benchmark_cycle"), int)
        ):
            continue
        cycles.setdefault(event["benchmark_cycle"], {})[event["benchmark_id"]] = event
    for cycle in sorted(cycles, reverse=True):
        rows = cycles[cycle]
        if set(rows) != set(BENCHMARK_IDS):
            continue
        if not all(
            row.get("judge_valid") is True
            and row.get("meaning_pass") is True
            and row.get("compression_success") is True
            and row.get("semantic_coverage_pct") == 100
            and row.get("inventions") == []
            for row in rows.values()
        ):
            continue
        savings = [rows[benchmark_id]["message_body_savings_pct"] for benchmark_id in BENCHMARK_IDS]
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in savings):
            continue
        return {
            "benchmark_cycle": cycle,
            "benchmark_ids": list(BENCHMARK_IDS),
            "average_message_body_savings_pct": sum(savings) / len(savings),
        }
    return None


def current_baseline_average(
    registry: dict[str, Any], contract: dict[str, Any]
) -> float | None:
    statuses = baseline_status(registry, contract)
    records = []
    for benchmark_id in BENCHMARK_IDS:
        item = statuses[benchmark_id]
        record = item["record"]
        if (
            item["state"] != "current"
            or not record
            or record.get("judge_valid") is not True
            or record.get("meaning_pass") is not True
            or record.get("semantic_coverage_pct") != 100
            or record.get("inventions") != []
        ):
            return None
        value = record.get("message_body_savings_pct")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        records.append(value)
    return sum(records) / len(records)


def twenty_exchange_projection(
    alato_savings_pct: float,
    english_savings_pct: float,
    rulebook_tokens: int,
) -> dict[str, Any] | None:
    if (
        isinstance(rulebook_tokens, bool)
        or not isinstance(rulebook_tokens, int)
        or rulebook_tokens <= 0
    ):
        return None
    for value in (alato_savings_pct, english_savings_pct):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return None
    a = PROJECTION_ASSUMPTIONS
    plain_input_tokens = a["history_message_copies"] * a["english_tokens_per_message"]
    plain_output_tokens = a["messages"] * a["english_tokens_per_message"]
    plain_cost = (
        plain_input_tokens * a["input_usd_per_million"]
        + plain_output_tokens * a["output_usd_per_million"]
    ) / 1_000_000

    def communication_cost(savings_pct: float) -> float:
        ratio = 1 - savings_pct / 100
        return (
            plain_input_tokens * ratio * a["input_usd_per_million"]
            + plain_output_tokens * ratio * a["output_usd_per_million"]
        ) / 1_000_000

    cache_cost = rulebook_tokens * (
        a["rulebook_cache_writes"] * a["cache_write_usd_per_million"]
        + a["rulebook_cache_reads"] * a["cache_read_usd_per_million"]
    ) / 1_000_000
    alato_cost = communication_cost(alato_savings_pct) + cache_cost
    english_cost = communication_cost(english_savings_pct)
    alato_projected_savings = 100 * (plain_cost - alato_cost) / plain_cost
    english_projected_savings = 100 * (plain_cost - english_cost) / plain_cost
    return {
        "plain_cost_usd": plain_cost,
        "alato_cost_usd": alato_cost,
        "english_cost_usd": english_cost,
        "rulebook_cache_cost_usd": cache_cost,
        "alato_projected_savings_pct": alato_projected_savings,
        "english_projected_savings_pct": english_projected_savings,
        "control_adjusted_percentage_points": (
            alato_projected_savings - english_projected_savings
        ),
        "assumptions": copy.deepcopy(a),
    }


def _parse_judgment(raw: str) -> dict[str, Any]:
    import re

    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _sample_identity(benchmark: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    digest = next(
        row["benchmark_digest"]
        for row in contract["benchmarks"]
        if row["id"] == benchmark["id"]
    )
    return {
        "benchmark_id": benchmark["id"],
        "benchmark_name": benchmark["name"],
        "benchmark_version": contract["benchmark_version"],
        "benchmark_digest": digest,
        "execution_inputs": copy.deepcopy(contract["execution_inputs"]),
    }


def _check_sample(sample: dict[str, Any], benchmark: dict[str, Any], contract: dict[str, Any]) -> None:
    expected = _sample_identity(benchmark, contract)
    for field in expected:
        if sample.get(field) != expected[field]:
            raise FrozenEnglishError(f"preserved_control_stale:{benchmark['id']}:{field}")
    for field in ("compressed_english", "decoded"):
        value = sample.get(field)
        if not isinstance(value, str) or not value or len(value) > CONTROL_ARTIFACT_MAX_CHARS:
            raise FrozenEnglishError(f"preserved_control_artifact_invalid:{benchmark['id']}:{field}")


def capture_control_sample(
    benchmark: dict[str, Any],
    contract: dict[str, Any],
    *,
    call_fn: Callable[..., tuple[str, dict[str, Any]]],
    token_count_fn: Callable[[str, dict[str, Any]], int],
    meta: dict[str, Any],
) -> dict[str, Any]:
    compressed, _ = call_fn(
        MODEL_ENCODER, ENGLISH_PROMPT_PATH.read_text(), benchmark["original"],
        max_tokens=MAX_TOKENS, temperature=ENCODER_TEMPERATURE, meta=meta,
    )
    decoded, _ = call_fn(
        MODEL_DECODER, DECODER_PROMPT_PATH.read_text(), compressed.strip(),
        max_tokens=MAX_TOKENS, temperature=DECODER_TEMPERATURE, meta=meta,
    )
    original_tokens = token_count_fn(benchmark["original"], meta)
    compressed_tokens = token_count_fn(compressed.strip(), meta)
    sample = _sample_identity(benchmark, contract) | {
        "compressed_english": compressed.strip(), "decoded": decoded.strip(),
        "original_tokens": original_tokens, "compressed_tokens": compressed_tokens,
        "message_body_savings_pct": -round(
            (compressed_tokens - original_tokens) / original_tokens * 100
        ),
        "judge_attempts": [],
    }
    _check_sample(sample, benchmark, contract)
    return sample


def judge_preserved_sample(
    sample: dict[str, Any],
    benchmark: dict[str, Any],
    contract: dict[str, Any],
    *,
    call_fn: Callable[..., tuple[str, dict[str, Any]]],
    meta: dict[str, Any],
) -> dict[str, Any]:
    _check_sample(sample, benchmark, contract)
    attempts = copy.deepcopy(sample.get("judge_attempts", []))
    if len(attempts) >= MAX_JUDGE_ATTEMPTS:
        raise FrozenEnglishError(f"preserved_control_judge_attempt_cap:{benchmark['id']}")
    key_text = json.dumps(
        [{"id": atom["id"], "meaning": atom["meaning"]} for atom in benchmark["answer_key"]],
        ensure_ascii=False,
    )
    grade_user = (
        f"ORIGINAL:\n{benchmark['original']}\n\nATOMIC ANSWER KEY:\n{key_text}"
        f"\n\nDECODED:\n{sample['decoded']}"
    )
    graded, _ = call_fn(
        MODEL_JUDGE,
        GRADER_PROMPT_PATH.read_text(),
        grade_user,
        max_tokens=MAX_TOKENS,
        temperature=JUDGE_TEMPERATURE,
        meta=meta,
    )
    scored = score_judgment_v2(
        benchmark["answer_key"], _parse_judgment(graded), sample["decoded"],
        sample["message_body_savings_pct"]
    )
    result = copy.deepcopy(sample)
    result["provider_spend_usd"] = meta.get("spend_usd", 0.0)
    attempts.append({
        "attempt": len(attempts) + 1,
        "status": scored["status"],
        "reason": scored["reason"],
        "provider_spend_usd": meta.get("spend_usd", 0.0),
    })
    result["judge_attempts"] = attempts
    if not scored["valid"]:
        result.update({
            "judge_valid": False,
            "judge_status": scored["status"],
            "judge_reason": scored["reason"],
            "atom_results": scored.get("items", []),
        })
        return result
    result.update({
        "judge_valid": True,
        "judge_status": scored["status"],
        "judge_reason": scored["reason"],
        "meaning_pass": scored["meaning_pass"],
        "compression_success": scored["compression_success"],
        "semantic_coverage_pct": scored["semantic_coverage_pct"],
        "critical_failures": scored["critical_failures"],
        "inventions": scored["inventions"],
        "atom_results": scored["items"],
    })
    return result


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _empty_registry() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "baseline_version": BASELINE_VERSION,
            "provider_spend_usd": 0.0, "records": []}


def _empty_progress(spend_usd: float = 0.0) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "baseline_version": BASELINE_VERSION,
            "provider_spend_usd": spend_usd, "sample": None}


def _spend(value: Any) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise FrozenEnglishError("invalid_provider_spend_receipt")
    return round(float(value), 12)


def _load_progress(path: Path, registry: dict[str, Any]) -> dict[str, Any]:
    registry_spend = _spend(registry.get("provider_spend_usd", 0.0))
    progress = load_json(path, _empty_progress(registry_spend))
    if (
        not isinstance(progress, dict)
        or progress.get("schema_version") != SCHEMA_VERSION
        or progress.get("baseline_version") != BASELINE_VERSION
        or (progress.get("sample") is not None
            and not isinstance(progress.get("sample"), dict))
    ):
        raise FrozenEnglishError("frozen_english_progress_invalid")
    progress["provider_spend_usd"] = max(
        registry_spend, _spend(progress.get("provider_spend_usd")))
    return progress


def _registry_checkpoint(registry: dict[str, Any], records: dict[str, dict[str, Any]],
                         spend_usd: float) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "baseline_version": BASELINE_VERSION,
        "created_at": registry.get("created_at", _utc_now()),
        "updated_at": _utc_now(),
        "provider_spend_usd": _spend(spend_usd),
        "records": [
            copy.deepcopy(records[benchmark_id])
            for benchmark_id in BENCHMARK_IDS
            if benchmark_id in records
        ],
    }


def preview_plan(
    contract: dict[str, Any], registry: dict[str, Any],
    progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    statuses = baseline_status(registry, contract)
    pending = (progress or {}).get("sample")
    return {
        "mode": "preview_no_provider_calls",
        "baseline_version": BASELINE_VERSION,
        "current": [key for key, value in statuses.items() if value["state"] == "current"],
        "to_run": [key for key, value in statuses.items() if value["state"] != "current"],
        "preserved_sample": pending.get("benchmark_id") if pending else None,
        "rejudge_required": bool(pending),
        "max_controls": len(BENCHMARK_IDS),
        "scheduled_turn_path_changed": False,
    }


def run_live_controls(
    suite: dict[str, Any],
    contract: dict[str, Any],
    *,
    registry_path: Path,
    progress_path: Path,
    call_fn: Callable[..., tuple[str, dict[str, Any]]],
    token_count_fn: Callable[[str, dict[str, Any]], int],
    max_spend_usd: float,
    rejudge_id: str | None = None,
) -> dict[str, Any]:
    """Run the five controls, preserving one sample for judge-only retry."""
    cap = _spend(max_spend_usd)
    if cap <= 0 or cap > MAX_APPROVED_SPEND_USD:
        raise FrozenEnglishError(
            "live_run_requires_max_spend_usd_at_or_below_0.25"
        )
    registry = load_json(registry_path, _empty_registry())
    progress = _load_progress(progress_path, registry)
    records = {
        row.get("benchmark_id"): row
        for row in registry.get("records", [])
        if isinstance(row, dict) and row.get("judge_valid") is True
    }
    starting_spend = progress["provider_spend_usd"]
    if starting_spend >= cap:
        raise FrozenEnglishError("frozen_english_spend_cap_reached")
    meta = {
        "spend_usd": starting_spend,
        "spend_usd_historical_estimate": 0.0,
        "spend_usd_provider_exact_since_cutover": starting_spend,
    }

    def write_progress(sample: dict[str, Any] | None) -> None:
        progress["sample"] = copy.deepcopy(sample)
        progress["provider_spend_usd"] = _spend(meta["spend_usd"])
        atomic_write_json(progress_path, progress)

    def write_registry() -> None:
        nonlocal registry
        registry = _registry_checkpoint(registry, records, meta["spend_usd"])
        atomic_write_json(registry_path, registry)

    def capped_call(*call_args: Any, **call_kwargs: Any) -> tuple[str, dict[str, Any]]:
        if meta["spend_usd"] >= cap:
            raise FrozenEnglishError("frozen_english_spend_cap_reached")
        result = call_fn(*call_args, **call_kwargs)
        _spend(meta["spend_usd"])
        write_progress(progress.get("sample"))
        if meta["spend_usd"] > cap:
            write_registry()
            raise FrozenEnglishError("frozen_english_spend_cap_exceeded")
        return result

    rows_by_id = {row["id"]: row for row in suite["benchmarks"]}
    pending = progress.get("sample")
    statuses = baseline_status(registry, contract)

    if pending and statuses.get(pending.get("benchmark_id"), {}).get("state") == "current":
        write_progress(None)
        pending = None
    elif pending and pending.get("judge_valid") is True:
        records[pending["benchmark_id"]] = pending
        write_registry()
        write_progress(None)
        pending = None

    if rejudge_id is not None:
        if rejudge_id not in BENCHMARK_IDS:
            raise FrozenEnglishError("rejudge_benchmark_invalid")
        if not pending or pending.get("benchmark_id") != rejudge_id:
            raise FrozenEnglishError(
                f"no_preserved_control_for_rejudge:{rejudge_id}"
            )
        benchmark = rows_by_id[rejudge_id]
        _check_sample(pending, benchmark, contract)
        result = judge_preserved_sample(
            pending, benchmark, contract, call_fn=capped_call, meta=meta
        )
        write_progress(result)
        write_registry()
        if not result["judge_valid"]:
            raise FrozenEnglishError(
                f"invalid_english_control_judge:{rejudge_id}:{result['judge_reason']}"
            )
        records[rejudge_id] = result
        write_registry()
        write_progress(None)
        return {
            "result": "frozen_english_rejudge_promoted",
            "benchmark_id": rejudge_id,
            "records": len(records),
            "provider_spend_usd": meta["spend_usd"],
        }

    if pending:
        raise FrozenEnglishError(
            f"preserved_control_requires_rejudge:{pending['benchmark_id']}"
        )

    for benchmark_id in BENCHMARK_IDS:
        statuses = baseline_status(registry, contract)
        if statuses[benchmark_id]["state"] == "current":
            continue
        benchmark = rows_by_id[benchmark_id]
        sample = capture_control_sample(
            benchmark, contract, call_fn=capped_call,
            token_count_fn=token_count_fn, meta=meta,
        )
        pending = sample
        write_progress(sample)
        result = judge_preserved_sample(
            sample, benchmark, contract, call_fn=capped_call, meta=meta
        )
        pending = result
        write_progress(result)
        if not result["judge_valid"]:
            write_registry()
            raise FrozenEnglishError(
                f"invalid_english_control_judge:{benchmark_id}:{result['judge_reason']}"
            )
        records[benchmark_id] = result
        write_registry()
        pending = None
        write_progress(None)

    return {
        "result": "frozen_english_controls_written",
        "records": len(records),
        "provider_spend_usd": meta["spend_usd"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="perform the one-time provider controls")
    parser.add_argument("--max-spend-usd", type=float)
    parser.add_argument("--output", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--progress", type=Path, default=PROGRESS_PATH)
    parser.add_argument("--rejudge", choices=BENCHMARK_IDS)
    args = parser.parse_args()

    from loop import call, load_benchmark_suite, token_count

    suite = load_benchmark_suite()
    contract = load_checked_contract(suite)
    registry = load_json(args.output, _empty_registry())
    progress = _load_progress(args.progress, registry)
    plan = preview_plan(contract, registry, progress)
    if not args.live:
        if args.rejudge:
            raise FrozenEnglishError("rejudge_requires_live_flag")
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    if (
        args.max_spend_usd is None
        or not math.isfinite(args.max_spend_usd)
        or args.max_spend_usd <= 0
        or args.max_spend_usd > MAX_APPROVED_SPEND_USD
    ):
        raise FrozenEnglishError("live_run_requires_max_spend_usd_at_or_below_0.25")

    result = run_live_controls(
        suite, contract, registry_path=args.output, progress_path=args.progress,
        call_fn=call, token_count_fn=token_count,
        max_spend_usd=args.max_spend_usd, rejudge_id=args.rejudge,
    )
    result["output"] = str(args.output.resolve())
    result["progress"] = str(args.progress.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
