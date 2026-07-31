# A Language All Their Own

A public, long-running experiment in which two agents build a compact AI-to-AI language and test it against fresh decoders.

## Current contract

- DeepSeek Agent A invents, revises, or proposes repeal of one focused rule at a time.
- Kimi Agent B audits A's add or repeal motion and alone may adopt or reject it.
- Each new A/B turn uses a strict, state-specific Pydantic/OpenRouter action envelope. The harness validates the typed motion, measurements, and `LOOKUP`/`RESEARCH`/`ASK` requests locally instead of extracting them from prose.
- A structurally invalid response receives at most two regeneration attempts. Exhaustion records a complete structural-failure receipt, changes no rule, and retains the same next legislative actor.
- Every attempted legislative turn records an authoritative post-state receipt with the exact changed/unchanged ids, open motion, adopted count, and adopted-language hash. Pre-cutover prose remains readable but non-authoritative.
- Canonical requests, rule records, collaboration rows, receipts, and event history remain complete. The transient A/B legislative prompt does not replay prior events: the authoritative current state/latest receipt, `COMPLETE LEGISLATURE`, and bounded collaboration input are the complete model-facing basis for the next action. No projected form is persisted.
- Full live-test encoded/decoded artifacts and outcome receipts also remain canonical and directly renderable in public history, but no prior live-test event enters a fresh legislative prompt. The structured schema describes the same substantive-deliberation boundary enforced locally.
- Only adopted rule text enters ordinary encoding, decoding, public Try It, and the scheduled Conversation exam. Proposed and rejected material remains public history.
- Ordinary exam results are corpus-level evidence tied to an immutable adopted-language version and hash. Legacy per-rule scores remain labeled history.
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

## Public Try It and optional X delivery

Try It pins encode and decode to one adopted-language version/hash. It uses only `OPENROUTER_PUBLIC_API_KEY`; production acceptance requires separate-key metadata proving a $20 monthly reset limit. Allowance exhaustion, version changes, and unrelated provider failures have distinct responses.

The core experiment timer never invokes X delivery. `tweet.py` remains available only
for a separately approved standalone run; it uses one `x_title` post of at most 250
characters, a stable idempotency identity, and an explicit X receipt. Dry runs and
failures do not advance watermarks or successful-post budget.

## Operations and status

The production loop is `run_turn.sh` on its existing 15-minute timer and commits
generated canonical state to `main`. Collaboration synchronization is best effort;
X delivery is not part of the scheduled turn path.

Offline tests:

```bash
python3 -m unittest discover -s tests/python -p 'test_*.py'
node --test tests/js/*.test.js
python3 tests/acceptance/check_contract_coverage.py
```

Passing these tests is not production acceptance. The required deployed run includes visible desktop and 375px journeys, the full `/human` session lifecycle, cross-turn restart/exact-once behavior, hostile/failure cases, numbered screenshots, one continuous video, independent receipts, and cleanup with one PASS/FAIL/BLOCKED result per row.
