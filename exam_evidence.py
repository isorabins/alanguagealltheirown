"""Development-exam evidence from saved experiment state and raw model responses.

run_exam owns benchmark selection, captured language, exact evidence, score,
canonical result, baseline and cursor. validated_persisted_exam defensively
rechecks historical input for the fault module without owning its lifecycle.
Conversation and transfer exams deliberately keep their separate contracts.
"""
from __future__ import annotations
import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from public_exam_progress import (PublicExamProgressWriter, classify_public_error,
    public_error_diagnostic, sanitize_completed_text)
from rulebook import _literal_set_survives, language_payload, render_language, score_judgment_v2
from turn_store import TurnState

@dataclass(frozen=True)
class ExamResources:
    root: Path
    suite: dict[str, Any]
    encoder: str
    decoder: str
    grader: str

def select_benchmark(meta, suite):
    """Return the next benchmark without advancing its durable cursor."""
    state = meta.get("benchmark_suite")
    if state is None or state.get("version") != suite["version"]:
        state = {"version": suite["version"], "next_index": 0, "cycle": 1}
        meta["benchmark_suite"] = state
    index = state.get("next_index")
    cycle = state.get("cycle")
    if not isinstance(index, int) or not 0 <= index < len(suite["benchmarks"]):
        raise ValueError("benchmark_cursor_invalid")
    if not isinstance(cycle, int) or cycle < 1:
        raise ValueError("benchmark_cycle_invalid")
    return copy.deepcopy(suite["benchmarks"][index]), cycle


def advance_benchmark(meta, benchmark, suite):
    """Advance exactly once after an exam receipt has been constructed."""
    state = meta["benchmark_suite"]
    index = state["next_index"]
    if suite["benchmarks"][index]["id"] != benchmark["id"]:
        raise ValueError("benchmark_cursor_drift")
    next_index = (index + 1) % len(suite["benchmarks"])
    state["next_index"] = next_index
    if next_index == 0:
        state["cycle"] += 1


def previous_benchmark_result(meta, benchmark):
    """Return only a prior valid Scoring V2 result; V1 is never a comparison baseline."""
    return copy.deepcopy(meta.get("benchmark_results_v2", {}).get(benchmark["id"]))


def _numbered_decoded(decoded):
    """Return a stable one-based view of decoded lines for the judge."""
    lines = decoded.splitlines()
    return "\n".join(
        f"{line_number:04d}: {line}"
        for line_number, line in enumerate(lines, start=1)
    )


def _grader_answer_key(answer_key, decoded):
    """Expose exact-literal requirements and deterministic decode preflight."""
    decoded_lines = decoded.splitlines()
    projected = []
    for atom in answer_key:
        literal_sets = copy.deepcopy(atom["literal_sets"])
        projected.append({
            "id": atom["id"],
            "meaning": atom["meaning"],
            "literal_sets": literal_sets,
            "missing_literal_sets": [
                alternatives for alternatives in literal_sets
                if not _literal_set_survives(decoded, alternatives)
            ],
            "literal_set_lines": [
                [
                    line_number
                    for line_number, line in enumerate(decoded_lines, start=1)
                    if _literal_set_survives(line, alternatives)
                ]
                for alternatives in literal_sets
            ],
        })
    return projected


