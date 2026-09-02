import copy
import json
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest import mock

import loop
from rule_legislation import (
    CostReceipt,
    PaidRole,
    PaidWorkRequest,
    RuleLegislation,
    WorkOutcome,
)
from rulebook import language_payload


ROOT = Path(__file__).parents[2]


class ShadowLegislationInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.rulebook = json.loads(
            (ROOT / "tests/fixtures/mixed-rulebook.json").read_text()
        )

    def test_shadow_snapshot_matches_canonical_language_without_mutation(self):
        before = copy.deepcopy(self.rulebook)
        module = RuleLegislation.shadow(self.rulebook)

        snapshot = module.snapshot()
        canonical = language_payload(self.rulebook)

        self.assertEqual(snapshot.adopted_language.version, canonical["version"])
        self.assertEqual(snapshot.adopted_language.hash, canonical["hash"])
        self.assertEqual(
            [rule.as_dict() for rule in snapshot.adopted_language.rules],
            canonical["rules"],
        )
        self.assertEqual(snapshot.classifications, {})
        self.assertEqual(snapshot.budget.mode, "shadow")
        self.assertEqual(snapshot.budget.monthly_ceiling_usd, "30.00")
        self.assertEqual(snapshot.public_read_model["legislation_identity"], {
            "version": canonical["version"], "hash": canonical["hash"]
        })
        self.assertEqual(self.rulebook, before)

        self.assertEqual(
            module.submit_change(None).outcome, WorkOutcome.DEFERRED
        )
        self.assertEqual(module.advance().outcome, WorkOutcome.DEFERRED)
        self.assertEqual(self.rulebook, before)

    def test_development_exam_uses_the_same_shadow_snapshot_identity_and_rules(self):
        canonical = language_payload(self.rulebook)
        calls = []

        def fake_call(model, system, user, **kwargs):
            calls.append((model, system, user))
            if len(calls) == 1:
                return "ENCODED", {}
            if len(calls) == 2:
                return "DECODED", {}
            return "{}", {}

        conv = []
        meta = {"tests_run": 0, "spend_usd": 0.0}
        with mock.patch("loop.call", side_effect=fake_call), mock.patch(
            "loop.token_count", side_effect=[10, 5]
        ):
            loop.test_turn(conv, self.rulebook, meta, 3)

        self.assertEqual(conv[-1]["language_version"], canonical["version"])
        self.assertEqual(conv[-1]["language_hash"], canonical["hash"])
        self.assertIn("Adopted alpha meaning.", calls[0][1])
        self.assertNotIn("Proposed beta meaning.", calls[0][1])
        self.assertNotIn("Rejected gamma meaning.", calls[0][1])


class MonthlyBudgetInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.rulebook = json.loads(
            (ROOT / "tests/fixtures/mixed-rulebook.json").read_text()
        )
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.ledger_path = Path(self.tempdir.name) / "budget.json"

    def _module(self, instant="2026-09-30T16:30:00+00:00"):
        now = datetime.fromisoformat(instant)
        return RuleLegislation.local(
            self.rulebook, budget_ledger_path=self.ledger_path, clock=lambda: now
        )

    def _request(self, identity, maximum, *, role=PaidRole.AGENT_A, key="private"):
        return PaidWorkRequest(
            identity=identity,
            role=role,
            provider_key=key,
            model="fixture/model",
            maximum_cost_usd=Decimal(maximum),
        )

    def test_wita_month_rollover_preserves_prior_receipts(self):
        september = self._module("2026-09-30T15:59:59+00:00")
        reserved = september.advance(self._request("sept-call", "30.00"))
        self.assertEqual(reserved.outcome, WorkOutcome.ELIGIBLE)
        september.submit_evidence(CostReceipt(
            reservation_id=reserved.detail["reservation_id"],
            response_id="sept-response",
            exact_cost_usd=Decimal("30.00"),
        ))

        october = self._module("2026-09-30T16:00:00+00:00")
        snapshot = october.snapshot()
        self.assertEqual(snapshot.budget.wita_month, "2026-10")
        self.assertEqual(snapshot.budget.available_usd, "30.00")
        self.assertEqual(october.advance(self._request("oct-call", "30.00")).outcome,
                         WorkOutcome.ELIGIBLE)
        ledger = json.loads(self.ledger_path.read_text())
        self.assertIn("2026-09", ledger["months"])
        self.assertIn("2026-10", ledger["months"])

    def test_roles_and_provider_keys_share_one_hard_ceiling(self):
        module = self._module()
        first = module.advance(self._request(
            "a-private", "20.00", role=PaidRole.AGENT_A, key="private"
        ))
        second = module.advance(self._request(
            "judge-public", "10.00", role=PaidRole.JUDGE, key="public"
        ))
        blocked = module.advance(self._request(
            "c-other", "0.01", role=PaidRole.AGENT_C, key="other"
        ))
        self.assertEqual(first.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(second.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(blocked.outcome, WorkOutcome.BLOCKED_BY_BUDGET)
        self.assertEqual(module.snapshot().budget.available_usd, "0.00")

    def test_concurrent_reservations_cannot_overrun(self):
        barrier = threading.Barrier(2)
        outcomes = []

        def reserve(identity):
            module = self._module()
            barrier.wait()
            outcomes.append(module.advance(self._request(identity, "20.00")).outcome)

        threads = [threading.Thread(target=reserve, args=(f"call-{n}",)) for n in (1, 2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(outcomes.count(WorkOutcome.ELIGIBLE), 1)
        self.assertEqual(outcomes.count(WorkOutcome.BLOCKED_BY_BUDGET), 1)

    def test_exact_receipts_are_idempotent_and_conflicts_fail_closed(self):
        module = self._module()
        reserved = module.advance(self._request("call-1", "5.00"))
        receipt = CostReceipt(
            reservation_id=reserved.detail["reservation_id"],
            response_id="response-1",
            exact_cost_usd=Decimal("3.25"),
        )
        first = module.submit_evidence(receipt)
        duplicate = module.submit_evidence(receipt)
        conflict = module.submit_evidence(CostReceipt(
            reservation_id=reserved.detail["reservation_id"],
            response_id="response-1",
            exact_cost_usd=Decimal("3.26"),
        ))
        missing = module.submit_evidence(CostReceipt(
            reservation_id="missing", response_id="response-2",
            exact_cost_usd=Decimal("1.00"),
        ))
        self.assertEqual(first.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(duplicate.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(conflict.outcome, WorkOutcome.REJECTED)
        self.assertEqual(missing.outcome, WorkOutcome.REJECTED)
        self.assertEqual(module.snapshot().budget.spent_usd, "3.25")

    def test_shadow_mode_and_ordinary_input_cannot_reserve_or_change_cap(self):
        shadow = RuleLegislation.shadow(self.rulebook)
        self.assertEqual(
            shadow.advance(self._request("forbidden", "1.00")).outcome,
            WorkOutcome.DEFERRED,
        )
        self.assertFalse(self.ledger_path.exists())
        with self.assertRaises(TypeError):
            RuleLegislation.local(
                self.rulebook,
                budget_ledger_path=self.ledger_path,
                clock=lambda: datetime.now(timezone.utc),
                monthly_ceiling_usd=Decimal("31.00"),
            )


if __name__ == "__main__":
    unittest.main()
