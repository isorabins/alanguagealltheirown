"""Product promises exercised through the same deep interfaces as the runner.

Keep expected behavior when implementations change. A requested behavior change
must explain which expectation changes; do not replace these with mock-call tests.
"""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import exam_evidence
import legislature
import loop
from collaboration import empty_state, stable_record
from legislative_protocol import derive_semantic_fault_ledger
from rulebook import language_payload
from state_store import atomic_write_json
from turn_store import TurnState, TurnStore

ROOT = Path(__file__).parents[2]


class ModuleContractTests(unittest.TestCase):
    def setUp(self):
        self.book = json.loads((ROOT/'tests/fixtures/mixed-rulebook.json').read_text())
        self.state = TurnState([], self.book, {'tests_run': 0, 'spend_usd': 0.0}, empty_state(), [])
        self.suite = loop.load_benchmark_suite()
        self.benchmark = self.suite['benchmarks'][0]
        self.resources = exam_evidence.ExamResources(ROOT, self.suite, 'encoder', 'decoder', 'judge')

    def exam(self, turn, verdict='SURVIVED', invalid_span=False, progress_path=None):
        benchmark = self.benchmark
        self.state.meta['benchmark_suite'] = {'version': self.suite['version'], 'next_index': 0, 'cycle': 1}
        decoded = '\n'.join(atom['meaning'] for atom in benchmark['answer_key'])
        items = [{'id': atom['id'], 'verdict': verdict,
                  'evidence_lines': [] if verdict == 'MISSING' else [n, n]}
                 for n, atom in enumerate(benchmark['answer_key'], 1)]
        if invalid_span: items[0]['evidence_lines'] = [9999, 9999]
        responses = iter([('ENCODED', {}), (decoded, {}), (json.dumps({'mode': 'RELAY', 'items': items, 'inventions': []}), {})])
        requests = []
        def provider(model, system, user, **options):
            requests.append((model, system, user))
            return next(responses)
        tokens = iter([100, 60])
        with contextlib.redirect_stdout(io.StringIO()):
            completed = exam_evidence.run_exam(self.state, turn, resources=self.resources,
                provider=provider, count_tokens=lambda _: next(tokens), progress_path=progress_path)
        self.assertEqual([r[0] for r in requests], ['encoder', 'decoder', 'judge'])
        self.assertEqual(requests[1][2], 'ENCODED')
        return completed

    def test_invalid_raw_judge_evidence_preserves_baseline_and_cannot_create_a_fault(self):
        self.exam(1506)
        before = copy.deepcopy(self.state.meta['benchmark_results_v2'])
        self.exam(1509, invalid_span=True)
        event = self.state.conversation[-1]
        self.assertFalse(event['judge_valid'])
        self.assertIn('invalid_evidence_line_range', event['judge_reason'])
        self.assertEqual(self.state.meta['benchmark_results_v2'], before)
        self.assertEqual(derive_semantic_fault_ledger(self.state.conversation), [])
        self.assertEqual(self.state.meta['tests_run'], 2)
        self.assertEqual(self.state.meta['benchmark_suite']['next_index'], 1)

    def test_valid_failure_and_valid_retest_drive_fault_lifecycle_from_raw_responses(self):
        self.exam(1506, verdict='MISSING')
        faults = derive_semantic_fault_ledger(self.state.conversation)
        self.assertTrue(faults)
        self.assertTrue(all(f.status == 'UNRESOLVED' for f in faults))
        self.exam(1509)
        self.assertTrue(all(f.status == 'RESOLVED' for f in derive_semantic_fault_ledger(self.state.conversation)))
        self.assertEqual(self.state.meta['benchmark_results_v2']['B1']['turn'], 1509)

    def test_persisted_fabricated_evidence_cannot_create_faults(self):
        self.exam(1506, verdict='CORRUPTED')
        event = self.state.conversation[-1]
        self.assertTrue(derive_semantic_fault_ledger([event]))
        for result in event['atom_results']:
            result['evidence'] = 'FABRICATED_NOT_IN_DECODED'
        for failure in event['critical_failures']:
            failure['decoded_evidence'] = 'FABRICATED_NOT_IN_DECODED'
        self.assertEqual(derive_semantic_fault_ledger([event]), [])

    def test_persisted_literal_conflict_cannot_resolve_existing_faults(self):
        self.exam(1506, verdict='MISSING')
        self.exam(1509)
        event = self.state.conversation[-1]
        atom = next(a for a in event['answer_key'] if a['critical'] and a['literal_sets'])
        result = next(r for r in event['atom_results'] if r['id'] == atom['id'])
        # A real span, but not the literal-bearing span the judge claimed survived.
        event['decoded'] += '\nA sentence without the required literal.'
        result['evidence'] = 'A sentence without the required literal.'
        ledger = derive_semantic_fault_ledger(self.state.conversation)
        self.assertTrue(ledger)
        self.assertTrue(all(f.status == 'UNRESOLVED' for f in ledger))

    def test_completed_exam_and_language_recover_together_at_every_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = self.exam(1506, progress_path=Path(tmp)/'attempt.local.json')
            self.assertEqual(completed['phase'], 'completed')
            self.state.public_exam_progress = completed
            # Prepare + five experiment files + terminal public trace.
            for failed_write in range(1, 7):
                directory = Path(tmp)/str(failed_write)
                with self.subTest(failed_write=failed_write), TurnStore(directory).writer() as store:
                    count = 0
                    def write(path, value):
                        nonlocal count
                        count += 1
                        if count == failed_write + 1: raise OSError('power loss')
                        atomic_write_json(path, value)
                    with mock.patch('turn_store.atomic_write_json', side_effect=write):
                        with self.assertRaises(OSError): store.commit(self.state)
                with TurnStore(directory).writer() as store:
                    result = store.load(TurnState([], {}, {}, {}, []))
                self.assertEqual(result.public_exam_progress, completed)
                self.assertEqual(result.conversation[-1]['turn'], completed['turn'])
                self.assertEqual(language_payload(result.rulebook)['hash'], completed['language_hash'])
                self.assertEqual(result.meta['benchmark_results_v2']['B1']['turn'], 1506)

    def test_structural_exhaustion_keeps_actor_language_and_delivery_eligibility(self):
        self.state.rulebook = {'version': '0.0', 'changes': 0, 'next_id': 1, 'kernel_tokens': 10, 'rules': []}
        loop.ensure_structured_protocol_cutover(self.state.conversation, self.state.rulebook, self.state.meta, activation_turn=0)
        ask = stable_record("ASK", "A", "Keep punctuation?", "ask-contract")
        ask.update(status="answered", answer="Yes, preserve it exactly.")
        self.state.collaboration["asks"].append(ask)
        before = copy.deepcopy(self.state)
        calls = []
        def provider(*args, **kwargs):
            calls.append(args)
            return 'unstructured model output', {}
        with contextlib.redirect_stdout(io.StringIO()):
            outcome = legislature.take_turn(self.state, 1, resources=loop._legislative_resources(), provider=provider, count_tokens=lambda _: 10)
        self.assertEqual(outcome, 'structural_failure')
        self.assertEqual(len(calls), 3)
        self.assertEqual(self.state.rulebook, before.rulebook)
        self.assertEqual(self.state.collaboration, before.collaboration)
        self.assertEqual(legislature.next_legislative_actor(self.state.meta), 'A')
        self.assertEqual(self.state.conversation[-1]['post_state_receipt']['next_actor'], 'A')

    def test_public_trace_publication_failure_keeps_the_exam_and_can_be_repaired(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'viewer').mkdir()
            self.state.public_exam_progress = self.exam(1506, progress_path=root/'attempt.local.json')
            with TurnStore(root/'state').writer() as store:
                store.commit(self.state)
            with mock.patch.object(loop, 'ROOT', root), mock.patch.object(loop, 'STATE', root/'state'), contextlib.redirect_stdout(io.StringIO()):
                with mock.patch.object(loop, 'publish_completed_snapshot', side_effect=OSError('public path unavailable')):
                    loop.publish_turn(self.state)
                self.assertFalse((root/'state/public-exam-progress.json').exists())
                with TurnStore(root/'state').writer() as store:
                    resumed = store.load(TurnState([], {}, {}, {}, []))
                self.assertEqual(resumed.conversation[-1]['turn'], 1506)
                self.assertEqual(resumed.public_exam_progress, self.state.public_exam_progress)
                loop.publish_turn(resumed)
                public = json.loads((root/'state/public-exam-progress.json').read_text())
                self.assertEqual(public['turn'], resumed.conversation[-1]['turn'])
                self.assertEqual(public['encoded'], resumed.conversation[-1]['encoded'])

    def test_bounded_public_preview_retains_the_real_best_and_latest_valid_exam(self):
        import public_snapshot
        best = {"type": "test", "turn": 1, "scoring_version": "v2", "judge_valid": True,
                "meaning_pass": True, "compression_success": True, "message_body_savings_pct": 43}
        latest = dict(best, turn=2, meaning_pass=False, compression_success=False, message_body_savings_pct=8)
        self.state.conversation = [best, latest] + [
            {"type": "test", "turn": turn, "scoring_version": "v2", "judge_valid": False}
            for turn in range(3, 50)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'viewer').mkdir()
            public_snapshot.write_snapshot(self.state, root, updated=None, policy=loop._public_policy())
            preview = json.loads((root/'viewer/preview.json').read_text())
            self.assertLessEqual(len(preview['conversation']), 30)
            self.assertEqual([e['turn'] for e in preview['conversation'] if e.get('judge_valid')], [1, 2])
            self.assertEqual(preview['conversation'][-1]['turn'], 49)
            self.assertLessEqual((root/'viewer/bootstrap.js').stat().st_size, 2048)