def _materialize_grader_evidence(grade, decoded):
    """Resolve judge-selected line ranges into exact spans owned by the harness."""
    if not isinstance(grade, dict):
        return grade, None
    items = grade.get("items")
    inventions = grade.get("inventions")
    if not isinstance(items, list) or not isinstance(inventions, list):
        return grade, None

    decoded_lines = decoded.splitlines()
    materialized = copy.deepcopy(grade)

    def resolve(entry, *, identity, missing_allowed):
        if not isinstance(entry, dict):
            return f"invalid_evidence_line_range:{identity}"
        evidence_lines = entry.pop("evidence_lines", None)
        if missing_allowed and evidence_lines == []:
            entry["evidence"] = ""
            return None
        if (
            not isinstance(evidence_lines, list)
            or len(evidence_lines) != 2
            or any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in evidence_lines
            )
        ):
            return f"invalid_evidence_line_range:{identity}"
        start, end = evidence_lines
        if start < 1 or end < start or end > len(decoded_lines):
            return f"invalid_evidence_line_range:{identity}"
        entry["evidence"] = "\n".join(decoded_lines[start - 1:end])
        return None

    for item in materialized["items"]:
        identity = item.get("id", "unknown") if isinstance(item, dict) else "unknown"
        missing_allowed = isinstance(item, dict) and item.get("verdict") == "MISSING"
        reason = resolve(item, identity=identity, missing_allowed=missing_allowed)
        if reason:
            return grade, reason
    for index, invention in enumerate(materialized["inventions"], start=1):
        reason = resolve(
            invention,
            identity=f"invention-{index}",
            missing_allowed=False,
        )
        if reason:
            return grade, reason
    return materialized, None


def _invalid_judge_diagnostic(grade, reason):
    """Retain only the rejected reference needed to explain an invalid result."""
    diagnostic = {"reason": reason}
    atom_id = reason.split(":", 1)[1] if ":" in reason else None
    items = grade.get("items") if isinstance(grade, dict) else None
    if atom_id and isinstance(items, list):
        item = next(
            (
                candidate for candidate in items
                if isinstance(candidate, dict) and candidate.get("id") == atom_id
            ),
            None,
        )
        if item:
            diagnostic.update({
                "atom_id": atom_id,
                "verdict": item.get("verdict"),
                "evidence_lines": copy.deepcopy(item.get("evidence_lines")),
            })
    return diagnostic


