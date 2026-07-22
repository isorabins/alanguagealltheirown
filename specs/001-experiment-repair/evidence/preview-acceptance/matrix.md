# Preview Acceptance Matrix

Date: 2026-07-22 WITA

Run state: **PLANNED; awaiting exact preview approval.**

Overall preview result is `PASS` only when every `REQUIRED` row below passes and
the evidence/cleanup audit passes. `BLOCKED-BY-DESIGN` rows remain production
gaps and prevent any production-complete claim, but do not invalidate an honest
Preview checkpoint.

| # | Preview row | Visible proof | Evidence | Requirement | Result |
|---:|---|---|---|---|---|
| 1 | Exact Preview identity | Open Preview URL; page and route receipt match tested commit; Production remains old deployment | `01-preview-identity.png`, Vercel/HTTP receipts | REQUIRED | PENDING |
| 2 | Public page and adopted-language story | First-time visitor can understand agents, adopted-only boundary, exams, history, and 50% mission | `02-public-story.png` plus source/hash receipt | REQUIRED | PENDING |
| 3 | `/human` authentication lifecycle | Wrong password denied; correct login, refresh, browser restart, logout, and private denial behave visibly | `03-wrong-password.png` through `07-logout-denied.png`; session metadata receipt | REQUIRED | PENDING |
| 4 | Visitor suggestion moderation | Submit below agent panes; pending text remains private publicly; approve and dismiss through `/human` with durable visible status | `08-suggestion-submit.png` through `11-suggestion-moderation.png`; Redis ids/count receipt | REQUIRED | PENDING |
| 5 | Try It normal journey | Encode and decode visibly complete with one rulebook version and the separate Preview key | `12-try-it-normal.png`; Vercel/key metadata receipt | REQUIRED | PENDING |
| 6 | Try It failure distinctions | Version mismatch, allowance exhaustion, and unrelated provider failure have distinct visible outcomes without private-key fallback | `13-version-mismatch.png` through `15-provider-failure.png`; no-call/key receipts | REQUIRED | PENDING |
| 7 | Hostile and duplicate inputs | Duplicate, rapid, HTML/script, and prompt-injection text remain inert, private, bounded, and non-duplicated | `16-duplicate.png` through `19-injection-inert.png`; queue/idempotency receipts | REQUIRED | PENDING |
| 8 | Desktop/mobile disclosure | Required public and `/human` journeys work at desktop and 375px; current material open, history collapsed | `20-desktop.png`, `21-mobile-375.png` | REQUIRED | PENDING |
| 9 | Documentation and truthful labels | README/MECHANICS/page copy match the Preview behavior; historical dumb-script material remains only as history | `22-docs-labels.png`; search/deploy receipts | REQUIRED | PENDING |
| 10 | Evidence quality and continuity | One outer X11 MP4 starts before browser action, visibly spans one browser-process restart, and ends on final clean state | `00-preview-workflow.mp4`, contact sheet, restart receipt, evidence guide | REQUIRED | PENDING |
| 11 | Cleanup and infrastructure | Disposable test data removed visibly; secret audit passes; spend <= `$2`; zero leases/servers/SSH keys | `23-clean-final.png`, cleanup/spend/provider receipts | REQUIRED | PENDING |
| 12 | Draft PR delivery | Final tested commit and scoped evidence are pushed only to existing draft PR 1; no merge/Production change | git/PR/Production receipts | REQUIRED | PENDING |
| 13 | A/B live legislative authority | Requires natural canonical loop turns and production state receipts | none | BLOCKED-BY-DESIGN | BLOCKED |
| 14 | Cleanup original/A/B/diff/apply | T120 has no valid cleanup bundle; Preview may show an honest empty/blocked cleanup state only | blocked screenshot/receipt | BLOCKED-BY-DESIGN | BLOCKED |
| 15 | RESEARCH/ASK exact-once loop delivery | Requires the paused production loop or an unapproved competing canonical writer | blocked screenshot/receipt | BLOCKED-BY-DESIGN | BLOCKED |
| 16 | Six-message scheduled Conversation | Requires the canonical scheduled loop artifact | blocked screenshot/receipt | BLOCKED-BY-DESIGN | BLOCKED |
| 17 | X correction/explainer/pin/follows/retry | Public X actions are explicitly excluded | none | BLOCKED-BY-DESIGN | BLOCKED |
| 18 | Production acceptance and live health | Requires merge, Production deploy, cleanup application, loop resume, and later per-item approvals | production read-only receipts | BLOCKED-BY-DESIGN | BLOCKED |
