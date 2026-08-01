# [Integrate and verify the ALATO roadmap draft PR](https://github.com/isorabins/alanguagealltheirown/issues/40): fixed-base review and story trace

## Review boundary

- Fixed pre-run base: `0ef2bab60f95c8e41d0ee81b9ca7beeeb06e7353`.
- Retained authored roadmap commits: `6cba726` for [Restore active legislative feedback in real prompts](https://github.com/isorabins/alanguagealltheirown/issues/36), `44e650f` for [Ship Scoring V2 development-exam evidence](https://github.com/isorabins/alanguagealltheirown/issues/37), and `e7b1c93` for [Feed valid Scoring V2 failures back to both legislators](https://github.com/isorabins/alanguagealltheirown/issues/38). The English-control work from `4080022` for [Show frozen-English comparison and 20-exchange projection](https://github.com/isorabins/alanguagealltheirown/issues/39) was removed by Iso's scope reduction.
- Current-main reconciliation: fresh-fetched `origin/main` at `bd91736` for review, then re-fetched and merged final tip `874585b` before push. This preserves the already-pushed sequential ticket history while adopting turns 1317–1335 exactly.
- Generated-only exclusions: `state/conversation.json`, `state/meta.json`, `state/public-collaboration.json`, `state/rulebook.json`, and `viewer/state.js`. They enter the branch only through the current-main merge.
- Immutable V1 proof: `benchmarks/v1.json` is byte-identical to the fixed base, SHA-256 `18ae4224645fef79dd1b14e3f9741ff5023725299ae94fe93c7f370b29d60d62`.

## Sequential review axes

### Standards

The fresh fixed-base post-removal review found three hard documentation problems directly related to the scope reduction: the field note did not name its verification sources, `CONTEXT.md` still defined the removed control concepts as active glossary terms, and this receipt still claimed that the superseded review had no remaining gap. This documentation pass repaired all three and replaced bare issue references with linked titles.

The review also noted judgment-call smells, not documented-standard violations: possible Data Clumps/Shotgun Surgery in the Scoring V2 result fields and possible Duplicated Code in viewer helpers and status construction. They are not release findings from the English-control removal and were not changed.

### Spec

Two hard findings were repaired:

1. Deterministic literal checks accepted a required literal as a substring of a larger value or identifier (`15` in `150`, `$48` in `$480`). The matcher now enforces alphanumeric/underscore token boundaries and regression tests cover valid and invalid boundaries.
2. Active feedback keyed only on rule id, so an old request could resurface after settlement when a later independent repeal targeted the same rule. Derivation now respects motion kind and stops at the current PROPOSE/REPEAL creation boundary while preserving feedback across revision, structural failure, and reconstruction.

One hard retained-scope finding remains: B2.05's deterministic alternatives reject the semantically correct plural phrase “five minutes”, so a correct scheduled B2 decode can be quarantined as an invalid judge result. This was not fixed because changing the shared Scoring V2 benchmark is outside the authorized English-control removal.

No replacement control, metric, evaluator, or experiment was added. The retained scope remains [Ship the ALATO roadmap with Scoring V2 regression protection](https://github.com/isorabins/alanguagealltheirown/issues/35), excluding the removed English-control feature.

### Design fidelity

`BLOCKED — accepted prototype not identified.` The roadmap changes the public viewer, but [Ship the ALATO roadmap with Scoring V2 regression protection](https://github.com/isorabins/alanguagealltheirown/issues/35), its sequential execution tickets, and the mission brief name no accepted revision-pinned prototype artifact or immutable screenshot set. The retained `03-v1-v2-invalid-history.png` is implementation evidence, not a prototype. The missing prototype is a review-evidence limitation, not an implementation defect; no prototype was created and no personal redesign judgment was substituted for fidelity review.

### Integrity, privacy, and operations

- Canonical generated state and hashes are not mutated by prompt-feedback helpers; raw benchmark messages, full answer keys, grader prompts/deliberation, and transcripts do not enter legislative prompts.
- Invalid judges, V1, and mismatched-language evidence cannot become semantic feedback or replace a valid V2 baseline.
- The English control and control-adjusted projection were removed; the experiment receipt remains in `docs/wayfinder/field-note-english-control-2026-08-01.md`.
- The CI workflow contains no secret/provider/live flag and runs only the established offline Python, Node, and historical coverage commands.
- No provider call, merge, deployment, timer/VPS change, Crabbox action, X action, public release, or live-state mutation occurred during [Integrate and verify the ALATO roadmap draft PR](https://github.com/isorabins/alanguagealltheirown/issues/40).

## [Ship the ALATO roadmap with Scoring V2 regression protection](https://github.com/isorabins/alanguagealltheirown/issues/35): story trace

| Stories | Implementation | Evidence |
|---|---|---|
| 1–2 | Active feedback projected through the real prompt assembler to A and B and retained across revision/failure/reconstruction. | `ActiveLegislativeFeedbackPromptTests`; full Python suite. |
| 3–4 | New request supersedes; settlement and later same-rule motion creation clear old feedback. | Supersession/settlement/repeated-repeal lifecycle tests. |
| 5–6 | No-motion/structural/restart preservation with motion-scoped isolation. | Production-shaped prompt lifecycle tests. |
| 7–8 | Corrected B1–B5 atomic source meanings preserve compound conditions and separable facts. | `benchmarks/v2.json`; benchmark digest/registry tests. |
| 9–10 | Meaning pass, compression success, coverage, critical failures, inventions, and body savings are independent; pass requires all atoms/no inventions. | `score_judgment_v2`; judge and exam-evidence tests. |
| 11–12 | Every non-missing verdict has an inspectable decoded span; practical literals veto false survival with exact boundaries. | Judge validation plus larger-value/identifier regression. |
| 13–14 | Unsupported/malformed judge output is `INVALID JUDGE RESULT`; V1 stays immutable and visibly legacy. | Python invalid-judge tests, V1 SHA receipt, screenshots 03. |
| 15–16 | One bounded current-language failure receipt reaches both legislators; invalid/V1/raw material stays out. | `ScoringV2FailureFeedbackPromptTests`; prompt sentinel/cap/hash tests. |
| 20 | Public history labels Scoring V2, invalid results, and V1 distinctly. | Node viewer tests; screenshot 03. |
| 23 | No unseen-comparison material or recurring unseen infrastructure was added. | Fixed-base changed-path and scope review. |
| 24 | Semantic regressions exercise the real Python prompt/test-turn path and current Node viewer path. | Focused lifecycle suite plus full offline suites. |
| 25 | One path-filtered offline Actions workflow ignores generated-state-only turns. | `.github/workflows/offline-acceptance.yml`; YAML/path/provider audit. |
| 26 | Implementation stops at a draft PR and explicitly separates every live release action. | Draft-PR status and live-actions-not-taken receipt. |
