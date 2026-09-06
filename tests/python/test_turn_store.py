import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from state_store import atomic_write_json
from turn_store import TurnRecoveryError, TurnState, TurnStore


def state(turn):
    return TurnState(
        [{"turn": turn}], {"rules": [{"id": f"rule-{turn}", "status": "adopted"}]},
        {"last_agent": "B", "benchmark_cursor": turn},
        {"deliveries": [{"id": f"delivery-{turn}"}]}, [{"turn": turn}],
    )


class CompleteTurnTests(unittest.TestCase):
    def test_failure_at_every_replacement_recovers_whole_old_or_new_turn(self):
        for failed_write in range(6):
            with self.subTest(failed_write=failed_write), tempfile.TemporaryDirectory() as tmp:
                store = TurnStore(Path(tmp))
                with store.writer():
                    store.commit(state(1))
                    count = 0
                    def fail(path, value):
                        nonlocal count
                        current = count
                        count += 1
                        if current == failed_write:
                            raise OSError("injected write failure")
                        atomic_write_json(path, value)
                    with mock.patch("turn_store.atomic_write_json", side_effect=fail):
                        with self.assertRaises(OSError):
                            store.commit(state(2))
                for _ in range(2):
                    with TurnStore(Path(tmp)).writer() as restarted:
                        actual = restarted.load(state(0))
                        self.assertEqual(actual, state(1 if failed_write == 0 else 2))
                        self.assertEqual(actual.next_turn, 2 if failed_write == 0 else 3)

    def test_interrupted_recovery_replays_again_without_losing_prepared_turn(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TurnStore(Path(tmp))
            with store.writer():
                store.commit(state(1))
                original = store._materialize
                with mock.patch.object(store, "_materialize", side_effect=OSError("stop")):
                    with self.assertRaises(OSError): store.commit(state(2))
                with mock.patch("turn_store.atomic_write_json", side_effect=OSError("stop again")):
                    with self.assertRaises(OSError): store.load(state(0))
                self.assertTrue(store.pending.exists())
                self.assertEqual(store.load(state(0)), state(2))

    def test_legacy_files_are_loaded_without_reset_or_rewrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"conversation.json"
            p.write_text('[{"turn": 200}]')
            before = p.read_bytes()
            with TurnStore(Path(tmp)).writer() as store:
                result = store.load(TurnState([], {}, {}, {}, []))
                self.assertEqual(result.next_turn, 201)
                self.assertEqual(p.read_bytes(), before)

    def test_corrupt_prepared_turn_stops_without_touching_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            with TurnStore(Path(tmp)).writer() as store:
                store.commit(state(1))
                before = (Path(tmp)/"conversation.json").read_bytes()
                for bad in ['null', '{', '{"schema_version":1,"files":{},"hash":"wrong"}']:
                    store.pending.write_text(bad)
                    with self.assertRaises(TurnRecoveryError): store.load(state(0))
                    self.assertEqual((Path(tmp)/"conversation.json").read_bytes(), before)
                    self.assertEqual(store.pending.read_text(), bad)

    def test_corrupt_archive_stops_before_canonical_state_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with TurnStore(Path(tmp)).writer() as store:
                store.commit(state(1))
                before = (Path(tmp)/"conversation.json").read_bytes()
                for bad in ['null', '{', '{"payload":{},"hash":"wrong"}']:
                    store.pending_archive.write_text(bad)
                    with self.assertRaises(TurnRecoveryError): store.load(state(0))
                    self.assertEqual((Path(tmp)/"conversation.json").read_bytes(), before)
                    self.assertEqual(store.pending_archive.read_text(), bad)

    def test_concurrent_writer_and_unlocked_use_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TurnStore(Path(tmp))
            with self.assertRaises(TurnRecoveryError): store.load(state(0))
            with store.writer():
                with self.assertRaises(TurnRecoveryError):
                    with TurnStore(Path(tmp)).writer(): pass

    def test_recovery_does_not_remove_a_replacement_notice(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            notice = directory/'pending-notice.txt'
            notice.write_text('old notice')
            completed = state(1)
            completed.consumed_notice = 'old notice'
            with TurnStore(directory).writer() as store:
                with mock.patch.object(store, '_materialize', side_effect=OSError('stop')):
                    with self.assertRaises(OSError): store.commit(completed)
            notice.write_text('new notice')
            with TurnStore(directory).writer() as store: store.load(state(0))
            self.assertEqual(notice.read_text(), 'new notice')