def _test_turn_impl(conv, rb, meta, turn, *, resources, provider, count_tokens, progress_path=None, progress_box=None):
    suite = resources.suite
    benchmark, benchmark_cycle = select_benchmark(meta, suite)
    pname = f"{benchmark['id']} · {benchmark['name']}"
    payload = benchmark["original"]
    key = copy.deepcopy(benchmark["answer_key"])
    previous = previous_benchmark_result(meta, benchmark)
    captured = language_payload(rb)
    rbook = render_language(rb)
    progress = None
    if progress_path is not None:
        progress = PublicExamProgressWriter(
            progress_path,
            turn=turn,
            benchmark_id=benchmark["id"],
            benchmark_name=benchmark["name"],
            language_version=captured["version"],
            language_hash=captured["hash"],
            replace_active=Path(progress_path).name.endswith(".local.json"),
        )
        if progress_box is not None:
            progress_box[:] = [progress]

    def publish_progress(phase, **fields):
        nonlocal progress
        if progress is None:
            return
        try:
            progress.advance(phase, **fields)
        except Exception:
            # Public observability is deliberately fail-open for the canonical
            # exam. Losing its tiny snapshot must not lose the real result.
            progress = None
            if progress_box is not None:
                progress_box[:] = []

    publish_progress("exam_started")
    publish_progress("benchmark_selected")
    publish_progress("language_loaded")
    publish_progress("encoder_started")
    enc_sys = ("You are the encoder. Encode the message below into the project language "
               "using ONLY this rulebook. Where the rulebook is silent, fall back to plain "
               "English for that part. Output ONLY the encoded message, nothing else.\n\n" + rbook)
    encoded, _ = provider(resources.encoder, enc_sys, payload, max_tokens=4000, temperature=0.3, meta=meta)
    encoded = sanitize_completed_text(encoded, stage="encoder")
    publish_progress("encoder_completed", encoded=encoded)
    publish_progress("decoder_started")
    dec_sys = ("You are a fresh agent. You have never seen any prior conversation. Below is the "
               "complete rulebook of a constructed language. Decode the message you receive: "
               "reconstruct the original content as faithfully as you can. Do not invent anything "
               "the message does not encode. Output ONLY the reconstruction.\n\n" + rbook)
    decoded, _ = provider(resources.decoder, dec_sys, encoded.strip(), max_tokens=4000, temperature=0.1, meta=meta)
    decoded = sanitize_completed_text(decoded, stage="decoder")
    publish_progress("decoder_completed", decoded=decoded)
    orig_t = count_tokens(payload)
    enc_t = count_tokens(encoded.strip())
    delta = round((enc_t - orig_t) / orig_t * 100)
    savings_pct = -delta
    grade_sys = (resources.root / "prompts" / "grader_v2.md").read_text()
    if key:
        publish_progress("judge_started")
        numbered_decoded = _numbered_decoded(decoded.strip())
        key_txt = json.dumps(_grader_answer_key(key, decoded.strip()), ensure_ascii=False)
        grade_user = (
            f"ORIGINAL:\n{payload}\n\nATOMIC ANSWER KEY:\n{key_txt}"
            f"\n\nNUMBERED DECODED:\n{numbered_decoded}"
        )
        graded, _ = provider(resources.grader, grade_sys, grade_user, max_tokens=4000, temperature=0, meta=meta)
        gm = re.search(r"\{.*\}", graded, re.S)
        try:
            g = json.loads(gm.group(0)) if gm else {}
        except json.JSONDecodeError:
            g = {}
    else:
        g = {}
    audit = {}
    if key:
        materialized_grade, evidence_reason = _materialize_grader_evidence(
            g, decoded.strip()
        )
        if evidence_reason:
            scored = {
                "valid": False,
                "status": "INVALID JUDGE RESULT",
                "reason": evidence_reason,
                "scoring_version": "v2",
            }
        else:
            scored = score_judgment_v2(
                key, materialized_grade, decoded.strip(), savings_pct
            )
        audit = {
            "judge_valid": scored["valid"], "judge_status": scored["status"],
            "judge_reason": scored["reason"], "atom_results": scored.get("items", []),
            "survived": scored.get("survived"), "total": scored.get("total", len(key)),
            "meaning_pass": scored.get("meaning_pass"),
            "compression_success": scored.get("compression_success"),
            "semantic_coverage_pct": scored.get("semantic_coverage_pct"),
            "critical_failures": scored.get("critical_failures", []),
            "inventions": scored.get("inventions", []),
        }
        if not scored["valid"]:
            audit["judge_diagnostic"] = _invalid_judge_diagnostic(
                g, scored["reason"]
            )
    else:
        scored = {"valid": False, "status": "INVALID JUDGE RESULT", "reason": "answer_key_unavailable"}
        audit = {"judge_valid": False, "judge_status": scored["status"],
                 "judge_reason": scored["reason"], "atom_results": [], "survived": None,
                 "total": 0, "meaning_pass": None, "compression_success": None,
                 "semantic_coverage_pct": None, "critical_failures": [], "inventions": []}
    meta["tests_run"] = meta.get("tests_run", 0) + 1
    event = {"turn": turn, "agent": "harness", "type": "test", "payload": pname,
             "original": payload, "orig_tokens": orig_t, "enc_tokens": enc_t,
             "token_delta_pct": delta, "message_body_savings_pct": savings_pct,
             "encoded": encoded.strip(), "decoded": decoded.strip(), "tokens": enc_t,
             "decoder_model": resources.decoder, "language_version": captured["version"],
             "language_hash": captured["hash"], "era": "benchmark-v2",
             "scoring_version": "v2",
             "benchmark_id": benchmark["id"], "benchmark_name": benchmark["name"],
             "benchmark_version": suite["version"], "benchmark_cycle": benchmark_cycle,
             "benchmark_source_turn": benchmark["source_turn"],
             "answer_key": [{"id": atom["id"], "meaning": atom["meaning"],
                              "critical": atom["critical"],
                              "literal_sets": copy.deepcopy(atom["literal_sets"])}
                             for atom in key],
             "prior_valid_v2_turn": previous.get("turn") if previous else None}
    event.update(audit)
    if scored["valid"]:
        verdicts = [item.get("verdict") for item in audit["atom_results"]]
        for completed in range(1, len(verdicts) + 1):
            observed = verdicts[:completed]
            publish_progress("audit_progress", audit={
                "completed": completed,
                "total": audit["total"],
                "survived": observed.count("SURVIVED"),
                "corrupted": observed.count("CORRUPTED"),
                "missing": observed.count("MISSING"),
                "inventions": len(audit["inventions"]),
            })
        publish_progress(
            "completed",
            tokens={"original": orig_t, "encoded": enc_t},
            result={
                "judge_valid": audit["judge_valid"],
                "meaning_pass": audit["meaning_pass"],
                "compression_success": audit["compression_success"],
                "semantic_coverage_pct": audit["semantic_coverage_pct"],
                "status": audit["judge_status"],
            },
        )
    elif progress is not None:
        try:
            progress.fail("invalid_judge_result")
        except Exception:
            pass
    conv.append(event)
    exams = meta.setdefault("corpus_exams", [])
    exams.append({"turn": turn, "language_version": captured["version"],
                  "language_hash": captured["hash"], "scoring_version": "v2",
                  "meaning_pass": audit["meaning_pass"],
                  "compression_success": audit["compression_success"],
                  "semantic_coverage_pct": audit["semantic_coverage_pct"],
                  "critical_failures": copy.deepcopy(audit["critical_failures"]),
                  "inventions": copy.deepcopy(audit["inventions"]),
                  "message_body_savings_pct": savings_pct,
                  "token_delta_pct": delta, "valid": scored["valid"],
                  "judge_status": audit["judge_status"],
                  "era": "benchmark-v2", "benchmark_id": benchmark["id"],
                  "benchmark_name": benchmark["name"],
                  "benchmark_version": suite["version"],
                  "benchmark_cycle": benchmark_cycle,
                  "prior_valid_v2_turn": previous.get("turn") if previous else None})
    meta["corpus_exams"] = exams[-500:]
    if scored["valid"]:
        meta.setdefault("benchmark_results_v2", {})[benchmark["id"]] = {
            "turn": turn, "meaning_pass": audit["meaning_pass"],
            "compression_success": audit["compression_success"],
            "semantic_coverage_pct": audit["semantic_coverage_pct"],
            "critical_failures": copy.deepcopy(audit["critical_failures"]),
            "inventions": copy.deepcopy(audit["inventions"]),
            "message_body_savings_pct": savings_pct,
            "language_version": captured["version"], "language_hash": captured["hash"],
        }
    advance_benchmark(meta, benchmark, suite)
    print(f"[t{turn} TEST] {pname}  {orig_t}->{enc_t}tok ({delta:+d}%)  "
          f"{audit['judge_status']} coverage {audit['semantic_coverage_pct']}  "
          f"${meta['spend_usd']:.3f}", flush=True)
    if progress is not None and progress.current and progress.current.get("phase") == "completed":
        return copy.deepcopy(progress.current)
    return None


