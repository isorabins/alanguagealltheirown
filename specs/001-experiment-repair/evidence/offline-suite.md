# Offline Suite Receipt

Run on 2026-07-21 at 10:39 WITA in the clean feature worktree on `codex/experiment-repair`.

## Current implementation

```text
$ python3 -m unittest discover -s tests/python -p 'test_*.py'
Ran 58 tests in 0.552s
OK

$ node --test tests/js/*.test.js
tests 27
pass 27
fail 0

$ python3 tests/acceptance/check_contract_coverage.py
PASS: 66 requirements traced; 133 sequential tasks present

$ ! rg -n "RedisRest|sync_remote" loop.py
(no output; exit 0)

$ rg -n "collab_sync.py (pull|push)|timeout" run_turn.sh
11:  timeout 8s python3 collab_sync.py pull >> state/collaboration-sync.log 2>&1 || true
13:  timeout 8s python3 collab_sync.py push >> state/collaboration-sync.log 2>&1 || true

$ node inline-script parser + node --check viewer/api/*.js
PASS viewer/index.html 1 inline script(s)
PASS viewer/human.html 1 inline script(s)
all viewer/api/*.js parsed successfully

$ git diff --check; bash -n run_turn.sh; python3 -m py_compile ...
(no output; exit 0)
```

The Python suite used copied fixtures and one loopback HTTP stub only. No provider,
Redis, Upload-Post, Vercel, X, or production endpoint was called.

## Local visible inspection

The local page rendered at desktop and 375px in Playwright. Both views visibly showed
the add/repeal legislature explanation, pending repeal area, and preserved historical
rules. Three local-preview 404s remain expected and are not waived: the favicon and two
raw-GitHub state files are unavailable from this unpushed branch. This is an offline UI
inspection only, not production acceptance.

## Meaningful old-baseline failure

The earlier read-only check against pre-feature commit `96e681f` intentionally failed
the adopted-only runtime boundary, separate public inference key, and confirmed
idempotent X delivery. The current tests did not exist at that baseline, so this checks
contract-defining source properties rather than pretending the new suite could run
unchanged there.

## Baseline-aware immutable state receipts

The feature was built from `96e681f`. The production loop continued normally while the
offline work proceeded; a final read-only fetch observed remote `main` at `73a71cf`
(turn 630), with intervening changes limited to generated state/viewer snapshots. The
five files in this worktree remain byte-identical to the `96e681f` implementation
baseline. The feature adds only the empty sanitized
`state/public-collaboration.json`; private canonical collaboration and courier spools
are gitignored.

```text
a0844b441b6594201b5d3343901c5374daf7aa7ac0072d79026b9149280d2d6a  state/rulebook.json
7ab4a3c1761e19332a22bb74b0af820f100f5b57ff6f65052adfde1a93d20f0b  state/conversation.json
ad8f8a23865eacf2c3b05a58384f14913aaa18e5b1d8fd454a5e9b9699cdbe96  state/meta.json
6f99797e25ebc580cfc4ae2757ba9e8e6088190399889545c3d9231e0846a041  state/tweet-state.json
4b41d6fd20afbf041eef73343bd7c0b2d1f6157801fb0641eb64fcfc886c7f9f  viewer/state.js
```

Result: **PASS for the corrected offline implementation only**. Deployment, live
credentials, paid calls, production turns, X, and visible production acceptance remain
**BLOCKED** behind T107–T143.
