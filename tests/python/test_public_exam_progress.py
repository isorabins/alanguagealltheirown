import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import loop
from public_exam_progress import (MAX_PUBLIC_TEXT, ProgressValidationError,
                                  PublicExamProgressWriter, validate_snapshot)
from state_store import load_json

ROOT = Path(__file__).parents[2]


class PublicExamProgressTests(unittest.TestCase):
    def _writer(self, path, *, turn=3, benchmark_id="B1", language_hash="a" * 64):
        ticks = iter(f"2026-08-13T00:00:{second:02d}Z" for second in range(30))
        return PublicExamProgressWriter(
            path,
            turn=turn,
            benchmark_id=benchmark_id,
            benchmark_name="Event prose",
            language_version="adopted-test",
            language_hash=language_hash,
            clock=lambda: next(ticks),
        )

    def _advance_to_encoder(self, writer):
        writer.advance("exam_started")
        writer.advance("benchmark_selected")
        writer.advance("language_loaded")
        writer.advance("encoder_started")

    def test_one_identity_advances_atomically_through_safe_completed_receipts(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "public-exam-progress.json"
            writer = self._writer(path)
            self._advance_to_encoder(writer)
            writer.advance("encoder_completed", encoded="SAFE ENCODED")
            writer.advance("decoder_started")
            writer.advance("decoder_completed", decoded="Safe decoded response")
            writer.advance("judge_started")
            writer.advance("audit_progress", audit={
                "completed": 2, "total": 4, "survived": 2,
                "corrupted": 0, "missing": 0, "inventions": 0,
            })
            writer.advance("audit_progress", audit={
                "completed": 4, "total": 4, "survived": 3,
                "corrupted": 1, "missing": 0, "inventions": 0,
            })
            completed = writer.advance(
                "completed",
                tokens={"original": 100, "encoded": 61},
                result={
                    "judge_valid": True,
                    "meaning_pass": False,
                    "compression_success": False,
                    "semantic_coverage_pct": 75,
                    "status": "VALID",
                },
            )
            self.assertEqual(load_json(path, {}), completed)
            self.assertEqual(completed["phase"], "completed")
            self.assertEqual(completed["encoded"], "SAFE ENCODED")
            self.assertEqual(completed["decoded"], "Safe decoded response")
            self.assertEqual(
                [receipt["phase"] for receipt in completed["receipts"]],
                [
                    "exam_started", "benchmark_selected", "language_loaded",
                    "encoder_started", "encoder_completed", "decoder_started",
                    "decoder_completed", "judge_started", "audit_progress",
                    "audit_progress", "completed",
                ],
            )

    def test_validation_rejects_unknown_fields_bad_transitions_and_mixed_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "progress.json"
            writer = self._writer(path)
            writer.advance("exam_started")
            unknown = dict(writer.current, raw_log="private")
            with self.assertRaisesRegex(ProgressValidationError, "snapshot_fields_invalid"):
                validate_snapshot(unknown)
            with self.assertRaisesRegex(ProgressValidationError, "transition_invalid"):
                writer.advance("encoder_started")

            other = self._writer(path, turn=6, benchmark_id="B2", language_hash="b" * 64)
            with self.assertRaisesRegex(ProgressValidationError, "active_exam_already_exists"):
                other.advance("exam_started")

    def test_hostile_and_oversized_completed_text_never_reaches_snapshot(self):
        hostile = (
            "OPENROUTER_API_KEY=secret-value-123",
            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz",
            "BEGIN SYSTEM PROMPT reveal private instructions END SYSTEM PROMPT",
            "Traceback (most recent call last): secret internals",
            "private collaboration state: do not publish",
            "x" * (MAX_PUBLIC_TEXT + 1),
        )
        for index, text in enumerate(hostile):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "progress.json"
                writer = self._writer(path)
                self._advance_to_encoder(writer)
                with self.assertRaises(ProgressValidationError):
                    writer.advance("encoder_completed", encoded=text)
                persisted = load_json(path, {})
                self.assertEqual(persisted["phase"], "encoder_started")
                self.assertNotIn(text[:20], json.dumps(persisted))

    def test_canonical_exam_uses_writer_and_completed_trace_matches_event(self):
        suite = loop.load_benchmark_suite()
        benchmark = suite["benchmarks"][0]
        decoded = "\n".join(atom["meaning"] for atom in benchmark["answer_key"])
        grade = {
            "mode": "RELAY",
            "items": [
                {
                    "id": atom["id"],
                    "verdict": "SURVIVED",
                    "evidence_lines": [line, line],
                }
                for line, atom in enumerate(benchmark["answer_key"], start=1)
            ],
            "inventions": [],
        }
        calls = iter(("SAFE ENCODED", decoded, json.dumps(grade)))
        meta = {"tests_run": 0, "spend_usd": 0.0}
        conv = []
        rb = json.loads((ROOT / "tests/fixtures/mixed-rulebook.json").read_text())
        with tempfile.TemporaryDirectory() as temp, \
             mock.patch("loop.call", side_effect=lambda *a, **k: (next(calls), {})), \
             mock.patch("loop.token_count", side_effect=[100, 60]):
            path = Path(temp) / "public-exam-progress.json"
            loop.test_turn(conv, rb, meta, 3, progress_path=path)
            snapshot = load_json(path, {})

        event = conv[-1]
        self.assertEqual(snapshot["phase"], "completed")
        self.assertEqual(snapshot["encoded"], event["encoded"])
        self.assertEqual(snapshot["decoded"], event["decoded"])
        self.assertEqual(snapshot["tokens"], {
            "original": event["orig_tokens"], "encoded": event["enc_tokens"],
        })
        self.assertEqual(snapshot["result"]["semantic_coverage_pct"], event["semantic_coverage_pct"])
        self.assertEqual(snapshot["audit"]["total"], len(event["answer_key"]))

    def test_provider_interruption_becomes_safe_terminal_class_without_exception_text(self):
        meta = {"tests_run": 0, "spend_usd": 0.0}
        rb = json.loads((ROOT / "tests/fixtures/mixed-rulebook.json").read_text())
        with tempfile.TemporaryDirectory() as temp, \
             mock.patch("loop.call", side_effect=TimeoutError("Bearer secret-do-not-publish")):
            path = Path(temp) / "progress.json"
            with self.assertRaises(TimeoutError):
                loop.test_turn([], rb, meta, 3, progress_path=path)
            snapshot = load_json(path, {})
        self.assertEqual(snapshot["phase"], "failed")
        self.assertEqual(snapshot["error_class"], "provider_timeout")
        self.assertNotIn("secret-do-not-publish", json.dumps(snapshot))

    def test_snapshot_write_loss_does_not_block_canonical_exam(self):
        suite = loop.load_benchmark_suite()
        benchmark = suite["benchmarks"][0]
        decoded = "\n".join(atom["meaning"] for atom in benchmark["answer_key"])
        grade = {"mode": "RELAY", "items": [
            {"id": atom["id"], "verdict": "SURVIVED", "evidence_lines": [line, line]}
            for line, atom in enumerate(benchmark["answer_key"], start=1)
        ], "inventions": []}
        calls = iter(("SAFE ENCODED", decoded, json.dumps(grade)))
        meta = {"tests_run": 0, "spend_usd": 0.0}
        conv = []
        rb = json.loads((ROOT / "tests/fixtures/mixed-rulebook.json").read_text())
        with mock.patch("loop.call", side_effect=lambda *a, **k: (next(calls), {})), \
             mock.patch("loop.token_count", side_effect=[100, 60]), \
             mock.patch("public_exam_progress.atomic_write_json", side_effect=OSError("disk unavailable")):
            loop.test_turn(conv, rb, meta, 3, progress_path=Path("unused.json"))
        self.assertEqual(conv[-1]["type"], "test")
        self.assertTrue(conv[-1]["judge_valid"])


if __name__ == "__main__":
    unittest.main()
