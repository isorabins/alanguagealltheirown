# US3 Offline Evidence — Rulebook Cleanup

Result: **PASS with fixture outputs; paid A/B cleanup and production application remain blocked by G4/G8**.

- `test_cleanup_rulebook.py` prepares an immutable fixture bundle containing `original.json`, `replacement.json`, `audit.json`, `exact.diff`, and `manifest.json`.
- Preparation leaves the active source byte-identical.
- Replacement validation requires every adopted source id exactly once, rejects omissions/duplicates, permits consolidation through `source_ids`, and rejects operational content.
- Apply rejects missing approval, changed source, changed replacement, or mismatched approval hashes.
- No production `state/` file was modified and no model/provider call was made.
