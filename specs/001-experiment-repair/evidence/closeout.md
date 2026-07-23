# Current-Deployment Acceptance Closeout

**Date:** 2026-07-21 WITA
**Overall result:** **FAIL**

## Product result

- Target: `https://alanguagealltheirown.com`
- Public homepage: HTTP 200.
- `/human`: HTTP 404 with visible Vercel `NOT_FOUND` evidence.
- Canonical acceptance matrix: 24 FAIL, 2 BLOCKED, 0 PASS.
- X: untouched; its two rows are BLOCKED by the approval boundary.
- Production deployment, configuration, canonical state, and loop state:
  unchanged.

## Infrastructure result

- One CPX32 `fsn1` lease was used for 601 seconds with an eight-hour TTL.
- New-infrastructure spend: approximately `$0.01` of the approved `$2` maximum.
- Teardown: 0 coordinator leases, 0 matching Hetzner servers, 0 matching
  Hetzner SSH keys.
- Production submissions/test records created: 0.

## Production readback

```text
language-loop.timer: inactive
language-loop.service: inactive
VPS HEAD: 75cd45704f3fd74906c3ee4edb53e81187b6ff2a
VPS worktree: clean
rulebook SHA-256: 5938df47b587aabfb9fe7231c07d12b315a3ac3f7bdcbfee73b076fe219e4933
```

## Verification

```text
python3 -m unittest discover -s tests/python -p 'test_*.py'
Ran 65 tests — OK

node --test tests/js/*.test.js
27 pass, 0 fail

npm test  # tests/acceptance/production
2 pass, 0 fail

python3 tests/acceptance/check_contract_coverage.py
PASS: 78 requirements traced; 148 sequential tasks present

Evidence audit
27/27 screenshots present; 120-second MP4 present; secret-shape matches: 0
```

## Git and delivery state

- Feature branch: `codex/experiment-repair`.
- Pre-closeout branch/remote/draft PR 1 head:
  `9607eab0ead9d0bd9e1d97f673c699a176a5543c`.
- Remote `main`: `75cd45704f3fd74906c3ee4edb53e81187b6ff2a`.
- This evidence closeout is a local feature-branch commit; it is not pushed by
  the as-is test approval.
- Draft PR: `https://github.com/isorabins/alanguagealltheirown/pull/1`.
- The product is not live from the reviewed feature branch.

## Remaining gap

The reviewed feature must pass its earlier production integration, deployment,
and loop-health gates before a new semantic T128-T143 acceptance run can pass.
The current evidence proves that trying the real as-is production URL now fails
because the required deployed surfaces do not exist; it is not another Crabbox
setup failure.
