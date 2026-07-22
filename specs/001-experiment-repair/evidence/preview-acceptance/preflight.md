# Preview Acceptance Preflight

Date: 2026-07-22 WITA

Status: **CLOSED PARTIAL — approval consumed; Preview is ready, cleaned, and not production.**

## User-visible definition of done

The preview checkpoint passes only when the reviewed draft-PR commit is served
from an isolated Vercel Preview URL, every preview-eligible row in `matrix.md`
passes through the visible browser, the final Crabbox evidence contains numbered
screenshots plus one continuous outer-desktop video across a browser restart,
all disposable test data is cleaned, and teardown proves zero coordinator leases
and zero matching Hetzner servers/SSH keys. Fixes may use at most three scoped
repair/redeploy loops and must be pushed only to draft PR 1.

Cleanup generation/application, natural production loop turns, canonical
production state, X actions, `main`, production credentials, and the production
domain remain `BLOCKED` by design. A preview pass is not production completion.

## Executed state

- Exact approval is preserved in `approval-receipt.md` (SHA-256
  `e964018822526a40f6ba585cd9ed85982d1c59b27c3809ac3e62832825be396b`).
- Isolated Preview is `dpl_F4hbURLyYz6n6AfXV8CG7F9Xd2jA`, Ready at
  `https://alanguagealltheirown-h1oh9h9q2-isorabins-projects.vercel.app`.
- Production remains `dpl_6rrcd4YdGMTYkcUdEUsCQan7qQCS`, Ready and unchanged.
- Local revalidation after the final harness repair: 7 acceptance-harness, 28
  JavaScript, and 71 Python tests pass; coverage reports 78 requirements and
  166 sequential tasks.
- Crabbox v0.40.0 used one CPX32 in `fsn1` with a 10,800-second (three-hour)
  TTL and a `$1` ceiling. Coordinator usage after release reports zero active
  leases and `$0.05` estimated actual infrastructure spend.

## Preview resources and boundaries

- Vercel target: Preview only; no production alias, promote, rollback, or
  `--prod` command.
- Upstash: one new free-tier-only Redis database named for PR 1; fail closed if
  a paid plan or broader team/account change is required.
- OpenRouter: one separate public Preview key with a `$5` monthly limit and
  expiry on 2026-08-21; the management credential and key are stored outside
  the repository.
  never reuse the private experiment key and never print the key.
- Preview failure controls may temporarily lower/restore that isolated key's
  limit or replace/restore only the Preview key value to prove allowance and
  unrelated-provider errors; final metadata must return to `$20`/monthly and
  the total test spend remains bounded by that same key.
- Preview secrets: only `UPSTASH_REDIS_REST_URL`,
  `UPSTASH_REDIS_REST_TOKEN`, `HUMAN_PASSWORD`, and
  `OPENROUTER_PUBLIC_API_KEY`, scoped to Preview.
- Crabbox: one Hetzner CPX32 in `fsn1`, three-hour TTL, one active lease
  maximum, `$1` maximum new-infrastructure spend, coordinator
  cleanup owner, no Semaphore.
- Evidence: repository-owned assertions, numbered screenshots, one outer X11
  MP4, independent receipts, secret scans, and visible product-path cleanup.
- Delivery: coherent fixes/evidence may be committed and pushed only to the
  existing draft PR branch. No PR comment is required.

## Rollback and cleanup

Preview failures redeploy only the reviewed feature branch. The production
deployment and aliases are re-read after every deploy. Test data is removed
through the preview UI, the Crabbox lease is always released in a `finally`
path, and provider/coordinator zero-resource readbacks are mandatory. Preview
resources remain isolated for Iso's review unless a security/billing mismatch
requires their approved teardown; they are never attached to Production.

## Result and planned stop

Three permitted remote attempts ran. The final attempt passed Preview matrix
rows 1–7, including browser restart and the real Try It flow, then failed row 8
because the harness looked for a textarea placeholder in `body.textContent`.
The visible mobile screenshot shows the copy. The assertion is now corrected
and covered by the local fixture suite, but it has not been re-run remotely.

The outer-video process was interrupted before it flushed an MP4. This means
the evidence checkpoint is `FAIL`, not a product failure claim. Rows 9–12 did
not run because the plan is fail-fast. Preview data was deleted and the lease
was released. A further remote pass requires a new exact approval because the
three-run envelope is exhausted.
