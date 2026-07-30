# Deterministic Model-Context Compaction — Phase 25 Preflight

Date: 2026-07-30 WITA

## Result and ownership boundary

PASS for offline implementation in the clean
`codex/alato-model-context-compaction` worktree. The manager separately paused
and snapshotted production before delegation. This offline worker will not
access or mutate production, call a model/provider/web service, commit, push,
open or merge a PR, resume the timer, or change canonical state/history,
models, cadence, credentials, limits, UI, DNS, or X.

## Fixed point and supplied canonical rehearsal

- Fixed point: `origin/main`
  `9f21b0e8aae717edd1727bb21938e4a0f95fe35b`
- Preserved canonical boundary: turn `1209`
- Exact next request: turn `1210`, Agent B, open add motion `rule-132`
- Rules: `127`; recent events: `30`
- Total model-facing characters: `142,488`
- Recent event window: `59,798`
- Complete legislature: `39,423`
- Authoritative request JSON: `32,767`
- Pending lookup delivery inside that request: `14,368`
- Canonical rulebook SHA-256:
  `8bcd8c49d62581f30c5d0bf676451dbc44c6dd8af8fdbf1940b5bc115059fb45`
- Canonical conversation SHA-256:
  `d301e0508837bb457f702e01c442f627f866ad47c996165abc81c2f2f9bc8be5`

These values were supplied by the manager from the already-paused/snapshotted
production boundary; this worker did not re-read production.

## Architecture decision

The failure is deterministic prompt duplication, not a canonical-state defect.
Keep full Pydantic models, JSON, rule/event history, research rows, and receipts.
Build only ephemeral projections:

1. compact model-window receipts without attempted actions or unchanged ids;
2. current state without the duplicate 127-item rule-status list;
3. a bounded lookup/research delivery with exact correlation fields,
   direct-prefix findings, safe bounded citations, and explicit truncation
   counts;
4. one pure prompt assembler shared by runtime and tests.

An LLM summarizer, database, cache, semantic rule compression, provider change,
or validator relaxation would add failure modes and is outside the approval.

## Runway

| Dependency | Status | Evidence / stop |
|---|---|---|
| Clean worktree at fixed point | available | branch/status/hash read locally |
| Phase 24 structured protocol | available | spec/plan/tasks plus structured-protocol evidence read |
| Full canonical receipt/state models | available | `legislative_protocol.py`; unchanged persistence contract |
| Exact-once structural restoration | available | `loop.agent_turn` deep-copy restoration and existing replay tests |
| Production-shaped fixture | available offline | 127 rules, 30 events, approximately 14k lookup; no network |
| Human-app testing | not needed | no interactive/public surface changes |
| Provider or web call | not needed / prohibited | patch/assert zero network in regression |
| Production/VPS/service access | manager-owned planned stop | T202 |
| Commit/push/PR/merge | manager-owned planned stop | T202 |
| Live cost allowance | manager-owned pre-approved envelope | at most `$0.10`; not consumed offline |

## Acceptance oracle

Offline PASS requires at least a 30% prompt reduction against the same
unprojected canonical fixture; exact B/open-`rule-132` schema; the complete
legislature still present; identical rulebook/event hashes and full research
findings/citations; prompt-only omission of attempted actions, unchanged ids,
and rule-state duplication; bounded deterministic redelivery after structural
failure; and zero web/provider calls.
