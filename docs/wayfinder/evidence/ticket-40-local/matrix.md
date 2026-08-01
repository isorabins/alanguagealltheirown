# Ticket 40 local viewer acceptance matrix

Target: the Scoring V2 history viewer at the integration branch revision, served
locally and driven through a visible browser. Deterministic fixture data is
injected only into the browser page; committed canonical state is not changed.

| Artifact | Claim | Visible cue | Supporting receipt | Status |
|---|---|---|---|---|
| `03-v1-v2-invalid-history.png` | History distinguishes V1, valid V2, and invalid V2 judge output without comparing V1/V2 scores. | `legacy V1`, `Scoring V2`, and `INVALID JUDGE RESULT` in visible history. | Node label and invalid-judge tests. | PASS |
| `console.txt` | The history state produces no browser console warnings or errors. | `Total messages: 0 (Errors: 0, Warnings: 0)`. | Playwright console readback in the same clean routed local session. | PASS |

No video is required for this local, browser-only, non-timed read-only journey;
the numbered screenshot and browser receipt are the primary evidence.

## Evidence guide

`03-v1-v2-invalid-history.png`

- Claim: valid V2, invalid V2, and legacy V1 remain distinct in the visible history.
- Look for: valid V2 rows, the orange invalid-judge panel explaining evaluator failure, and the `legacy V1 fidelity 92` row.
- Quality: strong.

`console.txt`

- Claim: the clean local session produced no console warnings or errors.
- Look for: the zero/zero receipt.
- Quality: strong.

## Run receipt

- Visible URL: `http://127.0.0.1:8876/` (temporary loopback server, stopped after capture).
- Desktop viewport: 1280×900.
- Loop count: one; no product repair was needed during the visible acceptance run.
- Fixture boundary: V1, valid V2, and invalid-judge rows were injected into the visible page after load.
- Cleanup: browser closed and loopback server stopped. No disposable public or canonical state was created.
- Live systems touched: none.
