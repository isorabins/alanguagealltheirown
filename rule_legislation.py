"""Authoritative rule-legislation interface.

Callers read one immutable legislation snapshot, submit typed work, or ask the
module to advance.  Provider, storage, token, and cost adapters remain internal
to this module.  Shadow mode is read-only and cannot reserve spend or adopt.
"""
from __future__ import annotations

import copy
import fcntl
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
    return amount.quantize(Decimal("0.01"))


def _money_text(value: Decimal | str | int) -> str:
    return f"{_money(value):.2f}"


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


class _EvidenceLedger:
    """Internal atomic evidence adapter; classifications are derived, never asserted."""

    def __init__(self, path: Path):
        self._path = Path(path)
        self._lock_path = self._path.with_suffix(self._path.suffix + ".lock")

    def _empty(self) -> dict[str, Any]:
        return {"schema_version": 1, "evidence": {}, "consolidations": {}}

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

class RuleLegislation:
    """Small external seam for all rule-legislation decisions."""

    def __init__(self, rulebook: dict[str, Any], *, mode: str,
                 budget_ledger: _BudgetLedger | None = None,
                 evidence_ledger: _EvidenceLedger | None = None):
        if mode not in {"shadow", "local"}:
            raise ValueError("production_activation_requires_human_approval")
        self._rulebook = copy.deepcopy(rulebook)
        self._mode = mode
        self._budget_ledger = budget_ledger
        self._evidence_ledger = evidence_ledger

    @classmethod
    def shadow(cls, rulebook: dict[str, Any]) -> "RuleLegislation":
        return cls(rulebook, mode="shadow")

    @classmethod
    def local(cls, rulebook: dict[str, Any], *, budget_ledger_path: Path,
              evidence_ledger_path: Path | None = None,
              clock=lambda: datetime.now(timezone.utc)) -> "RuleLegislation":
        return cls(
            rulebook,
            mode="local",
            budget_ledger=_BudgetLedger(Path(budget_ledger_path), clock),
            evidence_ledger=(
                _EvidenceLedger(Path(evidence_ledger_path))
                if evidence_ledger_path is not None else None
            ),
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
            },
            "complete_legislature_identity": legislature_identity,
            "classifications": copy.deepcopy(classifications),
            "budget": {
                "mode": budget.mode,
                "monthly_ceiling_usd": budget.monthly_ceiling_usd,
                "spent_usd": budget.spent_usd,
                "reserved_usd": budget.reserved_usd,
                "available_usd": budget.available_usd,
            },
        }
        return LegislationSnapshot(
            adopted_language=adopted,
            complete_legislature_identity=legislature_identity,
            open_work=copy.deepcopy(current_open_motion(self._rulebook)),
            classifications=classifications,
            budget=budget,
            public_read_model=public_read_model,
        )

    def submit_change(self, change: Any) -> WorkResult:
        if isinstance(change, Consolidation) and self._evidence_ledger:
            outcome, reason = self._evidence_ledger.consolidate(change)
            return WorkResult(outcome, reason, self.snapshot())
        return WorkResult(
            WorkOutcome.DEFERRED,
            "shadow_mode_change_submission_not_yet_available",
            self.snapshot(),
        )

    def submit_evidence(self, evidence: Any) -> WorkResult:
        if isinstance(evidence, CostReceipt) and self._budget_ledger:
            outcome, reason, detail = self._budget_ledger.reconcile(evidence)
            return WorkResult(outcome, reason, self.snapshot(), detail)
        if isinstance(evidence, (EvidenceReceipt, LegacyEvidenceReceipt)) \
                and self._evidence_ledger:
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
