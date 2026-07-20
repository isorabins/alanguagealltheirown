# Offline Suite Receipt

Run on 2026-07-20 at 13:10 WITA in the clean feature worktree on `codex/experiment-repair`.

## Current implementation

```text
$ python3 -m unittest discover -s tests/python -p 'test_*.py'
Ran 47 tests in 0.574s
OK

$ node --test tests/js/*.test.js
tests 26
pass 26
fail 0

$ python3 tests/acceptance/check_contract_coverage.py
PASS: 55 requirements traced; 133 sequential tasks present

$ node inline-script parser + node --check viewer/api/*.js
PASS viewer/index.html 1 inline script(s)
PASS viewer/human.html 1 inline script(s)
all viewer/api/*.js parsed successfully

$ git diff --check
(no output; exit 0)
```

The Python suite used copied fixtures and a loopback HTTP stub only. No provider, Redis, Upload-Post, Vercel, X, or production endpoint was called.

## Meaningful old-baseline failure

The following read-only check inspected commit `96e681f` without checking it out or changing files. It intentionally exited 1:

```text
FAIL: adopted-only runtime boundary
FAIL: separate public inference key
FAIL: confirmed idempotent X delivery
AssertionError: old baseline contract failures: adopted-only runtime boundary, separate public inference key, confirmed idempotent X delivery
```

The current tests did not exist at that baseline, so this checks three contract-defining source properties rather than pretending the new suite could run unchanged there.

## Immutable state receipts

The five production-derived state/viewer files remain byte-identical to pre-implementation receipts. The feature adds only an empty sanitized `state/public-collaboration.json`; private canonical `state/collaboration.json` is gitignored and backed up to private Redis before inbox acknowledgement.

```text
a0844b441b6594201b5d3343901c5374daf7aa7ac0072d79026b9149280d2d6a  state/rulebook.json
7ab4a3c1761e19332a22bb74b0af820f100f5b57ff6f65052adfde1a93d20f0b  state/conversation.json
ad8f8a23865eacf2c3b05a58384f14913aaa18e5b1d8fd454a5e9b9699cdbe96  state/meta.json
6f99797e25ebc580cfc4ae2757ba9e8e6088190399889545c3d9231e0846a041  state/tweet-state.json
4b41d6fd20afbf041eef73343bd7c0b2d1f6157801fb0641eb64fcfc886c7f9f  viewer/state.js
```

Result: **PASS for the offline implementation only**. Deployment, live credentials, paid calls, production turns, X, and visible production acceptance remain **BLOCKED** behind T107–T133.