def run_exam(
    state: TurnState, turn: int, *, resources: ExamResources,
    provider: Callable[..., tuple[str, dict[str, Any]]],
    count_tokens: Callable[[str], int], progress_path: Path | None = None,
) -> dict[str, Any] | None:
    """Run one canonical exam and optionally expose only its safe receipts."""
    conv, rb, meta = state.conversation, state.rulebook, state.meta
    progress_box = []
    try:
        return _test_turn_impl(
            conv, rb, meta, turn,
            resources=resources, provider=provider, count_tokens=count_tokens,
            progress_path=progress_path,
            progress_box=progress_box,
        )
    except BaseException as error:
        if progress_box:
            try:
                progress_box[0].fail(
                    classify_public_error(error),
                    interrupted=isinstance(error, KeyboardInterrupt),
                    diagnostic=public_error_diagnostic(error),
                )
            except Exception:
                pass
        raise


def validated_persisted_exam(
    event: dict[str, Any],
    canonical_atoms: dict[tuple[str, str], dict[str, Any]],
    *, cutover_turn: int,
) -> dict[str, Any] | None:
    """Return a fully correlated judge-valid V2 exam or fail closed."""
    turn = event.get("turn")
    required_strings = (
        "benchmark_id",
        "benchmark_version",
        "scoring_version",
        "language_version",
        "language_hash",
        "original",
        "encoded",
        "decoded",
    )
    if not (
        event.get("type") == "test"
        and event.get("era") == "benchmark-v2"
        and type(turn) is int
        and turn >= cutover_turn
        and event.get("benchmark_id") in {"B1", "B2", "B3", "B4", "B5"}
        and event.get("benchmark_version") == "v2"
        and event.get("scoring_version") == "v2"
        and event.get("judge_valid") is True
        and event.get("judge_status") == "VALID"
        and all(isinstance(event.get(key), str) for key in required_strings)
        and len(event.get("language_hash", "")) == 64
    ):
        return None

    answer_key = event.get("answer_key")
    atom_results = event.get("atom_results")
    critical_failures = event.get("critical_failures")
    if not all(
        isinstance(value, list)
        for value in (answer_key, atom_results, critical_failures)
    ) or not answer_key:
        return None

    normalized_key: list[dict[str, Any]] = []
    key_ids: list[str] = []
    for atom in answer_key:
        if not (
            isinstance(atom, dict)
            and isinstance(atom.get("id"), str)
            and atom.get("id")
            and isinstance(atom.get("meaning"), str)
            and atom.get("meaning")
            and type(atom.get("critical")) is bool
        ):
            return None
        literal_sets = atom.get("literal_sets")
        canonical_atom = canonical_atoms.get((event["benchmark_id"], atom["id"]))
        if canonical_atoms:
            if not (
                isinstance(canonical_atom, dict)
                and canonical_atom.get("meaning") == atom["meaning"]
                and canonical_atom.get("critical") is atom["critical"]
            ):
                return None
            canonical_literal_sets = canonical_atom.get("literal_sets")
            if literal_sets is None:
                literal_sets = canonical_literal_sets
            elif literal_sets != canonical_literal_sets:
                return None
        if not (
            isinstance(literal_sets, list)
            and all(
                isinstance(group, list)
                and group
                and all(isinstance(value, str) and value for value in group)
                for group in literal_sets
            )
        ):
            return None
        key_ids.append(atom["id"])
        normalized_key.append(
            {
                "id": atom["id"],
                "meaning": atom["meaning"],
                "critical": atom["critical"],
                "literal_sets": copy.deepcopy(literal_sets),
            }
        )
    if len(key_ids) != len(set(key_ids)):
        return None

    normalized_results: list[dict[str, str]] = []
    for item in atom_results:
        if not (
            isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and item.get("verdict") in {"SURVIVED", "MISSING", "CORRUPTED"}
            and isinstance(item.get("evidence"), str)
        ):
            return None
        evidence = item["evidence"]
        if (item["verdict"] == "MISSING") != (evidence == ""):
            return None
        normalized_results.append(
            {
                "id": item["id"],
                "verdict": item["verdict"],
                "evidence": evidence,
            }
        )
    if [item["id"] for item in normalized_results] != key_ids:
        return None

    # Reuse generation-time evidence and literal validation. Historical events
    # do not retain judge mode; replay only needs the normalized atom evidence.
    scored = score_judgment_v2(normalized_key, {
        "mode": "RELAY", "items": normalized_results,
        "inventions": event.get("inventions", []),
    }, event["decoded"], 0)
    if not scored["valid"]:
        return None
    expected_failures = scored["critical_failures"]
    normalized_failures = []
    for failure in critical_failures:
        if not (
            isinstance(failure, dict)
            and isinstance(failure.get("atom_id"), str)
            and isinstance(failure.get("decoded_evidence"), str)
            and isinstance(failure.get("expected_meaning"), str)
            and failure.get("verdict") in {"MISSING", "CORRUPTED"}
        ):
            return None
        normalized_failures.append(
            {
                "atom_id": failure["atom_id"],
                "decoded_evidence": failure["decoded_evidence"],
                "expected_meaning": failure["expected_meaning"],
                "verdict": failure["verdict"],
            }
        )
    if normalized_failures != expected_failures:
        return None

    return {
        "turn": turn,
        "event": event,
        "answer_key": normalized_key,
        "atom_results": normalized_results,
        "critical_failures": normalized_failures,
    }
