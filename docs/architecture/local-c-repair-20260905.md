# Local C repair — 2026-09-05 WITA

## Verified result

**PASS on a 12-rule fixture using real C, B and A calls.** The final run produced
a 2234-token candidate from 2560 source tokens (12.73% reduction); B raised no
objections. Automatic cleanup applied it locally (2230 rendered tokens), TurnStore
preserved it across reload, and A completed an accepted ordinary turn. A separate
fresh Python process reloaded the completed state and verified the same language
hash, the cleanup receipt and A's completed turn. Original source bytes/hash were
unchanged.

Total provider-reported spending across all six attempts and 29 HTTP calls:
**$0.38250397565 of the approved $1.00**. No pending charges/reservations remain.
The final run's evidence is under
`tests/acceptance/local-c/.evidence/20260905/run-06/` (ignored local artifacts).
`acceptance.json`, `fresh-process-verification.json`, `shadow/report.json` and
the archived `../budget-receipt.json` contain the compact results; adjacent files
retain the actual provider responses, prompts, fixture and state. The original
shared budget ledger remains at the path in the verified command below.

This proves the reduced local path, not cleanup of the complete historical state
or independent semantic-effect testing of every language rule.

## Authorized outcome

Iso wants existing Agent C cleanup working locally before new features. Preserve
the experiment, models, authority and deterministic cleanup gates. Do not release,
deploy, change production quarantine or institute per-rule effect experiments.

## Evidence and current boundary

The saved turn-2619 cleanup receipt has `finish_reason=error`, no candidate and a
permanent structural-output quarantine. The provider's underlying error body was
not retained in that receipt, so its original cause remains unknown. The current
saved source has 665 legislative records, including 83 adopted and one proposed
rule. Automatic cleanup correctly waits while a motion is open.

A deterministic replay through the real automatic/shadow cleanup boundary failed:
it classified the provider failure as invalid authored output. Edition v6 separates
`provider_failure` from structural errors. A provider failure changes no language,
does not authorize applying partial output, and does not create a new permanent
quarantine. Existing same-language retry suppression remains in place. Malformed
JSON, truncation and invalid B audits retain their existing protected behavior.
Existing quarantines still require an explicit reviewed-edition reset. Only the
disposable test fixtures were re-armed; canonical and production state were not.

Offline verification: 259 Python tests and 87 Node tests pass; historical contract
trace check passes (115 requirements, 210 tasks). This includes the new recorded
provider-error replay, B provider-error distinction, pre-dispatch spend refusal,
exact charge reconciliation, uncertain-charge retry prevention and cross-reference
correction limits. Real provider acceptance is evidenced separately above.

Live tests exposed undefined group references, self-overrides, undefined overrides
and a 4.73% compression near miss. C now receives the existing numeric size gate
and explicit reference invariants. Reference errors may use the remaining C call
for correction; other validation gates remain unchanged. The limit remains two C
calls and one advisory B call. If B objects after a correction used the last C
call, the run fails rather than applying without finalization. No validator was
relaxed. An evidence-path mistake in the new test harness was corrected before
the final fresh end-to-end run.

The original upstream cause and successful full-size cleanup remain unverified.
Request size and output allowance are hypotheses, not established causes.

## Local test boundary and approval

Automatic approval review rejected a real run because it would send the full
rulebook/history to OpenRouter without explicit payload/destination authorization,
and the old $1.10 stop check happens after spending. No model request was sent
before approval. Iso subsequently approved all necessary local testing with an
explicit **$1.00 total** ceiling, superseding the earlier proposed $6 allowance.

The full archive cannot fit the conservative $1 reservation with the existing
models. The approved smoke therefore selects 12 real adopted records verbatim,
labels the reduced scope, and preserves their source hash and selected IDs:

```sh
python3 tests/acceptance/run_local_c_smoke.py \
  --output /private/tmp/alato-c-local-20260905/approved-dollar/run-06 \
  --budget /private/tmp/alato-c-local-20260905/approved-dollar/budget.json \
  --max-spend-usd 1.00
```

Use the existing Bitwarden-managed `OPENROUTER_API_KEY` injected in process by the
workspace credential loader. Never materialize credentials or use the public
production key. The runner queries and retains the official OpenRouter model
catalog. For the existing text-only models, input reservation uses twice
the full request JSON's UTF-8 byte length plus 8192 framing tokens, capped at the
advertised context window; other request shapes reserve the full window. Output
reserves the requested maximum; the small fixture additionally caps output at
6000 tokens. Production's 22,000-token C/B limits are unchanged. Provider routing enforces the advertised uncached
price ceiling using `provider.max_price`. Unknown charges retain reservation and stop
without a retry. This is a client-side bound against advertised prices, not a
provider-side account spending limit. Any provider overcharge stops explicitly.
Run output is new and local; the shared allowance survives subsequent processes.
The generic CLI only rehearses cleanup. The opt-in acceptance harness explicitly
re-arms an isolated fixture, uses the real automatic application path, commits,
reloads with TurnStore, and asks real Agent A to continue. Canonical repository
state and production remain unchanged.

On 2026-09-05, the official catalog reports Kimi K3 context 1,048,576 at $3/M input
and $15/M output; Kimi K2.6 context 262,144 at $0.95/M input and $4/M output.
At 22,000 maximum output tokens, reservations are $3.475728 for C and $0.3370368
for B. The catalog must be read again at run time; these are preflight evidence,
not frozen billing assumptions.

## Remaining boundary

Full historical-source acceptance is unverified. That source also has an open
motion, which must settle normally before automatic cleanup can apply. Production
release/reset and per-rule semantic-effect experiments were not performed.
The completed local smoke is repeatable through the opt-in harness above with
an authorized allowance and new output directory; do not reset the shared ledger
or treat the archived budget receipt as a new spending allowance.
