# Ticket 40 local viewer acceptance matrix

Target: the viewer at the integration branch revision, served locally and driven
through a visible browser. Deterministic fixture data is injected only into the
browser page; committed canonical state and the empty live baseline registry are
not changed.

| Artifact | Claim | Visible cue | Supporting receipt | Status |
|---|---|---|---|---|
| `01-projection-gated-desktop.png` | The comparison stays unavailable without a complete qualifying cycle and five current controls. | “The paired projection is forming” and the B1–B5/current-control gate copy. | Node projection-gate test. | PASS |
| `02-projection-populated-desktop.png` | A qualifying deterministic fixture shows ALATO, frozen English, control-adjusted values, and fixed assumptions. | Three side-by-side values plus hypothetical/not-telemetry copy and cache cost. | Python/Node projection calculation tests. | PASS |
| `03-v1-v2-invalid-history.png` | History distinguishes V1, valid V2, and invalid V2 judge output without comparing V1/V2 scores. | `legacy V1`, `Scoring V2`, and `INVALID JUDGE RESULT` in visible history. | Node label and invalid-judge tests. | PASS |
| `04-projection-populated-mobile.png` | The populated comparison remains readable at 375px without horizontal overflow. | Three values and fixed-hypothesis copy at mobile width. | Browser viewport/overflow readback: `0px`. | PASS |
| `console.txt` | The tested states produce no browser console warnings or errors. | `Total messages: 0 (Errors: 0, Warnings: 0)`. | Playwright console readback in the same clean routed local session. | PASS |

No video is required for this local, browser-only, non-timed read-only journey;
numbered screenshots and browser receipts are the primary evidence.

## Evidence guide

`01-projection-gated-desktop.png`

- Claim: incomplete evidence cannot unlock the comparison.
- Look for: the Scoring V2 metrics awaiting evidence and the explicit B1–B5/five-control gate.
- Quality: strong.

`02-projection-populated-desktop.png`

- Claim: the deterministic qualifying fixture renders all three comparison values and assumptions.
- Look for: ALATO 31%, frozen English 20%, +11 control-adjusted points, “not provider telemetry,” and the `$0.0378` rulebook-cache cost.
- Quality: strong.

`03-v1-v2-invalid-history.png`

- Claim: valid V2, invalid V2, and legacy V1 remain distinct in the visible history.
- Look for: valid V2 rows, the orange invalid-judge panel explaining evaluator failure, and the `legacy V1 fidelity 92` row.
- Quality: strong.

`04-projection-populated-mobile.png`

- Claim: the populated comparison remains legible at an exact 375px browser width.
- Look for: the stacked three-value cards and complete fixed-assumptions copy with no horizontal clipping.
- Quality: strong.

`console.txt`

- Claim: the clean local session produced no console warnings or errors.
- Look for: the zero/zero receipt.
- Quality: strong.

## Run receipt

- Visible URL: `http://127.0.0.1:8876/` (temporary loopback server, stopped after capture).
- Desktop viewport: 1280×900. Mobile viewport: 375×812.
- Loop count: one; no product repair was needed during the visible acceptance run.
- Fixture boundary: injected into the visible page after load; the local browser routed the two not-yet-on-main baseline reads to deterministic JSON so pre-release 404s could not contaminate the console receipt.
- Cleanup: browser closed and loopback server stopped. No disposable public or canonical state was created.
- Live systems touched: none.
