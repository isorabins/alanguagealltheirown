# Current-Deployment Crabbox Acceptance Evidence

**Target:** `https://alanguagealltheirown.com` as deployed on 2026-07-21
**Result:** **FAIL**
**Canonical disposition:** 24 FAIL, 2 BLOCKED

The public homepage returned HTTP 200, but the deployed site is the old
production version. The required `/human` surface returns a visible Vercel
`404: NOT_FOUND`, so the new collaboration, cleanup, session, failure-control,
and production-acceptance journeys cannot run on this deployment. X rows 13
and 24 remain BLOCKED because the approval explicitly prohibited X actions.

The generic runner's 9 passing text/visibility probes are surface smoke checks,
not contract-row passes. The canonical matrix does not promote any row without
the required visible action and independent receipt.

## Primary evidence

- Canonical matrix: `../matrix.md`
- Runner receipt: `runner/matrix-results.json` (26 rows, 9 limited probes PASS,
  17 probes FAIL, 1 browser-process restart)
- Continuous outer recording: `00-cross-turn-workflow.mp4` (120 seconds,
  H.264, 1920x1080, 15 fps)
- Video contact sheet: `00-cross-turn-workflow.contact.png`
- HTTP receipt: `runner/production-home-http.json`
- Crabbox proof: `crabbox-proof/`
- Lease receipt: `lease.json`
- Spend receipt: `spend.json`
- Teardown receipts: `coordinator-cleanup.json` and `hetzner-cleanup.json`
- Evidence audit: `audit-summary.json`

The recording is continuous across the runner's browser-process restart, but
its visual quality is only acceptable when paired with the runner receipt: most
sampled frames show the remote desktop terminal and only some show the browser.
It does not independently prove the missing semantic journeys.

## Screenshot audit

| Screenshot | Visible location/state | Evidence quality and claim |
|---|---|---|
| `01-deploy-version.png` | Public homepage | Strong proof that the old public page renders; insufficient for reviewed commit/version identity. |
| `02-a-authority.png` | Public homepage | No repeal-authority surface; row fails. |
| `03-b-authority.png` | Public homepage | Text-only smoke probe passed, but no B audit/no-op actions or receipts; row fails. |
| `04-adopted-boundary.png` | Public homepage | Try It heading exists, but adopted-only prompt boundaries were not exercisable; row fails. |
| `05-cleanup.png` | `/human` | Strong visible 404 proof; cleanup surface absent. |
| `06-research.png` | `/human` | Strong visible 404 proof; RESEARCH lifecycle absent. |
| `07-human-ask.png` | `/human`, after browser restart | Strong visible 404 proof plus runner restart receipt; login/ASK lifecycle absent. |
| `08-suggestion.png` | Public homepage | No suggestion surface; row fails. |
| `09-conversation.png` | Public homepage | No six-message Conversation surface; row fails. |
| `10-try-it.png` | Public homepage | Try It heading exists, but four outcomes were not exercisable; row fails. |
| `11-desktop.png` | Public homepage, 1440px viewport | Desktop renders; required journeys are absent. |
| `12-mobile-375.png` | Public homepage, 375px viewport | Mobile page renders; required journeys are absent. |
| `13-docs-labels.png` | Public homepage | Required current labels/history comparison did not pass. |
| `14-x-profile.png` | Public homepage | No X action performed; canonical row BLOCKED. |
| `15-wrong-password.png` | `/human` | Strong visible 404 proof; password behavior cannot be exercised. |
| `16-expired-session.png` | `/human` | Strong visible 404 proof; expiry behavior cannot be exercised. |
| `17-duplicate.png` | `/human` | Strong visible 404 proof; duplicate submission cannot be exercised. |
| `18-rate-limit.png` | `/human` | Strong visible 404 proof; rapid-request behavior cannot be exercised. |
| `19-html-inert.png` | `/human` | Strong visible 404 proof; inert-markup behavior cannot be exercised. |
| `20-injection-inert.png` | `/human` | Strong visible 404 proof; prompt-injection boundary cannot be exercised. |
| `21-timeout.png` | Public homepage | No approved provider-failure control; row fails. |
| `22-no-evidence.png` | `/human` | Strong visible 404 proof; no-evidence lifecycle cannot be exercised. |
| `23-version-race.png` | Public homepage | Text-only smoke probe passed, but no version-race action/receipt; row fails. |
| `24-cap.png` | Public homepage | Text-only smoke probe passed, but no cap-exhaustion action/receipt; row fails. |
| `25-x-blocked.png` | Public homepage | No X action performed; canonical row BLOCKED. |
| `26-history.png` | Public homepage | Historical integrity was not independently verifiable; row fails. |
| `27-clean-final.png` | Public homepage | Site is visibly reachable and HTTP receipt is 200; full production cleanup/health contract is unproven, so row fails. |

## Infrastructure and cleanup

Exactly one Hetzner CPX32 lease (`cbx_c2769e5ab363`, server `153477287`,
`fsn1`) was used with an eight-hour TTL and 30-minute idle timeout. It ran for
601 seconds and Crabbox metered approximately `$0.01` of new infrastructure,
below the approved `$2` ceiling. After teardown, the coordinator reported zero
active leases and the Hetzner account reported zero matching servers and zero
matching SSH keys.

No bounded submissions could be created because the required visible surfaces
do not exist on the deployed site. Production configuration, canonical state,
deployment, loop state, and X were not changed. Crabbox proof reported that the
optional WebVNC daemon was not running. That diagnostic does not affect the
result because Playwright, outer X11 recording, proof capture, and teardown all
completed; the original manual classification of it as a separate pass blocker
was corrected on 2026-07-22.
