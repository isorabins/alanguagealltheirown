#!/usr/bin/env python3
"""Prepare or apply one review-gated rulebook cleanup bundle."""
from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from state_store import atomic_write_json, load_json, snapshot_hash

OPERATIONAL = re.compile(r"\b(system prompt|api key|password|deploy|timer|cron|vote|adopt|reject|human approval)\b", re.I)


def validate_candidate(source: dict[str, Any], replacement: dict[str, Any]) -> None:
    """Reject an A candidate before spending a second provider call on audit."""
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


def validate_replacement(source: dict[str, Any], replacement: dict[str, Any],
                         audit: dict[str, Any]) -> None:
    validate_candidate(source, replacement)
    adopted_ids = {r["id"] for r in source.get("rules", []) if r.get("status") == "adopted"}
    if audit.get("verdict") != "pass":
        raise ValueError("audit must explicitly pass")
    audit_covered = audit.get("covered_source_ids")
    if not isinstance(audit_covered, list) or set(audit_covered) != adopted_ids or len(audit_covered) != len(set(audit_covered)):
        raise ValueError("audit must cover every adopted source exactly once")
    for field in ("omissions", "meaning_changes", "operational_text"):
        if audit.get(field) != []:
            raise ValueError(f"audit {field} must be an empty list")
    if audit.get("reviewed_source_hash") != snapshot_hash(source):
        raise ValueError("audit is not bound to this source snapshot")
    if audit.get("reviewed_candidate_hash") != snapshot_hash(replacement):
        raise ValueError("audit is not bound to this replacement candidate")


def build_applied_rulebook(source: dict[str, Any], replacement: dict[str, Any]) -> dict[str, Any]:
    """Preserve the full legislature while replacing only the active adopted view."""
    applied = copy.deepcopy(source)
    next_id = int(applied.get("next_id", 1))
    for rule in applied.get("rules", []):
        if rule.get("status") == "adopted":
            rule["status"] = "historical"
            rule.pop("pending_repeal", None)
            rule.setdefault("history", []).append({"verb": "cleanup_superseded",
                                                    "source_status": "adopted"})
        elif rule.get("status") in {"proposed", "reverted"}:
            previous = rule["status"]
            rule["status"] = "historical"
            rule.pop("pending_repeal", None)
            rule.setdefault("history", []).append({"verb": "cleanup_terminalized",
                                                    "source_status": previous})
    for candidate in replacement.get("rules", []):
        new_rule = copy.deepcopy(candidate)
        new_rule["id"] = f"rule-{next_id:03d}"
        new_rule["status"] = "adopted"
        new_rule["history"] = [{"verb": "cleanup_adopted",
                                "source_ids": copy.deepcopy(candidate["source_ids"])}]
        applied.setdefault("rules", []).append(new_rule)
        next_id += 1
    applied["next_id"] = next_id
    applied["changes"] = int(applied.get("changes", 0)) + 1
    applied["version"] = f"cleanup-{applied['changes']}"
    applied["kernel_tokens"] = None  # old active-language measurement cannot survive replacement
    return applied


