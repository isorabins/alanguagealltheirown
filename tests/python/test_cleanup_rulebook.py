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


if __name__ == "__main__": unittest.main()
