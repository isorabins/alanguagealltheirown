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
