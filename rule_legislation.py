"""Authoritative rule-legislation interface.

Callers read one immutable legislation snapshot, submit typed work, or ask the
module to advance.  Provider, storage, token, and cost adapters remain internal
to this module.  Shadow mode is read-only and cannot reserve spend or adopt.
"""
from __future__ import annotations

import copy
import fcntl
import hashlib
import json
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from legislative_protocol import current_open_motion
from rulebook import language_payload
from state_store import atomic_write_json, load_json, snapshot_hash


MONTHLY_CEILING_USD = Decimal("30.00")


class WorkOutcome(str, Enum):
    ELIGIBLE = "eligible"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    BLOCKED_BY_BUDGET = "blocked_by_budget"


class PaidRole(str, Enum):
    AGENT_A = "agent_a"
    AGENT_B = "agent_b"
    AGENT_C = "agent_c"
    DECODER = "decoder"
    JUDGE = "judge"
    EXPERIMENT = "experiment"
    CONVERSATION = "conversation"
    PUBLIC_USE = "public_use"


@dataclass(frozen=True)
class PaidWorkRequest:
    identity: str
    role: PaidRole
    provider_key: str
    model: str
    maximum_cost_usd: Decimal


@dataclass(frozen=True)
class CostReceipt:
    reservation_id: str
    response_id: str
    exact_cost_usd: Decimal


class Classification(str, Enum):
    HELPFUL = "helpful"
    HARMFUL = "harmful"
    REDUNDANT = "redundant"
    INTERACTING = "interacting"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EvidenceReceipt:
    evidence_id: str
    subject_ids: tuple[str, ...]
    incumbent_workbook_id: str
    candidate_workbook_id: str
    task_id: str
    exact_inputs_hash: str
    incumbent_success: bool
    candidate_success: bool
    incumbent_total_system_tokens: int
    candidate_total_system_tokens: int
    incumbent_includes_subject: bool
    candidate_includes_subject: bool
    judgment_valid: bool
    comparable: bool
    noisy: bool
    bundled: bool
    cost_usd: Decimal
    final_artifact_hash: str
    scope: str = "development"
    incumbent_token_components: tuple[tuple[str, int], ...] = ()
    candidate_token_components: tuple[tuple[str, int], ...] = ()
    provider_response_ids: tuple[str, ...] = ()
    provider_models: tuple[str, ...] = ()
    cost_response_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class LegacyEvidenceReceipt:
    evidence_id: str
    subject_ids: tuple[str, ...]
    source_kind: str
    source_identity: str


@dataclass(frozen=True)
class Consolidation:
    interaction_group_id: str
    ordered_source_ids: tuple[str, ...]
    candidate_rule_id: str
    candidate_artifact_hash: str


@dataclass(frozen=True)
class ExperimentQuestion:
    subject_ids: tuple[str, ...]
    important: bool


@dataclass(frozen=True)
class ExperimentCandidate:
    experiment_id: str
    evidence_id: str
    subject_ids: tuple[str, ...]
    incumbent_workbook_id: str
    candidate_workbook_id: str
    incumbent_inputs_hash: str
    candidate_inputs_hash: str
    controlled_variants: tuple[str, ...]
    expected_decision_impact: str
    proof_capable: bool
    held_out: bool
    maximum_cost_usd: Decimal
    provider_key: str
    model: str


@dataclass(frozen=True)
class ExperimentPlanRequest:
    question: ExperimentQuestion
    candidates: tuple[ExperimentCandidate, ...]


@dataclass(frozen=True)
class ModelOutput:
    role: str
    response_id: str
    returned_model: str
    finish_reason: str
    content: str
    content_sha256: str


@dataclass(frozen=True)
class AdoptionRequest:
    request_id: str
    proposal_id: str
    candidate_hash: str
    audit_id: str
    incumbent_language_version: str
    incumbent_language_hash: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class AdoptedRule:
    id: str
    text_en: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.id, "text_en": self.text_en}


@dataclass(frozen=True)
class AdoptedLanguage:
    version: str
    hash: str
    rules: tuple[AdoptedRule, ...]

    def render(self) -> str:
        if not self.rules:
            return f"LANGUAGE {self.version}\nNo adopted rules. Use plain English."
        lines = [f"LANGUAGE {self.version} ({len(self.rules)} adopted rules)"]
        lines.extend(f"{rule.id}: {rule.text_en}" for rule in self.rules)
        return "\n".join(lines)


@dataclass(frozen=True)
class BudgetState:
    mode: str
    wita_month: str | None
    monthly_ceiling_usd: str
    spent_usd: str
    reserved_usd: str
    available_usd: str


@dataclass(frozen=True)
class LegislationSnapshot:
    adopted_language: AdoptedLanguage
    complete_legislature_identity: str
    open_work: dict[str, Any] | None
    classifications: dict[str, str]
    budget: BudgetState
    public_read_model: dict[str, Any]


@dataclass(frozen=True)
class WorkResult:
    outcome: WorkOutcome
    reason: str
    snapshot: LegislationSnapshot
    detail: dict[str, Any] = field(default_factory=dict)


def _money(value: Decimal | str | int) -> Decimal:
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0:
        raise ValueError("cost_must_be_finite_and_non_negative")
    return amount


def _money_text(value: Decimal | str | int) -> str:
    whole, separator, fraction = format(_money(value), "f").partition(".")
    significant_fraction = fraction.rstrip("0")
    if len(significant_fraction) < 2:
        significant_fraction = significant_fraction.ljust(2, "0")
    return f"{whole}.{significant_fraction}" if separator else f"{whole}.00"


