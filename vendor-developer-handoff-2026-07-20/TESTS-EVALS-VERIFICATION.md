# Tests, Evals, and Verification Contract

Passing unit tests is necessary but not sufficient. The implementation is complete only with evidence for the actual state boundary, user journeys, provider/account boundaries, and approved public actions.

The binding final acceptance procedure is the `Required Production Acceptance Test` in `BUILD-SPEC.md`. This file supplies the engineering test detail; it does not reduce or replace that visible production run. The overall result is `PASS` only when every evidence-matrix row passes, the continuous cross-turn video and numbered screenshots are complete, independent receipts agree with visible state, and test cleanup leaves no stuck or duplicate state.

## P1 Contract Tests

- Status fixture proves ordinary encoder, decoder, Conversation, and Try It prompts contain all adopted rules and no proposed/rejected/reverted text.
- Explicit proposal trial proves only one labeled proposal can join the adopted set.
- Corpus exam updates corpus evidence only; no per-rule “survived” claim appears without a proposal trial.
- A vote, B unrelated proposal, repeated settled motion, malformed id, no-op revise/adopt/reject, and multi-motion overflow cause zero forbidden mutations.
- Judge fixtures for complete, missing, duplicate, nonnumeric, and out-of-range ids publish a score only for the complete one-to-one case.
- Dumb-script runtime, prompt, economics, and current-page searches return zero active references while history remains readable.
- Cleanup fixture produces immutable before state, A output, B audit, and exact diff without production writes.

## Collaboration Tests

- RESEARCH request/result survives restart, retains original question, cites sources, returns at most one oldest request per turn, and cannot mutate rule state.
- ASK retains original question and Iso's verbatim answer, remains non-blocking, rejects duplicate/closed-id answers, and delivers once.
- Wrong/missing `/human` password cannot read private moderation data or write answers; successful session uses a secure remembered cookie without accounts/OAuth.
- Pending/dismissed suggestions appear in neither public output nor agent prompts.
- One approved suggestion is delivered once, clearly optional, with no automatic rule effect.
- Concurrency fixtures prove website submission and loop consumption are idempotent and do not overwrite each other.

## Conversation and Try It

- Judged Conversation contains the full intended alternating exchange, adopted rulebook version, models, task requirements, and visible outcome verdict.
- Try It covers: normal journey, forced rulebook-version mismatch, monthly-cap exhaustion, unrelated provider error, and restart/cold-start behavior.
- Current key metadata proves the public key differs from the private experiment key and has a $20 monthly reset limit before production acceptance.

## X Delivery Tests

- Dry run, non-2xx response, timeout before receipt, timeout after provider acceptance, asynchronous receipt, and partial-platform response never create false posted state.
- Retries reuse one stable provider idempotency identity.
- Exactly three failed attempts lead to `blocked`; a fourth automatic attempt cannot occur; later notes continue.
- Successful records include the confirmed post id.
- Generated automated copy is at most 250 characters and uses the X-specific text field; no implicit thread.

## Human-App-Testing Journeys

Test both desktop and 375px mobile through the deployed surface:

1. First-time visitor understands the premise, agents, adopted-language boundary, exam, and 50% access mission.
2. Current/interesting material is open; repetitive history is collapsed.
3. Suggestion form is directly below the A/B windows and its moderation status is honest.
4. Open and answered ASK states are understandable.
5. Iso signs into `/human`, answers an ASK, moderates a suggestion, refreshes/revisits, and sees durable state.
6. Try It shows correct normal, mismatch, allowance, and provider-error states.

## Public Verification

Do not call correction, explainer, pin, or follows complete from API responses alone. After Iso approves each item, inspect the real X profile and record the live post/profile evidence. Likewise, do not call the site live from a deploy receipt alone; open the production URL and verify the relevant journeys.
