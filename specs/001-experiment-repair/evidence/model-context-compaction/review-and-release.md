# Deterministic Model-Context Compaction — Review and Release

Date: 2026-07-30 WITA
Fixed point: `9f21b0e8aae717edd1727bb21938e4a0f95fe35b`
Reviewed code head: `a70488a601232e7c147fa2dc2c24f0a5b6ed3280`

## Three-axis review

Design Fidelity is not applicable because Phase 25 changes no frontend or
interactive surface.

The first parallel Standards and Spec review found two hard runtime gaps and
one stale-evidence gap:

1. correlation ids/questions/routes were truncated despite FR-072 requiring
   their original values;
2. projection happened after delivery lifecycle mutation, so escaped content
   could exceed the serialized cap after the row had already been consumed;
3. implementation evidence still described the branch as uncommitted.

The reviewed remediation preserves correlation fields exactly, fits findings,
limitations, and citations against their escaped serialized size, completes
projection before lifecycle mutation, and proves a forced projection exception
leaves the eligible row and canonical delivery log unchanged. The follow-up
runtime reviews confirmed those defects resolved. Their only remaining findings
were the stale mechanism wording and missing review lifecycle receipt corrected
by this documentation checkpoint.

## Verification after remediation

- focused Python: 54 passed;
- full Python: 124 passed;
- JavaScript: 31 passed;
- contract coverage: 110 requirements / 202 sequential tasks;
- compile, `git diff --check`, canonical-state/prompt/viewer preservation:
  PASS;
- exact paused-state rehearsal: 142,488 to 87,193 model-facing characters,
  38.81% smaller;
- real `lookup-1202-b`: 11,248 findings characters projected to 3,000, 10
  citations projected to 4, exact id/question/route retained;
- no model, provider, web, canonical-state, or production mutation occurred.

## Delivery state before publication

The branch is `codex/alato-model-context-compaction`. Its reviewed code consists
of implementation checkpoint `3773732074e469735ce2adab9bdfb2a619bdfeed`
and remediation checkpoint
`a70488a601232e7c147fa2dc2c24f0a5b6ed3280`. This review receipt and its
documentation corrections form the next documentation-only checkpoint.

At this receipt, the branch is unpushed and has no PR. Production is clean,
paused, and snapshotted at turn 1209 / commit
`9f21b0e8aae717edd1727bb21938e4a0f95fe35b`; no provider validation spend has
begun. T202 remains open for ready-PR publication, merge, VPS sync, normal
cadence, and one natural B receipt within the approved `$0.10` ceiling.
