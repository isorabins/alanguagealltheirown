# Launch-First Verification

Date: 2026-07-24 WITA

Status: **HOTFIX VERIFIED OFFLINE; LIVE RETRY PENDING**

## Fail-closed finding

The first two successful core turns exposed one collaboration-only warning:
`collaboration courier not configured: RuntimeError`. The systemd unit does not
load `.env`; `loop.py` and `tweet.py` read that file themselves, while
`collab_sync.py` previously checked only process environment.

The timer was stopped before turn 653. No canonical corruption, duplicate
process, external X post, or dirty VPS state occurred.

## Repair

- `collab_sync.py` now reads exactly `UPSTASH_REDIS_REST_URL` and
  `UPSTASH_REDIS_REST_TOKEN` from process environment first and repo-local
  `.env` second.
- Quoted values are accepted without sourcing or executing the entire file.
- A regression test proves exact-name `.env` fallback.

## Offline verification

- Focused collaboration suite: 12 tests, PASS.
- Full Python suite: 72 tests, PASS.
- Full Node/acceptance suite: 37 tests, PASS.
- Contract coverage: 80 requirements traced across sequential T001–T176, PASS.
- `git diff --check`: PASS.
- Secret-pattern review: only the explicit `fixture-token` test value matched;
  no runtime secret value appears in the diff or evidence.

The hotfix must still merge to `main`, sync to the paused VPS, and complete one
warning-free production turn before core-live can be PASS.

## Repaired-turn preflight finding

PR #2 merged the courier repair as
`ceb4747c2b0a2105f5ffc08f655653ec6546b9c5`. The paused VPS fast-forwarded to
that commit with semantic rulebook/conversation hashes unchanged, and direct
courier pull/push probes returned silently with a clean worktree.

The subsequent service retry failed before producing turn 653 because
`render_window()` treated a turn-652 `legislature` receipt as an agent message
and accessed its intentionally absent `content` field. Systemd exited 1, the
canonical state stayed at turn 652, the repository stayed clean, and the timer
remained inactive.

The second scoped repair renders legislature receipts explicitly and adds a
regression fixture with no `content` field. Verification after that repair:

- Focused evidence/collaboration suite: 18 tests, PASS.
- Full Python suite: 73 tests, PASS.
- Full Node/acceptance suite: 37 tests, PASS.
- Contract coverage: 80 requirements / 176 tasks, PASS.
- `git diff --check`: PASS.
