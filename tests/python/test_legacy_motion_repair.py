import copy
import json
import tempfile
import unittest
from pathlib import Path

from legacy_motion_repair import apply_bundle, prepare, terminalize_legacy_motions
from rulebook import apply_authorized_motion, language_payload
from state_store import snapshot_hash


ROOT = Path(__file__).parents[2]


def synthetic_rulebook():
    return {
        "version": "0.9",
        "changes": 9,
        "next_id": 5,
        "kernel_tokens": 123,
        "rules": [
            {
                "id": "rule-001",
                "text_en": "Keep this adopted rule exact.",
                "status": "adopted",
                "history": [{"verb": "adopted", "turn": 2}],
            },
            {
                "id": "rule-002",
                "text_en": "Legacy proposed rule.",
                "status": "proposed",
                "proposed_turn": 3,
                "history": [{"verb": "proposed", "turn": 3}],
            },
            {
                "id": "rule-003",
                "text_en": "Legacy reverted rule.",
                "status": "reverted",
                "proposed_turn": 4,
                "history": [{"verb": "reverted", "turn": 5}],
            },
            {
                "id": "rule-004",
                "text_en": "Already rejected rule.",
                "status": "rejected",
                "history": [],
            },
        ],
    }


class LegacyMotionRepairTests(unittest.TestCase):
    def test_production_shaped_snapshot_preserves_language_and_unblocks_governance(self):
        source = json.loads((
            ROOT
            / "specs/001-experiment-repair/evidence/backlog-repair/"
            "migration-bundle/original.json"
        ).read_text())
        adopted_before = [
            copy.deepcopy(rule) for rule in source["rules"]
            if rule.get("status") == "adopted"
        ]
        language_before = language_payload(source)

        repaired, report = terminalize_legacy_motions(source)

        self.assertEqual(report["terminalized"], {"proposed": 69, "reverted": 7})
        self.assertEqual(report["legacy_records_before"], 76)
        self.assertEqual(report["open_before"], 69)
        self.assertEqual(report["open_after"], 0)
        self.assertEqual(report["adopted_count"], 23)
        self.assertEqual(
            [rule for rule in repaired["rules"] if rule.get("status") == "adopted"],
            adopted_before,
        )
        self.assertEqual(language_payload(repaired), language_before)
        self.assertEqual(repaired["version"], source["version"])
        self.assertEqual(repaired["changes"], source["changes"])
        self.assertEqual(repaired["next_id"], source["next_id"])
        self.assertEqual(repaired["kernel_tokens"], source["kernel_tokens"])

        proposed = apply_authorized_motion(
            "PROPOSE: Define one new focused rule after legacy repair.",
            repaired,
            1200,
            "A",
        )
        self.assertTrue(proposed.changed)
        settled = apply_authorized_motion(
            f"ADOPT: {proposed.rule_id}",
            repaired,
            1201,
            "B",
        )
        self.assertTrue(settled.changed)
        self.assertEqual(settled.reason, "motion_applied")

    def test_transform_is_idempotent_and_records_prior_status(self):
        source = synthetic_rulebook()
        repaired, first = terminalize_legacy_motions(source)
        again, second = terminalize_legacy_motions(repaired)

        self.assertEqual(first["terminalized"], {"proposed": 1, "reverted": 1})
        self.assertEqual(second["terminalized"], {"proposed": 0, "reverted": 0})
        self.assertEqual(repaired, again)
        by_id = {rule["id"]: rule for rule in repaired["rules"]}
        self.assertEqual(by_id["rule-002"]["history"][-1], {
            "verb": "legacy_motion_terminalized",
            "source_status": "proposed",
        })
        self.assertEqual(by_id["rule-003"]["history"][-1], {
            "verb": "legacy_motion_terminalized",
            "source_status": "reverted",
        })
        self.assertEqual(by_id["rule-004"], source["rules"][3])

    def test_pending_repeal_fails_closed_to_protect_adopted_records(self):
        source = synthetic_rulebook()
        source["rules"][0]["pending_repeal"] = {
            "kind": "repeal",
            "target_id": "rule-001",
            "proposed_turn": 8,
        }
        with self.assertRaisesRegex(ValueError, "pending repeal"):
            terminalize_legacy_motions(source)

    def test_prepare_apply_and_retry_are_hash_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            active = directory / "active.json"
            active.write_text(json.dumps(synthetic_rulebook()))
            bundle = directory / "bundle"

            manifest = prepare(active, bundle)
            replacement = json.loads((bundle / "replacement.json").read_text())
            self.assertEqual(manifest["kind"], "legacy_motion_terminalization")
            self.assertEqual(manifest["status"], "pending_iso")
            self.assertEqual(manifest["source_hash"], snapshot_hash(synthetic_rulebook()))
            self.assertEqual(manifest["replacement_hash"], snapshot_hash(replacement))
            self.assertTrue((bundle / "exact.diff").read_text().startswith("--- original.json"))

            approval = directory / "approval.json"
            approval.write_text(json.dumps({
                "approved": True,
                "kind": "legacy_motion_terminalization",
                "source_hash": manifest["source_hash"],
                "replacement_hash": manifest["replacement_hash"],
            }))
            applied = apply_bundle(active, bundle, approval)
            self.assertEqual(applied["status"], "applied")
            self.assertFalse(applied["idempotent_retry"])
            self.assertEqual(snapshot_hash(json.loads(active.read_text())),
                             manifest["replacement_hash"])

            retried = apply_bundle(active, bundle, approval)
            self.assertTrue(retried["idempotent_retry"])
            self.assertEqual(snapshot_hash(json.loads(active.read_text())),
                             manifest["replacement_hash"])

    def test_apply_rejects_source_drift_tamper_and_wrong_approval_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            for case in ("source", "replacement", "diff", "approval"):
                active = directory / f"active-{case}.json"
                active.write_text(json.dumps(synthetic_rulebook()))
                bundle = directory / f"bundle-{case}"
                manifest = prepare(active, bundle)
                approval = directory / f"approval-{case}.json"
                approval.write_text(json.dumps({
                    "approved": True,
                    "kind": "wrong" if case == "approval" else "legacy_motion_terminalization",
                    "source_hash": manifest["source_hash"],
                    "replacement_hash": manifest["replacement_hash"],
                }))
                if case == "source":
                    changed = json.loads(active.read_text())
                    changed["version"] = "drifted"
                    active.write_text(json.dumps(changed))
                elif case == "replacement":
                    changed = json.loads((bundle / "replacement.json").read_text())
                    changed["version"] = "tampered"
                    (bundle / "replacement.json").write_text(json.dumps(changed))
                elif case == "diff":
                    (bundle / "exact.diff").write_text(
                        (bundle / "exact.diff").read_text() + "tamper\n"
                    )
                with self.assertRaises(ValueError):
                    apply_bundle(active, bundle, approval)


if __name__ == "__main__":
    unittest.main()
