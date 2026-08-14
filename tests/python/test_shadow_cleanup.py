import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from shadow_cleanup import (
    FINALIZER_PROMPT,
    MAX_B_TOKENS,
    MAX_C_TOKENS,
    cleanup_c_request_options,
    compile_c_response,
    prompt_version,
    run_shadow_cleanup,
    validate_b_audit,
)
from state_store import snapshot_hash


ROOT = Path(__file__).parents[2]
FIX = ROOT / "tests/fixtures/cleanup"


def c_response():
    return {
        "assignments": {"rule-001": "deadlines", "rule-002": "deadlines"},
        "groups": [{"id": "deadlines", "text_en": "Mark each deadline or due time once."}],
        "exclusions": [],
        "creative_seeds": [
            {"idea": "Try a scoped time marker.", "experiment": "Compare one deadline payload.", "risk": "The marker may be ambiguous."},
            {"idea": "Try positional task slots.", "experiment": "Compare one handoff payload.", "risk": "Slot order may be brittle."},
            {"idea": "Try local repeated-phrase aliases.", "experiment": "Compare one repetitive payload.", "risk": "Definitions may cost more than they save."},
        ],
    }


class ShadowCleanupTests(unittest.TestCase):
    def _source_copy(self, directory):
        source = Path(directory) / "source.json"
        source.write_bytes((FIX / "source.json").read_bytes())
        return source

    def _token_counter(self, text, _meta):
        return 100 if "2 adopted rules" in text else 80

    def _passing_call(self, calls, token_limits=None):
        def call(model, _system, user, **_kwargs):
            calls.append(model)
            if token_limits is not None:
                token_limits.append(_kwargs["max_tokens"])
            if len(calls) == 1:
                return json.dumps(c_response()), {"cost": 0.01}
            request = json.loads(user)
            source = json.loads((self.source_path).read_text())
            audit = {
                "verdict": "pass",
                "reviewed_source_hash": request["source_hash"],
                "reviewed_candidate_hash": request["candidate_hash"],
                "covered_source_ids": ["rule-001", "rule-002"],
                "omissions": [],
                "meaning_changes": [],
                "operational_text": [],
                "notes": [f"Reviewed {snapshot_hash(source)[:8]}"],
            }
            return json.dumps(audit), {"cost": 0.01}
        return call

    def test_c_schema_requires_three_separate_creative_seeds(self):
        source = json.loads((FIX / "source.json").read_text())
        schema = cleanup_c_request_options(source)["response_format"]["json_schema"]["schema"]
        seeds = schema["properties"]["creative_seeds"]
        self.assertEqual((seeds["minItems"], seeds["maxItems"]), (3, 3))
        self.assertIn("creative_seeds", schema["required"])
        self.assertFalse(seeds["items"]["additionalProperties"])

    def test_c_budget_can_represent_a_minimally_passing_current_size_candidate(self):
        source_tokens = 19_080
        largest_minimally_passing_candidate = math.floor(
            source_tokens * (100 - 5) / 100
        )
        required_with_json_and_cross_tokenizer_headroom = math.ceil(
            largest_minimally_passing_candidate * 1.20
        )

        self.assertEqual(largest_minimally_passing_candidate, 18_126)
        self.assertGreaterEqual(
            MAX_C_TOKENS, required_with_json_and_cross_tokenizer_headroom
        )

    def test_b_prompt_requires_paired_semantic_evidence(self):
        prompt = (ROOT / "prompts/cleanup_b_v1.md").read_text()
        contract = " ".join(prompt.split())
        self.assertIn('Source clause: "..." Candidate clause: "..." Difference:', contract)
        self.assertIn("search the whole edition before calling it absent", contract)
        self.assertIn("bookkeeping, rule structure, or explanatory framing", contract)
        self.assertIn("broadens or narrows a requirement's scope", contract)
        self.assertIn("never use it to inventory preserved language law", contract)

    def test_passing_shadow_writes_evidence_and_never_changes_source(self):
        with tempfile.TemporaryDirectory() as directory:
            self.source_path = self._source_copy(directory)
            before = self.source_path.read_bytes()
            output = Path(directory) / "shadow"
            calls = []
            token_limits = []
            report = run_shadow_cleanup(
                self.source_path,
                output,
                model_c="different-family-c",
                model_b="kimi-b",
                call_model=self._passing_call(calls, token_limits),
                token_counter=self._token_counter,
                meta={"spend_usd": 0.0},
            )
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["reduction_pct"], 20.0)
            self.assertEqual(calls, ["different-family-c", "kimi-b"])
            self.assertEqual(token_limits, [MAX_C_TOKENS, MAX_B_TOKENS])
            self.assertEqual(self.source_path.read_bytes(), before)
            self.assertTrue(report["source_unchanged"])
            self.assertFalse(report["applied"])
            self.assertEqual(report["prompt_c_version"], "cleanup-c-v1")
            self.assertEqual(report["prompt_b_version"], "cleanup-b-v1")
            self.assertEqual(report["decision_authority"], "C")
            self.assertEqual(report["b_review_mode"], "single_advisory")
            self.assertEqual(len(json.loads((output / "creative-seeds.json").read_text())), 3)
            self.assertEqual(json.loads((output / "c-call.json").read_text())["model"], "different-family-c")
            self.assertEqual(json.loads((output / "b-call.json").read_text())["model"], "kimi-b")
            self.assertFalse((output / "applied-rulebook.json").exists())
            self.assertFalse((output / "manifest.json").exists())

    def test_shadow_can_freeze_explicit_agent_prompts(self):
        with tempfile.TemporaryDirectory() as directory:
            self.source_path = self._source_copy(directory)
            prompt = Path(directory) / "candidate-c.md"
            prompt.write_text("candidate Agent C behavior contract")
            prompt_b = Path(directory) / "candidate-b.md"
            prompt_b.write_text("candidate Agent B behavior contract")
            systems = []
            passing_call = self._passing_call([])

            def call(model, system, user, **kwargs):
                systems.append(system)
                return passing_call(model, system, user, **kwargs)

            output = Path(directory) / "shadow"
            report = run_shadow_cleanup(
                self.source_path,
                output,
                model_c="different-family-c",
                model_b="kimi-b",
                call_model=call,
                token_counter=self._token_counter,
                meta={"spend_usd": 0.0},
                prompt_c_path=prompt,
                prompt_b_path=prompt_b,
            )
            expected_hash = hashlib.sha256(prompt.read_bytes()).hexdigest()
            expected_b_hash = hashlib.sha256(prompt_b.read_bytes()).hexdigest()
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(systems[0], prompt.read_text())
            self.assertEqual(systems[1], prompt_b.read_text())
            self.assertEqual(report["prompt_c_sha256"], expected_hash)
            self.assertEqual(report["prompt_b_sha256"], expected_b_hash)
            self.assertEqual(report["prompt_c_version"], f"custom-c-{expected_hash[:12]}")
            self.assertEqual(report["prompt_b_version"], f"custom-b-{expected_b_hash[:12]}")
            receipt = json.loads((output / "c-prompt.json").read_text())
            receipt_b = json.loads((output / "b-prompt.json").read_text())
            self.assertEqual(receipt["version"], report["prompt_c_version"])
            self.assertEqual(receipt["sha256"], expected_hash)
            self.assertEqual(receipt["content"], prompt.read_text())
            self.assertEqual(receipt_b["version"], report["prompt_b_version"])
            self.assertEqual(receipt_b["sha256"], expected_b_hash)
            self.assertEqual(receipt_b["content"], prompt_b.read_text())

    def test_versioned_candidate_prompts_have_stable_ids_and_exact_test_content(self):
        prompt_c_v1 = ROOT / "prompts/cleanup_c_v1.md"
        prompt_b_v1 = ROOT / "prompts/cleanup_b_v1.md"
        prompt_c = ROOT / "prompts/cleanup_c_v2.md"
        prompt_b = ROOT / "prompts/cleanup_b_v2.md"
        finalizer = ROOT / "prompts/cleanup_c_finalizer_v1.md"
        c_hash = hashlib.sha256(prompt_c.read_bytes()).hexdigest()
        b_hash = hashlib.sha256(prompt_b.read_bytes()).hexdigest()
        self.assertEqual(prompt_version(prompt_c, "c", c_hash), "cleanup-c-v2")
        self.assertEqual(prompt_version(prompt_b, "b", b_hash), "cleanup-b-v2")
        self.assertEqual(prompt_version(finalizer, "c-finalizer",
                                        hashlib.sha256(finalizer.read_bytes()).hexdigest()),
                         "cleanup-c-finalizer-v1")
        self.assertEqual(hashlib.sha256(finalizer.read_bytes()).hexdigest(),
                         "28b66aeb1cba08d1f905e062bda40d0eda82b0d19370694c201303fdfb8f8b10")
        self.assertEqual(hashlib.sha256(prompt_c_v1.read_bytes()).hexdigest(),
                         "a7489096e4dedcab2f0287c45fc663f0daeab84e47311d0a7b7b92e04e17e730")
        self.assertEqual(hashlib.sha256(prompt_b_v1.read_bytes()).hexdigest(),
                         "39a9062ce640b760769bd70a8563f85b0358a962426c412c3d822ccc013ae32f")
        self.assertEqual(c_hash, "aa454bf3c8f9ea4d124398716e91956529c33acd7206016003fa43bed6d71ad0")
        self.assertEqual(b_hash, "0d6ea9d93245cf1e714cccf928434724a9b13a5f3094f2c1f365b758416e850b")

    def test_shadow_refuses_the_same_model_for_c_and_b(self):
        with tempfile.TemporaryDirectory() as directory:
            self.source_path = self._source_copy(directory)
            with self.assertRaisesRegex(ValueError, "different"):
                run_shadow_cleanup(
                    self.source_path,
                    Path(directory) / "shadow",
                    model_c="same-model",
                    model_b="same-model",
                    call_model=lambda *_args, **_kwargs: self.fail("provider should not run"),
                    token_counter=lambda *_args: self.fail("token counter should not run"),
                    meta={"spend_usd": 0.0},
                )

    def test_missing_source_assignment_fails_before_token_or_b_call(self):
        with tempfile.TemporaryDirectory() as directory:
            self.source_path = self._source_copy(directory)
            response = c_response()
            del response["assignments"]["rule-002"]
            calls = []

            def call(model, _system, _user, **_kwargs):
                calls.append(model)
                return json.dumps(response), {"cost": 0.01}

            report = run_shadow_cleanup(
                self.source_path,
                Path(directory) / "shadow",
                model_c="c",
                model_b="b",
                call_model=call,
                token_counter=lambda *_: self.fail("token counter should not run"),
                meta={"spend_usd": 0.0},
            )
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["stage"], "c_validation")
            self.assertEqual(calls, ["c"])
            self.assertTrue(report["source_unchanged"])

    def test_insufficient_reduction_stops_before_b(self):
        with tempfile.TemporaryDirectory() as directory:
            self.source_path = self._source_copy(directory)
            calls = []

            def call(model, _system, _user, **_kwargs):
                calls.append(model)
                return json.dumps(c_response()), {"cost": 0.01}

            report = run_shadow_cleanup(
                self.source_path,
                Path(directory) / "shadow",
                model_c="c",
                model_b="b",
                call_model=call,
                token_counter=lambda _text, _meta: 100,
                meta={"spend_usd": 0.0},
            )
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["stage"], "token_gate")
            self.assertEqual(calls, ["c"])

    def test_b_rejection_is_advisory_and_c_final_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            self.source_path = self._source_copy(directory)
            calls = []
            token_limits = []

            def call(model, _system, user, **kwargs):
                calls.append(model)
                token_limits.append(kwargs["max_tokens"])
                if model == "c":
                    return json.dumps(c_response()), {"cost": 0.01}
                request = json.loads(user)
                return json.dumps({
                    "verdict": "REJECT",
                    "reviewed_source_hash": request["source_hash"],
                    "reviewed_candidate_hash": request["candidate_hash"],
                    "covered_source_ids": ["rule-001", "rule-002"],
                    "omissions": [],
                    "meaning_changes": [{"location": "rule-c001", "issue": "The due-time boundary changed."}],
                    "operational_text": [],
                    "notes": [],
                }), {"cost": 0.01}

            output = Path(directory) / "shadow"
            report = run_shadow_cleanup(
                self.source_path,
                output,
                model_c="c",
                model_b="b",
                call_model=call,
                token_counter=self._token_counter,
                meta={"spend_usd": 0.0},
            )
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["stage"], "complete")
            self.assertIn("C finalized", report["reason"])
            self.assertEqual(report["round_count"], 2)
            self.assertEqual(calls, ["c", "b", "c"])
            self.assertEqual(
                token_limits, [MAX_C_TOKENS, MAX_B_TOKENS, MAX_C_TOKENS]
            )
            self.assertEqual([item["b_verdict"] for item in report["rounds"]],
                             ["REJECT", None])
            self.assertTrue((output / "rounds/01/b-audit.json").exists())
            self.assertFalse((output / "rounds/02/b-audit.json").exists())
            self.assertFalse((output / "applied-rulebook.json").exists())

    def test_final_c_call_gets_full_context_and_has_decision_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            self.source_path = self._source_copy(directory)
            c_requests = []
            c_systems = []
            b_requests = []

            def audit(request, verdict, findings):
                return {
                    "verdict": verdict,
                    "reviewed_source_hash": request["source_hash"],
                    "reviewed_candidate_hash": request["candidate_hash"],
                    "covered_source_ids": ["rule-001", "rule-002"],
                    "omissions": [],
                    "meaning_changes": findings,
                    "operational_text": [],
                    "notes": ["non-actionable audit context must not go back to C"],
                }

            def call(model, system, user, **_kwargs):
                request = json.loads(user)
                if model == "c":
                    c_requests.append(request)
                    c_systems.append(system)
                    response = c_response()
                    if len(c_requests) == 2:
                        response["groups"][0]["text_en"] = "Mark every deadline or due time once."
                    return json.dumps(response), {"cost": 0.01}
                b_requests.append(request)
                findings = [{"location": "rule-c001", "issue": "The deadline scope changed."}]
                return json.dumps(audit(request, "REJECT", findings)), {"cost": 0.01}

            output = Path(directory) / "shadow"
            report = run_shadow_cleanup(
                self.source_path,
                output,
                model_c="c",
                model_b="b",
                call_model=call,
                token_counter=self._token_counter,
                meta={"spend_usd": 0.0},
            )
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["round_count"], 2)
            self.assertEqual([item["b_verdict"] for item in report["rounds"]],
                             ["REJECT", None])
            self.assertIsNone(report["rounds"][0]["candidate_changed_from_previous"])
            self.assertTrue(report["rounds"][1]["candidate_changed_from_previous"])
            final = c_requests[1]
            self.assertEqual(final["source_hash"], c_requests[0]["source_hash"])
            self.assertEqual(len(final["adopted_language"]), 2)
            self.assertTrue(final["final_decision"])
            self.assertEqual(set(final["b_advisory"]),
                             {"omissions", "meaning_changes", "operational_text"})
            self.assertEqual(final["b_advisory"]["meaning_changes"][0]["location"],
                             "rule-c001")
            self.assertEqual(final["previous_candidate"], b_requests[0]["candidate"])
            self.assertIn(FINALIZER_PROMPT, c_systems[1])
            self.assertEqual(len(b_requests), 1)
            final_candidate = json.loads((output / "candidate.json").read_text())
            self.assertEqual(final_candidate["rules"][0]["text_en"],
                             "Mark every deadline or due time once.")
            stored = json.loads((output / "rounds/02/c-request.json").read_text())
            self.assertEqual(stored["b_advisory"], final["b_advisory"])
            assembled = json.loads((output / "rounds/02/c-system-prompt.json").read_text())
            self.assertEqual(assembled["content"], c_systems[1])
            self.assertIn("cleanup-c-finalizer-v1", assembled["version"])

    def test_b_rejection_requires_an_actionable_finding(self):
        source = json.loads((FIX / "source.json").read_text())
        candidate, _ = compile_c_response(source, c_response())
        audit = {
            "verdict": "REJECT",
            "reviewed_source_hash": snapshot_hash(source),
            "reviewed_candidate_hash": snapshot_hash(candidate),
            "covered_source_ids": ["rule-001", "rule-002"],
            "omissions": [],
            "meaning_changes": [],
            "operational_text": [],
            "notes": ["No actionable semantic defect."],
        }
        with self.assertRaisesRegex(ValueError, "actionable"):
            validate_b_audit(source, candidate, audit)

    def test_invalid_b_advisory_fails_with_exact_response_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            self.source_path = self._source_copy(directory)
            calls = []

            def call(model, _system, _user, **_kwargs):
                calls.append(model)
                if model == "c":
                    return json.dumps(c_response()), {"cost": 0.01}
                return "not json", {"cost": 0.01}

            output = Path(directory) / "shadow"
            report = run_shadow_cleanup(
                self.source_path,
                output,
                model_c="c",
                model_b="b",
                call_model=call,
                token_counter=self._token_counter,
                meta={"spend_usd": 0.0},
            )
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["stage"], "b_audit")
            self.assertEqual(report["failure_class"], "invalid_advisory")
            self.assertEqual(calls, ["c", "b"])
            self.assertEqual(report["rounds"][0]["b_verdict"], "invalid")
            error = report["b_advisory_error"]
            self.assertEqual(error["status"], "invalid")
            self.assertEqual(error["reason"], "Agent B did not return valid JSON")
            self.assertEqual(error["response_receipt"]["model"], "b")
            self.assertEqual(error["response_receipt"]["content"], "not json")
            self.assertEqual(error["response_receipt"]["usage"], {"cost": 0.01})
            stored_report = json.loads((output / "report.json").read_text())
            self.assertEqual(stored_report["b_advisory_error"], error)
            self.assertTrue((output / "candidate.json").exists())
            self.assertFalse((output / "rounds/02").exists())

    def test_unavailable_b_advisory_fails_without_second_c_call(self):
        with tempfile.TemporaryDirectory() as directory:
            self.source_path = self._source_copy(directory)
            calls = []

            def call(model, _system, _user, **_kwargs):
                calls.append(model)
                if model == "c":
                    return json.dumps(c_response()), {"cost": 0.01}
                raise RuntimeError("provider timeout")

            output = Path(directory) / "shadow"
            report = run_shadow_cleanup(
                self.source_path,
                output,
                model_c="c",
                model_b="b",
                call_model=call,
                token_counter=self._token_counter,
                meta={"spend_usd": 0.0},
            )
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["stage"], "b_call")
            self.assertEqual(report["failure_class"], "invalid_advisory")
            self.assertEqual(calls, ["c", "b"])
            self.assertEqual(report["rounds"][0]["b_verdict"], "unavailable")
            self.assertEqual(report["b_advisory_error"], {
                "status": "unavailable",
                "error_type": "RuntimeError",
                "reason": "provider timeout",
            })
            self.assertFalse((output / "rounds/02").exists())

    def test_source_drift_is_detected_before_b(self):
        with tempfile.TemporaryDirectory() as directory:
            self.source_path = self._source_copy(directory)
            calls = []

            def call(model, _system, _user, **_kwargs):
                calls.append(model)
                changed = json.loads(self.source_path.read_text())
                changed["version"] = "changed-elsewhere"
                self.source_path.write_text(json.dumps(changed))
                return json.dumps(c_response()), {"cost": 0.01}

            report = run_shadow_cleanup(
                self.source_path,
                Path(directory) / "shadow",
                model_c="c",
                model_b="b",
                call_model=call,
                token_counter=lambda *_: self.fail("token counter should not run"),
                meta={"spend_usd": 0.0},
            )
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["stage"], "source_integrity")
            self.assertFalse(report["source_unchanged"])
            self.assertEqual(calls, ["c"])


if __name__ == "__main__":
    unittest.main()
