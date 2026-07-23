# Preview Acceptance Preflight

Date: 2026-07-23 WITA

Status: **PASS — isolated Preview acceptance complete; Production remains an explicit planned stop.**

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

- The exact final approval is preserved in `approval-receipt.md`; it bounds one
  CPX32 in `fsn1`, a three-hour TTL, and `$1` infrastructure ceiling.
- Isolated Preview is `dpl_F4hbURLyYz6n6AfXV8CG7F9Xd2jA`, Ready at
  `https://alanguagealltheirown-h1oh9h9q2-isorabins-projects.vercel.app`.
- Production remains `dpl_6rrcd4YdGMTYkcUdEUsCQan7qQCS`, Ready and unchanged.
- Local revalidation before the lease: 9 acceptance-harness, 28 JavaScript,
  and 71 Python tests pass; coverage reports 78 requirements and 167 sequential
  tasks. The local Preview selector preflight passed against the actual viewer
  markup before the remote run.
- Crabbox v0.40.0 used lease `cbx_de7cea9d8ff0` on one CPX32 in `fsn1` with a
  10,800-second (three-hour) TTL and a `$1` ceiling. Coordinator usage after
  release reports zero active leases and `$0.07` cumulative estimated
  infrastructure spend.

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

The final approved remote attempt used the corrected, non-fail-fast plan and
passed all twelve required Preview rows. It produced 23 numbered screenshots,
independent JSON receipts, a 180.000-second continuous outer-desktop MP4, and
a proof bundle. Preview cleanup deleted 12 namespaced test keys with zero
remaining; the lease was released and coordinator/Hetzner readbacks are empty.

This is a Preview acceptance `PASS`, not a Production result. Merge, `main`,
Production deployment/routing/credentials, canonical-state application, loop
resume, and publication remain blocked by design and require their own exact
approvals.
