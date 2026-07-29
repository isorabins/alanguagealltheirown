# Human answer repair evidence matrix

Pass target: from the real `/human` surface, Iso can enter an answer, submit it,
see an unambiguous success state, refresh the page, and see the same answer
persisted.

| Check | Environment | Expected | Evidence | Status |
|---|---|---|---|---|
| Pending question renders with an answer control | Production, existing signed-in Chrome tab | The question and answer form are visible | `production-expired-session.png` | Pass |
| Current submit failure is characterized | Production UI plus read-only browser diagnostics | The visible symptom and failing request or client error are identified without creating production data | Six `POST /api/human-action` requests at approximately 11:34 WITA returned `401`; the visible session expiry was 10:57:13 WITA | Pass |
| Expired-session recovery preserves the draft | Local test surface | The stale inbox becomes a clear login prompt, then the same draft returns after login | `local-expired-session.png`, `local-draft-restored.png` | Pass |
| Repaired submit succeeds | Local test surface | Submit gives a clear success state | `local-answer-queued.png`; `collaboration-api.test.js` | Pass |
| Submitted answer persists after refresh | Local test surface | The same answer remains after reload | `local-answer-persisted.png`; `collaboration-api.test.js` | Pass |
| Production authentication recovers | Production, existing signed-in Chrome tab | A fresh non-sliding session exposes the five named questions | `01-live-authenticated-five-asks.png`; `GET /api/human-inbox` returned `200` | Pass |
| Production submit succeeds | Production, existing signed-in Chrome tab | Each answer receives a clear queued state | `02-live-first-answer-pending.png`, `03-live-five-answers-pending.png`; exactly five `POST /api/human-action` requests returned `202` from deployment `dpl_EytqptsgKTxvEmweXD2TCBcQ7bz7` | Pass |
| Production answers persist after refresh | Production, existing signed-in Chrome tab | All five exact answers remain visible after the real Refresh action | `04-live-five-answers-persisted.png`; subsequent `GET /api/human-inbox` requests returned `200` | Pass |
| Queued answers enter canonical history | Production loop and refreshed `/human` surface | The courier imports each accepted command exactly once and the UI replaces queued state with recorded state | Turn 1147 imported four commands; turn 1148 imported the fifth and delivered the first to Agent B. `05-live-four-answers-recorded.png`, `07-live-five-answers-recorded.png` | Pass |

## Finding

The six production clicks were not dead: they reached the API after the
non-sliding session had expired and correctly received `401`. The page kept the
stale inbox visible and discarded the rejected promise, so the failure looked
like an inert button.

The repair now:

- swaps the stale inbox for an explicit login prompt;
- preserves the typed draft in page memory through re-authentication;
- shows a submitting state and visible API errors;
- overlays accepted moderation commands as `answer_pending`; and
- displays the exact queued answer after submit and refresh.
