#!/usr/bin/env python3
"""Hash-bound repair for legacy open motions; adopted language is immutable."""
from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
from pathlib import Path
from typing import Any

from rulebook import language_payload
from state_store import atomic_write_json, load_json, snapshot_hash


REPAIR_KIND = "legacy_motion_terminalization"
LEGACY_OPEN_STATUSES = ("proposed", "reverted")


def _status_counts(rulebook: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for rule in rulebook.get("rules", []):
        status = str(rule.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def _open_count(rulebook: dict[str, Any]) -> int:
    return sum(
        rule.get("status") == "proposed"
        or isinstance(rule.get("pending_repeal"), dict)
        for rule in rulebook.get("rules", [])
    )


def terminalize_legacy_motions(
    source: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Terminalize legacy proposals while preserving adopted records exactly."""
    if not isinstance(source, dict) or not isinstance(source.get("rules"), list):
        raise ValueError("source must be a rulebook object with a rules array")
    pending_repeals = [
        rule.get("id") for rule in source["rules"]
        if isinstance(rule.get("pending_repeal"), dict)
    ]
    if pending_repeals:
        raise ValueError(
            "pending repeal requires separate governance resolution: "
            + ", ".join(str(rule_id) for rule_id in pending_repeals)
        )

    repaired = copy.deepcopy(source)
    adopted_before = [
        copy.deepcopy(rule) for rule in source["rules"]
        if rule.get("status") == "adopted"
    ]
    language_before = language_payload(source)
    terminalized = {status: 0 for status in LEGACY_OPEN_STATUSES}
    changed_ids: list[str] = []

    for rule in repaired["rules"]:
        previous = rule.get("status")
        if previous not in LEGACY_OPEN_STATUSES:
            continue
        rule["status"] = "historical"
        rule.setdefault("history", []).append({
            "verb": "legacy_motion_terminalized",
            "source_status": previous,
        })
        terminalized[previous] += 1
        changed_ids.append(str(rule.get("id")))

    adopted_after = [
        rule for rule in repaired["rules"]
        if rule.get("status") == "adopted"
    ]
    if adopted_after != adopted_before:
        raise ValueError("repair changed an adopted rule")
    if language_payload(repaired) != language_before:
        raise ValueError("repair changed the adopted language")

    report = {
        "kind": REPAIR_KIND,
        "terminalized": terminalized,
        "legacy_records_before": sum(terminalized.values()),
        "changed_rule_ids": changed_ids,
        "open_before": _open_count(source),
        "open_after": _open_count(repaired),
        "adopted_count": len(adopted_before),
        "adopted_records_hash": snapshot_hash({"rules": adopted_before}),
        "language_hash": language_before["hash"],
        "language_version": language_before["version"],
        "status_counts_before": _status_counts(source),
        "status_counts_after": _status_counts(repaired),
    }
    return repaired, report


def _diff(source: dict[str, Any], replacement: dict[str, Any]) -> str:
    before = json.dumps(source, indent=2, sort_keys=True).splitlines()
    after = json.dumps(replacement, indent=2, sort_keys=True).splitlines()
    return "\n".join(
        difflib.unified_diff(
            before,
            after,
            "original.json",
            "replacement.json",
            lineterm="",
        )
    ) + "\n"


def prepare(source_path: Path, output_dir: Path) -> dict[str, Any]:
    """Create immutable review artifacts without changing the source."""
    source = load_json(source_path, None)
    if not isinstance(source, dict):
        raise ValueError("source must be a JSON object")
    replacement, report = terminalize_legacy_motions(source)
    if report["open_before"] == 0:
        raise ValueError("source has no legacy open motions")
    if report["open_after"] != 0:
        raise ValueError("repair left open motions")

    output_dir.mkdir(parents=True, exist_ok=True)
    exact_diff = _diff(source, replacement)
    source_hash = snapshot_hash(source)
    replacement_hash = snapshot_hash(replacement)
    diff_hash = hashlib.sha256(exact_diff.encode()).hexdigest()
    manifest = {
        **report,
        "source_path": source_path.as_posix(),
        "source_hash": source_hash,
        "replacement_hash": replacement_hash,
        "diff_hash": diff_hash,
        "status": "pending_iso",
        "applied": False,
    }
    atomic_write_json(output_dir / "original.json", source)
    atomic_write_json(output_dir / "replacement.json", replacement)
    (output_dir / "exact.diff").write_text(exact_diff)
    atomic_write_json(output_dir / "manifest.json", manifest)
    return manifest


def apply_bundle(
    active_path: Path,
    bundle_dir: Path,
    approval_path: Path,
) -> dict[str, Any]:
    """Apply an approved bundle once; a retry after the write is idempotent."""
    manifest = load_json(bundle_dir / "manifest.json", {})
    original = load_json(bundle_dir / "original.json", None)
    replacement = load_json(bundle_dir / "replacement.json", None)
    active = load_json(active_path, None)
    approval = load_json(approval_path, {})
    if not all(isinstance(value, dict) for value in (manifest, original, replacement, active)):
        raise ValueError("bundle and active rulebook must be JSON objects")
    if manifest.get("kind") != REPAIR_KIND:
        raise ValueError("wrong repair bundle kind")
    if approval.get("approved") is not True or approval.get("kind") != REPAIR_KIND:
        raise ValueError("missing exact legacy-motion approval receipt")

    expected, report = terminalize_legacy_motions(original)
    if expected != replacement or report["open_after"] != 0:
        raise ValueError("replacement does not match deterministic repair")
    if snapshot_hash(original) != manifest.get("source_hash"):
        raise ValueError("original source hash changed")
    if snapshot_hash(replacement) != manifest.get("replacement_hash"):
        raise ValueError("replacement hash changed")
    if hashlib.sha256((bundle_dir / "exact.diff").read_bytes()).hexdigest() != manifest.get("diff_hash"):
        raise ValueError("exact diff changed")
    if (
        approval.get("source_hash") != manifest["source_hash"]
        or approval.get("replacement_hash") != manifest["replacement_hash"]
    ):
        raise ValueError("approval hashes do not match bundle")

    active_hash = snapshot_hash(active)
    if active_hash == manifest["source_hash"]:
        atomic_write_json(active_path, replacement)
        idempotent_retry = False
    elif active_hash == manifest["replacement_hash"]:
        idempotent_retry = True
    else:
        raise ValueError("active source hash changed")

    manifest.update({
        "status": "applied",
        "applied": True,
        "idempotent_retry": idempotent_retry,
        "approval_hash": snapshot_hash(approval),
    })
    atomic_write_json(bundle_dir / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--source", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    apply = sub.add_parser("apply")
    apply.add_argument("--active", type=Path, required=True)
    apply.add_argument("--bundle", type=Path, required=True)
    apply.add_argument("--approval", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        print(json.dumps(prepare(args.source, args.output), indent=2))
    else:
        print(json.dumps(apply_bundle(args.active, args.bundle, args.approval), indent=2))


if __name__ == "__main__":
    main()
