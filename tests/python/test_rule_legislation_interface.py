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
    AdoptionRequest,
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


def _fixture_receipt_bindings(module, identity, cost):
    response_id = f"provider-{identity}"
    reserved = module.advance(PaidWorkRequest(
        identity=f"paid-{identity}", role=PaidRole.EXPERIMENT,
        provider_key="fixture-key", model="fixture/evaluator",
        maximum_cost_usd=Decimal(cost),
    ))
    reconciled = module.submit_evidence(CostReceipt(
        reservation_id=reserved.detail["reservation_id"],
        response_id=response_id, exact_cost_usd=Decimal(cost),
        returned_model="fixture/evaluator",
    ))
    if reconciled.outcome is not WorkOutcome.ELIGIBLE:
        raise AssertionError(reconciled.reason)
    return {
        "provider_response_ids": (response_id,),
        "provider_models": ("fixture/evaluator",),
        "cost_response_ids": (response_id,),
    }


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

    def test_public_read_model_is_complete_and_version_bound(self):
        runtime = {"status": "paused", "turn": 10}
        snapshot = RuleLegislation.shadow(
            self.rulebook, public_context={"runtime_status": runtime}
        ).snapshot()
        model = snapshot.public_read_model
        self.assertEqual(model["legislation_identity"], {
            "version": snapshot.adopted_language.version,
            "hash": snapshot.adopted_language.hash,
        })
        self.assertEqual(len(model["complete_legislature"]), 4)
        self.assertEqual(model["roles"], {
            "agent_a": "proposer",
            "agent_b": "mandatory_auditor",
            "agent_c": "evidence_guided_editor",
            "authority": "rule_legislation_module",
        })
        self.assertEqual(model["runtime_status"]["legislation_identity"],
                         model["legislation_identity"])
        self.assertEqual(model["budget"]["monthly_ceiling_usd"], "30.00")


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
            returned_model="fixture/model",
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
            returned_model="fixture/model",
        )
        first = module.submit_evidence(receipt)
        duplicate = module.submit_evidence(receipt)
        conflict = module.submit_evidence(CostReceipt(
            reservation_id=reserved.detail["reservation_id"],
            response_id="response-1",
            exact_cost_usd=Decimal("3.26"),
            returned_model="fixture/model",
        ))
        missing = module.submit_evidence(CostReceipt(
            reservation_id="missing", response_id="response-2",
            exact_cost_usd=Decimal("1.00"),
            returned_model="fixture/model",
        ))
        self.assertEqual(first.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(duplicate.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(conflict.outcome, WorkOutcome.REJECTED)
        self.assertEqual(missing.outcome, WorkOutcome.REJECTED)
        self.assertEqual(module.snapshot().budget.spent_usd, "3.25")

        model_reservation = module.advance(self._request("model-call", "1.00"))
        model_mismatch = module.submit_evidence(CostReceipt(
            reservation_id=model_reservation.detail["reservation_id"],
            response_id="model-response", exact_cost_usd=Decimal("0.50"),
            returned_model="fixture/other-model",
        ))
        self.assertEqual(model_mismatch.reason, "returned_model_mismatch")

    def test_exact_receipt_preserves_provider_fractional_precision(self):
        module = self._module()
        reserved = module.advance(self._request("fractional-call", "0.10"))
        result = module.submit_evidence(CostReceipt(
            reservation_id=reserved.detail["reservation_id"],
            response_id="fractional-response",
            exact_cost_usd=Decimal("0.012345678901"),
            returned_model="fixture/model",
        ))

        self.assertEqual(result.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(result.snapshot.budget.spent_usd, "0.012345678901")
        ledger = json.loads(self.ledger_path.read_text())
        self.assertEqual(
            ledger["months"]["2026-10"]["responses"]["fractional-response"]
            ["exact_cost_usd"],
            "0.012345678901",
        )

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
            **_fixture_receipt_bindings(self.module, evidence_id, "0.20"),
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

    def test_matched_evidence_requires_reconciled_model_and_cost_receipts(self):
        receipt = self._receipt("e-forged")
        forged = EvidenceReceipt(**{
            **receipt.__dict__,
            "provider_response_ids": ("missing-provider-response",),
            "cost_response_ids": ("missing-provider-response",),
        })
        missing_model = EvidenceReceipt(**{
            **receipt.__dict__,
            "provider_response_ids": (),
            "provider_models": (),
        })
        wrong_model = EvidenceReceipt(**{
            **receipt.__dict__,
            "provider_models": ("fixture/other-model",),
        })
        self.assertEqual(
            self.module.submit_evidence(forged).reason,
            "evidence_cost_receipt_not_reconciled",
        )
        self.assertEqual(
            self.module.submit_evidence(missing_model).reason,
            "model_and_cost_receipt_identity_required",
        )
        self.assertEqual(
            self.module.submit_evidence(wrong_model).reason,
            "evidence_cost_receipt_not_reconciled",
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
            **_fixture_receipt_bindings(self.module, "evidence-settled", "0.01"),
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
            **_fixture_receipt_bindings(self.module, "evidence-repeat", "0.01"),
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

    def test_malformed_a_object_is_reason_coded_not_raised(self):
        result = self.module.submit_change(self._output("A", "response-a-empty", {}))
        self.assertEqual(result.outcome, WorkOutcome.REJECTED)
        self.assertEqual(result.reason, "a_proposal_schema_invalid")

        unhashable_target = self.module.submit_change(self._proposal(
            kind="REVISE", target_rule_id={"malformed": "target"},
        ))
        self.assertEqual(unhashable_target.outcome, WorkOutcome.REJECTED)
        self.assertEqual(
            unhashable_target.reason, "revision_or_repeal_target_required",
        )

    def test_shadow_mode_never_persists_or_makes_a_candidate_eligible(self):
        shadow = RuleLegislation.shadow(self.rulebook)
        result = shadow.submit_change(self._proposal())
        self.assertEqual(result.outcome, WorkOutcome.DEFERRED)
        self.assertEqual(result.snapshot.adopted_language.hash, language_payload(self.rulebook)["hash"])


class AgentCBWorkflowInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.rulebook = json.loads(
            (ROOT / "tests/fixtures/mixed-rulebook.json").read_text()
        )
        next(rule for rule in self.rulebook["rules"]
             if rule["id"] == "rule-002")["status"] = "adopted"
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = Path(self.tempdir.name)
        self.module = RuleLegislation.local(
            self.rulebook,
            budget_ledger_path=root / "budget.json",
            evidence_ledger_path=root / "evidence.json",
            clock=lambda: datetime.fromisoformat("2026-09-02T04:00:00+00:00"),
        )
        for rule_id in ("rule-001", "rule-002"):
            self.module.submit_evidence(LegacyEvidenceReceipt(
                evidence_id=f"evidence-{rule_id}", subject_ids=(rule_id,),
                source_kind="historical_rule_score", source_identity=f"history-{rule_id}",
            ))

    def _output(self, role, response_id, payload):
        content = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        return ModelOutput(
            role=role, response_id=response_id, returned_model=f"fixture/{role.lower()}",
            finish_reason="stop", content=content,
            content_sha256=hashlib.sha256(content.encode()).hexdigest(),
        )

    def _candidate(self, response_id="response-c-1", **changes):
        payload = {
            "proposal_id": "candidate-c-1",
            "kind": "MERGE",
            "source_ids": ["rule-001", "rule-002"],
            "evidence_links": {
                "rule-001": ["evidence-rule-001"],
                "rule-002": ["evidence-rule-002"],
            },
            "source_coverage": {
                "rule-001": "merged-001",
                "rule-002": "merged-001",
            },
            "operative_rules": [{
                "id": "merged-001", "text_en": "Use !ok for confirmed success."
            }],
            "rationale": "Evidence suggests the meanings should be tested together.",
            "deliberation": "Agent C proposes one evidence-linked merge.",
            "asserted_authority": "edit_only",
        }
        payload.update(changes)
        return self._output("C", response_id, payload)

    def _audit(self, candidate_hash, **changes):
        payload = {
            "audit_id": "audit-c-b-1", "proposal_id": "candidate-c-1",
            "candidate_hash": candidate_hash, "decision": "APPROVE",
            "findings": ["Every source has an evidence link and coverage."],
            "deliberation": "Agent B audits the exact C artifact.",
            "asserted_authority": "audit_only",
        }
        payload.update(changes)
        return self._output("B", "response-c-b-1", payload)

    def test_c_edit_requires_evidence_for_every_source_and_exact_b_audit(self):
        candidate = self.module.submit_change(self._candidate())
        self.assertEqual(candidate.outcome, WorkOutcome.DEFERRED)
        self.assertEqual(candidate.detail["origin"], "C")
        self.assertEqual(candidate.reason, "awaiting_mandatory_b_audit")
        audited = self.module.submit_change(self._audit(candidate.detail["candidate_hash"]))
        self.assertEqual(audited.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(
            audited.reason, "candidate_audited_and_eligible_for_evaluation"
        )
        self.assertEqual(
            audited.snapshot.adopted_language.hash, language_payload(self.rulebook)["hash"]
        )

    def test_uncited_or_uncovered_c_edits_and_direct_authority_are_rejected(self):
        uncited = self.module.submit_change(self._candidate(
            evidence_links={"rule-001": ["evidence-rule-001"]}
        ))
        self.assertEqual(uncited.outcome, WorkOutcome.REJECTED)
        uncovered = self.module.submit_change(self._candidate(
            source_coverage={"rule-001": "merged-001"}
        ))
        self.assertEqual(uncovered.outcome, WorkOutcome.REJECTED)
        direct = self.module.submit_change(self._candidate(asserted_authority="adopted"))
        self.assertEqual(direct.outcome, WorkOutcome.REJECTED)

    def test_c_edit_rejects_nonadopted_sources_and_colliding_output_ids(self):
        missing = self.module.submit_change(self._candidate(
            response_id="response-c-missing",
            proposal_id="candidate-c-missing",
            source_ids=["rule-001", "rule-999"],
        ))
        colliding = self.module.submit_change(self._candidate(
            response_id="response-c-collision",
            proposal_id="candidate-c-collision",
            operative_rules=[{"id": "rule-001", "text_en": "Collision."}],
        ))
        self.assertEqual(missing.reason, "c_source_not_currently_adopted")
        self.assertEqual(colliding.reason, "c_operative_rule_identity_conflict")

        malformed = self.module.submit_change(self._output(
            "C", "response-c-malformed", {
                "proposal_id": "candidate-c-malformed", "kind": "MERGE",
                "source_ids": [{"not": "hashable"}], "evidence_links": {},
                "source_coverage": {}, "operative_rules": [],
                "rationale": "Malformed fixture.", "deliberation": "Fixture.",
                "asserted_authority": "edit_only",
            },
        ))
        self.assertEqual(malformed.reason, "c_candidate_fields_invalid")

    def test_prior_audit_cannot_authorize_a_finalized_or_drifted_artifact(self):
        first = self.module.submit_change(self._candidate())
        self.module.submit_change(self._audit(first.detail["candidate_hash"]))
        drifted = self.module.submit_change(self._candidate(
            response_id="response-c-final", proposal_id="candidate-c-final", operative_rules=[{
                "id": "merged-001", "text_en": "Use !confirmed for confirmed success."
            }]
        ))
        self.assertEqual(drifted.outcome, WorkOutcome.DEFERRED)
        stale_audit = self.module.submit_change(self._audit(
            first.detail["candidate_hash"], proposal_id="candidate-c-final",
            audit_id="audit-stale-final",
        ))
        self.assertEqual(stale_audit.outcome, WorkOutcome.REJECTED)


class ExactArtifactAdoptionInterfaceTests(unittest.TestCase):
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
        self.budget_path = root / "budget.json"
        self.evidence_path = root / "evidence.json"
        proposal_payload = {
            "proposal_id": "proposal-adopt", "kind": "PROPOSE",
            "target_rule_id": None, "operative_text": "Use !ok for confirmed success.",
            "rationale": "Reduce repeated confirmation language.",
            "deliberation": "Agent A proposes one focused rule.",
            "asserted_authority": "proposal_only",
        }
        self.proposal = self._output("A", "response-adopt-a", proposal_payload)
        proposed = self.module.submit_change(self.proposal)
        self.candidate_hash = proposed.detail["candidate_hash"]
        audit_payload = {
            "audit_id": "audit-adopt-b", "proposal_id": "proposal-adopt",
            "candidate_hash": self.candidate_hash, "decision": "APPROVE",
            "findings": ["Focused and testable."],
            "deliberation": "Agent B audits the exact proposal.",
            "asserted_authority": "audit_only",
        }
        self.module.submit_change(self._output("B", "response-adopt-b", audit_payload))
        self.incumbent = language_payload(self.rulebook)

    def _output(self, role, response_id, payload):
        content = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        return ModelOutput(
            role=role, response_id=response_id, returned_model=f"fixture/{role.lower()}",
            finish_reason="stop", content=content,
            content_sha256=hashlib.sha256(content.encode()).hexdigest(),
        )

    def _evidence(self, evidence_id, scope, *, candidate_success=True,
                  candidate_tokens=100, judgment_valid=True,
                  final_artifact_hash=None, comparable=True):
        return EvidenceReceipt(
            evidence_id=evidence_id, subject_ids=("rule-005",),
            incumbent_workbook_id=self.incumbent["hash"],
            candidate_workbook_id=self.candidate_hash,
            task_id=f"task-{evidence_id}", exact_inputs_hash=f"inputs-{evidence_id}",
            incumbent_success=True, candidate_success=candidate_success,
            incumbent_total_system_tokens=120,
            candidate_total_system_tokens=candidate_tokens,
            incumbent_includes_subject=False, candidate_includes_subject=True,
            judgment_valid=judgment_valid, comparable=comparable, noisy=False,
            bundled=False, cost_usd=Decimal("0.10"),
            final_artifact_hash=final_artifact_hash or self.candidate_hash,
            scope=scope,
            incumbent_token_components=(("agent_a", 10), ("agent_b", 10), ("work", 100)),
            candidate_token_components=(("agent_a", 8), ("agent_b", 7),
                                        ("work", candidate_tokens - 15)),
            **_fixture_receipt_bindings(self.module, evidence_id, "0.10"),
        )

    def _request(self, *evidence_ids, **changes):
        values = dict(
            request_id="adoption-1", proposal_id="proposal-adopt",
            candidate_hash=self.candidate_hash, audit_id="audit-adopt-b",
            incumbent_language_version=self.incumbent["version"],
            incumbent_language_hash=self.incumbent["hash"],
            evidence_ids=tuple(evidence_ids),
        )
        values.update(changes)
        return AdoptionRequest(**values)

    def test_adopts_only_exact_audited_artifact_with_matched_and_heldout_improvement(self):
        for receipt in (
            self._evidence("dev-evidence", "development"),
            self._evidence("held-evidence", "held_out", candidate_tokens=90),
        ):
            self.assertEqual(self.module.submit_evidence(receipt).outcome,
                             WorkOutcome.ELIGIBLE)
        result = self.module.submit_change(self._request("dev-evidence", "held-evidence"))
        self.assertEqual(result.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(result.reason, "exact_candidate_adopted")
        self.assertEqual(result.detail["adopted_artifact_hash"], self.candidate_hash)
        self.assertEqual(result.snapshot.adopted_language.hash, self.candidate_hash)
        self.assertIn("Use !ok for confirmed success.", result.snapshot.adopted_language.render())

        restarted = RuleLegislation.local(
            self.rulebook,
            budget_ledger_path=self.budget_path,
            evidence_ledger_path=self.evidence_path,
            clock=lambda: datetime.fromisoformat("2026-09-02T04:00:00+00:00"),
        )
        self.assertEqual(restarted.snapshot().adopted_language.hash, self.candidate_hash)

        ledger = json.loads(self.evidence_path.read_text())
        first = ledger["adoptions"].pop("adoption-1")
        first["sequence"] = 1
        second = copy.deepcopy(first)
        second["sequence"] = 2
        second["request"]["request_id"] = "a-newer"
        second["resulting_rulebook"]["rules"].append({
            "id": "rule-999", "text_en": "Second durable adoption.",
            "status": "adopted", "scores": None, "history": [],
        })
        ledger["adoptions"] = {"z-older": first, "a-newer": second}
        self.evidence_path.write_text(json.dumps(ledger, sort_keys=True))
        restarted_twice = RuleLegislation.local(
            self.rulebook, budget_ledger_path=self.budget_path,
            evidence_ledger_path=self.evidence_path,
            clock=lambda: datetime.fromisoformat("2026-09-02T04:00:00+00:00"),
        )
        self.assertIn(
            "Second durable adoption.",
            restarted_twice.snapshot().adopted_language.render(),
        )

    def test_rejects_success_loss_non_saving_invalid_judge_and_artifact_drift(self):
        cases = (
            ("lost", dict(candidate_success=False), WorkOutcome.REJECTED),
            ("flat", dict(candidate_tokens=120), WorkOutcome.REJECTED),
            ("invalid", dict(judgment_valid=False), WorkOutcome.DEFERRED),
            ("drift", dict(final_artifact_hash="other-artifact"), WorkOutcome.REJECTED),
            ("unequal", dict(comparable=False), WorkOutcome.DEFERRED),
        )
        for label, changes, expected in cases:
            with self.subTest(label=label):
                evidence_id = f"{label}-evidence"
                self.module.submit_evidence(self._evidence(
                    evidence_id, "development", **changes
                ))
                held_id = f"{label}-held"
                self.module.submit_evidence(self._evidence(
                    held_id, "held_out", **changes
                ))
                before = self.module.snapshot().adopted_language.hash
                result = self.module.submit_change(self._request(
                    evidence_id, held_id, request_id=f"adoption-{label}"
                ))
                self.assertEqual(result.outcome, expected)
                self.assertEqual(result.snapshot.adopted_language.hash, before)

    def test_missing_heldout_or_missing_ab_token_components_defers(self):
        development = self._evidence("only-dev", "development")
        self.module.submit_evidence(development)
        missing_held = self.module.submit_change(self._request("only-dev"))
        self.assertEqual(missing_held.outcome, WorkOutcome.DEFERRED)
        bad_components = self._evidence("bad-components", "held_out")
        bad_components = EvidenceReceipt(**{
            **bad_components.__dict__,
            "candidate_token_components": (("work", 100),),
        })
        self.module.submit_evidence(bad_components)
        missing_ab = self.module.submit_change(self._request(
            "only-dev", "bad-components", request_id="adoption-components"
        ))
        self.assertEqual(missing_ab.outcome, WorkOutcome.DEFERRED)

    def test_duplicate_adoption_is_idempotent_and_conflict_fails_closed(self):
        for receipt in (
            self._evidence("dev-idempotent", "development"),
            self._evidence("held-idempotent", "held_out"),
        ):
            self.module.submit_evidence(receipt)
        request = self._request("dev-idempotent", "held-idempotent")
        first = self.module.submit_change(request)
        duplicate = self.module.submit_change(request)
        conflict = self.module.submit_change(self._request(
            "dev-idempotent", "held-idempotent", candidate_hash="wrong"
        ))
        self.assertEqual(first.outcome, WorkOutcome.ELIGIBLE)
        self.assertEqual(duplicate.reason, "adoption_already_recorded")
        self.assertEqual(conflict.outcome, WorkOutcome.REJECTED)


if __name__ == "__main__":
    unittest.main()
