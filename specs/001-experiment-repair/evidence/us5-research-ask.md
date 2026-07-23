# US5 Offline Evidence — RESEARCH, ASK, and `/human`

Result: **PASS for local contracts; deployed login lifecycle and cross-turn production receipt remain blocked**.

- Redis transport is isolated in `collab_sync.py`. The bounded courier uses atomic idempotent enqueue, queue-wide leases, peek-without-remove claims, fsynced local inbox receipts before owner-bound ack-only removal, and stable-id dedupe. The loop contains no Redis client or call and alone imports the spool into canonical history. A crash expires the lease while leaving the record queued; a stale owner cannot acknowledge a new lease, and a spooled private snapshot can recover after local loss.
- `test_research_lifecycle.py` resolves only the oldest queued request, retains its original question, standardized citations/limitations, and cannot mutate rule state. Provider/no-evidence failure is explicit.
- Research delivery is requester-only and includes the original question, findings, limitations, and citations together. Provider tokens and web-search request fees are included in canonical spend accounting.
- `test_ask_lifecycle.py` proves unanswered questions stay open and non-blocking; an answer is delivered verbatim with the original question to its requester exactly once.
- `/human` has login, session check, refresh, private inbox, answer/moderate actions, and logout. The opaque secure cookie is persistent for an absolute non-sliding 30 minutes; no accounts or OAuth exist.
- Vercel queues commands; the courier moves transport only; the Python loop alone writes gitignored canonical `state/collaboration.json` and an atomic private outbox. Best-effort courier publication backs that snapshot up to Redis. The page fetches only sanitized `state/public-collaboration.json`/viewer state and never canonical private collaboration.
