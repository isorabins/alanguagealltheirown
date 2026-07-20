# US5 Offline Evidence — RESEARCH, ASK, and `/human`

Result: **PASS for local contracts; deployed login lifecycle and cross-turn production receipt remain blocked**.

- Redis transport uses atomic idempotent enqueue, queue-wide leases, peek-without-remove claims, fsynced canonical receipt plus private Redis backup before owner-bound ack-only removal, and processed-id dedupe. A crash expires the lease while leaving the record queued; a stale owner cannot acknowledge a new lease, and private state can recover after local loss.
- `test_research_lifecycle.py` resolves only the oldest queued request, retains its original question, standardized citations/limitations, and cannot mutate rule state. Provider/no-evidence failure is explicit.
- Research delivery is requester-only and includes the original question, findings, limitations, and citations together. Provider tokens and web-search request fees are included in canonical spend accounting.
- `test_ask_lifecycle.py` proves unanswered questions stay open and non-blocking; an answer is delivered verbatim with the original question to its requester exactly once.
- `/human` has login, session check, refresh, private inbox, answer/moderate actions, and logout. The opaque secure cookie is persistent for an absolute non-sliding 30 minutes; no accounts or OAuth exist.
- Vercel queues commands; the Python loop alone writes gitignored canonical `state/collaboration.json`, backs it up privately, and publishes only sanitized `state/public-collaboration.json`/viewer state. The public page never fetches canonical private collaboration.
