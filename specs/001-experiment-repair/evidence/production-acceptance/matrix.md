# Required Production Acceptance Matrix

**Run state:** PREPARED, NOT AUTHORIZED, NOT RUN

**Overall result:** **BLOCKED**

**Reason:** no reviewed feature push/PR, production pause, credentials, integration, deploy, cleanup, resume, G10 acceptance authorization, or X approvals have occurred.

No row may become PASS from unit tests, source inspection, or backend-only receipts. Screenshot names are reserved; the continuous workflow video is `00-cross-turn-workflow.mp4`.

| # | Feature / failure state | Visible action and expected result | Screenshot | Independent receipt | Cleanup | Result |
|---:|---|---|---|---|---|---|
| 1 | Deployed identity | Open production page; visible commit and adopted version match approved deployment/current state. | `01-deploy-version.png` | Vercel deployment + Git/state hashes | none | BLOCKED |
| 2 | A authority | Observe A propose/revise, then attempt vote; only focused proposal mutates. | `02-a-authority.png` | canonical rule diff + motion receipt | test proposal per approved path | BLOCKED |
| 3 | B authority/no-ops | Observe B audit latest proposal and forbidden unrelated/stale/malformed/settled motions; forbidden actions do nothing. | `03-b-authority.png` | before/after hash + receipts | test motions | BLOCKED |
| 4 | Adopted-only boundary | Complete ordinary, Conversation, and Try It journeys; no non-adopted/collaboration text enters prompts. | `04-adopted-boundary.png` | redacted read-only prompt/hash receipt | none | BLOCKED |
| 5 | Cleanup preview/apply history | `/human` shows original/A/B/exact diff and pending stop; approved apply later preserves full history. | `05-cleanup.png` | source/candidate/audit/applied hashes + state diff | retain immutable artifacts | BLOCKED |
| 6 | RESEARCH lifecycle | Request, reload/restart, show cited or no-evidence result, and correct one-time delivery without rule mutation. | `06-research.png` | canonical record + prompt/state hashes | remove disposable request if approved | BLOCKED |
| 7 | ASK + `/human` lifecycle | Show awaiting, wrong/right login, refresh, browser restart, expiry, logout, private denial, verbatim answer, restart, exact-once delivery. | `07-human-ask.png` | Redis session metadata + canonical delivery receipt | expire/delete test session and ASK | BLOCKED |
| 8 | Suggestions | Submit beneath panes; pending stays private, dismiss/approve persists, approved record publishes and delivers once as optional. | `08-suggestion.png` | queue/canonical/delivery ids | remove test submissions | BLOCKED |
| 9 | Conversation | Display all six alternating messages and a requirement-complete concrete judgment. | `09-conversation.png` | artifact/language hashes | none | BLOCKED |
| 10 | Try It four outcomes | Show normal decode, version mismatch, exhausted monthly allowance, and unrelated provider failure distinctly. | `10-try-it.png` | Vercel logs + key metadata, values redacted | restore normal key/config | BLOCKED |
| 11 | Desktop/mobile disclosure | Complete ASK, suggestion, Conversation, and Try It at desktop and 375px; key content open and history collapsed. | `11-desktop.png`, `12-mobile-375.png` | viewport + deployed commit receipt | none | BLOCKED |
| 12 | Docs/current labels | Compare deployed behavior with README, MECHANICS, page labels; active stale framing absent, history accessible. | `13-docs-labels.png` | source/deploy hashes + search receipt | none | BLOCKED |
| 13 | X approved results | Real profile shows correction, one-post delivery, retry/block result, explainer, pin, and individually approved follows. | `14-x-profile.png` | profile + provider receipts | only approved reversals | BLOCKED |
| 14 | Wrong password | Enter wrong password; no session or private content appears. | `15-wrong-password.png` | 401/session absence | none | BLOCKED |
| 15 | Expired session | Let/test approved absolute expiry; private view closes without extending lifetime. | `16-expired-session.png` | session timestamps | delete expired session | BLOCKED |
| 16 | Duplicate submission | Repeat identical ASK/suggestion action; one stable id and one delivery exist. | `17-duplicate.png` | queue/canonical ids | remove test record | BLOCKED |
| 17 | Rapid requests | Submit approved rapid sequence; perimeter rejects excess without leak or duplicate. | `18-rate-limit.png` | WAF/Vercel receipt | reset only approved test controls | BLOCKED |
| 18 | HTML/script text | Submit literal markup; it renders inert and stays private pending approval. | `19-html-inert.png` | stored payload encoding | dismiss/remove test record | BLOCKED |
| 19 | Prompt injection text | Submit instruction-like text; it cannot vote, expose secrets, bypass moderation, or become law. | `20-injection-inert.png` | prompt delimiter + rule hash | dismiss/remove test record | BLOCKED |
| 20 | Provider timeout | Trigger approved temporary timeout; visible failure is explicit, no silent delivery/retry duplication occurs. | `21-timeout.png` | provider/Vercel request id | restore normal config | BLOCKED |
| 21 | Missing research evidence | Run no-evidence case; limitations are visible and no claim/rule mutation occurs. | `22-no-evidence.png` | research record + rule hash | remove test record | BLOCKED |
| 22 | Rule change during Try It | Change approved fixture version between encode/decode; decode requests re-encode before provider call. | `23-version-race.png` | 409 + provider-call absence | restore fixture/current state | BLOCKED |
| 23 | Spending cap | Exhaust approved temporary public cap; reopening message is distinct and no private key fallback occurs. | `24-cap.png` | public key limit/reset/id metadata | restore approved production key/config | BLOCKED |
| 24 | Three X failures | Exercise exactly three approved failures; fourth attempt is absent, item is blocked, later note can proceed. | `25-x-blocked.png` | stable id/attempt/provider receipts | restore test delivery config | BLOCKED |
| 25 | Historical integrity | Verify proposed/rejected history, rolling last-ten average, immutable pre-cleanup artifacts, and truthful posted/delivered states. | `26-history.png` | hashes/query results | none | BLOCKED |
| 26 | Final cleanup/health | Visible cleanup completes; queues/leases/test data are empty, no duplicates, dirty files, stuck warnings, or timer/site warnings remain. | `27-clean-final.png` | Redis/state/git/service/Vercel/X receipts | all disposable data removed | BLOCKED |

An overall PASS is forbidden until all 26 rows are PASS, every screenshot and the continuous video are inspectable, supporting receipts agree, and cleanup is complete.
