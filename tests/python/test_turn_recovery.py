"""Protected runner behavior: real turns + filesystem, offline provider adapter."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import loop
from collaboration import empty_state, append_inbox_spool, import_inbox_spool, deliver_one, write_outbox
import collab_sync
from tests.python.test_collaboration_inbox import FakeRedis
from state_store import atomic_write_json, load_json
from turn_store import TurnState, TurnStore, TurnRecoveryError


class RunnerRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.addCleanup(loop.disable_cost_receipt_ledger)
        for name, value in [('STATE', self.root), ('SPEND_CAP', 999)]:
            self.stack.enter_context(mock.patch.object(loop, name, value))
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.stack.enter_context(mock.patch.object(loop, 'token_count', return_value=10))
        self.stack.enter_context(mock.patch.object(loop.requests, 'post', side_effect=AssertionError('network forbidden')))
        self.stack.enter_context(mock.patch.object(loop, 'maybe_run_automatic_cleanup'))
        self.projection = self.stack.enter_context(mock.patch.object(loop, 'write_viewer_state'))
        self.calls = []
        self.stack.enter_context(mock.patch.object(loop, 'call', side_effect=self.provider))

    def provider(self, model, system, user, **kwargs):
        self.calls.append(model)
        motion = ({'kind': 'PROPOSE', 'text': 'Use EXAMPLE for an explicitly declared reusable meaning.'}
                  if len(self.calls) == 1 else {'kind': 'ADOPT', 'target_rule_id': 'rule-001'})
        return json.dumps({'deliberation': 'One explicit marker.', 'motion': motion,
                           'fault_response': None, 'measurements': [], 'requests': []}), {'completion_tokens': 10}

    def test_restart_completes_prepared_proposal_before_b_adopts_same_rule(self):
        (self.root/"pending-notice.txt").write_text("A durable human notice.")
        def interrupted(path, value):
            if path.name == 'rulebook.json':
                raise OSError('power loss before language replacement')
            atomic_write_json(path, value)
        with mock.patch('turn_store.atomic_write_json', side_effect=interrupted):
            with self.assertRaises(OSError): loop.run(1)
        self.assertEqual(load_json(self.root/'conversation.json', [])[-1]['turn'], 1)
        loop.disable_cost_receipt_ledger()
        loop.run(1)
        conv = load_json(self.root/'conversation.json', [])
        rules = load_json(self.root/'rulebook.json', {})['rules']
        self.assertEqual([e['agent'] for e in conv if e.get('type') == 'message'], ['A', 'B'])
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]['id'], 'rule-001')
        self.assertEqual(rules[0]['status'], 'adopted')
        self.assertEqual(len(self.calls), 2)
        self.assertEqual([e["content"] for e in conv if e.get("type") == "notice"], ["A durable human notice."])
        self.assertFalse((self.root/"pending-notice.txt").exists())
        self.assertEqual(loop.latest_post_state_receipt(conv)['next_actor'], 'A')

    def test_capped_restart_repairs_projection_after_commit_without_changing_freshness(self):
        # Startup projection succeeds; publication after the committed turn fails.
        self.projection.side_effect = [None, OSError('projection interrupted')]
        with self.assertRaises(OSError): loop.run(1)
        self.assertFalse((self.root/'turn-commit.local.json').exists())
        committed_at = load_json(self.root/'meta.json', {})['last_completed_turn_at']
        self.projection.reset_mock(side_effect=True)
        loop.disable_cost_receipt_ledger()
        with mock.patch.object(loop, 'SPEND_CAP', 0): loop.run(1)
        self.projection.assert_called_once()
        self.assertEqual(self.projection.call_args.args[0][-1]['turn'], 1)
        self.assertEqual(self.projection.call_args.args[2]['last_completed_turn_at'], committed_at)
        self.assertEqual(len(self.calls), 1)

    def test_archive_recovers_prepared_work_and_cannot_resurrect_it(self):
        state = TurnState([{'turn': 1}], {'rules': []}, {}, empty_state(), [])
        with TurnStore(self.root).writer() as store:
            with mock.patch.object(store, '_materialize', side_effect=OSError('power loss')):
                with self.assertRaises(OSError): store.commit(state)
        loop.archive('saved')
        self.assertEqual(load_json(self.root/'tuning-runs/saved/conversation.json', []), state.conversation)
        with TurnStore(self.root).writer() as store:
            blank = TurnState([], {}, {}, empty_state(), [])
            loaded = store.load(blank)
            self.assertEqual(loaded.conversation, [])
            self.assertEqual(loaded.rulebook, {})
            self.assertEqual(loaded.collaboration["suggestions"], [])
            self.assertEqual(loaded.collaboration["asks"], [])
            with self.assertRaises(TurnRecoveryError): loop.archive('overlap')
        self.assertFalse((self.root/'turn-commit.local.json').exists())

    def test_archive_retires_spool_and_stale_remote_recovery_but_accepts_new_input(self):
        suggestion = {'id': 'retired', 'kind': 'SUGGESTION', 'text': 'Old idea', 'status': 'approved'}
        previous = empty_state()
        previous['suggestions'] = [dict(suggestion, status='acted')]
        previous['processed_inbox_ids'] = ['retired']
        with TurnStore(self.root).writer() as store:
            store.commit(TurnState([], {}, {}, previous, []))
        inbox = self.root/'collaboration-inbox.json'
        append_inbox_spool(inbox, [suggestion], previous)
        write_outbox(self.root/'collaboration-outbox.json', previous)
        redis = FakeRedis()
        redis.publish_private(previous)
        loop.archive('retired')
        self.assertIsNone(deliver_one(import_inbox_spool(empty_state(), inbox), 'SUGGESTION', 'A'))
        # A late courier can still see an old remote backup and duplicate record.
        redis.enqueue('suggestion', suggestion)
        collab_sync.pull(redis, inbox)
        fresh = import_inbox_spool(empty_state(), inbox)
        self.assertEqual(fresh['suggestions'], [])
        self.assertIsNone(deliver_one(fresh, 'SUGGESTION', 'A'))
        collab_sync.push(redis, self.root/'collaboration-outbox.json')
        self.assertEqual(redis.load_private()['suggestions'], [])
        new = dict(suggestion, id='new', text='New idea')
        redis.enqueue('suggestion', new)
        collab_sync.pull(redis, inbox)
        fresh = import_inbox_spool(fresh, inbox)
        self.assertEqual(deliver_one(fresh, 'SUGGESTION', 'A')['id'], 'new')
        self.assertIsNone(deliver_one(fresh, 'SUGGESTION', 'A'))
        write_outbox(self.root/'collaboration-outbox.json', fresh)
        collab_sync.push(redis, self.root/'collaboration-outbox.json')
        collab_sync.pull(redis, inbox)
        restored = import_inbox_spool(empty_state(), inbox)
        self.assertEqual([r['id'] for r in restored['suggestions']], ['new'])
        self.assertIsNone(deliver_one(restored, 'SUGGESTION', 'A'))
        self.assertTrue((self.root/'tuning-runs/retired/collaboration-inbox.json').exists())

    def test_interrupted_archive_replays_moves_and_reseed_before_next_turn(self):
        # Failure after any move, or during any reset write, must be resumable.
        for fail_at in range(1, 12):
            with self.subTest(fail_at=fail_at), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                previous = empty_state()
                previous['suggestions'] = [{'id': 'old', 'status': 'acted'}]
                with TurnStore(root).writer() as store:
                    store.commit(TurnState([{'turn': 1}], {'rules': []}, {}, previous, []))
                append_inbox_spool(root/'collaboration-inbox.json', [{'id': 'old', 'kind': 'SUGGESTION', 'status': 'approved'}])
                write_outbox(root/'collaboration-outbox.json', previous)
                original_rename = Path.rename
                count = 0
                def checkpoint():
                    nonlocal count
                    count += 1
                    if count == fail_at:
                        raise OSError('archive interrupted')
                def rename(path, target):
                    result = original_rename(path, target)
                    checkpoint()
                    return result
                def write(path, value):
                    atomic_write_json(path, value)
                    if path.name != 'turn-archive.local.json':
                        checkpoint()
                with TurnStore(root).writer() as store:
                    with mock.patch.object(Path, 'rename', rename), mock.patch('turn_store.atomic_write_json', side_effect=write):
                        with self.assertRaises(OSError): store.archive('saved')
                # Courier must not import/publish a half-reset run.
                redis = FakeRedis()
                redis.enqueue('suggestion', {'id': 'later', 'kind': 'SUGGESTION'})
                collab_sync.pull(redis, root/'collaboration-inbox.json')
                self.assertEqual(len(redis.queues['test:queue:suggestion']), 1)
                with TurnStore(root).writer() as store:
                    fresh = store.load(TurnState([], {}, {}, empty_state(), []))
                    again = store.load(TurnState([], {}, {}, empty_state(), []))
                self.assertEqual(fresh, again)
                self.assertEqual(fresh.conversation, [])
                self.assertEqual(fresh.collaboration['suggestions'], [])
                self.assertIn('old', fresh.collaboration['processed_inbox_ids'])
                self.assertEqual(load_json(root/'tuning-runs/saved/collaboration.json', {}), previous)
                self.assertFalse((root/'turn-archive.local.json').exists())

    def test_courier_does_not_cross_active_archive_writer(self):
        redis = FakeRedis()
        redis.enqueue('suggestion', {'id': 'later', 'kind': 'SUGGESTION'})
        with TurnStore(self.root).writer():
            collab_sync.pull(redis, self.root/'collaboration-inbox.json')
            self.assertEqual(len(redis.queues['test:queue:suggestion']), 1)
        collab_sync.pull(redis, self.root/'collaboration-inbox.json')
        self.assertEqual(len(redis.queues['test:queue:suggestion']), 0)

    def test_failure_before_prepare_does_not_consume_human_notice(self):
        notice = self.root/'pending-notice.txt'
        notice.write_text('Keep this notice.\n')
        with mock.patch.object(loop, 'call', side_effect=OSError('provider down')):
            with self.assertRaises(OSError): loop.run(1)
        self.assertEqual(notice.read_text(), 'Keep this notice.\n')
        self.assertFalse((self.root/'turn-commit.local.json').exists())
