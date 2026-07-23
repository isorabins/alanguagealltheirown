import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import state_store


class StateStoreTests(unittest.TestCase):
    def test_atomic_write_survives_reload_and_has_stable_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "state.json"
            state_store.atomic_write_json(path, {"b": 2, "a": [1]})
            self.assertEqual(json.loads(path.read_text()), {"a": [1], "b": 2})
            self.assertEqual(state_store.snapshot_hash({"a": [1], "b": 2}),
                             state_store.snapshot_hash({"b": 2, "a": [1]}))

    def test_replace_failure_preserves_previous_file_and_removes_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text('{"old":true}')
            with mock.patch("state_store.os.replace", side_effect=OSError("crash")):
                with self.assertRaises(OSError):
                    state_store.atomic_write_json(path, {"new": True})
            self.assertEqual(json.loads(path.read_text()), {"old": True})
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])


if __name__ == "__main__": unittest.main()
