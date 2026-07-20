import json
import tempfile
import unittest
from pathlib import Path

from cleanup_rulebook import apply_bundle, prepare
from state_store import snapshot_hash

ROOT = Path(__file__).parents[2]
FIX = ROOT / "tests/fixtures/cleanup"


class CleanupTests(unittest.TestCase):
    def test_prepare_is_snapshot_only_and_apply_needs_exact_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory); active = directory / "active.json"
            active.write_text((FIX / "source.json").read_text())
            before = active.read_bytes(); bundle = directory / "bundle"
            manifest = prepare(active, FIX / "replacement.json", FIX / "audit.json", bundle)
            self.assertEqual(before, active.read_bytes()); self.assertEqual(manifest["status"], "pending_iso")
            self.assertTrue((bundle / "exact.diff").read_text().startswith("--- original.json"))
            with self.assertRaises(ValueError): apply_bundle(active, bundle, directory / "missing.json")
            receipt = directory / "approval.json"
            receipt.write_text(json.dumps({"approved":True,"source_hash":manifest["source_hash"],
                                           "replacement_hash":manifest["replacement_hash"]}))
            apply_bundle(active, bundle, receipt)
            self.assertEqual(snapshot_hash(json.loads(active.read_text())), manifest["replacement_hash"])

    def test_source_mismatch_and_operational_text_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory); bundle = directory / "bundle"
            bad = json.loads((FIX / "replacement.json").read_text()); bad["rules"][0]["text_en"] += " deploy the timer"
            bad_path = directory / "bad.json"; bad_path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError): prepare(FIX / "source.json", bad_path, FIX / "audit.json", bundle)


if __name__ == "__main__": unittest.main()
