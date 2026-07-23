# Current State Receipt

## State

- Audited local commit: `820ae90` on `main`.
- Remote `main` verified without fetching: `5551f6f280f8a74e273178e354da7f94f16887af` on 2026-07-20 WITA.
- The remote is 13 commits beyond the audited checkout; those commits change generated/runtime state only, not prompts, engine code, PRDs, or docs.
- Latest inspected remote state: turn 537, rulebook version `0.236`, 20 adopted, 61 proposed, 24 rejected, 7 reverted, 173 exams, recorded spend `$1.605049`, last legislative agent `B`.
- X state in that snapshot: 6 notes recorded posted, 30 total tweets recorded sent.

## Result

The app is a real evolving experiment, but its strongest public claim is not currently justified. The engine gives proposed rules to ordinary encoder/decoder exams and stamps corpus scores across many rules, so it cannot show that each adopted rule individually survived a test.

## Evidence

- `AUDIT-FINDINGS-2026-07-20.md` contains the decision-grade audit, scorecard, contradictions, and Iso's agreed repair decisions.
- `loop.py` currently renders the rulebook, runs DeepSeek legislative turns, generates payloads, invokes the encoder/decoder/judge, and writes public state.
- `state/rulebook.json` and `state/conversation.json` are canonical runtime artifacts.
- `viewer/index.html` plus `viewer/state.js` form the public static view; `viewer/api/*.js` are Vercel Try It handlers.
- `tweet.py` handles X delivery through Upload-Post.

## Blocker

There is no implementation blocker yet because planning has not begun. The planning phase must resolve the smallest durable bridge for website-submitted ASK answers and suggestions: Vercel functions cannot safely write the VPS's canonical JSON files directly, and the existing single-file notice inbox is not a safe multi-message queue.

Do not solve this by adding a large auth/admin platform. Choose one minimal durable inbox in the plan, keep the production loop as the sole writer of canonical experiment history, and make website submissions idempotent.

## Human Gate

The spec does not authorize implementation or live changes. The new chat must produce `plan.md` and `tasks.md`, analyze them against `BUILD-SPEC.md`, and obtain Iso's approval before implementation.

## Claims Not Yet Verified

- Production Try It paid flow after these changes.
- Current OpenRouter key metadata or a verified $20 public monthly limit.
- Production server-side cache behavior.
- Any future cleanup diff or repaired rulebook.
- Any corrected/pinned X post or curated follows.
- Any deployed `/human`, suggestion, RESEARCH, ASK, or Conversation journey.

