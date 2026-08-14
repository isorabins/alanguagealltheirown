# ALATO roadmap release progress

Status verified 2026-08-03 WITA.

## Live release

- The retained scope from issues #35–#40 is live at
  https://alanguagealltheirown.com and https://alanguagealltheirown.com/human.
- Release PR #41 merged as
  `dcd584d5bba39d93c28e17c887fb7a7bbb4117ab`.
- The bounded Scoring V2 literal-preflight repair merged in PR #42 as
  `286c674a2381d62f4558cac0e3861672de99c3f5`.
- The production viewer deployment receipt is
  `dpl_5jCZTBCawpZVpHrDv6ND6PgcvshE`.
- Production was clean and synchronized at generated turn 1499,
  `fbe23015461f61c11b75dc1b26ebedd4e5bc391b`, on 2026-08-03 03:00 UTC. The
  loop timer was active/enabled and the latest service run exited 0.

## Completed gates

- Fixed-base code review and the repair re-review completed with hard findings
  resolved. The review receipt remains in
  `docs/wayfinder/evidence/ticket-40-local/review-and-trace.md`.
- Offline Python, Node, and contract-coverage gates passed for the release and
  repair.
- The actual public viewer and canonical runtime were deployed.
- The 12-hour SSH/HTTP production monitor completed with the verdict **PASS
  WITH KNOWN PROVIDER-CONFORMANCE LIMITATION**. Its complete timeline is
  `/Users/isorabins/CrabboxEvidence/alato-roadmap-live-20260801/monitoring/timeline.md`.
- The monitor automation was deleted after closeout.

## Known evaluation limitation and next task

Scoring V2 correctly fails closed, but provider judge evidence remains
intermittently non-conformant. Invalid judge results preserve valid baselines
and never become legislative feedback. Separately, valid exams continue to
show recurring real meaning loss, especially B3.10 and B5.26. These two failure
classes must not be conflated or hidden by weakening the benchmark. The current
evidence and diagnosis boundary are recorded in
`docs/wayfinder/field-note-scoring-v2-live-evaluations-2026-08-03.md`.

The next task is diagnosis only: identify the smallest truthful repair for
judge conformance and/or the recurring language-fidelity failures before any
new provider call or live change.

## Remaining release closeout

The release is live, reviewed, and monitored, but the Iso-confirmed definition
of done is not yet fully closed. Disposable Crabbox browser acceptance still
needs the continuous outer-X11 MP4, numbered screenshots, matrix and spend
receipts, independent public/runtime evidence, and verified zero-resource
cleanup. The three local acceptance artifacts in the original worktree under
`tests/acceptance/production/` are intentionally untracked and must be
preserved. Do not claim final completion until this gate and the final evidence
receipt are complete.

One isolated `language-loop.service` failure occurred at 2026-08-02 21:45 UTC;
the next 22:00 run and later runs recovered without manager action. It is
recorded here for completeness and is not currently linked to the evaluation
failure pattern.
