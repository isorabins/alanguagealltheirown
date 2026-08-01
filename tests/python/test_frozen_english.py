import copy
import hashlib
import json
import unittest
from pathlib import Path
from unittest import mock

import frozen_english as frozen
import loop


ROOT = Path(__file__).parents[2]


class FrozenEnglishTests(unittest.TestCase):
    def setUp(self):
        self.suite = loop.load_benchmark_suite()
        self.contract = frozen.load_checked_contract(self.suite)

    def _record(self, benchmark_id, savings=20):
        digest = next(
            row["benchmark_digest"]
            for row in self.contract["benchmarks"]
            if row["id"] == benchmark_id
        )
        return {
            "benchmark_id": benchmark_id,
            "benchmark_version": "v2",
            "benchmark_digest": digest,
            "execution_inputs": copy.deepcopy(self.contract["execution_inputs"]),
            "judge_valid": True,
            "meaning_pass": True,
            "semantic_coverage_pct": 100,
            "inventions": [],
            "message_body_savings_pct": savings,
        }

    def _registry(self):
        return {
            "schema_version": 1,
            "baseline_version": "frozen-english-v2",
            "records": [self._record(benchmark_id) for benchmark_id in frozen.BENCHMARK_IDS],
        }

    def _event(self, benchmark_id, cycle=4, savings=30):
        return {
            "turn": 100 + int(benchmark_id[1:]),
            "type": "test",
            "era": "benchmark-v2",
            "scoring_version": "v2",
            "benchmark_version": "v2",
            "benchmark_id": benchmark_id,
            "benchmark_cycle": cycle,
            "judge_valid": True,
            "meaning_pass": True,
            "compression_success": True,
            "semantic_coverage_pct": 100,
            "inventions": [],
            "message_body_savings_pct": savings,
        }

    def test_checked_contract_pins_all_five_messages_and_execution_inputs(self):
        self.assertEqual([row["id"] for row in self.contract["benchmarks"]], list(frozen.BENCHMARK_IDS))
        inputs = self.contract["execution_inputs"]
        self.assertEqual(inputs["encoder_model"], loop.MODEL_A)
        self.assertEqual(inputs["decoder_model"], loop.MODEL_DECODER)
        self.assertEqual(inputs["judge_model"], loop.MODEL_GRADER)
        self.assertEqual(inputs["tokenizer_model"], loop.MODEL_GRADER)
        self.assertEqual(inputs["max_tokens"], 4000)
        self.assertEqual(inputs["encoder_temperature"], 0.3)
        self.assertEqual(inputs["decoder_temperature"], 0.1)
        self.assertEqual(inputs["judge_temperature"], 0)
        self.assertEqual(inputs["tokenizer_temperature"], 0)
        for key in ("compression_instruction_sha256", "decoder_instruction_sha256", "grader_instruction_sha256"):
            self.assertRegex(inputs[key], r"^[0-9a-f]{64}$")

    def test_only_named_benchmark_and_execution_inputs_make_records_stale(self):
        registry = self._registry()
        registry["created_at"] = "unrelated metadata"
        registry["provider_spend_usd"] = 999
        self.assertTrue(all(
            value["state"] == "current"
            for value in frozen.baseline_status(registry, self.contract).values()
        ))
        named_fields = [
            "encoder_model", "decoder_model", "judge_model", "tokenizer_model",
            "compression_instruction_sha256", "decoder_instruction_sha256",
            "grader_instruction_sha256", "encoder_temperature", "decoder_temperature",
            "judge_temperature", "tokenizer_temperature", "max_tokens",
        ]
        for field in named_fields:
            changed = copy.deepcopy(registry)
            changed["records"][0]["execution_inputs"][field] = "changed"
            self.assertEqual(
                frozen.baseline_status(changed, self.contract)["B1"]["state"], "stale", field
            )
        changed = copy.deepcopy(registry)
        changed["records"][0]["benchmark_digest"] = "changed"
        self.assertEqual(frozen.baseline_status(changed, self.contract)["B1"]["state"], "stale")

    def test_one_time_runner_uses_matched_models_instructions_temperatures_and_ceiling(self):
        benchmark = self.suite["benchmarks"][0]
        decoded = "\n".join(atom["meaning"] for atom in benchmark["answer_key"])
        grade = {"mode": "RELAY", "items": [
            {"id": atom["id"], "verdict": "SURVIVED", "evidence": atom["meaning"]}
            for atom in benchmark["answer_key"]
        ], "inventions": []}
        calls = mock.Mock(side_effect=[
            ("concise ordinary English", {}),
            (decoded, {}),
            (json.dumps(grade), {}),
        ])
        record = frozen.run_one_baseline(
            benchmark, self.contract, call_fn=calls,
            token_count_fn=mock.Mock(side_effect=[100, 70]), meta={},
        )
        self.assertEqual(calls.call_count, 3)
        expected = [
            (loop.MODEL_A, 0.3),
            (loop.MODEL_DECODER, 0.1),
            (loop.MODEL_GRADER, 0),
        ]
        for call, (model, temperature) in zip(calls.call_args_list, expected):
            self.assertEqual(call.args[0], model)
            self.assertEqual(call.kwargs["temperature"], temperature)
            self.assertEqual(call.kwargs["max_tokens"], 4000)
        self.assertNotIn("target length", calls.call_args_list[0].args[1].lower())
        self.assertEqual(record["message_body_savings_pct"], 30)
        self.assertTrue(record["meaning_pass"])
        self.assertEqual(record["execution_inputs"], self.contract["execution_inputs"])

    def test_preview_requires_no_provider_and_scheduled_loop_has_no_control_import(self):
        plan = frozen.preview_plan(self.contract, {
            "schema_version": 1, "baseline_version": frozen.BASELINE_VERSION, "records": []
        })
        self.assertEqual(plan["mode"], "preview_no_provider_calls")
        self.assertEqual(plan["to_run"], list(frozen.BENCHMARK_IDS))
        self.assertFalse(plan["scheduled_turn_path_changed"])
        self.assertNotIn("frozen_english", (ROOT / "loop.py").read_text())

    def test_projection_gates_on_complete_qualifying_v2_cycle_not_legacy_history(self):
        legacy = [{"benchmark_id": benchmark_id, "benchmark_cycle": 99,
                   "benchmark_version": "v1", "era": "benchmark-v1", "fidelity": 100}
                  for benchmark_id in frozen.BENCHMARK_IDS]
        self.assertIsNone(frozen.latest_qualifying_cycle(legacy))
        cycle = [self._event(benchmark_id) for benchmark_id in frozen.BENCHMARK_IDS]
        self.assertIsNone(frozen.latest_qualifying_cycle(cycle[:-1]))
        failed = copy.deepcopy(cycle)
        failed[1]["meaning_pass"] = False
        failed[1]["compression_success"] = False
        self.assertIsNone(frozen.latest_qualifying_cycle(failed))
        result = frozen.latest_qualifying_cycle(cycle)
        self.assertEqual(result["benchmark_cycle"], 4)
        self.assertEqual(result["average_message_body_savings_pct"], 30)

    def test_projection_requires_five_current_meaning_safe_controls(self):
        registry = self._registry()
        self.assertEqual(frozen.current_baseline_average(registry, self.contract), 20)
        registry["records"].pop()
        self.assertIsNone(frozen.current_baseline_average(registry, self.contract))
        registry = self._registry()
        registry["records"][0]["benchmark_digest"] = "stale"
        self.assertIsNone(frozen.current_baseline_average(registry, self.contract))
        registry = self._registry()
        registry["records"][0]["meaning_pass"] = False
        self.assertIsNone(frozen.current_baseline_average(registry, self.contract))

    def test_paired_projection_includes_fixed_cache_cost_and_control_adjustment(self):
        result = frozen.twenty_exchange_projection(32, 18, 1654)
        self.assertAlmostEqual(result["plain_cost_usd"], 2.94)
        self.assertAlmostEqual(result["rulebook_cache_cost_usd"], 0.0312606)
        self.assertAlmostEqual(result["alato_projected_savings_pct"], 30.93671428571428)
        self.assertAlmostEqual(result["english_projected_savings_pct"], 18)
        self.assertAlmostEqual(result["control_adjusted_percentage_points"], 12.93671428571428)
        self.assertEqual(result["assumptions"]["messages"], 40)
        self.assertEqual(result["assumptions"]["history_message_copies"], 780)
        self.assertEqual(result["assumptions"]["rulebook_cache_writes"], 2)
        self.assertEqual(result["assumptions"]["rulebook_cache_reads"], 38)
        self.assertIsNone(frozen.twenty_exchange_projection(32, 18, 0))

    def test_projection_helpers_do_not_mutate_historical_events_or_registry(self):
        events = [self._event(benchmark_id) for benchmark_id in frozen.BENCHMARK_IDS]
        registry = self._registry()
        before = hashlib.sha256(json.dumps(
            {"events": events, "registry": registry}, sort_keys=True
        ).encode()).hexdigest()
        frozen.latest_qualifying_cycle(events)
        frozen.current_baseline_average(registry, self.contract)
        after = hashlib.sha256(json.dumps(
            {"events": events, "registry": registry}, sort_keys=True
        ).encode()).hexdigest()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
