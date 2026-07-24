# Launch-First First Production Turn

Date: 2026-07-24 WITA

Status: **FAIL-CLOSED — courier repair required before final retry**

The scheduler remained inactive while one ordinary service execution was
observed in isolation.

- Started: 2026-07-24 09:37:42 WITA.
- Finished: 2026-07-24 09:39:11 WITA.
- Service result: success; exit status 0.
- Turn advanced from 650 to 651.
- Commit: `6d77d73886ed01afcbcc1e35ca21bd6679012582`,
  subject `turn 651`.
- Commit and upstream matched; worktree remained clean.
- Event: harness test, 370 original tokens to 243 encoded tokens, 34% smaller,
  96% fidelity, valid judge result.
- The rulebook's byte representation was compacted, but canonical sorted JSON
  before and after had the identical hash
  `57fbf58ea571eb6de76059e46da5ceb3eb918f6f8c047e7b23a8d01e46c85606`.
  The existing rulebook was therefore semantically unchanged.
- `TWEET_ENABLE=0`; the delivery code created pending local state only. The X
  log contains no 2026-07-24 delivery.
- Loop and systemd logs contain normal completion lines with no provider,
  duplicate, state, or invariant warning.
- The collaboration log did contain
  `collaboration courier not configured: RuntimeError` on both pull and push.
  The turn itself was intentionally exception-safe, but this proved the VPS
  process did not expose the newly installed Redis names to `collab_sync.py`.
  Recurrence was paused before the next scheduled turn.

When the persistent timer was enabled at 09:40:02 WITA, systemd immediately
replayed its missed scheduled event. That ordinary recurrence completed turn
652 successfully at 09:40:25 WITA and then moved the timer into its normal
waiting state. It was not a concurrent duplicate. The final log audit found the
same courier warning on that turn, so the timer was stopped at 09:44 WITA before
turn 653. A repaired-turn receipt is required before this artifact may become
PASS.
