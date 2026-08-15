import json
import tempfile
import unittest
from pathlib import Path

from cleanup_rulebook import (
    apply_bundle,
    build_applied_rulebook,
    cleanup_draft_request_options,
    cleanup_revision_context,
    compile_cleanup_draft,
    compile_structured_cleanup_draft,
    prepare,
    structured_cleanup_request_options,
    validate_candidate,
)
from state_store import snapshot_hash

ROOT = Path(__file__).parents[2]
FIX = ROOT / "tests/fixtures/cleanup"


class CleanupTests(unittest.TestCase):
    def structured_draft(self):
        return {
            "assignments": {"rule-001": "deadlines", "rule-002": "deadlines"},
            "groups": [{
                "id": "deadlines",
                "trigger": "A message contains a deadline.",
                "encoder": ["Mark the deadline once."],
                "decoder": ["Restore the deadline at its original scope."],
                "invalid_if": ["The deadline changes or loses its scope."],
                "overrides": [],
            }],
            "exclusions": [],
            "legislative_memory": {
                "retired_mechanisms": [],
                "failure_modes": [{
                    "failure": "A deadline lost its governed action.",
                    "lesson": "Bind the time to its action.",
                    "source_ids": ["rule-001"],
                }],
                "unresolved_questions": [],
            },
        }

    def test_structured_cleanup_compiles_contracts_without_changing_canonical_shape(self):
        source = json.loads((FIX / "source.json").read_text())
        schema = structured_cleanup_request_options(source)["response_format"]["json_schema"]["schema"]
        self.assertEqual(
            schema["properties"]["groups"]["items"]["required"],
            ["id", "trigger", "encoder", "decoder", "invalid_if", "overrides"],
        )
        self.assertIn("legislative_memory", schema["required"])
        candidate = compile_structured_cleanup_draft(source, self.structured_draft())
        self.assertEqual(set(candidate["rules"][0]), {
            "id", "text_en", "status", "source_ids", "history"
        })
        self.assertTrue(candidate["rules"][0]["text_en"].startswith("CONTRACT {"))
        self.assertEqual(
            candidate["structured_rulebook"]["rules"][0]["source_ids"],
            ["rule-001", "rule-002"],
        )

    def test_structured_cleanup_rejects_malformed_provenance_overrides_and_oversize(self):
        source = json.loads((FIX / "source.json").read_text())
        cases = []
        missing = self.structured_draft()
        del missing["groups"][0]["invalid_if"]
        cases.append(missing)
        empty_decoder = self.structured_draft()
        empty_decoder["groups"][0]["decoder"] = []
        cases.append(empty_decoder)
        unknown_override = self.structured_draft()
        unknown_override["groups"][0]["overrides"] = ["unknown-contract"]
        cases.append(unknown_override)
        unknown_source = self.structured_draft()
        unknown_source["legislative_memory"]["failure_modes"][0]["source_ids"] = ["rule-999"]
        cases.append(unknown_source)
        for draft in cases:
            with self.assertRaises(ValueError):
                compile_structured_cleanup_draft(source, draft)

        oversize = self.structured_draft()
        long_text = "x" * 1000
        oversize["legislative_memory"] = {
            "retired_mechanisms": [{
                "mechanism": long_text, "outcome": "rejected", "reason": long_text,
                "source_ids": ["rule-001"],
            } for _ in range(8)],
            "failure_modes": [{
                "failure": long_text, "lesson": long_text, "source_ids": ["rule-001"],
            } for _ in range(8)],
            "unresolved_questions": [],
        }
        with self.assertRaisesRegex(ValueError, "size budget"):
            compile_structured_cleanup_draft(source, oversize)

    def test_cleanup_draft_schema_requires_every_adopted_source_exactly(self):
        source = json.loads((FIX / "source.json").read_text())
        options = cleanup_draft_request_options(source)
        response_format = options["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        self.assertTrue(response_format["json_schema"]["strict"])
        schema = response_format["json_schema"]["schema"]
        assignments = schema["properties"]["assignments"]
        self.assertEqual(assignments["required"], ["rule-001", "rule-002"])
        self.assertEqual(list(assignments["properties"]), ["rule-001", "rule-002"])
        self.assertFalse(assignments["additionalProperties"])
        exclusions = schema["properties"]["exclusions"]
        self.assertEqual(exclusions["items"]["properties"]["source_id"]["enum"], ["rule-001", "rule-002"])
        self.assertEqual(exclusions["items"]["required"], ["source_id", "reason"])
        self.assertFalse(exclusions["items"]["additionalProperties"])
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(options["provider"], {"require_parameters": True})

    def test_valid_cleanup_draft_compiles_coverage_in_source_order(self):
        source = json.loads((FIX / "source.json").read_text())
        draft = {
            "assignments": {"rule-001": "deadlines", "rule-002": "deadlines"},
            "groups": [{"id": "deadlines", "text_en": "Mark each deadline once."}],
            "exclusions": [],
        }
        candidate = compile_cleanup_draft(source, draft)
        self.assertEqual(candidate, {
            "version": "cleanup-candidate",
            "rules": [{
                "id": "rule-c001",
                "text_en": "Mark each deadline once.",
                "status": "adopted",
                "source_ids": ["rule-001", "rule-002"],
                "history": [],
            }],
            "excluded_sources": [],
        })
        validate_candidate(source, candidate)

    def test_cleanup_draft_rejects_missing_or_extra_assignment(self):
        source = json.loads((FIX / "source.json").read_text())
        groups = [{"id": "one", "text_en": "Preserve each deadline."}]
        for assignments in (
            {"rule-001": "one"},
            {"rule-001": "one", "rule-002": "one", "rule-999": "one"},
        ):
            with self.assertRaisesRegex(ValueError, "assignment keys"):
                compile_cleanup_draft(source, {"assignments": assignments, "groups": groups, "exclusions": []})

    def test_cleanup_draft_rejects_unknown_or_orphan_group(self):
        source = json.loads((FIX / "source.json").read_text())
        cases = (
            {
                "assignments": {"rule-001": "one", "rule-002": "missing"},
                "groups": [{"id": "one", "text_en": "Preserve each deadline."}],
                "exclusions": [],
            },
            {
                "assignments": {"rule-001": "one", "rule-002": "one"},
                "groups": [
                    {"id": "one", "text_en": "Preserve each deadline."},
                    {"id": "unused", "text_en": "Unused text."},
                ],
                "exclusions": [],
            },
        )
        for draft in cases:
            with self.assertRaisesRegex(ValueError, "defined groups"):
                compile_cleanup_draft(source, draft)

    def test_cleanup_draft_rejects_duplicate_group_and_operational_text(self):
        source = json.loads((FIX / "source.json").read_text())
        assignments = {"rule-001": "one", "rule-002": "one"}
        duplicate = {
            "assignments": assignments,
            "groups": [
                {"id": "one", "text_en": "Preserve each deadline."},
                {"id": "one", "text_en": "Preserve each due time."},
            ],
            "exclusions": [],
        }
        with self.assertRaisesRegex(ValueError, "unique"):
            compile_cleanup_draft(source, duplicate)
        operational = {
            "assignments": assignments,
            "groups": [{"id": "one", "text_en": "Deploy the timer."}],
            "exclusions": [],
        }
        with self.assertRaisesRegex(ValueError, "operational text"):
            compile_cleanup_draft(source, operational)

    def test_explicit_exclusion_accounts_for_non_language_source(self):
        source = json.loads((FIX / "source.json").read_text())
        draft = {
            "assignments": {"rule-001": "deadlines", "rule-002": "__exclude__"},
            "groups": [{"id": "deadlines", "text_en": "Mark each deadline once."}],
            "exclusions": [{"source_id": "rule-002", "reason": "operational"}],
        }
        candidate = compile_cleanup_draft(source, draft)
        self.assertEqual(candidate["rules"][0]["source_ids"], ["rule-001"])
        self.assertEqual(candidate["excluded_sources"], [
            {"source_id": "rule-002", "reason": "operational"},
        ])
        validate_candidate(source, candidate)

    def test_exclusion_must_match_assignments_and_allowed_reasons(self):
        source = json.loads((FIX / "source.json").read_text())
        base = {
            "assignments": {"rule-001": "deadlines", "rule-002": "__exclude__"},
            "groups": [{"id": "deadlines", "text_en": "Mark each deadline once."}],
        }
        for exclusions in (
            [],
            [{"source_id": "rule-001", "reason": "fragment"}],
            [{"source_id": "rule-002", "reason": "preference"}],
        ):
            with self.assertRaisesRegex(ValueError, "exclusion"):
                compile_cleanup_draft(source, {**base, "exclusions": exclusions})

    def test_candidate_rejects_silent_duplicate_or_unknown_exclusion(self):
        source = json.loads((FIX / "source.json").read_text())
        candidate = json.loads((FIX / "replacement.json").read_text())
        for excluded_sources in (
            [{"source_id": "rule-002", "reason": "operational"}],
            [{"source_id": "rule-999", "reason": "fragment"}],
            [{"source_id": "rule-002", "reason": "unknown"}],
        ):
            candidate["excluded_sources"] = excluded_sources
            with self.assertRaises(ValueError):
                validate_candidate(source, candidate)

    def test_turn_650_non_language_sources_can_be_excluded_without_active_law(self):
        evidence = ROOT / "specs/001-experiment-repair/evidence/cleanup-live"
        source = json.loads((evidence / "source-rulebook-turn-650.json").read_text())
        draft = json.loads((evidence / "a-structured-draft.json").read_text())
        reasons = {
            "rule-075": "operational",
            "rule-077": "fragment",
            "rule-085": "fragment",
            "rule-099": "operational",
        }
        for source_id in reasons:
            draft["assignments"][source_id] = "__exclude__"
        draft["groups"] = [
            group for group in draft["groups"]
            if group["id"] != "rulebook-maintenance"
        ]
        draft["exclusions"] = [
            {"source_id": source_id, "reason": reasons[source_id]}
            for source_id in reasons
        ]
        candidate = compile_cleanup_draft(source, draft)
        self.assertEqual(
            {item["source_id"] for item in candidate["excluded_sources"]},
            set(reasons),
        )
        retained = {
            source_id
            for rule in candidate["rules"]
            for source_id in rule["source_ids"]
        }
        self.assertTrue(set(reasons).isdisjoint(retained))
        validate_candidate(source, candidate)

    def test_revision_context_binds_rejected_audit_as_data(self):
        source = json.loads((FIX / "source.json").read_text())
        replacement = json.loads((FIX / "replacement.json").read_text())
        audit = json.loads((FIX / "audit.json").read_text())
        audit.update({
            "verdict": "REJECT",
            "omissions": ["rule-002"],
            "meaning_changes": [{"location": "rule-c001", "issue": "Threshold lost."}],
        })
        context = cleanup_revision_context(source, replacement, audit)
        self.assertEqual(context["boundary"], "UNTRUSTED_AUDIT_FEEDBACK_DATA")
        self.assertEqual(context["audit_feedback"]["omissions"], ["rule-002"])
        self.assertEqual(context["prior_candidate_hash"], snapshot_hash(replacement))

    def test_revision_context_rejects_unbound_or_passing_audit(self):
        source = json.loads((FIX / "source.json").read_text())
        replacement = json.loads((FIX / "replacement.json").read_text())
        audit = json.loads((FIX / "audit.json").read_text())
        with self.assertRaisesRegex(ValueError, "rejected audit"):
            cleanup_revision_context(source, replacement, audit)
        audit["verdict"] = "REJECT"
        audit["reviewed_candidate_hash"] = "wrong"
        with self.assertRaisesRegex(ValueError, "bound"):
            cleanup_revision_context(source, replacement, audit)

    def test_prepare_is_snapshot_only_and_apply_needs_exact_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory); active = directory / "active.json"
            active.write_text((FIX / "source.json").read_text())
            before = active.read_bytes(); bundle = directory / "bundle"
            manifest = prepare(active, FIX / "replacement.json", FIX / "audit.json", bundle)
            self.assertEqual(before, active.read_bytes()); self.assertEqual(manifest["status"], "pending_iso")
            self.assertTrue((bundle / "exact.diff").read_text().startswith("--- original.json"))
            review=json.loads((bundle / "review.json").read_text())
            self.assertEqual(review["source_rulebook_hash"],manifest["source_hash"])
            self.assertEqual(review["replacement_hash"],manifest["replacement_hash"])
            self.assertEqual(snapshot_hash(review["original"]),manifest["source_hash"])
            self.assertEqual(review["a_replacement"]["rules"][0]["source_ids"],["rule-001","rule-002"])
            self.assertEqual(review["b_audit"]["verdict"],"pass")
            self.assertTrue(review["exact_diff"].startswith("--- original.json"))
            with self.assertRaises(ValueError): apply_bundle(active, bundle, directory / "missing.json")
            receipt = directory / "approval.json"
            receipt.write_text(json.dumps({"approved":True,"source_hash":manifest["source_hash"],
                                           "replacement_hash":manifest["replacement_hash"]}))
            apply_bundle(active, bundle, receipt)
            self.assertEqual(snapshot_hash(json.loads(active.read_text())), manifest["replacement_hash"])
            self.assertTrue(json.loads((bundle / "manifest.json").read_text())["applied"])
            self.assertEqual(json.loads((bundle / "review.json").read_text())["status"],"applied")
            applied = json.loads(active.read_text())
            self.assertEqual([r["id"] for r in applied["rules"]],
                             ["rule-001", "rule-002", "rule-003", "rule-004"])
            self.assertEqual([r["status"] for r in applied["rules"]],
                             ["historical", "historical", "rejected", "adopted"])
            self.assertEqual(applied["rules"][3]["source_ids"], ["rule-001", "rule-002"])
            self.assertEqual(applied["next_id"], 5)
            self.assertIsNone(applied["kernel_tokens"])

    def test_source_mismatch_and_operational_text_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory); bundle = directory / "bundle"
            bad = json.loads((FIX / "replacement.json").read_text()); bad["rules"][0]["text_en"] += " deploy the timer"
            bad_path = directory / "bad.json"; bad_path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError): prepare(FIX / "source.json", bad_path, FIX / "audit.json", bundle)

    def test_candidate_is_rejected_before_audit_on_missing_or_duplicate_source(self):
        source = json.loads((FIX / "source.json").read_text())
        for sources in (["rule-001"], ["rule-001", "rule-001", "rule-002"]):
            candidate = json.loads((FIX / "replacement.json").read_text())
            candidate["rules"][0]["source_ids"] = sources
            with self.assertRaises(ValueError):
                validate_candidate(source, candidate)

    def test_candidate_can_pass_before_audit(self):
        validate_candidate(
            json.loads((FIX / "source.json").read_text()),
            json.loads((FIX / "replacement.json").read_text()),
        )

    def test_audit_omission_or_non_pass_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            for field, value in (("verdict", "fail"), ("covered_source_ids", ["rule-001"]),
                                 ("omissions", ["rule-002"]), ("reviewed_candidate_hash", "wrong")):
                audit = json.loads((FIX / "audit.json").read_text())
                audit[field] = value
                audit_path = directory / f"bad-{field}.json"
                audit_path.write_text(json.dumps(audit))
                with self.assertRaises(ValueError):
                    prepare(FIX / "source.json", FIX / "replacement.json", audit_path,
                            directory / f"bundle-{field}")

    def test_apply_rejects_tampered_candidate_audit_or_diff(self):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory)
            for name in ("replacement.json","audit.json","exact.diff"):
                active=directory/f"active-{name}.json"; active.write_text((FIX/"source.json").read_text())
                bundle=directory/f"bundle-{name}"; manifest=prepare(active,FIX/"replacement.json",FIX/"audit.json",bundle)
                target=bundle/name
                if name.endswith(".json"):
                    changed=json.loads(target.read_text()); changed["tampered"]=True; target.write_text(json.dumps(changed))
                else:
                    target.write_text(target.read_text()+"tamper\n")
                receipt=directory/f"approval-{name}.json"; receipt.write_text(json.dumps({"approved":True,
                    "source_hash":manifest["source_hash"],"replacement_hash":manifest["replacement_hash"]}))
                with self.assertRaises(ValueError): apply_bundle(active,bundle,receipt)

    def test_cleanup_terminalizes_legacy_open_states_with_history_receipts(self):
        source = json.loads((FIX / "source.json").read_text())
        source["rules"][0]["pending_repeal"] = {
            "kind":"repeal", "target_id":"rule-001", "rationale":"Legacy pending repeal."
        }
        source["rules"].extend([
            {"id":"rule-004","text_en":"Legacy open proposal.","status":"proposed","history":[]},
            {"id":"rule-005","text_en":"Legacy reverted proposal.","status":"reverted","history":[]},
        ])
        source["next_id"] = 6
        replacement = json.loads((FIX / "replacement.json").read_text())
        applied = build_applied_rulebook(source, replacement)
        by_id = {r["id"]: r for r in applied["rules"]}
        for rule_id, prior in (("rule-004", "proposed"), ("rule-005", "reverted")):
            self.assertEqual(by_id[rule_id]["status"], "historical")
            self.assertEqual(by_id[rule_id]["history"][-1],
                             {"verb":"cleanup_terminalized","source_status":prior})
        self.assertFalse(any(r.get("status") in {"proposed","reverted"} for r in applied["rules"]))
        self.assertNotIn("pending_repeal", by_id["rule-001"])


if __name__ == "__main__": unittest.main()
