import copy
import hashlib
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
    Classification,
    Consolidation,
    CostReceipt,
    EvidenceReceipt,
    ExperimentCandidate,
    ExperimentPlanRequest,
    ExperimentQuestion,
    LegacyEvidenceReceipt,
    ModelOutput,
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


class AtomicEvidenceInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.rulebook = json.loads(
            (ROOT / "tests/fixtures/mixed-rulebook.json").read_text()
        )
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = Path(self.tempdir.name)
        self.module = RuleLegislation.local(
            self.rulebook,
            budget_ledger_path=root / "budget.json",
            evidence_ledger_path=root / "evidence.json",
            clock=lambda: datetime.fromisoformat("2026-09-02T04:00:00+00:00"),
        )

    def _receipt(self, evidence_id="e-1", **changes):
        values = dict(
            evidence_id=evidence_id,
            subject_ids=("rule-001",),
            incumbent_workbook_id="workbook-with-rule",
            candidate_workbook_id="workbook-without-rule",
            task_id="matched-task-1",
            exact_inputs_hash="inputs-1",
            incumbent_success=True,
            candidate_success=True,
            incumbent_total_system_tokens=120,
            candidate_total_system_tokens=100,
            incumbent_includes_subject=True,
            candidate_includes_subject=False,
            judgment_valid=True,
            comparable=True,
            noisy=False,
            bundled=False,
            cost_usd=Decimal("0.20"),
            final_artifact_hash="artifact-1",
        )
        values.update(changes)
        return EvidenceReceipt(**values)

    def test_atomic_evidence_classifies_only_the_bound_rule(self):
        result = self.module.submit_evidence(self._receipt())
        self.assertEqual(result.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(
            result.snapshot.classifications,
            {"rule-001": Classification.HARMFUL.value},
        )
        self.assertNotIn("rule-002", result.snapshot.classifications)

    def test_bundled_invalid_or_incomparable_evidence_cannot_claim_causality(self):
        bundled = self.module.submit_evidence(self._receipt(
            "e-bundle", subject_ids=("rule-001", "rule-002"), bundled=True
        ))
        self.assertEqual(
            bundled.snapshot.classifications["interaction:rule-001+rule-002"],
            Classification.INTERACTING.value,
        )
        invalid = self.module.submit_evidence(self._receipt(
            "e-invalid", judgment_valid=False
        ))
        self.assertEqual(
            invalid.snapshot.classifications["rule-001"],
            Classification.UNKNOWN.value,
        )
        incomparable = self.module.submit_evidence(self._receipt(
            "e-incomparable", comparable=False
        ))
        self.assertEqual(
            incomparable.snapshot.classifications["rule-001"],
            Classification.UNKNOWN.value,
        )

    def test_duplicate_evidence_is_idempotent_and_conflict_fails_closed(self):
        receipt = self._receipt()
        self.assertEqual(self.module.submit_evidence(receipt).outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(self.module.submit_evidence(receipt).reason, "evidence_already_recorded")
        conflict = self.module.submit_evidence(self._receipt(
            candidate_total_system_tokens=99
        ))
        self.assertEqual(conflict.outcome, WorkOutcome.REJECTED)
        self.assertEqual(
            conflict.snapshot.classifications["rule-001"],
            Classification.HARMFUL.value,
        )

    def test_revision_keeps_rule_identity_and_consolidation_keeps_sources(self):
        revised = self._receipt("revision-evidence", final_artifact_hash="revision-hash")
        self.module.submit_evidence(revised)
        consolidated = self.module.submit_change(Consolidation(
            interaction_group_id="interaction:rule-001+rule-002",
            ordered_source_ids=("rule-001", "rule-002"),
            candidate_rule_id="rule-005",
            candidate_artifact_hash="merged-hash",
        ))
        self.assertEqual(consolidated.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(
            consolidated.snapshot.classifications["interaction:rule-001+rule-002"],
            Classification.INTERACTING.value,
        )
        self.assertIn("rule-001", consolidated.snapshot.classifications)

    def test_historical_scores_import_as_noncausal_unknown(self):
        imported = self.module.submit_evidence(LegacyEvidenceReceipt(
            evidence_id="legacy-score-rule-001",
            subject_ids=("rule-001",),
            source_kind="historical_rule_score",
            source_identity="turn-100-score",
        ))
        self.assertEqual(imported.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(
            imported.snapshot.classifications["rule-001"],
            Classification.UNKNOWN.value,
        )


class ExperimentPlannerInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.rulebook = json.loads(
            (ROOT / "tests/fixtures/mixed-rulebook.json").read_text()
        )
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = Path(self.tempdir.name)
        self.module = RuleLegislation.local(
            self.rulebook,
            budget_ledger_path=root / "budget.json",
            evidence_ledger_path=root / "evidence.json",
            clock=lambda: datetime.fromisoformat("2026-09-02T04:00:00+00:00"),
        )

    def _candidate(self, identity, cost, **changes):
        values = dict(
            experiment_id=identity,
            evidence_id=f"evidence-{identity}",
            subject_ids=("rule-002",),
            incumbent_workbook_id="incumbent-1",
            candidate_workbook_id="candidate-1",
            incumbent_inputs_hash="same-inputs",
            candidate_inputs_hash="same-inputs",
            controlled_variants=("without-rule-002", "with-rule-002"),
            expected_decision_impact="adopt_or_reject_rule-002",
            proof_capable=True,
            held_out=False,
            maximum_cost_usd=Decimal(cost),
            provider_key="private",
            model="fixture/model",
        )
        values.update(changes)
        return ExperimentCandidate(**values)

    def _request(self, *candidates, important=True, subject_ids=("rule-002",)):
        return ExperimentPlanRequest(
            question=ExperimentQuestion(subject_ids=subject_ids, important=important),
            candidates=tuple(candidates),
        )

    def test_selects_cheapest_capable_matched_experiment_and_reserves_it(self):
        result = self.module.advance(self._request(
            self._candidate("expensive", "2.00"),
            self._candidate("cheap", "0.50"),
        ))
        self.assertEqual(result.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(result.detail["experiment_id"], "cheap")
        self.assertEqual(result.snapshot.budget.reserved_usd, "0.50")
        self.assertNotIn("same-inputs", json.dumps(result.detail))

    def test_refuses_unequal_unactionable_or_unavailable_proof_without_spend(self):
        cases = (
            self._candidate("unequal", "0.10", candidate_inputs_hash="different"),
            self._candidate("unactionable", "0.10", expected_decision_impact=""),
            self._candidate("unavailable", "0.10", proof_capable=False),
        )
        for candidate in cases:
            with self.subTest(candidate=candidate.experiment_id):
                result = self.module.advance(self._request(candidate))
                self.assertEqual(result.outcome, WorkOutcome.DEFERRED)
        self.assertEqual(self.module.snapshot().budget.reserved_usd, "0.00")

    def test_refuses_unimportant_settled_repeated_and_over_budget_questions(self):
        unimportant = self.module.advance(self._request(
            self._candidate("unimportant", "0.10"), important=False
        ))
        self.assertEqual(unimportant.outcome, WorkOutcome.DEFERRED)

        self.module.submit_evidence(EvidenceReceipt(
            evidence_id="evidence-settled", subject_ids=("rule-001",),
            incumbent_workbook_id="with", candidate_workbook_id="without",
            task_id="task", exact_inputs_hash="inputs",
            incumbent_success=True, candidate_success=True,
            incumbent_total_system_tokens=100, candidate_total_system_tokens=90,
            incumbent_includes_subject=True, candidate_includes_subject=False,
            judgment_valid=True, comparable=True, noisy=False, bundled=False,
            cost_usd=Decimal("0.01"), final_artifact_hash="artifact",
        ))
        settled = self.module.advance(self._request(
            self._candidate("settled", "0.10", subject_ids=("rule-001",)),
            subject_ids=("rule-001",),
        ))
        self.assertEqual(settled.outcome, WorkOutcome.DEFERRED)

        recorded = self.module.submit_evidence(EvidenceReceipt(
            evidence_id="evidence-repeat", subject_ids=("rule-003",),
            incumbent_workbook_id="a", candidate_workbook_id="b", task_id="task",
            exact_inputs_hash="repeat", incumbent_success=False,
            candidate_success=False, incumbent_total_system_tokens=10,
            candidate_total_system_tokens=10, incumbent_includes_subject=True,
            candidate_includes_subject=False, judgment_valid=False,
            comparable=True, noisy=False, bundled=False, cost_usd=Decimal("0.01"),
            final_artifact_hash="artifact-repeat",
        ))
        self.assertEqual(recorded.outcome, WorkOutcome.ELIGIBLE)
        repeated = self.module.advance(self._request(
            self._candidate("repeat", "0.10", evidence_id="evidence-repeat",
                            subject_ids=("rule-003",)),
            subject_ids=("rule-003",),
        ))
        self.assertEqual(repeated.outcome, WorkOutcome.DEFERRED)

        over = self.module.advance(self._request(self._candidate("over", "30.01")))
        self.assertEqual(over.outcome, WorkOutcome.BLOCKED_BY_BUDGET)

    def test_interaction_question_requires_the_exact_group(self):
        result = self.module.advance(self._request(
            self._candidate("group", "0.20", subject_ids=("rule-001", "rule-002")),
            subject_ids=("rule-001", "rule-002"),
        ))
        self.assertEqual(result.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(result.detail["subject_ids"], ["rule-001", "rule-002"])


class AgentABWorkflowInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.rulebook = json.loads(
            (ROOT / "tests/fixtures/mixed-rulebook.json").read_text()
        )
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = Path(self.tempdir.name)
        self.module = RuleLegislation.local(
            self.rulebook,
            budget_ledger_path=root / "budget.json",
            evidence_ledger_path=root / "evidence.json",
            clock=lambda: datetime.fromisoformat("2026-09-02T04:00:00+00:00"),
        )

    def _output(self, role, response_id, payload):
        content = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        return ModelOutput(
            role=role,
            response_id=response_id,
            returned_model=f"fixture/{role.lower()}",
            finish_reason="stop",
            content=content,
            content_sha256=hashlib.sha256(content.encode()).hexdigest(),
        )

    def _proposal(self, **changes):
        payload = {
            "proposal_id": "proposal-a-1",
            "kind": "PROPOSE",
            "target_rule_id": None,
            "operative_text": "Use !ok for a confirmed successful result.",
            "rationale": "This may reduce repeated confirmation language.",
            "deliberation": "Agent A proposes a focused measurable shorthand.",
            "asserted_authority": "proposal_only",
        }
        payload.update(changes)
        return self._output("A", "response-a-1", payload)

    def _audit(self, candidate_hash, **changes):
        payload = {
            "audit_id": "audit-b-1",
            "proposal_id": "proposal-a-1",
            "candidate_hash": candidate_hash,
            "decision": "APPROVE",
            "findings": ["The proposal is focused and testable."],
            "deliberation": "Agent B audits the exact candidate and approves testing.",
            "asserted_authority": "audit_only",
        }
        payload.update(changes)
        return self._output("B", "response-b-1", payload)

    def test_a_proposal_is_visible_but_requires_identity_bound_b_audit(self):
        proposed = self.module.submit_change(self._proposal())
        self.assertEqual(proposed.outcome, WorkOutcome.DEFERRED)
        self.assertEqual(proposed.reason, "awaiting_mandatory_b_audit")
        self.assertEqual(proposed.detail["origin"], "A")
        self.assertEqual(
            proposed.detail["operative_text"],
            "Use !ok for a confirmed successful result.",
        )
        before_hash = proposed.snapshot.adopted_language.hash

        audited = self.module.submit_change(
            self._audit(proposed.detail["candidate_hash"])
        )
        self.assertEqual(audited.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(audited.reason, "candidate_audited_and_eligible_for_evaluation")
        self.assertEqual(audited.snapshot.adopted_language.hash, before_hash)
        self.assertEqual(audited.detail["audit"]["decision"], "APPROVE")

    def test_missing_stale_malformed_or_rejecting_audit_fails_closed(self):
        proposed = self.module.submit_change(self._proposal())
        before = proposed.snapshot.adopted_language.hash
        stale = self.module.submit_change(self._audit("wrong-hash"))
        self.assertEqual(stale.outcome, WorkOutcome.REJECTED)
        malformed = self.module.submit_change(ModelOutput(
            role="B", response_id="malformed-b", returned_model="fixture/b",
            finish_reason="stop", content="not json",
            content_sha256=hashlib.sha256(b"not json").hexdigest(),
        ))
        self.assertEqual(malformed.outcome, WorkOutcome.REJECTED)
        rejected = self.module.submit_change(self._audit(
            proposed.detail["candidate_hash"], decision="REJECT",
            audit_id="audit-b-2",
        ))
        self.assertEqual(rejected.outcome, WorkOutcome.REJECTED)
        self.assertEqual(rejected.snapshot.adopted_language.hash, before)

    def test_model_claim_of_direct_authority_and_fabricated_content_hash_are_rejected(self):
        direct = self.module.submit_change(self._proposal(asserted_authority="adopted"))
        self.assertEqual(direct.outcome, WorkOutcome.REJECTED)
        fabricated = self._proposal()
        fabricated = ModelOutput(
            role=fabricated.role, response_id="fabricated", returned_model=fabricated.returned_model,
            finish_reason=fabricated.finish_reason, content=fabricated.content,
            content_sha256="0" * 64,
        )
        self.assertEqual(self.module.submit_change(fabricated).outcome, WorkOutcome.REJECTED)

    def test_shadow_mode_never_persists_or_makes_a_candidate_eligible(self):
        shadow = RuleLegislation.shadow(self.rulebook)
        result = shadow.submit_change(self._proposal())
        self.assertEqual(result.outcome, WorkOutcome.DEFERRED)
        self.assertEqual(result.snapshot.adopted_language.hash, language_payload(self.rulebook)["hash"])


if __name__ == "__main__":
    unittest.main()
