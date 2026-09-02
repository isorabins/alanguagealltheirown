"""Authoritative rule-legislation interface.

Callers read one immutable legislation snapshot, submit typed work, or ask the
module to advance.  Provider, storage, token, and cost adapters remain internal
to this module.  Shadow mode is read-only and cannot reserve spend or adopt.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

from legislative_protocol import current_open_motion
from rulebook import language_payload
from state_store import snapshot_hash


MONTHLY_CEILING_USD = Decimal("30.00")


class WorkOutcome(str, Enum):
    ELIGIBLE = "eligible"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    BLOCKED_BY_BUDGET = "blocked_by_budget"


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


class RuleLegislation:
    """Small external seam for all rule-legislation decisions."""

    def __init__(self, rulebook: dict[str, Any], *, mode: str):
        if mode != "shadow":
            raise ValueError("production_activation_requires_human_approval")
        self._rulebook = copy.deepcopy(rulebook)
        self._mode = mode

    @classmethod
    def shadow(cls, rulebook: dict[str, Any]) -> "RuleLegislation":
        return cls(rulebook, mode="shadow")

    def snapshot(self) -> LegislationSnapshot:
        payload = language_payload(self._rulebook)
        adopted = AdoptedLanguage(
            version=payload["version"],
            hash=payload["hash"],
            rules=tuple(AdoptedRule(**rule) for rule in payload["rules"]),
        )
        budget = BudgetState(
            mode=self._mode,
            wita_month=None,
            monthly_ceiling_usd=str(MONTHLY_CEILING_USD),
            spent_usd="0.00",
            reserved_usd="0.00",
            available_usd=str(MONTHLY_CEILING_USD),
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
        return WorkResult(
            WorkOutcome.DEFERRED,
            "shadow_mode_evidence_submission_not_yet_available",
            self.snapshot(),
        )

    def advance(self) -> WorkResult:
        return WorkResult(
            WorkOutcome.DEFERRED,
            "shadow_mode_has_no_permitted_work",
            self.snapshot(),
        )