def prepare(source_path: Path, replacement_path: Path, audit_path: Path, output_dir: Path) -> dict[str, Any]:
    source = load_json(source_path, None)
    replacement = load_json(replacement_path, None)
    audit = load_json(audit_path, None)
    if not all(isinstance(x, dict) for x in (source, replacement, audit)):
        raise ValueError("source, replacement, and audit must be JSON objects")
    validate_replacement(source, replacement, audit)
    applied = build_applied_rulebook(source, replacement)
    output_dir.mkdir(parents=True, exist_ok=True)
    original_out = output_dir / "original.json"
    replacement_out = output_dir / "replacement.json"
    audit_out = output_dir / "audit.json"
    atomic_write_json(original_out, source)
    atomic_write_json(replacement_out, replacement)
    atomic_write_json(audit_out, audit)
    atomic_write_json(output_dir / "applied-rulebook.json", applied)
    before = json.dumps(source, indent=2, sort_keys=True).splitlines()
    after = json.dumps(applied, indent=2, sort_keys=True).splitlines()
    diff = "\n".join(difflib.unified_diff(before, after, "original.json", "replacement.json", lineterm="")) + "\n"
    (output_dir / "exact.diff").write_text(diff)
    source_hash, candidate_hash, applied_hash = (snapshot_hash(source), snapshot_hash(replacement),
                                                  snapshot_hash(applied))
    manifest = {"status": "pending_iso", "source_path": str(source_path.resolve()),
                "source_hash": source_hash, "candidate_hash": candidate_hash,
                "replacement_hash": applied_hash,
                "audit_hash": snapshot_hash(audit),
                "diff_hash": hashlib.sha256(diff.encode()).hexdigest(), "applied": False}
    atomic_write_json(output_dir / "manifest.json", manifest)
    atomic_write_json(output_dir / "review.json", {
        "bundle_id": f"cleanup-{source_hash[:12]}-{candidate_hash[:12]}",
        "source_rulebook_hash": source_hash, "candidate_hash": candidate_hash,
        "replacement_hash": applied_hash, "original": source, "a_replacement": replacement,
        "b_audit": audit, "exact_diff": diff, "status": "pending_iso",
    })
    return manifest


def apply_bundle(active_path: Path, bundle_dir: Path, approval_path: Path) -> None:
    manifest = load_json(bundle_dir / "manifest.json", {})
    active = load_json(active_path, None)
    replacement = load_json(bundle_dir / "applied-rulebook.json", None)
    candidate = load_json(bundle_dir / "replacement.json", None)
    audit = load_json(bundle_dir / "audit.json", None)
    approval = load_json(approval_path, {})
    if approval.get("approved") is not True:
        raise ValueError("missing explicit approval receipt")
    if snapshot_hash(active) != manifest.get("source_hash"):
        raise ValueError("active source hash changed")
    if snapshot_hash(replacement) != manifest.get("replacement_hash"):
        raise ValueError("replacement hash changed")
    if snapshot_hash(candidate) != manifest.get("candidate_hash"):
        raise ValueError("candidate hash changed")
    if snapshot_hash(audit) != manifest.get("audit_hash"):
        raise ValueError("audit hash changed")
    if hashlib.sha256((bundle_dir / "exact.diff").read_bytes()).hexdigest() != manifest.get("diff_hash"):
        raise ValueError("exact diff changed")
    if approval.get("source_hash") != manifest["source_hash"] or approval.get("replacement_hash") != manifest["replacement_hash"]:
        raise ValueError("approval hashes do not match bundle")
    atomic_write_json(active_path, replacement)
    manifest.update({"status": "applied", "applied": True,
                     "approval_hash": snapshot_hash(approval)})
    atomic_write_json(bundle_dir / "manifest.json", manifest)
    review = load_json(bundle_dir / "review.json", {})
    review.update({"status": "applied", "approval_hash": snapshot_hash(approval)})
    atomic_write_json(bundle_dir / "review.json", review)


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
    candidate = sub.add_parser("validate-candidate")
    candidate.add_argument("--source", type=Path, required=True)
    candidate.add_argument("--replacement", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        print(json.dumps(prepare(args.source, args.replacement, args.audit, args.output), indent=2))
    elif args.command == "apply":
        apply_bundle(args.active, args.bundle, args.approval)
    else:
        source = load_json(args.source, None)
        replacement = load_json(args.replacement, None)
        if not isinstance(source, dict) or not isinstance(replacement, dict):
            raise ValueError("source and replacement must be JSON objects")
        validate_candidate(source, replacement)
        print(json.dumps({"result": "PASS", "candidate_hash": snapshot_hash(replacement)}))


if __name__ == "__main__":
    main()