class _BudgetLedger:
    """Internal durable adapter with a process-safe reservation transaction."""

    def __init__(self, path: Path, clock):
        self._path = Path(path)
        self._lock_path = self._path.with_suffix(self._path.suffix + ".lock")
        self._clock = clock

    def _month_id(self) -> str:
        instant = self._clock()
        if instant.tzinfo is None:
            raise ValueError("budget_clock_must_be_timezone_aware")
        return instant.astimezone(ZoneInfo("Asia/Makassar")).strftime("%Y-%m")

    def _empty(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "timezone": "Asia/Makassar",
            "monthly_ceiling_usd": _money_text(MONTHLY_CEILING_USD),
            "months": {},
        }

    def _load(self) -> dict[str, Any]:
        ledger = load_json(self._path, self._empty())
        if ledger.get("schema_version") != 1:
            raise ValueError("budget_ledger_schema_invalid")
        if ledger.get("timezone") != "Asia/Makassar":
            raise ValueError("budget_ledger_timezone_conflict")
        if ledger.get("monthly_ceiling_usd") != _money_text(MONTHLY_CEILING_USD):
            raise ValueError("budget_ledger_ceiling_conflict")
        if not isinstance(ledger.get("months"), dict):
            raise ValueError("budget_ledger_months_invalid")
        return ledger

    def _month(self, ledger: dict[str, Any], month_id: str) -> dict[str, Any]:
        return ledger["months"].setdefault(
            month_id, {"reservations": {}, "responses": {}}
        )

    def _totals(self, month: dict[str, Any]) -> tuple[Decimal, Decimal]:
        spent = sum(
            (_money(row["exact_cost_usd"]) for row in month["responses"].values()),
            Decimal("0.00"),
        )
        reserved = sum(
            (_money(row["maximum_cost_usd"]) for row in month["reservations"].values()
             if row["status"] == "reserved"),
            Decimal("0.00"),
        )
        return _money(spent), _money(reserved)

    def _locked(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        handle = self._lock_path.open("a+")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return handle

    def state(self) -> BudgetState:
        handle = self._locked()
        try:
            ledger = self._load()
            month_id = self._month_id()
            month = ledger["months"].get(
                month_id, {"reservations": {}, "responses": {}}
            )
            spent, reserved = self._totals(month)
            available = max(Decimal("0.00"), MONTHLY_CEILING_USD - spent - reserved)
            return BudgetState(
                mode="local",
                wita_month=month_id,
                monthly_ceiling_usd=_money_text(MONTHLY_CEILING_USD),
                spent_usd=_money_text(spent),
                reserved_usd=_money_text(reserved),
                available_usd=_money_text(available),
            )
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def reserve(self, request: PaidWorkRequest) -> tuple[WorkOutcome, str, dict[str, Any]]:
        if not isinstance(request.role, PaidRole):
            return WorkOutcome.REJECTED, "paid_role_invalid", {}
        if not request.identity.strip() or not request.provider_key.strip() or not request.model.strip():
            return WorkOutcome.REJECTED, "paid_work_identity_invalid", {}
        maximum = _money(request.maximum_cost_usd)
        if maximum <= 0:
            return WorkOutcome.REJECTED, "reservation_must_be_positive", {}
        month_id = self._month_id()
        request_row = {
            "identity": request.identity,
            "role": request.role.value,
            "provider_key": request.provider_key,
            "model": request.model,
            "maximum_cost_usd": _money_text(maximum),
        }
        reservation_id = "reservation-" + snapshot_hash(
            {"wita_month": month_id, **request_row}
        )[:24]
        handle = self._locked()
        try:
            ledger = self._load()
            month = self._month(ledger, month_id)
            existing = month["reservations"].get(reservation_id)
            if existing:
                comparable = {key: existing[key] for key in request_row}
                if comparable != request_row:
                    return WorkOutcome.REJECTED, "reservation_identity_conflict", {}
                return WorkOutcome.ELIGIBLE, "reservation_already_exists", {
                    "reservation_id": reservation_id,
                    "wita_month": month_id,
                }
            spent, reserved = self._totals(month)
            if spent + reserved + maximum > MONTHLY_CEILING_USD:
                return WorkOutcome.BLOCKED_BY_BUDGET, "monthly_ceiling_exhausted", {}
            month["reservations"][reservation_id] = {
                **request_row,
                "status": "reserved",
                "created_at": self._clock().astimezone(timezone.utc).isoformat(),
            }
            atomic_write_json(self._path, ledger)
            return WorkOutcome.ELIGIBLE, "budget_reserved", {
                "reservation_id": reservation_id,
                "wita_month": month_id,
            }
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def reconcile(self, receipt: CostReceipt) -> tuple[WorkOutcome, str, dict[str, Any]]:
        if not receipt.reservation_id.strip() or not receipt.response_id.strip():
            return WorkOutcome.REJECTED, "cost_receipt_identity_missing", {}
        exact = _money(receipt.exact_cost_usd)
        handle = self._locked()
        try:
            ledger = self._load()
            found_month_id = None
            reservation = None
            for month_id, month in ledger["months"].items():
                existing_response = month["responses"].get(receipt.response_id)
                if existing_response:
                    expected = {
                        "reservation_id": receipt.reservation_id,
                        "exact_cost_usd": _money_text(exact),
                    }
                    if existing_response == expected:
                        return WorkOutcome.ELIGIBLE, "cost_receipt_already_reconciled", {
                            "reservation_id": receipt.reservation_id,
                            "response_id": receipt.response_id,
                        }
                    return WorkOutcome.REJECTED, "cost_response_identity_conflict", {}
                if receipt.reservation_id in month["reservations"]:
                    found_month_id = month_id
                    reservation = month["reservations"][receipt.reservation_id]
            if reservation is None or found_month_id is None:
                return WorkOutcome.REJECTED, "reservation_not_found", {}
            if reservation["status"] == "reconciled":
                return WorkOutcome.REJECTED, "reservation_receipt_conflict", {}
            if exact > _money(reservation["maximum_cost_usd"]):
                return WorkOutcome.REJECTED, "exact_cost_exceeds_reservation", {}
            month = ledger["months"][found_month_id]
            month["responses"][receipt.response_id] = {
                "reservation_id": receipt.reservation_id,
                "exact_cost_usd": _money_text(exact),
            }
            reservation["status"] = "reconciled"
            reservation["response_id"] = receipt.response_id
            atomic_write_json(self._path, ledger)
            return WorkOutcome.ELIGIBLE, "exact_cost_reconciled", {
                "reservation_id": receipt.reservation_id,
                "response_id": receipt.response_id,
            }
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def verifies_evidence_cost(self, response_ids: tuple[str, ...],
                               exact_total: Decimal) -> bool:
        if not response_ids or len(set(response_ids)) != len(response_ids):
            return False
        handle = self._locked()
        try:
            ledger = self._load()
            found: dict[str, Decimal] = {}
            for month in ledger["months"].values():
                for response_id in response_ids:
                    row = month["responses"].get(response_id)
                    if row is not None:
                        if response_id in found:
                            return False
                        found[response_id] = _money(row["exact_cost_usd"])
            return set(found) == set(response_ids) and sum(
                found.values(), Decimal("0")
            ) == _money(exact_total)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()


class _EvidenceLedger:
    """Internal atomic evidence adapter; classifications are derived, never asserted."""

    def __init__(self, path: Path):
        self._path = Path(path)
        self._lock_path = self._path.with_suffix(self._path.suffix + ".lock")

    def _empty(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "evidence": {},
            "consolidations": {},
            "workflows": {"candidates": {}, "audits": {}, "attempts": {}},
            "adoptions": {},
        }

    def _locked(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        handle = self._lock_path.open("a+")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return handle

    def _load(self) -> dict[str, Any]:
        ledger = load_json(self._path, self._empty())
        if ledger.get("schema_version") != 1:
            raise ValueError("evidence_ledger_schema_invalid")
        if not isinstance(ledger.get("evidence"), dict):
            raise ValueError("evidence_rows_invalid")
        if not isinstance(ledger.get("consolidations"), dict):
            raise ValueError("consolidation_rows_invalid")
        ledger.setdefault("adoptions", {})
        if not isinstance(ledger["adoptions"], dict):
            raise ValueError("adoption_rows_invalid")
        ledger.setdefault(
            "workflows", {"candidates": {}, "audits": {}, "attempts": {}}
        )
        if not all(
            isinstance(ledger["workflows"].get(key), dict)
            for key in ("candidates", "audits", "attempts")
        ):
            raise ValueError("workflow_rows_invalid")
        return ledger

    @staticmethod
    def _subject_key(subject_ids: list[str] | tuple[str, ...]) -> str:
        if len(subject_ids) == 1:
            return subject_ids[0]
        return "interaction:" + "+".join(subject_ids)

    def record(self, receipt: EvidenceReceipt | LegacyEvidenceReceipt):
        if not receipt.evidence_id.strip() or not receipt.subject_ids:
            return WorkOutcome.REJECTED, "evidence_identity_missing"
        if any(not item.strip() for item in receipt.subject_ids):
            return WorkOutcome.REJECTED, "evidence_subject_invalid"
        if isinstance(receipt, EvidenceReceipt):
            required = (
                receipt.incumbent_workbook_id, receipt.candidate_workbook_id,
                receipt.task_id, receipt.exact_inputs_hash, receipt.final_artifact_hash,
            )
            if any(not value.strip() for value in required):
                return WorkOutcome.REJECTED, "evidence_binding_missing"
            if (isinstance(receipt.incumbent_total_system_tokens, bool)
                    or isinstance(receipt.candidate_total_system_tokens, bool)
                    or receipt.incumbent_total_system_tokens < 0
                    or receipt.candidate_total_system_tokens < 0):
                return WorkOutcome.REJECTED, "total_system_tokens_invalid"
            if receipt.scope not in {"development", "held_out"}:
                return WorkOutcome.REJECTED, "evidence_scope_invalid"
            for components in (
                receipt.incumbent_token_components,
                receipt.candidate_token_components,
            ):
                if (not isinstance(components, tuple)
                        or any(not isinstance(item, tuple) or len(item) != 2
                               or not isinstance(item[0], str)
                               or not item[0].strip()
                               or isinstance(item[1], bool)
                               or not isinstance(item[1], int)
                               or item[1] < 0 for item in components)):
                    return WorkOutcome.REJECTED, "system_token_components_invalid"
            row = {
                "kind": "matched",
                "evidence_id": receipt.evidence_id,
                "subject_ids": list(receipt.subject_ids),
                "incumbent_workbook_id": receipt.incumbent_workbook_id,
                "candidate_workbook_id": receipt.candidate_workbook_id,
                "task_id": receipt.task_id,
                "exact_inputs_hash": receipt.exact_inputs_hash,
                "incumbent_success": receipt.incumbent_success,
                "candidate_success": receipt.candidate_success,
                "incumbent_total_system_tokens": receipt.incumbent_total_system_tokens,
                "candidate_total_system_tokens": receipt.candidate_total_system_tokens,
                "incumbent_includes_subject": receipt.incumbent_includes_subject,
                "candidate_includes_subject": receipt.candidate_includes_subject,
                "judgment_valid": receipt.judgment_valid,
                "comparable": receipt.comparable,
                "noisy": receipt.noisy,
                "bundled": receipt.bundled,
                "cost_usd": _money_text(receipt.cost_usd),
                "final_artifact_hash": receipt.final_artifact_hash,
                "scope": receipt.scope,
                "incumbent_token_components": [list(item) for item in receipt.incumbent_token_components],
                "candidate_token_components": [list(item) for item in receipt.candidate_token_components],
                "provider_response_ids": list(receipt.provider_response_ids),
                "provider_models": list(receipt.provider_models),
                "cost_response_ids": list(receipt.cost_response_ids),
            }
        else:
            if not receipt.source_kind.strip() or not receipt.source_identity.strip():
                return WorkOutcome.REJECTED, "legacy_evidence_source_missing"
            row = {
                "kind": "historical_noncausal",
                "evidence_id": receipt.evidence_id,
                "subject_ids": list(receipt.subject_ids),
                "source_kind": receipt.source_kind,
                "source_identity": receipt.source_identity,
            }
        handle = self._locked()
        try:
            ledger = self._load()
            existing = ledger["evidence"].get(receipt.evidence_id)
            if existing is not None:
                if existing == row:
                    return WorkOutcome.ELIGIBLE, "evidence_already_recorded"
                return WorkOutcome.REJECTED, "evidence_identity_conflict"
            ledger["evidence"][receipt.evidence_id] = row
            atomic_write_json(self._path, ledger)
            return WorkOutcome.ELIGIBLE, "evidence_recorded"
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def consolidate(self, consolidation: Consolidation):
        if (not consolidation.interaction_group_id.startswith("interaction:")
                or len(consolidation.ordered_source_ids) < 2
                or len(set(consolidation.ordered_source_ids)) != len(consolidation.ordered_source_ids)
                or any(not source.strip() for source in consolidation.ordered_source_ids)
                or not consolidation.candidate_rule_id.strip()
                or not consolidation.candidate_artifact_hash.strip()):
            return WorkOutcome.REJECTED, "consolidation_identity_invalid"
        row = {
            "interaction_group_id": consolidation.interaction_group_id,
            "ordered_source_ids": list(consolidation.ordered_source_ids),
            "candidate_rule_id": consolidation.candidate_rule_id,
            "candidate_artifact_hash": consolidation.candidate_artifact_hash,
        }
        expected_group = self._subject_key(consolidation.ordered_source_ids)
        if consolidation.interaction_group_id != expected_group:
            return WorkOutcome.REJECTED, "interaction_group_identity_mismatch"
        handle = self._locked()
        try:
            ledger = self._load()
            existing = ledger["consolidations"].get(consolidation.interaction_group_id)
            if existing is not None:
                if existing == row:
                    return WorkOutcome.ELIGIBLE, "consolidation_already_recorded"
                return WorkOutcome.REJECTED, "consolidation_identity_conflict"
            ledger["consolidations"][consolidation.interaction_group_id] = row
            atomic_write_json(self._path, ledger)
            return WorkOutcome.ELIGIBLE, "consolidation_recorded"
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    @staticmethod
    def _causal_classification(row: dict[str, Any]) -> Classification | None:
        if (row["kind"] != "matched" or not row["judgment_valid"]
                or not row["comparable"] or row["noisy"]):
            return None
        if row["bundled"] or len(row["subject_ids"]) != 1:
            return Classification.INTERACTING
        incumbent_success = row["incumbent_success"]
        candidate_success = row["candidate_success"]
        if not incumbent_success and not candidate_success:
            return None
        if incumbent_success != candidate_success:
            preferred_includes = (
                row["incumbent_includes_subject"] if incumbent_success
                else row["candidate_includes_subject"]
            )
            return Classification.HELPFUL if preferred_includes else Classification.HARMFUL
        incumbent_tokens = row["incumbent_total_system_tokens"]
        candidate_tokens = row["candidate_total_system_tokens"]
        if incumbent_tokens == candidate_tokens:
            return Classification.REDUNDANT
        preferred_includes = (
            row["candidate_includes_subject"] if candidate_tokens < incumbent_tokens
            else row["incumbent_includes_subject"]
        )
        return Classification.HELPFUL if preferred_includes else Classification.HARMFUL

    def classifications(self) -> dict[str, str]:
        handle = self._locked()
        try:
            ledger = self._load()
            subjects: dict[str, list[Classification]] = {}
            observed: set[str] = set()
            for row in ledger["evidence"].values():
                key = self._subject_key(row["subject_ids"])
                observed.add(key)
                classification = self._causal_classification(row)
                if classification is not None:
                    subjects.setdefault(key, []).append(classification)
            result = {}
            for key in sorted(observed):
                classes = subjects.get(key, [])
                if not classes:
                    result[key] = Classification.UNKNOWN.value
                elif len(set(classes)) == 1:
                    result[key] = classes[0].value
                else:
                    result[key] = Classification.INTERACTING.value
            for key in ledger["consolidations"]:
                result[key] = Classification.INTERACTING.value
            return result
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def has_evidence(self, evidence_id: str) -> bool:
        handle = self._locked()
        try:
            return evidence_id in self._load()["evidence"]
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def evidence_rows(self, evidence_ids: tuple[str, ...]) -> list[dict[str, Any]] | None:
        handle = self._locked()
        try:
            evidence = self._load()["evidence"]
            if any(identity not in evidence for identity in evidence_ids):
                return None
            return [copy.deepcopy(evidence[identity]) for identity in evidence_ids]
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    @staticmethod
    def _adoption_request_row(request: AdoptionRequest) -> dict[str, Any]:
        return {
            "request_id": request.request_id,
            "proposal_id": request.proposal_id,
            "candidate_hash": request.candidate_hash,
            "audit_id": request.audit_id,
            "incumbent_language_version": request.incumbent_language_version,
            "incumbent_language_hash": request.incumbent_language_hash,
            "evidence_ids": list(request.evidence_ids),
        }

    def existing_adoption(self, request: AdoptionRequest):
        handle = self._locked()
        try:
            existing = self._load()["adoptions"].get(request.request_id)
            if existing is None:
                return None
            if existing["request"] != self._adoption_request_row(request):
                return WorkOutcome.REJECTED, "adoption_identity_conflict", {}, None
            return (
                WorkOutcome.ELIGIBLE,
                "adoption_already_recorded",
                copy.deepcopy(existing["receipt"]),
                copy.deepcopy(existing["resulting_rulebook"]),
            )
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def candidate_and_audit(self, proposal_id: str, audit_id: str):
        handle = self._locked()
        try:
            workflows = self._load()["workflows"]
            candidate = workflows["candidates"].get(proposal_id)
            audit = workflows["audits"].get(audit_id)
            return copy.deepcopy(candidate), copy.deepcopy(audit)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def record_adoption(self, request: AdoptionRequest, resulting_rulebook: dict[str, Any],
                        receipt: dict[str, Any]):
        handle = self._locked()
        try:
            ledger = self._load()
            existing = ledger["adoptions"].get(request.request_id)
            request_row = self._adoption_request_row(request)
            if existing is not None:
                if existing["request"] != request_row:
                    return WorkOutcome.REJECTED, "adoption_identity_conflict", {}, None
                return (WorkOutcome.ELIGIBLE, "adoption_already_recorded",
                        copy.deepcopy(existing["receipt"]),
                        copy.deepcopy(existing["resulting_rulebook"]))
            ledger["adoptions"][request.request_id] = {
                "request": request_row,
                "receipt": copy.deepcopy(receipt),
                "resulting_rulebook": copy.deepcopy(resulting_rulebook),
            }
            ledger["workflows"]["candidates"][request.proposal_id]["status"] = "adopted_local"
            atomic_write_json(self._path, ledger)
            return (WorkOutcome.ELIGIBLE, "exact_candidate_adopted",
                    copy.deepcopy(receipt), copy.deepcopy(resulting_rulebook))
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def open_work(self) -> dict[str, Any] | None:
        handle = self._locked()
        try:
            candidates = self._load()["workflows"]["candidates"]
            pending = [row for row in candidates.values() if row["status"] == "awaiting_b_audit"]
            if not pending:
                return None
            row = sorted(pending, key=lambda item: item["proposal_id"])[-1]
            return {
                "kind": "model_candidate",
                "origin": row["origin"],
                "proposal_id": row["proposal_id"],
                "candidate_hash": row["candidate_hash"],
                "status": row["status"],
            }
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def record_model_output(self, output: ModelOutput,
                            candidate_artifact_hash: str | None = None):
        if (output.role not in {"A", "B", "C"} or not output.response_id.strip()
                or not output.returned_model.strip() or not output.finish_reason.strip()):
            return WorkOutcome.REJECTED, "provider_output_identity_invalid", {}
        actual_hash = hashlib.sha256(output.content.encode()).hexdigest()
        if actual_hash != output.content_sha256:
            return WorkOutcome.REJECTED, "provider_output_hash_mismatch", {}
        try:
            payload = json.loads(output.content)
        except json.JSONDecodeError:
            payload = None
        attempt = {
            "role": output.role,
            "response_id": output.response_id,
            "returned_model": output.returned_model,
            "finish_reason": output.finish_reason,
            "content": output.content,
            "content_sha256": output.content_sha256,
            "valid_json": isinstance(payload, dict),
        }
        handle = self._locked()
        try:
            ledger = self._load()
            attempts = ledger["workflows"]["attempts"]
            existing_attempt = attempts.get(output.response_id)
            if existing_attempt is not None and existing_attempt != attempt:
                return WorkOutcome.REJECTED, "provider_response_identity_conflict", {}
            attempts[output.response_id] = attempt
            if not isinstance(payload, dict):
                atomic_write_json(self._path, ledger)
                return WorkOutcome.REJECTED, "model_output_not_json_object", {}
            if output.role == "A":
                result = self._record_a_proposal(
                    ledger, output, payload, candidate_artifact_hash
                )
            elif output.role == "B":
                result = self._record_b_audit(ledger, output, payload)
            else:
                result = self._record_c_candidate(
                    ledger, output, payload, candidate_artifact_hash
                )
            atomic_write_json(self._path, ledger)
            return result
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    @staticmethod
    def _record_a_proposal(ledger, output: ModelOutput, payload: dict[str, Any],
                           candidate_artifact_hash: str | None):
        expected = {
            "proposal_id", "kind", "target_rule_id", "operative_text", "rationale",
            "deliberation", "asserted_authority",
        }
        if set(payload) != expected:
            return WorkOutcome.REJECTED, "a_proposal_schema_invalid", {}
        if (payload["kind"] not in {"PROPOSE", "REPEAL", "REVISE"}
                or not isinstance(payload["proposal_id"], str)
                or not payload["proposal_id"].strip()
                or not isinstance(payload["operative_text"], str)
                or not payload["operative_text"].strip()
                or not isinstance(payload["rationale"], str)
                or not payload["rationale"].strip()
                or not isinstance(payload["deliberation"], str)
                or not payload["deliberation"].strip()):
            return WorkOutcome.REJECTED, "a_proposal_fields_invalid", {}
        if payload["asserted_authority"] != "proposal_only":
            return WorkOutcome.REJECTED, "model_cannot_assert_adoption_authority", {}
        if payload["kind"] == "PROPOSE" and payload["target_rule_id"] is not None:
            return WorkOutcome.REJECTED, "new_proposal_cannot_target_existing_rule", {}
        if payload["kind"] != "PROPOSE" and (
                not isinstance(payload["target_rule_id"], str)
                or not payload["target_rule_id"].strip()):
            return WorkOutcome.REJECTED, "revision_or_repeal_target_required", {}
        if not candidate_artifact_hash:
            return WorkOutcome.REJECTED, "candidate_artifact_invalid", {}
        candidate_hash = candidate_artifact_hash
        row = {
            **payload,
            "origin": "A",
            "candidate_hash": candidate_hash,
            "provider_response_id": output.response_id,
            "provider_model": output.returned_model,
            "provider_content_sha256": output.content_sha256,
            "provider_content": output.content,
            "status": "awaiting_b_audit",
        }
        candidates = ledger["workflows"]["candidates"]
        existing = candidates.get(payload["proposal_id"])
        if existing is not None:
            if existing != row:
                return WorkOutcome.REJECTED, "proposal_identity_conflict", {}
            return WorkOutcome.DEFERRED, "awaiting_mandatory_b_audit", copy.deepcopy(row)
        candidates[payload["proposal_id"]] = row
        return WorkOutcome.DEFERRED, "awaiting_mandatory_b_audit", copy.deepcopy(row)

    @staticmethod
    def _record_b_audit(ledger, output: ModelOutput, payload: dict[str, Any]):
        expected = {
            "audit_id", "proposal_id", "candidate_hash", "decision", "findings",
            "deliberation", "asserted_authority",
        }
        if set(payload) != expected:
            return WorkOutcome.REJECTED, "b_audit_schema_invalid", {}
        string_fields = ("audit_id", "proposal_id", "candidate_hash", "deliberation")
        if (any(not isinstance(payload[field], str) or not payload[field].strip()
                for field in string_fields)
                or payload["decision"] not in {"APPROVE", "REJECT", "DEFER"}
                or not isinstance(payload["findings"], list)
                or any(not isinstance(item, str) or not item.strip()
                       for item in payload["findings"])):
            return WorkOutcome.REJECTED, "b_audit_fields_invalid", {}
        if payload["asserted_authority"] != "audit_only":
            return WorkOutcome.REJECTED, "model_cannot_assert_adoption_authority", {}
        candidate = ledger["workflows"]["candidates"].get(payload["proposal_id"])
        if candidate is None:
            return WorkOutcome.REJECTED, "audit_candidate_not_found", {}
        if candidate["candidate_hash"] != payload["candidate_hash"]:
            return WorkOutcome.REJECTED, "audit_candidate_identity_mismatch", {}
        row = {
            **payload,
            "provider_response_id": output.response_id,
            "provider_model": output.returned_model,
            "provider_content_sha256": output.content_sha256,
            "provider_content": output.content,
        }
        audits = ledger["workflows"]["audits"]
        existing = audits.get(payload["audit_id"])
        if existing is not None and existing != row:
            return WorkOutcome.REJECTED, "audit_identity_conflict", {}
        audits[payload["audit_id"]] = row
        detail = copy.deepcopy(candidate)
        detail["audit"] = copy.deepcopy(row)
        if payload["decision"] == "APPROVE":
            candidate["status"] = "audited_eligible_for_evaluation"
            detail["status"] = candidate["status"]
            return (WorkOutcome.ELIGIBLE,
                    "candidate_audited_and_eligible_for_evaluation", detail)
        if payload["decision"] == "REJECT":
            candidate["status"] = "audit_rejected"
            detail["status"] = candidate["status"]
            return WorkOutcome.REJECTED, "candidate_rejected_by_b_audit", detail
        candidate["status"] = "audit_deferred"
        detail["status"] = candidate["status"]
        return WorkOutcome.DEFERRED, "candidate_deferred_by_b_audit", detail

    @staticmethod
    def _record_c_candidate(ledger, output: ModelOutput, payload: dict[str, Any],
                            candidate_artifact_hash: str | None):
        expected = {
            "proposal_id", "kind", "source_ids", "evidence_links", "source_coverage",
            "operative_rules", "rationale", "deliberation", "asserted_authority",
        }
        if set(payload) != expected:
            return WorkOutcome.REJECTED, "c_candidate_schema_invalid", {}
        if (payload["kind"] not in {"REMOVE", "MERGE", "REWRITE"}
                or not isinstance(payload["proposal_id"], str)
                or not payload["proposal_id"].strip()
                or not isinstance(payload["source_ids"], list)
                or not payload["source_ids"]
                or len(set(payload["source_ids"])) != len(payload["source_ids"])
                or any(not isinstance(item, str) or not item.strip()
                       for item in payload["source_ids"])
                or not isinstance(payload["rationale"], str)
                or not payload["rationale"].strip()
                or not isinstance(payload["deliberation"], str)
                or not payload["deliberation"].strip()):
            return WorkOutcome.REJECTED, "c_candidate_fields_invalid", {}
        if payload["asserted_authority"] != "edit_only":
            return WorkOutcome.REJECTED, "model_cannot_assert_adoption_authority", {}
        sources = payload["source_ids"]
        links = payload["evidence_links"]
        coverage = payload["source_coverage"]
        if (not isinstance(links, dict) or set(links) != set(sources)
                or not isinstance(coverage, dict) or set(coverage) != set(sources)):
            return WorkOutcome.REJECTED, "c_source_evidence_or_coverage_incomplete", {}
        for source_id in sources:
            source_links = links[source_id]
            if (not isinstance(source_links, list) or not source_links
                    or any(not isinstance(item, str) or not item.strip()
                           for item in source_links)):
                return WorkOutcome.REJECTED, "c_evidence_links_invalid", {}
            for evidence_id in source_links:
                evidence = ledger["evidence"].get(evidence_id)
                if evidence is None or source_id not in evidence["subject_ids"]:
                    return WorkOutcome.REJECTED, "c_evidence_link_not_bound_to_source", {}
            destination = coverage[source_id]
            if not isinstance(destination, str) or not destination.strip():
                return WorkOutcome.REJECTED, "c_source_coverage_invalid", {}
        operative = payload["operative_rules"]
        if not isinstance(operative, list):
            return WorkOutcome.REJECTED, "c_operative_rules_invalid", {}
        rule_ids = []
        for rule in operative:
            if (not isinstance(rule, dict) or set(rule) != {"id", "text_en"}
                    or not isinstance(rule["id"], str) or not rule["id"].strip()
                    or not isinstance(rule["text_en"], str) or not rule["text_en"].strip()):
                return WorkOutcome.REJECTED, "c_operative_rules_invalid", {}
            rule_ids.append(rule["id"])
        if len(set(rule_ids)) != len(rule_ids):
            return WorkOutcome.REJECTED, "c_operative_rule_identity_duplicate", {}
        allowed_destinations = set(rule_ids) | {"removed_with_evidence"}
        if any(destination not in allowed_destinations for destination in coverage.values()):
            return WorkOutcome.REJECTED, "c_source_coverage_orphaned", {}
        if payload["kind"] == "REMOVE" and operative:
            return WorkOutcome.REJECTED, "remove_candidate_must_not_add_rules", {}
        if payload["kind"] != "REMOVE" and not operative:
            return WorkOutcome.REJECTED, "merge_or_rewrite_requires_output_rule", {}
        if not candidate_artifact_hash:
            return WorkOutcome.REJECTED, "candidate_artifact_invalid", {}
        candidate_hash = candidate_artifact_hash
        row = {
            **copy.deepcopy(payload),
            "origin": "C",
            "candidate_hash": candidate_hash,
            "provider_response_id": output.response_id,
            "provider_model": output.returned_model,
            "provider_content_sha256": output.content_sha256,
            "provider_content": output.content,
            "status": "awaiting_b_audit",
        }
        candidates = ledger["workflows"]["candidates"]
        existing = candidates.get(payload["proposal_id"])
        if existing is not None:
            if existing != row:
                return WorkOutcome.REJECTED, "proposal_identity_conflict", {}
            return WorkOutcome.DEFERRED, "awaiting_mandatory_b_audit", copy.deepcopy(row)
        candidates[payload["proposal_id"]] = row
        return WorkOutcome.DEFERRED, "awaiting_mandatory_b_audit", copy.deepcopy(row)

    def latest_resulting_rulebook(self) -> dict[str, Any] | None:
        handle = self._locked()
        try:
            adoptions = self._load()["adoptions"]
            if not adoptions:
                return None
            return copy.deepcopy(next(reversed(adoptions.values()))["resulting_rulebook"])
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

class RuleLegislation:
    """Small external seam for all rule-legislation decisions."""

    def __init__(self, rulebook: dict[str, Any], *, mode: str,
                 budget_ledger: _BudgetLedger | None = None,
                 evidence_ledger: _EvidenceLedger | None = None,
                 public_context: dict[str, Any] | None = None):
        if mode not in {"shadow", "local"}:
            raise ValueError("production_activation_requires_human_approval")
        self._rulebook = copy.deepcopy(rulebook)
        self._mode = mode
        self._budget_ledger = budget_ledger
        self._evidence_ledger = evidence_ledger
        self._public_context = copy.deepcopy(public_context or {})

    @classmethod
    def shadow(cls, rulebook: dict[str, Any], *,
               public_context: dict[str, Any] | None = None) -> "RuleLegislation":
        return cls(rulebook, mode="shadow", public_context=public_context)

    @classmethod
    def local(cls, rulebook: dict[str, Any], *, budget_ledger_path: Path,
              evidence_ledger_path: Path | None = None,
              clock=lambda: datetime.now(timezone.utc)) -> "RuleLegislation":
        evidence_ledger = (
            _EvidenceLedger(Path(evidence_ledger_path))
            if evidence_ledger_path is not None else None
        )
        persisted_rulebook = (
            evidence_ledger.latest_resulting_rulebook() if evidence_ledger else None
        )
        return cls(
            persisted_rulebook or rulebook,
            mode="local",
            budget_ledger=_BudgetLedger(Path(budget_ledger_path), clock),
            evidence_ledger=evidence_ledger,
        )

    def snapshot(self) -> LegislationSnapshot:
        payload = language_payload(self._rulebook)
        adopted = AdoptedLanguage(
            version=payload["version"],
            hash=payload["hash"],
            rules=tuple(AdoptedRule(**rule) for rule in payload["rules"]),
        )
        budget = self._budget_ledger.state() if self._budget_ledger else BudgetState(
            mode=self._mode, wita_month=None,
            monthly_ceiling_usd=_money_text(MONTHLY_CEILING_USD),
            spent_usd="0.00", reserved_usd="0.00",
            available_usd=_money_text(MONTHLY_CEILING_USD),
        )
        legislature_identity = snapshot_hash(self._rulebook)
        classifications = (
            self._evidence_ledger.classifications() if self._evidence_ledger else {}
        )
        public_read_model = {
            "schema_version": 1,
            "mode": self._mode,
            "legislation_identity": {
                "version": adopted.version,
                "hash": adopted.hash,
            },
            "adopted_language": {
                "rules": [rule.as_dict() for rule in adopted.rules],
                "text": adopted.render(),
            },
            "complete_legislature_identity": legislature_identity,
            "complete_legislature": copy.deepcopy(self._rulebook.get("rules", [])),
            "roles": {
                "agent_a": "proposer",
                "agent_b": "mandatory_auditor",
                "agent_c": "evidence_guided_editor",
                "authority": "rule_legislation_module",
            },
            "classifications": copy.deepcopy(classifications),
            "budget": {
                "mode": budget.mode,
                "monthly_ceiling_usd": budget.monthly_ceiling_usd,
                "spent_usd": budget.spent_usd,
                "reserved_usd": budget.reserved_usd,
                "available_usd": budget.available_usd,
            },
            "workflow_evidence": copy.deepcopy(
                self._public_context.get("workflow_evidence", [])
            ),
        }
        runtime_status = copy.deepcopy(self._public_context.get("runtime_status"))
        if isinstance(runtime_status, dict):
            runtime_status["legislation_identity"] = copy.deepcopy(
                public_read_model["legislation_identity"]
            )
            public_read_model["runtime_status"] = runtime_status
        workflow_open = self._evidence_ledger.open_work() if self._evidence_ledger else None
        return LegislationSnapshot(
            adopted_language=adopted,
            complete_legislature_identity=legislature_identity,
            open_work=(workflow_open or copy.deepcopy(current_open_motion(self._rulebook))),
            classifications=classifications,
            budget=budget,
            public_read_model=public_read_model,
        )

    def submit_change(self, change: Any) -> WorkResult:
        if isinstance(change, AdoptionRequest) and self._evidence_ledger:
            return self._adopt(change)
        if isinstance(change, ModelOutput) and self._evidence_ledger:
            candidate_hash = None
            if change.role in {"A", "C"}:
                candidate, reason = self._candidate_from_output(change)
                if candidate is None:
                    return WorkResult(WorkOutcome.REJECTED, reason, self.snapshot())
                candidate_hash = language_payload(
                    self._apply_candidate(candidate)
                )["hash"]
            outcome, reason, detail = self._evidence_ledger.record_model_output(
                change, candidate_hash
            )
            return WorkResult(outcome, reason, self.snapshot(), detail)
        if isinstance(change, Consolidation) and self._evidence_ledger:
            outcome, reason = self._evidence_ledger.consolidate(change)
            return WorkResult(outcome, reason, self.snapshot())
        return WorkResult(
            WorkOutcome.DEFERRED,
            "shadow_mode_change_submission_not_yet_available",
            self.snapshot(),
        )

    def _candidate_from_output(self, output: ModelOutput) -> tuple[dict[str, Any] | None, str]:
        try:
            payload = json.loads(output.content)
        except json.JSONDecodeError:
            return None, "model_output_not_json_object"
        if not isinstance(payload, dict):
            return None, "model_output_not_json_object"
        adopted_ids = {
            rule.get("id") for rule in self._rulebook.get("rules", [])
            if rule.get("status") == "adopted"
        }
        all_ids = {rule.get("id") for rule in self._rulebook.get("rules", [])}
        if output.role == "A":
            kind = payload.get("kind")
            target = payload.get("target_rule_id")
            if kind in {"REVISE", "REPEAL"} and target not in adopted_ids:
                return None, "adoption_target_not_currently_adopted"
            return {
                "origin": "A", "kind": kind, "target_rule_id": target,
                "operative_text": payload.get("operative_text"),
                "proposal_id": payload.get("proposal_id"),
                "candidate_hash": "pending-exact-artifact-hash",
            }, "candidate_artifact_ready"
        sources = payload.get("source_ids")
        operative = payload.get("operative_rules")
        if not isinstance(sources, list) or not set(sources).issubset(adopted_ids):
            return None, "c_source_not_currently_adopted"
        if not isinstance(operative, list):
            return None, "c_operative_rules_invalid"
        operative_ids = {
            rule.get("id") for rule in operative if isinstance(rule, dict)
        }
        if None in operative_ids or operative_ids & all_ids:
            return None, "c_operative_rule_identity_conflict"
        return {
            **copy.deepcopy(payload), "origin": "C",
            "candidate_hash": "pending-exact-artifact-hash",
        }, "candidate_artifact_ready"

    def submit_evidence(self, evidence: Any) -> WorkResult:
        if isinstance(evidence, CostReceipt) and self._budget_ledger:
            outcome, reason, detail = self._budget_ledger.reconcile(evidence)
            return WorkResult(outcome, reason, self.snapshot(), detail)
        if isinstance(evidence, (EvidenceReceipt, LegacyEvidenceReceipt)) \
                and self._evidence_ledger:
            if isinstance(evidence, EvidenceReceipt):
                if (not evidence.provider_response_ids
                        or len(evidence.provider_models) != len(evidence.provider_response_ids)
                        or evidence.provider_response_ids != evidence.cost_response_ids
                        or any(not item.strip() for item in (
                            *evidence.provider_response_ids, *evidence.provider_models,
                            *evidence.cost_response_ids,
                        ))):
                    return WorkResult(
                        WorkOutcome.REJECTED,
                        "model_and_cost_receipt_identity_required",
                        self.snapshot(),
                    )
                if not self._budget_ledger or not self._budget_ledger.verifies_evidence_cost(
                        evidence.cost_response_ids, evidence.cost_usd):
                    return WorkResult(
                        WorkOutcome.REJECTED,
                        "evidence_cost_receipt_not_reconciled",
                        self.snapshot(),
                    )
            outcome, reason = self._evidence_ledger.record(evidence)
            return WorkResult(outcome, reason, self.snapshot())
        if self._budget_ledger:
            return WorkResult(
                WorkOutcome.REJECTED,
                "exact_cost_receipt_required",
                self.snapshot(),
            )
        return WorkResult(
            WorkOutcome.DEFERRED,
            "shadow_mode_evidence_submission_not_yet_available",
            self.snapshot(),
        )

    def advance(self, request: Any = None) -> WorkResult:
        if isinstance(request, ExperimentPlanRequest):
            return self._plan_experiment(request)
        if isinstance(request, PaidWorkRequest) and self._budget_ledger:
            outcome, reason, detail = self._budget_ledger.reserve(request)
            return WorkResult(outcome, reason, self.snapshot(), detail)
        return WorkResult(
            WorkOutcome.DEFERRED,
            "shadow_mode_has_no_permitted_work",
            self.snapshot(),
        )

    def _plan_experiment(self, request: ExperimentPlanRequest) -> WorkResult:
        snapshot = self.snapshot()
        question = request.question
        if not self._budget_ledger or not self._evidence_ledger:
            return WorkResult(WorkOutcome.DEFERRED, "planner_adapters_unavailable", snapshot)
        if not question.important:
            return WorkResult(WorkOutcome.DEFERRED, "question_not_important", snapshot)
        if not question.subject_ids or any(not item.strip() for item in question.subject_ids):
            return WorkResult(WorkOutcome.REJECTED, "question_identity_invalid", snapshot)
        subject_key = _EvidenceLedger._subject_key(question.subject_ids)
        classification = snapshot.classifications.get(
            subject_key, Classification.UNKNOWN.value
        )
        if classification not in {
            Classification.UNKNOWN.value, Classification.INTERACTING.value
        }:
            return WorkResult(WorkOutcome.DEFERRED, "question_already_settled", snapshot)

        capable: list[ExperimentCandidate] = []
        refused_reasons: set[str] = set()
        for candidate in request.candidates:
            if candidate.subject_ids != question.subject_ids:
                refused_reasons.add("subject_identity_mismatch")
                continue
            identities = (
                candidate.experiment_id, candidate.evidence_id,
                candidate.incumbent_workbook_id, candidate.candidate_workbook_id,
                candidate.incumbent_inputs_hash, candidate.candidate_inputs_hash,
                candidate.provider_key, candidate.model,
            )
            if any(not value.strip() for value in identities):
                refused_reasons.add("experiment_identity_missing")
                continue
            if candidate.incumbent_inputs_hash != candidate.candidate_inputs_hash:
                refused_reasons.add("experiment_inputs_not_matched")
                continue
            if len(candidate.controlled_variants) != 2 or any(
                    not variant.strip() for variant in candidate.controlled_variants):
                refused_reasons.add("controlled_variants_invalid")
                continue
            if not candidate.expected_decision_impact.strip():
                refused_reasons.add("experiment_unactionable")
                continue
            if not candidate.proof_capable:
                refused_reasons.add("proof_unavailable")
                continue
            if self._evidence_ledger.has_evidence(candidate.evidence_id):
                refused_reasons.add("evidence_already_exists")
                continue
            try:
                if _money(candidate.maximum_cost_usd) <= 0:
                    refused_reasons.add("experiment_cost_invalid")
                    continue
            except (ValueError, ArithmeticError):
                refused_reasons.add("experiment_cost_invalid")
                continue
            capable.append(candidate)
        if not capable:
            reason = sorted(refused_reasons)[0] if refused_reasons else "no_experiment_available"
            return WorkResult(WorkOutcome.DEFERRED, reason, snapshot)

        selected = min(capable, key=lambda row: (_money(row.maximum_cost_usd), row.experiment_id))
        reserved = self._budget_ledger.reserve(PaidWorkRequest(
            identity=selected.experiment_id,
            role=PaidRole.EXPERIMENT,
            provider_key=selected.provider_key,
            model=selected.model,
            maximum_cost_usd=selected.maximum_cost_usd,
        ))
        outcome, reason, reservation = reserved
        if outcome is not WorkOutcome.ELIGIBLE:
            return WorkResult(outcome, reason, self.snapshot())
        detail = {
            "experiment_id": selected.experiment_id,
            "evidence_id": selected.evidence_id,
            "subject_ids": list(selected.subject_ids),
            "incumbent_workbook_id": selected.incumbent_workbook_id,
            "candidate_workbook_id": selected.candidate_workbook_id,
            "controlled_variants": list(selected.controlled_variants),
            "expected_decision_impact": selected.expected_decision_impact,
            "held_out": selected.held_out,
            **reservation,
        }
        return WorkResult(
            WorkOutcome.ELIGIBLE,
            "experiment_planned_and_budget_reserved",
            self.snapshot(),
            detail,
        )

    def _adopt(self, request: AdoptionRequest) -> WorkResult:
        snapshot = self.snapshot()
        fields = (
            request.request_id, request.proposal_id, request.candidate_hash,
            request.audit_id, request.incumbent_language_version,
            request.incumbent_language_hash,
        )
        if any(not field.strip() for field in fields) or not request.evidence_ids:
            return WorkResult(WorkOutcome.REJECTED, "adoption_identity_invalid", snapshot)
        existing = self._evidence_ledger.existing_adoption(request)
        if existing is not None:
            outcome, reason, detail, resulting = existing
            if resulting is not None:
                self._rulebook = resulting
            return WorkResult(outcome, reason, self.snapshot(), detail)
        if (snapshot.adopted_language.version != request.incumbent_language_version
                or snapshot.adopted_language.hash != request.incumbent_language_hash):
            return WorkResult(WorkOutcome.REJECTED, "stale_incumbent_identity", snapshot)
        candidate, audit = self._evidence_ledger.candidate_and_audit(
            request.proposal_id, request.audit_id
        )
        if candidate is None or audit is None:
            return WorkResult(WorkOutcome.DEFERRED, "candidate_or_b_audit_missing", snapshot)
        if (candidate["candidate_hash"] != request.candidate_hash
                or audit["proposal_id"] != request.proposal_id
                or audit["candidate_hash"] != request.candidate_hash):
            return WorkResult(WorkOutcome.REJECTED, "candidate_or_audit_identity_mismatch", snapshot)
        if audit["decision"] != "APPROVE":
            return WorkResult(WorkOutcome.REJECTED, "mandatory_b_audit_not_approved", snapshot)
        rows = self._evidence_ledger.evidence_rows(request.evidence_ids)
        if rows is None:
            return WorkResult(WorkOutcome.DEFERRED, "adoption_evidence_missing", snapshot)
        scopes = {row.get("scope") for row in rows}
        if not {"development", "held_out"}.issubset(scopes):
            return WorkResult(WorkOutcome.DEFERRED, "development_and_heldout_evidence_required", snapshot)
        incumbent_total = 0
        candidate_total = 0
        for row in rows:
            if row["kind"] != "matched" or not row["judgment_valid"]:
                return WorkResult(WorkOutcome.DEFERRED, "valid_judgment_required", snapshot)
            if not row["comparable"] or row["noisy"] or row["bundled"]:
                return WorkResult(WorkOutcome.DEFERRED, "comparable_atomic_evidence_required", snapshot)
            if (row["incumbent_workbook_id"] != request.incumbent_language_hash
                    or row["candidate_workbook_id"] != request.candidate_hash
                    or row["final_artifact_hash"] != request.candidate_hash):
                return WorkResult(WorkOutcome.REJECTED, "evaluated_artifact_identity_drift", snapshot)
            if row["incumbent_success"] and not row["candidate_success"]:
                return WorkResult(WorkOutcome.REJECTED, "candidate_loses_success", snapshot)
            for prefix, total_field in (
                ("incumbent", "incumbent_total_system_tokens"),
                ("candidate", "candidate_total_system_tokens"),
            ):
                components = dict(row[f"{prefix}_token_components"])
                if not {"agent_a", "agent_b"}.issubset(components):
                    return WorkResult(WorkOutcome.DEFERRED, "ab_communication_tokens_required", snapshot)
                if sum(components.values()) != row[total_field]:
                    return WorkResult(WorkOutcome.REJECTED, "system_token_total_conflict", snapshot)
            if row["incumbent_success"]:
                incumbent_total += row["incumbent_total_system_tokens"]
            if row["candidate_success"]:
                candidate_total += row["candidate_total_system_tokens"]
        if candidate_total >= incumbent_total:
            return WorkResult(WorkOutcome.REJECTED, "total_successful_system_tokens_not_lower", snapshot)
        resulting = self._apply_candidate(candidate)
        receipt = {
            "request_id": request.request_id,
            "proposal_id": request.proposal_id,
            "audit_id": request.audit_id,
            "evaluated_artifact_hash": request.candidate_hash,
            "adopted_artifact_hash": request.candidate_hash,
            "incumbent_total_successful_system_tokens": incumbent_total,
            "candidate_total_successful_system_tokens": candidate_total,
            "evidence_ids": list(request.evidence_ids),
            "resulting_adopted_language": language_payload(resulting),
            "mode": "local_not_live",
        }
        outcome, reason, detail, persisted = self._evidence_ledger.record_adoption(
            request, resulting, receipt
        )
        if persisted is not None:
            self._rulebook = persisted
        return WorkResult(outcome, reason, self.snapshot(), detail)

    def _apply_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        result = copy.deepcopy(self._rulebook)
        rules = result.setdefault("rules", [])
        if candidate["origin"] == "A":
            if candidate["kind"] == "PROPOSE":
                next_id = int(result.get("next_id", len(rules) + 1))
                rules.append({
                    "id": f"rule-{next_id:03d}",
                    "text_en": candidate["operative_text"],
                    "status": "adopted",
                    "scores": None,
                    "history": [{
                        "kind": "module_adoption",
                        "proposal_id": candidate["proposal_id"],
                        "candidate_hash": candidate["candidate_hash"],
                    }],
                })
                result["next_id"] = next_id + 1
            else:
                target = next((rule for rule in rules
                               if rule.get("id") == candidate["target_rule_id"]), None)
                if target is None or target.get("status") != "adopted":
                    raise ValueError("adoption_target_not_currently_adopted")
                target.setdefault("history", []).append({
                    "kind": "module_adoption",
                    "proposal_id": candidate["proposal_id"],
                    "candidate_hash": candidate["candidate_hash"],
                    "prior_text_en": target.get("text_en"),
                })
                if candidate["kind"] == "REVISE":
                    target["text_en"] = candidate["operative_text"]
                else:
                    target["status"] = "repealed"
        else:
            sources = set(candidate["source_ids"])
            for rule in rules:
                if rule.get("id") in sources and rule.get("status") == "adopted":
                    rule["status"] = "historical"
                    rule.setdefault("history", []).append({
                        "kind": "module_consolidation",
                        "proposal_id": candidate["proposal_id"],
                        "candidate_hash": candidate["candidate_hash"],
                    })
            for operative in candidate["operative_rules"]:
                rules.append({
                    **copy.deepcopy(operative), "status": "adopted", "scores": None,
                    "history": [{
                        "kind": "module_adoption",
                        "proposal_id": candidate["proposal_id"],
                        "candidate_hash": candidate["candidate_hash"],
                        "source_ids": copy.deepcopy(candidate["source_ids"]),
                    }],
                })
        result["changes"] = int(result.get("changes", 0)) + 1
        return result
