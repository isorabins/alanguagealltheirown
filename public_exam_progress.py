"""One bounded, sanitized public snapshot for the canonical scheduled exam."""
from __future__ import annotations

import copy
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from state_store import atomic_write_json, load_json

SCHEMA_VERSION = 1
MAX_PUBLIC_TEXT = 20_000
MAX_RECEIPTS = 64
PHASES = (
    "exam_started",
    "benchmark_selected",
    "language_loaded",
    "encoder_started",
    "encoder_completed",
    "decoder_started",
    "decoder_completed",
    "judge_started",
    "audit_progress",
    "completed",
)
TERMINAL_PHASES = {"completed", "interrupted", "failed"}
PUBLIC_ERROR_CLASSES = {
    "provider_unavailable",
    "provider_timeout",
    "invalid_provider_response",
    "invalid_judge_result",
    "interrupted",
    "state_write_failed",
}
TOP_LEVEL_FIELDS = {
    "schema_version", "run_id", "turn", "phase", "updated_at", "receipts",
    "benchmark_id", "benchmark_name", "language_version", "language_hash",
    "encoded", "decoded", "audit", "tokens", "result", "error_class",
    "diagnostic",
}
AUDIT_FIELDS = {"completed", "total", "survived", "corrupted", "missing", "inventions"}
TOKEN_FIELDS = {"original", "encoded"}
RESULT_FIELDS = {
    "judge_valid", "meaning_pass", "compression_success",
    "semantic_coverage_pct", "status",
}
RECEIPT_FIELDS = {"phase", "at", "message"}
DIAGNOSTIC_FIELDS = {"stage", "reason", "response_chars"}
_UNSAFE_TEXT = re.compile(
    r"(?i)(?:"
    r"\b(?:OPENROUTER_API_KEY|API_KEY|PASSWORD|CLIENT_SECRET|AUTHORIZATION)\s*[:=]|"
    r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}|"
    r"\bsk-[A-Za-z0-9_-]{12,}|"
    r"(?:BEGIN|END)\s+(?:SYSTEM|DEVELOPER|HIDDEN)\s+PROMPT|"
    r"\b(?:system|developer|hidden)\s+prompt\s*[:=]|"
    r"\bchain[- ]of[- ]thought\b|\bprivate collaboration state\b|"
    r"Traceback \(most recent call last\)"
    r")"
)


class ProgressValidationError(ValueError):
    def __init__(self, reason: str, *, stage: str | None = None,
                 response_chars: int | None = None):
        super().__init__(reason)
        self.reason = reason
        self.stage = stage
        self.response_chars = response_chars


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_run_id(turn: int, benchmark_id: str, language_hash: str) -> str:
    identity = f"{int(turn)}\0{benchmark_id}\0{language_hash}".encode()
    return f"exam-{int(turn)}-{hashlib.sha256(identity).hexdigest()[:16]}"


def sanitize_completed_text(value: Any, *, stage: str | None = None) -> str:
    if not isinstance(value, str):
        raise ProgressValidationError("public_text_not_string", stage=stage)
    value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    value = "".join(character for character in value
                    if character in "\n\t" or ord(character) >= 32)
    if not value:
        raise ProgressValidationError("public_text_empty", stage=stage, response_chars=0)
    if len(value) > MAX_PUBLIC_TEXT:
        raise ProgressValidationError(
            "public_text_too_large", stage=stage, response_chars=len(value),
        )
    if _UNSAFE_TEXT.search(value):
        raise ProgressValidationError(
            "unsafe_public_text", stage=stage, response_chars=len(value),
        )
    return value


def classify_public_error(error: BaseException) -> str:
    if isinstance(error, KeyboardInterrupt):
        return "interrupted"
    if isinstance(error, TimeoutError):
        return "provider_timeout"
    if isinstance(error, ProgressValidationError):
        return "invalid_provider_response"
    return "provider_unavailable"


def public_error_diagnostic(error: BaseException) -> dict[str, Any] | None:
    if not isinstance(error, ProgressValidationError) or error.stage not in {"encoder", "decoder"}:
        return None
    diagnostic = {"stage": error.stage, "reason": error.reason}
    if error.response_chars is not None:
        diagnostic["response_chars"] = min(max(0, error.response_chars), 1_000_000_000)
    return diagnostic


