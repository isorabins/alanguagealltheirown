# Skeptical Review Handoff

This is an adversarial inspection brief, not a claim that the feature is done.

## Review target

- Worktree: `/Users/isorabins/alex-workspace-worktrees/experiment-repair`
- Branch: `codex/experiment-repair`
- Implementation baseline: `96e681f`; read-only remote observation at closeout: `73a71cf` (turn 630)
- Current state: offline implementation only; not pushed, deployed, connected to production Redis/OpenRouter, run on the VPS, or exercised on X. A Crabbox acceptance-infrastructure addendum is drafted with a `$2` ceiling; no binary, coordinator, provider credential, lease, or remote proof exists yet.
- Binding contract: `spec.md`, `plan.md`, `tasks.md`; DoD truth table: `evidence/production-acceptance/matrix.md`.

Do not infer production success from green tests or this document. Independently recompute the diff, test results, state hashes, task coverage, and matrix statuses.

## What deserves the most suspicion

1. **Authority bypasses:** search for every rule mutation and confirm `apply_authorized_motion` is the sole live legislature writer. Try one-open overflow, full add/repeal lifecycles, B-originated repeal, A votes, Unicode ids, nested verbs, multiple motions, repeats, and settled/terminal rules.
2. **Language contamination:** compare Python and Vercel hashes and inspect every encoder, decoder, Conversation, and Try It prompt for proposed/rejected/historical/research/ASK/suggestion text.
3. **Invalid scoring:** force absent, duplicate, boolean, string, out-of-range, and malformed judge ids. Confirm ordinary fallback and Conversation both publish no valid score on incomplete coverage.
4. **Cleanup substitution/history loss:** swap source, candidate, audit, applied ledger, and approval files one at a time. Confirm the audit binds exact hashes, old ids/history survive, and no command can default to production.
5. **Queue races:** prove `loop.py` contains no Redis client/call, expire and re-claim a courier lease, kill the courier before/after spool fsync, let the stale owner ack, replay ids after restart, reorder moderation/suggestion records, and verify only the loop writes canonical collaboration history.
6. **Private/public leakage:** use hostile markup, prompt instructions, and secret-shaped text. Inspect raw public JSON and browser output, not only UI labels. Pending/dismissed text must appear nowhere public or in agent context.
7. **Session lifecycle:** check timing-safe wrong-password rejection, cookie flags, browser restart, absolute non-sliding expiry, logout deletion, and unauthenticated private endpoints against a production-equivalent Redis namespace.
8. **Try It spend/version boundary:** prove the public key cannot fall back to the private key, decode makes no provider call after a version/hash race, and monthly exhaustion is not confused with ordinary 429/5xx/auth failures.
9. **X ambiguity:** test official sync and async shapes, partial multi-platform success, non-JSON/non-2xx, connection failure, timeout after send, pending poll, missing job, three attempts, later-note continuation, and process restart. No provider-only receipt passes the real-profile DoD.
10. **Operational truth:** verify no existing state file changed and the only baseline state addition is the empty sanitized `state/public-collaboration.json` scaffold; verify no paid/live call occurred, the original dirty checkout remains untouched, and documentation never describes unrun production behavior as live.

## Known limitations and deliberate blockers

- All live rows in the production matrix are BLOCKED. There are no screenshots or continuous video yet, by design.
- The future remote evidence path is specified but unverified. It must pass T108–T117, including browser-restart continuity, cap/TTL enforcement, secret audit, and provider-confirmed teardown, before production acceptance.
- The production loop advanced 88 generated-state commits after the implementation baseline. Do not treat that drift as a feature state mutation; independently compare the feature side of `origin/main...HEAD`, then require the paused rebase at T123.
- Tests use mocks, copied fixtures, and one loopback HTTP server; they do not establish vendor response compatibility or live persistence.
- The implementation was delivered in coherent foundation/core/UI/final commits rather than one commit per user story. Review commit boundaries and the final diff; do not treat task checkmarks as proof.
- Official docs were checked on 2026-07-20, but beta OpenRouter search and Upload-Post receipt behavior must be revalidated in the approved production-equivalence pass.
- Production cleanup requires paid A/B outputs and human review. The fixture proves mechanics only, not semantic adequacy of the future cleaned language.

## Minimum independent commands

```bash
python3 -m unittest discover -s tests/python -p 'test_*.py'
node --test tests/js/*.test.js
python3 tests/acceptance/check_contract_coverage.py
git diff --check
git diff --name-status origin/main...HEAD -- state viewer/state.js
git status --short --branch
```

Then inspect `offline-suite.md`, `offline-review.md`, every user-story evidence file, and every row of the production matrix. The correct overall verdict today is **BLOCKED**, not PASS, because the deployed Definition of Done has not run.
