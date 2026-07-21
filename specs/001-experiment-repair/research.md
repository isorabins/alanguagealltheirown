# Phase 0 Research: Experiment Repair and Public Collaboration

**Checked**: 2026-07-20 WITA  
**Baseline**: synchronized local/remote `main`
`72badf981298fdbdeb8b5a28f074d7bd5fd6b2bb` (turn 540)

No material product clarification remains. The specification fixes the product
boundaries; this research resolves implementation choices only.

## Decision 1: One Upstash Redis collaboration inbox

**Decision**: Use one Upstash Redis database, accessed only through server-side
REST calls from Vercel functions and the VPS loop. Store immutable event bodies,
small lifecycle records, sorted-set queues, short leases, session records, and
idempotency keys under a project namespace. Use atomic Lua/transaction commands
for enqueue, claim, moderate, answer, acknowledge, and retry transitions.

**Rationale**: Vercel functions and the VPS need one durable, mutually reachable
store. Upstash is Vercel's current standard Redis marketplace path, its REST API
supports transactions and scripting, and neither runtime needs a long-lived
connection. The loop remains the only writer of canonical experiment history in
`state/collaboration.json`; Redis is the collaboration inbox and session store,
not a second rule ledger.

**Alternatives considered**:

- SQLite on the VPS: rejected because Vercel would need a new public VPS service,
  TLS/routing, and an additional production daemon.
- Postgres/Supabase: rejected as unnecessary schema/admin scope for a low-volume
  queue.
- Vercel Blob or `pending-notice.txt`: rejected because they do not provide the
  atomic multi-message claim/ack behavior required for concurrency.
- A general auth/admin SaaS: rejected by FR-020 and the explicit non-goal.

**Official sources**:

- Vercel Marketplace storage: https://vercel.com/docs/marketplace-storage
- Vercel Redis direction: https://vercel.com/docs/redis
- Upstash REST transactions/scripts: https://upstash.com/docs/redis/features/restapi

## Decision 2: Idempotent inbox plus canonical deduplication

**Decision**: Every command/event has a stable UUID and optional client
idempotency key. Redis enqueue is atomic. The loop claims at most the bounded
eligible item, records the event id in canonical state when it affects a prompt,
writes state atomically, then acknowledges the lease. On restart, a claimed item
is either already present in canonical history and safely acknowledged, or its
lease expires and it is retried. Agent calls are stateless; only a response that
is durably recorded counts as delivery.

**Rationale**: This makes persistence and canonical delivery exactly once under
process restart without letting Vercel mutate experiment JSON. A provider timeout
cannot create a lasting hidden agent action because parser/state mutation occurs
only after a valid response is durably recorded.

**Alternative considered**: Destructive queue pop before processing was rejected
because a crash would silently lose work. Marking delivered before the model call
was rejected because a crash could falsely report delivery.

## Decision 3: Minimal password session, no account system

**Decision**: `/human` uses one environment-held password. A successful login
creates a random opaque session id stored in the same Redis database with a
30-minute absolute expiry; the browser receives only a `Secure`, `HttpOnly`,
`SameSite=Strict` persistent cookie. Login, session check, logout, expiry, and
private inbox reads are separate server-side checks. Password comparison is
constant-time and error messages do not reveal which check failed.

Use Vercel WAF fixed-window rules for coarse abuse limits on login, suggestion,
and paid Try It endpoints. Do not build the database-backed rate-limiter framework
that the specification excludes. If the current Vercel plan cannot enforce the
required rules, production acceptance is blocked until Iso approves an equivalent
platform control.

**Rationale**: This satisfies the remembered-password lifecycle while avoiding
users, OAuth, roles, password reset, or an admin framework. Server-side sessions
support real logout and expiry, unlike a purely signed long-lived cookie.

**Official source**: Vercel WAF is available across plans and supports path/IP
rate limits: https://vercel.com/security/web-application-firewall

## Decision 4: Keep the loop as sole canonical writer

**Decision**: Add `state/collaboration.json` as the append-only canonical record
for RESEARCH, ASK, approved suggestions, and delivery receipts. Vercel writes only
to Redis. A separate bounded courier copies Redis commands into an atomic local
inbox spool and publishes a loop-authored outbox snapshot after the turn. The loop
alone reconciles spooled events into canonical state, delivers at most one eligible
answer/suggestion to the agent whose turn it is, and republishes the sanitized
view. Pending/dismissed suggestions never enter canonical public output or prompts.

**Rationale**: This preserves the current single-writer git history and prevents
Vercel/VPS write races.

**Alternative considered**: Letting Vercel or the courier edit canonical
`state/*.json` was rejected because it creates competing writers and lost-update
races. Direct Redis calls in the turn path were also rejected because a transport
outage could cancel an otherwise healthy experiment turn.

## Decision 5: Adopted-only rulebook views

**Decision**: Split the current renderer into explicit views:

- legislature view: adopted, proposed, rejected, reverted, provenance/history;
- language view: adopted text only, with a deterministic version/hash;
- proposal-trial view: language view plus exactly one labeled proposal.

Encoder, decoder, Conversation, and Try It may call only the language view.
Ordinary exams write corpus-level evidence only. Proposal trials are separate,
explicit events and are the only path to per-rule evidence.

**Rationale**: A typed view boundary is simpler to test than filtering ad hoc in
every caller and directly enforces FR-001 through FR-005.