def _bounded_int(value: Any, *, maximum: int = 1_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ProgressValidationError("invalid_public_count")
    return value


def _exact_fields(value: Any, allowed: set[str], *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not set(value).issubset(allowed):
        raise ProgressValidationError(f"{name}_fields_invalid")
    return value


def validate_snapshot(snapshot: Any, previous: Any = None) -> dict[str, Any]:
    value = _exact_fields(snapshot, TOP_LEVEL_FIELDS, name="snapshot")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ProgressValidationError("schema_version_invalid")
    run_id = value.get("run_id")
    if not isinstance(run_id, str) or not re.fullmatch(r"exam-[0-9]+-[a-f0-9]{16}", run_id):
        raise ProgressValidationError("run_id_invalid")
    turn = value.get("turn")
    if isinstance(turn, bool) or not isinstance(turn, int) or turn < 1:
        raise ProgressValidationError("turn_invalid")
    phase = value.get("phase")
    if phase not in set(PHASES) | {"interrupted", "failed"}:
        raise ProgressValidationError("phase_invalid")
    updated_at = value.get("updated_at")
    if not isinstance(updated_at, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", updated_at
    ):
        raise ProgressValidationError("timestamp_invalid")

    receipts = value.get("receipts")
    if not isinstance(receipts, list) or not 1 <= len(receipts) <= MAX_RECEIPTS:
        raise ProgressValidationError("receipts_invalid")
    receipt_phases = []
    for receipt in receipts:
        receipt = _exact_fields(receipt, RECEIPT_FIELDS, name="receipt")
        if set(receipt) != RECEIPT_FIELDS or receipt.get("phase") not in set(PHASES) | {"interrupted", "failed"}:
            raise ProgressValidationError("receipt_invalid")
        if not isinstance(receipt.get("at"), str) or not isinstance(receipt.get("message"), str):
            raise ProgressValidationError("receipt_invalid")
        if len(receipt["message"]) > 240 or _UNSAFE_TEXT.search(receipt["message"]):
            raise ProgressValidationError("receipt_message_invalid")
        receipt_phases.append(receipt["phase"])
    if receipt_phases[-1] != phase:
        raise ProgressValidationError("receipt_phase_mismatch")

    for field in ("benchmark_id", "benchmark_name", "language_version", "language_hash"):
        if field in value and (not isinstance(value[field], str) or not value[field] or len(value[field]) > 160):
            raise ProgressValidationError(f"{field}_invalid")
    if "encoded" in value:
        sanitize_completed_text(value["encoded"])
    if "decoded" in value:
        sanitize_completed_text(value["decoded"])
    if "audit" in value:
        audit = _exact_fields(value["audit"], AUDIT_FIELDS, name="audit")
        if set(audit) != AUDIT_FIELDS:
            raise ProgressValidationError("audit_fields_invalid")
        for item in audit.values():
            _bounded_int(item)
        if audit["completed"] > audit["total"]:
            raise ProgressValidationError("audit_progress_invalid")
    if "tokens" in value:
        tokens = _exact_fields(value["tokens"], TOKEN_FIELDS, name="tokens")
        if set(tokens) != TOKEN_FIELDS:
            raise ProgressValidationError("token_fields_invalid")
        _bounded_int(tokens["original"])
        _bounded_int(tokens["encoded"])
    if "result" in value:
        result = _exact_fields(value["result"], RESULT_FIELDS, name="result")
        if set(result) != RESULT_FIELDS:
            raise ProgressValidationError("result_fields_invalid")
        if any(result[field] not in (True, False, None)
               for field in ("judge_valid", "meaning_pass", "compression_success")):
            raise ProgressValidationError("result_boolean_invalid")
        coverage = result["semantic_coverage_pct"]
        if coverage is not None and (isinstance(coverage, bool) or not isinstance(coverage, (int, float)) or not 0 <= coverage <= 100):
            raise ProgressValidationError("coverage_invalid")
        if not isinstance(result["status"], str) or len(result["status"]) > 80:
            raise ProgressValidationError("result_status_invalid")
    if "error_class" in value and value["error_class"] not in PUBLIC_ERROR_CLASSES:
        raise ProgressValidationError("error_class_invalid")
    if "diagnostic" in value:
        if phase != "failed":
            raise ProgressValidationError("diagnostic_phase_invalid")
        diagnostic = _exact_fields(value["diagnostic"], DIAGNOSTIC_FIELDS, name="diagnostic")
        if not {"stage", "reason"}.issubset(diagnostic):
            raise ProgressValidationError("diagnostic_fields_invalid")
        if diagnostic["stage"] not in {"encoder", "decoder"}:
            raise ProgressValidationError("diagnostic_stage_invalid")
        if diagnostic["reason"] not in {
            "public_text_not_string", "public_text_empty",
            "public_text_too_large", "unsafe_public_text",
        }:
            raise ProgressValidationError("diagnostic_reason_invalid")
        if "response_chars" in diagnostic:
            _bounded_int(diagnostic["response_chars"], maximum=1_000_000_000)

    required_by_phase = {
        "benchmark_selected": ("benchmark_id", "benchmark_name"),
        "language_loaded": ("benchmark_id", "benchmark_name", "language_version", "language_hash"),
        "encoder_completed": ("encoded",),
        "decoder_completed": ("encoded", "decoded"),
        "judge_started": ("encoded", "decoded"),
        "audit_progress": ("audit",),
        "completed": ("encoded", "decoded", "audit", "tokens", "result"),
        "interrupted": ("error_class",),
        "failed": ("error_class",),
    }
    for field in required_by_phase.get(phase, ()):
        if field not in value:
            raise ProgressValidationError(f"{phase}_{field}_missing")

    if previous is not None:
        prior = validate_snapshot(previous)
        if prior["run_id"] != run_id or prior["turn"] != turn:
            raise ProgressValidationError("mixed_exam_identity")
        if prior["phase"] in TERMINAL_PHASES:
            raise ProgressValidationError("terminal_snapshot_immutable")
        if phase in {"interrupted", "failed"}:
            pass
        elif prior["phase"] == "audit_progress" and phase == "audit_progress":
            if value["audit"]["completed"] < prior["audit"]["completed"]:
                raise ProgressValidationError("audit_progress_regressed")
        else:
            expected = PHASES[PHASES.index(prior["phase"]) + 1]
            if phase != expected:
                raise ProgressValidationError("transition_invalid")
        for field in ("benchmark_id", "benchmark_name", "language_version", "language_hash"):
            if field in prior and value.get(field) != prior[field]:
                raise ProgressValidationError("exam_identity_drift")
        if receipts[:-1] != prior["receipts"]:
            raise ProgressValidationError("receipt_history_invalid")
    return copy.deepcopy(value)


class PublicExamProgressWriter:
    """Atomic single-run writer. The caller remains the only state owner."""

    def __init__(self, path: Path, *, turn: int, benchmark_id: str,
                 benchmark_name: str, language_version: str, language_hash: str,
                 clock=_now, replace_active: bool = False):
        self.path = Path(path)
        self.turn = int(turn)
        self.benchmark_id = benchmark_id
        self.benchmark_name = benchmark_name
        self.language_version = language_version
        self.language_hash = language_hash
        self.run_id = build_run_id(turn, benchmark_id, language_hash)
        self.clock = clock
        self.replace_active = replace_active
        self.current = None

    def _receipt_message(self, phase: str, fields: dict[str, Any]) -> str:
        if phase == "exam_started": return "exam boundary reached"
        if phase == "benchmark_selected": return f"benchmark {self.benchmark_id} · {self.benchmark_name} selected"
        if phase == "language_loaded": return f"adopted language {self.language_version} loaded"
        if phase == "encoder_started": return "encoder started"
        if phase == "encoder_completed": return "encoder completed · sanitized response available"
        if phase == "decoder_started": return "decoder started"
        if phase == "decoder_completed": return "decoder completed · sanitized response available"
        if phase == "judge_started": return "judge started"
        if phase == "audit_progress":
            audit = fields["audit"]
            return (f"semantic audit {audit['completed']}/{audit['total']} · "
                    f"{audit['survived']} survived · {audit['corrupted']} corrupted · "
                    f"{audit['missing']} missing · {audit['inventions']} inventions")
        if phase == "completed": return "final verified result available"
        if phase == "interrupted": return "exam interrupted before verification"
        diagnostic = fields.get("diagnostic")
        if diagnostic:
            reason = diagnostic["reason"].replace("public_text_", "").replace("_", " ")
            size = diagnostic.get("response_chars")
            suffix = f" · {size} characters" if size is not None else ""
            return f"exam failed · invalid {diagnostic['stage']} response · {reason}{suffix}"
        return f"exam failed · {fields['error_class'].replace('_', ' ')}"

    def advance(self, phase: str, **fields: Any) -> dict[str, Any]:
        timestamp = self.clock()
        if self.current is None:
            if phase != "exam_started":
                raise ProgressValidationError("first_phase_invalid")
            existing = load_json(self.path, None)
            if isinstance(existing, dict):
                existing = validate_snapshot(existing)
                if existing["phase"] not in TERMINAL_PHASES and not self.replace_active:
                    raise ProgressValidationError("active_exam_already_exists")
            snapshot = {
                "schema_version": SCHEMA_VERSION,
                "run_id": self.run_id,
                "turn": self.turn,
                "phase": phase,
                "updated_at": timestamp,
                "receipts": [],
            }
        else:
            snapshot = copy.deepcopy(self.current)
            snapshot.update(fields)
            snapshot["phase"] = phase
            snapshot["updated_at"] = timestamp
        if phase == "benchmark_selected":
            snapshot.update(benchmark_id=self.benchmark_id, benchmark_name=self.benchmark_name)
        if phase == "language_loaded":
            snapshot.update(language_version=self.language_version, language_hash=self.language_hash)
        snapshot["receipts"].append({
            "phase": phase,
            "at": timestamp,
            "message": self._receipt_message(phase, fields),
        })
        snapshot = validate_snapshot(snapshot, self.current)
        atomic_write_json(self.path, snapshot)
        self.current = snapshot
        return copy.deepcopy(snapshot)

    def fail(self, error_class: str, *, interrupted: bool = False,
             diagnostic: dict[str, Any] | None = None) -> dict[str, Any]:
        if error_class not in PUBLIC_ERROR_CLASSES:
            error_class = "provider_unavailable"
        fields = {"error_class": error_class}
        if diagnostic is not None:
            fields["diagnostic"] = diagnostic
        return self.advance("interrupted" if interrupted else "failed", **fields)


def publish_completed_snapshot(path: Path, snapshot: Any) -> dict[str, Any]:
    """Publish only a fully validated terminal result to the tracked public path."""
    validated = validate_snapshot(snapshot)
    if validated["phase"] != "completed":
        raise ProgressValidationError("completed_snapshot_required")
    atomic_write_json(Path(path), validated)
    return copy.deepcopy(validated)
