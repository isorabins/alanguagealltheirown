# Cleanup Attempt 1 — Safe Failure

Result: **FAIL at A replacement validation; T120 remains open.**

The one approved DeepSeek V3.2 request completed normally (`stop`) for
`$0.011541708`, well below the `$1.00` cap. Its JSON parsed, but its
`source_ids` did not cover every one of the 23 adopted source rules exactly
once. The fail-closed validator rejected it before any candidate bundle or Kimi
audit could proceed.

No retry was made because the approval authorized exactly one DeepSeek cleanup
call. No Kimi call was made. OpenRouter I/O logging was disabled, so the
provider retained metadata but not completion content; the first-run wrapper
also wrote output only after validation, leaving no recoverable failed
candidate. That wrapper behavior must be repaired before any newly approved
attempt: save the raw completion atomically before validation and send only
`id` plus `text_en` for each adopted source, not its accumulated history.

Post-failure readback verified the production timer inactive, VPS head still
`75cd45704f3fd74906c3ee4edb53e81187b6ff2a`, worktree clean, and production
rulebook file SHA-256 still
`5938df47b587aabfb9fe7231c07d12b315a3ac3f7bdcbfee73b076fe219e4933`.
Production state, deployment, credentials, and X were unchanged.
