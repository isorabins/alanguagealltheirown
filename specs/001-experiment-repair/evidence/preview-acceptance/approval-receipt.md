# Preview acceptance approval receipt

- Approved by: Iso Rabins
- Approved at: 2026-07-22 WITA
- Target: existing draft PR #1 and an isolated Vercel Preview

Exact approval:

> APPROVE LIVE CHANGE: create the automated Crabbox preview-testing setup with one securely stored OpenRouter management credential and capped repo-specific testing keys; deploy draft PR #1 only to Vercel Preview; run up to three repair and redeploy loops; lease one Hetzner CPX32 with a three-hour TTL and $1 infrastructure ceiling; capture screenshots and continuous video; update and validate the Crabbox skill; clean up the test lease and data; push fixes only to the existing draft PR; do not merge, deploy production, change production credentials or routing, resume the live loop, or publish anything.

Boundaries: no merge, production deploy, production credential/routing change, live-loop resume, or publication. The test lease must be a Hetzner CPX32 with a three-hour TTL and no more than $1 infrastructure spend. Preview data and the lease must be cleaned up after evidence capture.

## Follow-up approval

> APPROVE LIVE CHANGE: run one additional Crabbox Preview acceptance attempt for draft PR #1 using one Hetzner CPX32 in fsn1 with a three-hour TTL and $1 infrastructure ceiling; verify all 12 Preview rows with the corrected assertion, capture and inspect one continuous video, clean test data and lease, push only fixes to existing draft PR #1; do not merge, deploy production, change production credentials or routing, resume the live loop, or publish.

This one additional attempt ran on 2026-07-22 WITA. It passed rows 1–8 and
recorded a continuous 180-second MP4, then failed row 9 because its assertion
looked for a section-intro sentence inside `#cast`. The corrected assertion is
now in the local harness but has not been re-run remotely.

## Final approval

> APPROVE LIVE CHANGE: run one final Crabbox Preview acceptance attempt for draft PR #1 using one Hetzner CPX32 in fsn1 with a three-hour TTL and $1 infrastructure ceiling; verify all 12 Preview rows using the local Preview preflight, capture and inspect one continuous video, clean test data and lease, push only fixes to existing draft PR #1; do not merge, deploy production, change production credentials or routing, resume the live loop, or publish.

This one final attempt ran on 2026-07-23 WITA. The local Preview preflight and
the remote twelve-row matrix both passed. It used the existing isolated Vercel
Preview only; it did not merge, deploy Production, alter Production credentials
or routing, resume the live loop, or publish.
