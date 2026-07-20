#!/usr/bin/env python3
"""Prepare or apply one review-gated rulebook cleanup bundle."""
from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path
from typing import Any

from state_store import atomic_write_json, load_json, snapshot_hash

OPERATIONAL = re.compile(r"\b(system prompt|api key|password|deploy|timer|cron|vote|adopt|reject|human approval)\b", re.I)


def validate_replacement(source: dict[str, Any], replacement: dict[str, Any]) -> None:
    adopted_ids = {r["id"] for r in source.get("rules", []) if r.get("status") == "adopted"}
    covered: list[str] = []
    for rule in replacement.get("rules", []):
        if rule.get("status") != "adopted":
            raise ValueError("replacement contains non-adopted active rule")
        if OPERATIONAL.search(rule.get("text_en", "")):
            raise ValueError("replacement contains operational text")
        sources = rule.get("source_ids")
        if not isinstance(sources, list) or not sources:
            raise ValueError("every replacement rule requires source_ids")
        covered.extend(sources)
    if set(covered) != adopted_ids or len(covered) != len(set(covered)):
        raise ValueError("replacement must cover every adopted source exactly once")


def prepare(source_path: Path, replacement_path: Path, audit_path: Path, output_dir: Path) -> dict[str, Any]:
    source = load_json(source_path, None)
    replacement = load_json(replacement_path, None)
    audit = load_json(audit_path, None)
    if not all(isinstance(x, dict) for x in (source, replacement, audit)):
        raise ValueError("source, replacement, and audit must be JSON objects")
    validate_replacement(source, replacement)
    output_dir.mkdir(parents=True, exist_ok=True)
    original_out = output_dir / "original.json"
    replacement_out = output_dir / "replacement.json"
    audit_out = output_dir / "audit.json"
    atomic_write_json(original_out, source)
    atomic_write_json(replacement_out, replacement)
    atomic_write_json(audit_out, audit)
    before = json.dumps(source, indent=2, sort_keys=True).splitlines()
    after = json.dumps(replacement, indent=2, sort_keys=True).splitlines()
    diff = "\n".join(difflib.unified_diff(before, after, "original.json", "replacement.json", lineterm="")) + "\n"
    (output_dir / "exact.diff").write_text(diff)
    manifest = {"status": "pending_iso", "source_path": str(source_path.resolve()),
                "source_hash": snapshot_hash(source), "replacement_hash": snapshot_hash(replacement),
                "audit_hash": snapshot_hash(audit), "applied": False}
    atomic_write_json(output_dir / "manifest.json", manifest)
    return manifest


def apply_bundle(active_path: Path, bundle_dir: Path, approval_path: Path) -> None:
    manifest = load_json(bundle_dir / "manifest.json", {})
    active = load_json(active_path, None)
    replacement = load_json(bundle_dir / "replacement.json", None)
    approval = load_json(approval_path, {})
    if approval.get("approved") is not True:
        raise ValueError("missing explicit approval receipt")
    if snapshot_hash(active) != manifest.get("source_hash"):
        raise ValueError("active source hash changed")
    if snapshot_hash(replacement) != manifest.get("replacement_hash"):
        raise ValueError("replacement hash changed")
    if approval.get("source_hash") != manifest["source_hash"] or approval.get("replacement_hash") != manifest["replacement_hash"]:
        raise ValueError("approval hashes do not match bundle")
    atomic_write_json(active_path, replacement)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--source", type=Path, required=True)
    prep.add_argument("--replacement", type=Path, required=True)
    prep.add_argument("--audit", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    app = sub.add_parser("apply")
    app.add_argument("--active", type=Path, required=True)
    app.add_argument("--bundle", type=Path, required=True)
    app.add_argument("--approval", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        print(json.dumps(prepare(args.source, args.replacement, args.audit, args.output), indent=2))
    else:
        apply_bundle(args.active, args.bundle, args.approval)


if __name__ == "__main__":
    main()
