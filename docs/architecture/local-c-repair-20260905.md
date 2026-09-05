# Local C repair — 2026-09-05 WITA

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
Existing quarantines still require an explicit reviewed-edition reset; none has
been reset as part of this work.

Offline verification: 251 Python tests and 87 Node tests pass; historical contract
trace check passes (115 requirements, 210 tasks). This includes the new recorded
provider-error replay, B provider-error distinction, pre-dispatch spend refusal,
exact charge reconciliation and uncertain-charge retry prevention. These checks
prove failure handling and local budget mechanics, not real provider acceptance.

The original upstream cause and successful full-size cleanup remain unverified.
Request size and output allowance are hypotheses, not established causes.

## Local test boundary awaiting approval

Automatic approval review rejected a real run because it would send the full
rulebook/history to OpenRouter without explicit payload/destination authorization,
and the old $1.10 stop check happens after spending. No model request was sent.

Prepared command, to run only within an approved provider-test envelope:

```sh
python3 local_cleanup.py --source state/rulebook.json \
  --output /private/tmp/alato-c-local-20260905/rehearsal \
  --max-spend-usd 6
```

Use the existing Bitwarden-managed `OPENROUTER_API_KEY` injected in process by the
workspace credential loader. Never materialize credentials or use the public
production key. The runner queries the official OpenRouter model catalog, retains
that catalog, and reserves every advertised context token plus requested output
at uncached prices before dispatch. Unknown charges keep the reservation and stop
without a retry. This is a client-side bound against advertised prices, not a
provider-side account spending limit. Any provider overcharge stops explicitly.
Run output is new and local; source bytes remain unchanged. The CLI only rehearses
cleanup; it has no application or quarantine-reset operation.

On 2026-09-05, the official catalog reports Kimi K3 context 1,048,576 at $3/M input
and $15/M output; Kimi K2.6 context 262,144 at $0.95/M input and $4/M output.
At 22,000 maximum output tokens, reservations are $3.475728 for C and $0.3370368
for B. The catalog must be read again at run time; these are preflight evidence,
not frozen billing assumptions.

## Remaining acceptance

1. Approve full experiment context to existing OpenRouter models, local repair
   and verification only, up to $6 total across the authorized test work.
2. Run real C and B with retained raw evidence. Diagnose failures before retries;
   share one cumulative allowance across subsequent runs, never reset the budget.
3. Prove deterministic coverage, semantic advisory review, at least 5% measured
   reduction and the structured-checkpoint size limit. Safe rejection alone does
   not establish that useful cleanup works on this source.
4. In a disposable state copy, resolve the existing open motion through the normal
   authority path, explicitly re-arm the reviewed local edition, and verify local
   application, restart and a subsequent ordinary turn. Include these model calls
   in the same allowance. Do not fabricate a model candidate to pass acceptance.
5. Report the exact stage reached, receipts and remaining limits. Production is
   untouched. No claim of per-rule semantic-effect test coverage.
