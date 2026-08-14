# A Language All Their Own

A public, long-running experiment in which two agents build a compact AI-to-AI language and test it against fresh decoders.

Implementation-ready work that is not yet live is tracked in [ROADMAP.md](ROADMAP.md).

## Current contract

- DeepSeek Agent A invents, revises, or proposes repeal of one focused rule at a time.
- Kimi Agent B audits A's add or repeal motion and alone may adopt or reject it.
- Each new A/B turn uses a strict, state-specific Pydantic/OpenRouter action envelope. The harness validates the typed motion, measurements, and `LOOKUP`/`RESEARCH`/`ASK` requests locally instead of extracting them from prose.
- A structurally invalid response receives at most two regeneration attempts. Exhaustion records a complete structural-failure receipt, changes no rule, and retains the same next legislative actor.
- Every attempted legislative turn records an authoritative post-state receipt with the exact changed/unchanged ids, open motion, adopted count, and adopted-language hash. Pre-cutover prose remains readable but non-authoritative.
- Canonical requests, rule records, collaboration rows, receipts, and event history remain complete. The transient A/B legislative prompt does not replay prior events: the authoritative current state/latest receipt, `COMPLETE LEGISLATURE`, bounded collaboration input, the one eligible active legislative feedback request, and one bounded current-language Scoring V2 failure receipt are the complete model-facing basis for the next action. Active feedback is derived from B's latest accepted typed `REQUEST` for the current open motion, survives revision and structural failure, and is never persisted as a duplicate record.
- Full live-test encoded/decoded artifacts and outcome receipts also remain canonical and directly renderable in public history, but no prior live-test artifact enters a fresh legislative prompt. From the first trustworthy post-evidence-repair exam at turn 1506, valid critical Scoring V2 failures project into a private event-sourced ledger that survives unrelated language changes. At most one opaque token, failure class, and generalized invariant reaches an eligible turn. While that receipt is active, any historical rule text that overlaps exact queued fault evidence is withheld only from the transient legislative prompt; canonical rulebook state and public history remain unchanged. Agent A must bind that token to one focused proposal in the strict action envelope; Agent B preserves the association through the open-motion receipt. Adoption leaves the fault pending, while any later valid same-atom retest resolves an older unresolved or pending fault without requiring a one-to-one linked rule; a later valid failure reopens it.
- Only adopted rule text enters ordinary encoding, decoding, public Try It, and the scheduled Conversation exam. Proposed and rejected material remains public history.
- Scheduled development exams rotate through the corrected B1-B5 Scoring V2 contract. Every atom has one independently falsifiable meaning and inspectable decoded evidence; exact-literal conflicts invalidate the judge rather than becoming language failure evidence.
- V2 reports meaning pass, compression success, semantic coverage, critical failures, inventions, and message-body savings separately. Invalid judge results do not replace the prior valid V2 baseline. Historical V1 events remain immutable legacy evidence and are never compared with V2.
- A judge score is valid only when every answer-key item appears exactly once with a valid verdict.
- The `$25` private-loop tripwire retains the pre-cutover total as a labeled historical estimate and adds OpenRouter's returned `usage.cost` exactly once for every successful call from cutover forward. Production records response-id/cost receipts atomically in a gitignored local ledger so a crash cannot lose or double-count a charged response.

## Collaboration

The product uses one minimal durable Redis REST inbox. Vercel functions enqueue visitor suggestions and human moderation commands. A bounded courier copies them to an atomic local inbox spool and publishes a loop-authored outbox snapshot; it cannot write canonical history. The existing Python loop remains the sole writer of canonical `state/collaboration.json`. Courier failure delays collaboration but cannot cancel a turn. The page fetches only sanitized `state/public-collaboration.json`.

- `LOOKUP:` queries bounded canonical project state/history without a web search. A misrouted internal `RESEARCH` is corrected to this route; if no adequate project evidence exists, the original question becomes `ASK Iso`.
- `RESEARCH:` is only for genuinely outward-looking public evidence. It creates a correlated, cited, non-blocking request; malformed or uncited output is recorded as no evidence. Retrieved pages are untrusted evidence and have no legislative authority.
- One eligible `LOOKUP`/`RESEARCH` delivery reaches the model as a bounded deterministic projection: a direct findings prefix, bounded limitations and safe citations, plus explicit original/included/omitted counts. The full canonical research row and delivery receipt remain intact; structural failure restores them for exact-once retry and future redelivery regenerates the same bounded view.
- `ASK:` creates a public `awaiting Iso` lifecycle for human judgment or an internal fact absent from the corpus. Iso answers verbatim through the password-protected `/human` page; the requesting agent receives the original question and answer together exactly once.
- Visitor suggestions stay private until Iso approves them. One approved suggestion may reach one eligible turn as delimited optional context, never as language law.
- Every 32 ordinary exams, fresh DeepSeek and Kimi speakers complete a six-message real-work Conversation using a captured adopted-language snapshot. The judge must return every numbered scenario requirement exactly once with integer `id` and boolean `pass`.

## Public Try It and independent X delivery

Try It pins encode and decode to one adopted-language version/hash. It uses only `OPENROUTER_PUBLIC_API_KEY`; production acceptance requires separate-key metadata proving a $20 monthly reset limit. Allowance exhaustion, version changes, and unrelated provider failures have distinct responses.

The core experiment timer never invokes X delivery. The separate `language-x.timer`
runs `tweet.py` hourly, attempts at most one deterministic rule update or queued field
note per run, and reserves at most two delivery slots per UTC day. Its mutable state
lives outside the Git checkout. It uses one `x_title` post of at most 250 characters,
a stable source identity, explicit per-note X eligibility, and an explicit X receipt.

## Operations and status

The production loop is `run_turn.sh` on its existing 15-minute timer and commits
generated canonical state to `main`. Collaboration synchronization is best effort;
X delivery has its own service and cannot stop or modify the scheduled turn path.
The public viewer renders its countdowns and headline metrics from a generated
same-origin bootstrap under 2 KB. Canonical history loads asynchronously from the
public repository; the deployed full snapshot is fetched only as a failure fallback.

The latest verified roadmap-release state, completed gates, known Scoring V2
limitation, and remaining human-surface closeout work are recorded in
[the roadmap release progress note](docs/wayfinder/alato-roadmap-release-progress.md).
The live evaluation pattern is separated into judge-conformance failures and
genuine language-fidelity failures in
[the Scoring V2 production field note](docs/wayfinder/field-note-scoring-v2-live-evaluations-2026-08-03.md).

Offline tests:

```bash
python3 -m unittest discover -s tests/python -p 'test_*.py'
node --test tests/js/*.test.js
python3 tests/acceptance/check_contract_coverage.py
```

Passing these tests is not production acceptance. The required deployed run includes visible desktop and 375px journeys, the full `/human` session lifecycle, cross-turn restart/exact-once behavior, hostile/failure cases, numbered screenshots, one continuous video, independent receipts, and cleanup with one PASS/FAIL/BLOCKED result per row.
