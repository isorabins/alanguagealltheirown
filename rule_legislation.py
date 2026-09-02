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


class RuleLegislation:
    """Small external seam for all rule-legislation decisions."""

    def __init__(self, rulebook: dict[str, Any], *, mode: str,
                 budget_ledger: _BudgetLedger | None = None):
        if mode not in {"shadow", "local"}:
            raise ValueError("production_activation_requires_human_approval")
        self._rulebook = copy.deepcopy(rulebook)
        self._mode = mode
        self._budget_ledger = budget_ledger

    @classmethod
    def shadow(cls, rulebook: dict[str, Any]) -> "RuleLegislation":
        return cls(rulebook, mode="shadow")

    @classmethod
    def local(cls, rulebook: dict[str, Any], *, budget_ledger_path: Path,
              clock=lambda: datetime.now(timezone.utc)) -> "RuleLegislation":
        return cls(
            rulebook,
            mode="local",
            budget_ledger=_BudgetLedger(Path(budget_ledger_path), clock),
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
            "classifications": {},
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
            classifications={},
            budget=budget,
            public_read_model=public_read_model,
        )

    def submit_change(self, change: Any) -> WorkResult:
        return WorkResult(
            WorkOutcome.DEFERRED,
            "shadow_mode_change_submission_not_yet_available",
            self.snapshot(),
        )

    def submit_evidence(self, evidence: Any) -> WorkResult:
        if isinstance(evidence, CostReceipt) and self._budget_ledger:
            outcome, reason, detail = self._budget_ledger.reconcile(evidence)
            return WorkResult(outcome, reason, self.snapshot(), detail)
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
        if isinstance(request, PaidWorkRequest) and self._budget_ledger:
            outcome, reason, detail = self._budget_ledger.reserve(request)
            return WorkResult(outcome, reason, self.snapshot(), detail)
        return WorkResult(
            WorkOutcome.DEFERRED,
            "shadow_mode_has_no_permitted_work",
            self.snapshot(),
        )
