# US5 Offline Evidence — RESEARCH, ASK, and `/human`

Result: **PASS for local contracts; deployed login lifecycle and cross-turn production receipt remain blocked**.

- Redis transport uses atomic idempotent enqueue, queue-wide leases, peek-without-remove claims, ack-only removal, and processed-id dedupe. A crash expires the lease while leaving the record queued.
- `test_research_lifecycle.py` resolves only the oldest queued request, retains its original question, standardized citations/limitations, and cannot mutate rule state. Provider/no-evidence failure is explicit.
- Research delivery is requester-only and includes the original question, findings, limitations, and citations together.
- `test_ask_lifecycle.py` proves unanswered questions stay open and non-blocking; an answer is delivered verbatim with the original question to its requester exactly once.
- `/human` has login, session check, refresh, private inbox, answer/moderate actions, and logout. The opaque secure cookie is persistent for an absolute non-sliding 30 minutes; no accounts or OAuth exist.
- Vercel queues commands; the Python loop alone writes canonical `state/collaboration.json` and sanitized public state.
