# A Language All Their Own

A public, long-running experiment in which two agents build a compact AI-to-AI language and test it against fresh decoders.

## Current contract

- DeepSeek Agent A invents or revises one focused proposal.
- Kimi Agent B audits A's proposal and alone may adopt or reject it.
- The harness rejects role violations, malformed references, repeated settled motions, and multiple motions as reason-coded no-ops.
- Only adopted rule text enters ordinary encoding, decoding, public Try It, and the scheduled Conversation exam. Proposed and rejected material remains public history.
- Ordinary exam results are corpus-level evidence tied to an immutable adopted-language version and hash. Legacy per-rule scores remain labeled history.
- A judge score is valid only when every answer-key item appears exactly once with a valid verdict.

## Collaboration

The product uses one minimal durable Redis REST inbox. Vercel functions enqueue visitor suggestions and human moderation commands; the existing Python loop is the sole writer of canonical `state/collaboration.json` history. That canonical file stays off the public Git history and is backed up to private Redis; the page fetches only `state/public-collaboration.json`, which contains the sanitized lifecycle view.

- `RESEARCH:` creates a correlated, cited, non-blocking evidence request. Retrieved pages are untrusted evidence and have no legislative authority.
- `ASK:` creates a public `awaiting Iso` lifecycle. Iso answers verbatim through the password-protected `/human` page; the requesting agent receives the original question and answer together exactly once.
- Visitor suggestions stay private until Iso approves them. One approved suggestion may reach one eligible turn as delimited optional context, never as language law.
- Every 32 ordinary exams, fresh DeepSeek and Kimi speakers complete a six-message real-work Conversation using a captured adopted-language snapshot, followed by a concrete-outcome judgment.

## Public Try It and X

Try It pins encode and decode to one adopted-language version/hash. It uses only `OPENROUTER_PUBLIC_API_KEY`; production acceptance requires separate-key metadata proving a $20 monthly reset limit. Allowance exhaustion, version changes, and unrelated provider failures have distinct responses.

X delivery uses one `x_title` post of at most 250 characters, a stable idempotency identity, and an explicit X receipt. Dry runs and failures do not advance watermarks or successful-post budget. Three unconfirmed attempts block that item while later items may continue.

## Operations and status

The production loop remains `run_turn.sh` on its existing 15-minute timer and commits generated canonical state to `main`. The feature branch does not change production until its separately approved pause, credential, integration, deploy, cleanup, resume, acceptance, and X gates are executed.

Offline tests:

```bash
python3 -m unittest discover -s tests/python -p 'test_*.py'
node --test tests/js/*.test.js
python3 tests/acceptance/check_contract_coverage.py
```

Passing these tests is not production acceptance. The required deployed run includes visible desktop and 375px journeys, the full `/human` session lifecycle, cross-turn restart/exact-once behavior, hostile/failure cases, numbered screenshots, one continuous video, independent receipts, and cleanup with one PASS/FAIL/BLOCKED result per row.