## Decision 6: Enforced asymmetric legislature

**Decision**: Keep the plain-text motion grammar but validate parsed motions
against the acting role and current ledger before mutation. DeepSeek A may emit
one propose/revise/measure motion and never vote. Kimi B may audit A's current
focused proposal and adopt/reject/request revision/test, but cannot originate an
unrelated proposal. Invalid, repeated, malformed, settled, or multi-motion output
is recorded as a no-op receipt, not a revision.

Use `deepseek/deepseek-v3.2` and `moonshotai/kimi-k2.6`; both slugs were present
on OpenRouter on 2026-07-20. The Kimi stranger remains a separate stateless call.

**Official sources**:

- DeepSeek V3.2: https://openrouter.ai/deepseek/deepseek-v3.2
- Kimi K2.6: https://openrouter.ai/moonshotai/kimi-k2.6

## Decision 7: One-time cleanup is a gated artifact pipeline

**Decision**: A dedicated cleanup command operates only on an explicit snapshot
path. It writes four immutable artifacts: original snapshot, A replacement, B
audit, and exact diff. It has no default production path and cannot apply output.
The authenticated `/human` surface shows the pending bundle and exact diff
read-only after the repaired site is deployed. A separate apply command requires
the snapshot hash, approved replacement hash, and explicit live-change gate
before writing canonical state.

**Rationale**: Separating generation from application makes the human diff stop
structural, not procedural.

## Decision 8: RESEARCH via the current OpenRouter server tool

**Decision**: Parse one concise `RESEARCH:` request into durable state. On each
turn, answer at most the oldest open request, using the
`openrouter:web_search` server tool with bounded result/cost parameters. Store
the original question, citations, limitations, errors, and answer. Deliver the
question and answer together only to the requester on its next eligible turn.
Retrieved content is delimited as untrusted evidence and never passed to the
motion parser.

**Rationale**: This is the official current replacement for the deprecated
`:online`/plugin path and preserves the project's prompt-injection boundary.

**Official source**: https://openrouter.ai/docs/guides/features/server-tools/web-search

## Decision 9: Conversation is a bounded loop artifact

**Decision**: Run a six-message alternating DeepSeek/Kimi Conversation as a
scheduled harness artifact, using one captured adopted-rulebook snapshot and a
blind real-work scenario with concrete success requirements. A separate judge
scores the final agreement. Conversation does not replace or enter the rolling
ordinary-exam average. The first live run is approval-gated; later cadence is
once per 32 completed ordinary exams unless the measured cost or duration trips
the switch trigger in `plan.md`.

**Rationale**: A loop-authored artifact keeps canonical history single-writer and
avoids an uncapped public paid endpoint. One run per roughly 24 hours at the
current cadence is enough to show native use without dominating spend.

## Decision 10: Try It compares versions, not client-supplied rules

**Decision**: Encode returns the adopted-rulebook version/hash. Decode refetches
the current canonical rulebook and refuses with a distinct `409 rulebook_changed`
unless the version/hash matches. It never trusts rule text from the browser.

Try It uses `OPENROUTER_PUBLIC_API_KEY`, never the private VPS key. Before deploy,
read-only key metadata must prove `limit: 20`, `limit_reset: monthly`, and a
different key hash/identity from the private experiment key. Allowance exhaustion
and unrelated provider failure have distinct response codes and UI copy.

**Official source**: OpenRouter supports per-key USD limits and monthly reset:
https://openrouter.ai/docs/api/api-reference/api-keys/create-keys

## Decision 11: X delivery is confirmed, idempotent, bounded

**Decision**: Persist a stable request/idempotency id before delivery. Send only
`platform[]=x`, `x_title`, and copy of at most 250 characters. Treat synchronous
`results.x.success` plus a post URL/id, or an asynchronously polled confirmed
receipt, as success. Dry run, timeout, partial response, and failure do not mark
posted or consume successful-post budget. After three failed attempts the note
is `blocked`; later notes remain eligible.

**Rationale**: Upload-Post documents idempotency headers, asynchronous fallback,
per-platform results, and automatic thread splitting for long X text. The 250
character precondition prevents implicit threads.

**Official source**: https://docs.upload-post.com/api/upload-text/

## Decision 12: No new third-party runtime libraries

**Decision**: Use Python 3.12 standard library plus existing `requests` 2.31 on
the VPS, and Vercel Node 24 built-ins (`fetch`, `crypto`). Use Python `unittest`
and Node `node:test`. Add no SDK solely for Redis, sessions, or OpenRouter.

**Rationale**: REST integrations are small, auditable, and avoid dependency
installation, lockfile, bundling, and supply-chain work for a narrow project.

## Verified live facts informing the plan

- VPS `language-loop.timer` was active and firing every 15 minutes at 11:53 WITA.
- Local/remote `main` synchronized cleanly to `72badf9` (turn 540) after
  planning began; the intervening commits changed generated state/viewer data
  only. VPS commit must be rechecked at the live pause gate.
- Production Vercel deployment `dpl_6rrcd4YdGMTYkcUdEUsCQan7qQCS` was Ready.
- Vercel project runtime is Node 24.x and deploys from the explicitly linked
  `viewer/` directory; git push alone does not deploy.
- Production Vercel currently has only `OPENROUTER_API_KEY`; Redis, human-session,
  and separate public-key secrets do not yet exist.
- No live action, paid call, environment change, or deployment was performed.
