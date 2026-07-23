# Production Acceptance Harness Repair — 2026-07-22

Result: **PASS offline; production remains unchanged and the 2026-07-21 run remains FAIL.**

## What failed

The canonical product failure was real: production served the old application
and `/human` returned Vercel 404. The run also exposed three harness defects
that could weaken or confuse the next approved attempt:

1. `run-production-current.mjs` created its own vague approval file.
2. It returned exit code 0 whenever a results file existed, even when the
   matrix result was FAIL.
3. The runner completed too quickly for the fixed outer recording, leaving
   most sampled frames on an idle terminal. The optional WebVNC bridge was also
   incorrectly described as a separate pass blocker after the run.

## Repair

- Production plans now require a non-loopback HTTPS target, an externally
  created approval receipt, and bounded visible dwell timing.
- The wrapper requires the exact external receipt path, cannot create it, and
  propagates the child/matrix exit status.
- The visible runner foregrounds the browser, dwells on numbered screenshots,
  holds the final state briefly, and records run/browser-visible timing in the
  matrix receipt.
- The reusable Crabbox skill and evidence audit now state explicitly that
  WebVNC is optional review transport. Playwright control, outer X11 video,
  proof, row results, spend, and teardown remain mandatory.
- The historical evidence README and audit summary correct only that diagnostic
  classification; the 24 FAIL / 2 BLOCKED product result is unchanged.

## Verification

- `npm test --prefix tests/acceptance/production`: PASS, 6/6.
- `python3 -m unittest discover -s tests/python -p 'test_*.py'`: PASS, 65/65.
- `node --test tests/js/*.test.js`: PASS, 27/27.
- `python3 tests/acceptance/check_contract_coverage.py`: PASS, 78 requirements
  and sequential T001–T152.
- Quickstart bypass searches: PASS; no `RedisRest`/`sync_remote` loop path, and
  the bounded courier pull/push timeouts remain present.
- `git diff --check`: PASS.
- Changed-diff secret-shape scan: PASS, zero matches.
- Credential-free private manifest validation against Crabbox v0.40.0: PASS;
  no coordinator/provider action was run.
- Reusable skill SHA-256:
  `710fb2981e63f1a1b15522f7aa045df292bbc251b9f7333fb9e19dce26651fad`.
- Evidence-audit script SHA-256:
  `090d3215eacadb3636ee659efc65dfccfd67866c9666c3c7be43622072a46820`.

## Boundary

No feature push, paid call, credential/configuration change, merge, deployment,
production state write, loop change, Crabbox lease, DNS action, or X action was
performed. The next production-path blocker is still T120: Kimi rejected the
cleanup candidate, so the reviewed app cannot lawfully proceed to credentials,
rebase/merge, deploy, and full acceptance until a separately approved cleanup
repair/audit passes.
