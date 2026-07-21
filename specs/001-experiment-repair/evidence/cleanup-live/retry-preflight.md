# Cleanup Retry Preflight

Date: 2026-07-21 WITA

## Current immutable target

- Production timer and service are both inactive.
- Production `main` remains
  `75cd45704f3fd74906c3ee4edb53e81187b6ff2a` at turn 650.
- Production rulebook SHA-256 remains
  `5938df47b587aabfb9fe7231c07d12b315a3ac3f7bdcbfee73b076fe219e4933`.
- The copied source still contains exactly 23 adopted source ids.
- Attempt 1 spent `$0.011541708`; no Kimi call occurred.

## Repaired execution boundary

The retry payload will include only `id` and `text_en` for the 23 adopted
sources, not their accumulated histories. The raw A response will be saved
atomically before parsing or validation. The new `validate-candidate` command
then rejects missing, duplicate, non-adopted, or operational output before any
Kimi request. Only a passing A candidate may be sent to the one Kimi audit; the
existing `prepare` command remains the final exact-hash and semantic gate.

The focused cleanup suite passes seven tests, including candidate rejection
before audit for missing and duplicate source ids. No production file, key,
deployment, or X state was changed during repair.

## Remaining gate

The original phrase authorized exactly one DeepSeek request, and that request
was consumed. A second DeepSeek request is therefore a new paid live action and
must not be inferred from the remaining dollar headroom. The bounded retry is
one additional DeepSeek V3.2 cleanup plus one Kimi K2.6 audit, with `$0.10`
additional spend and `$0.12` cumulative G4 spend ceilings; stop before Kimi if
A fails again and stop on any identity, cost, validation, or state uncertainty.
