import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from shadow_cleanup import MAX_B_TOKENS, MAX_C_TOKENS, cleanup_c_request_options, run_shadow_cleanup
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

    def test_b_prompt_requires_paired_semantic_evidence(self):
        prompt = (ROOT / "prompts/cleanup_b.md").read_text()
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
            self.assertEqual(len(json.loads((output / "creative-seeds.json").read_text())), 3)
            self.assertEqual(json.loads((output / "c-call.json").read_text())["model"], "different-family-c")
            self.assertEqual(json.loads((output / "b-call.json").read_text())["model"], "kimi-b")
            self.assertFalse((output / "applied-rulebook.json").exists())
            self.assertFalse((output / "manifest.json").exists())

    def test_shadow_can_freeze_an_explicit_agent_c_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            self.source_path = self._source_copy(directory)
            prompt = Path(directory) / "candidate-c.md"
            prompt.write_text("candidate Agent C behavior contract")
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
            )
            expected_hash = hashlib.sha256(prompt.read_bytes()).hexdigest()
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(systems[0], prompt.read_text())
            self.assertEqual(report["prompt_c_sha256"], expected_hash)
            receipt = json.loads((output / "c-prompt.json").read_text())
            self.assertEqual(receipt["sha256"], expected_hash)
            self.assertEqual(receipt["content"], prompt.read_text())

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

    def test_b_rejection_is_a_failed_shadow_not_an_apply_request(self):
        with tempfile.TemporaryDirectory() as directory:
            self.source_path = self._source_copy(directory)
            calls = []

            def call(model, _system, user, **_kwargs):
                calls.append(model)
                if len(calls) == 1:
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
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["stage"], "b_audit")
            self.assertIn("rejected", report["reason"])
            self.assertFalse((output / "applied-rulebook.json").exists())

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
