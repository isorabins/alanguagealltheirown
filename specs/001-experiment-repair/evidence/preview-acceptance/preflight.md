# Preview Acceptance Preflight

Date: 2026-07-22 WITA

Status: **READY FOR ONE EXACT APPROVAL; no preview mutation has occurred.**

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

## Verified starting state

- Local branch: `codex/experiment-repair` at
  `94d7e40c5ea4741849b22d57eee3ada9dc365496`, clean before this checkpoint and
  one evidence-only commit ahead of its upstream.
- Remote draft PR 1: open/draft/mergeable at reviewed commit
  `9ede27860d9d20c9e8f77dc26c56040f342471a4`.
- Remote `main`: `75cd45704f3fd74906c3ee4edb53e81187b6ff2a`.
- Production deployment: `dpl_6rrcd4YdGMTYkcUdEUsCQan7qQCS`, Ready; homepage
  `200`, `/human` `404`; production remains the old application.
- Production Vercel env: only `OPENROUTER_API_KEY`; no Preview variables exist.
- VPS: clean `main` at turn 650; `language-loop.timer` and service inactive;
  rulebook SHA-256
  `5938df47b587aabfb9fe7231c07d12b315a3ac3f7bdcbfee73b076fe219e4933`.
- Offline suite: 71 Python tests, 27 JavaScript tests, six acceptance-harness
  tests, 78 traced requirements, and sequential T001-T156 all pass.
- Crabbox: v0.40.0 checksum matches the pinned binary. Coordinator identity is
  `crabbox-pilot@local` / `crabbox-iso-pilot`; zero active leases.
- Isolated Hetzner project: zero servers and zero SSH keys. CPX32 `fsn1` live
  gross quote is EUR 0.0673/hour; eight hours is EUR 0.5384 before minor extras,
  within the `$2` hard ceiling.

## Preview resources and boundaries

- Vercel target: Preview only; no production alias, promote, rollback, or
  `--prod` command.
- Upstash: one new free-tier-only Redis database named for PR 1; fail closed if
  a paid plan or broader team/account change is required.
- OpenRouter: one separate public Preview key with `$20` limit and monthly reset;
  never reuse the private experiment key and never print the key.
- Preview failure controls may temporarily lower/restore that isolated key's
  limit or replace/restore only the Preview key value to prove allowance and
  unrelated-provider errors; final metadata must return to `$20`/monthly and
  the total test spend remains bounded by that same key.
- Preview secrets: only `UPSTASH_REDIS_REST_URL`,
  `UPSTASH_REDIS_REST_TOKEN`, `HUMAN_PASSWORD`, and
  `OPENROUTER_PUBLIC_API_KEY`, scoped to Preview.
- Crabbox: one Hetzner CPX32 in `fsn1`, eight-hour TTL, 30-minute idle timeout,
  one active lease maximum, `$2` maximum new-infrastructure spend, coordinator
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

## Approval gate

No approval receipt exists yet. The user must paste the exact bounded phrase
presented in chat. A paraphrase or prior Crabbox approval is not reusable.
