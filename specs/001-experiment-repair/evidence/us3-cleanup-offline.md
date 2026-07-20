# US3 Offline Evidence — Rulebook Cleanup

Result: **PASS with fixture outputs; paid A/B cleanup and production application remain blocked by G4/G8**.

- `test_cleanup_rulebook.py` prepares an immutable fixture bundle containing `original.json`, `replacement.json`, `audit.json`, `applied-rulebook.json`, `exact.diff`, and `manifest.json`.
- Preparation leaves the active source byte-identical.
- Replacement validation requires every adopted source id exactly once, rejects omissions/duplicates, permits consolidation through `source_ids`, and rejects operational content. The audit must pass with empty gap lists and bind the exact source/candidate hashes.
- The applied ledger retains all prior ids and rejected/proposed history, marks old adopted sources historical, and appends newly numbered adopted cleanup rules.
- Apply rejects missing approval, changed source, changed replacement, or mismatched approval hashes, then records the approval hash in the manifest.
- No production `state/` file was modified and no model/provider call was made.
