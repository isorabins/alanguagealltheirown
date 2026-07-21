# Mechanics

## One invariant

Only the current adopted rule set may govern encoding and decoding, and every public status must match verified state.

`rulebook.py` produces two intentionally different views:

- the language view contains only adopted ids and text plus a deterministic version/hash;
- the legislature view contains all statuses so proposals and failures remain visible history.

Ordinary exams, Try It, and Conversation use the language view. Agent deliberation sees both views with clear labels. A future proposal-specific trial must be explicit; proposed material never enters an ordinary exam implicitly.

## Turn sequence

`run_turn.sh` rebases the VPS checkout onto current `main`, gives the collaboration courier a strict eight-second best-effort pull, runs one turn, gives the courier a strict eight-second best-effort push, runs the independent X delivery state machine, then commits and pushes generated state if anything changed. Courier failure is ignored and cannot cancel the turn. The legacy benchmark artifact remains in repository history but is not imported, executed, prompted, measured, or rendered by the active path.

On a normal turn `loop.py`:

1. atomically loads canonical state;
2. reconciles only the atomic local inbox spool into `state/collaboration.json`;
3. resolves at most the oldest queued research request;
4. runs either one legislative agent turn or the existing every-third-turn ordinary exam;
5. after every 32 completed ordinary exams, runs one six-message Conversation without changing ordinary cadence or averages;
6. atomically persists canonical JSON, writes the private courier outbox, and generates the sanitized public snapshot.

All JSON replacement uses a temporary file, file sync, atomic rename, and directory sync. Stable hashes use canonical JSON.

## Legislature

DeepSeek A may issue one `PROPOSE`, `REPEAL`, or `REVISE` motion. Kimi B may issue one `ADOPT`, `REJECT`, or focused `REQUEST`. Only one add or repeal motion may remain open. A ratified repeal moves its adopted target out of the language while preserving its complete history; the repeal rationale never becomes language law. `MEASURE`, `RESEARCH`, and `ASK` are non-legislative requests. Multiple motions, wrong-role actions, malformed ids, duplicate live proposals, overflow proposals, and settled votes are reason-coded no-ops.

## Ordinary exam and judge

The existing cadence and payload generator remain. Encoder and foreign Kimi decoder both receive the same captured adopted-language text. Each exam records its language version/hash, original, encoding, decode, token counts, and corpus judgment.

For keyed exams, `rulebook.score_judgment` requires a one-to-one set of item ids `1..N`, each exactly once and each with a valid verdict. Missing, duplicate, nonnumeric, out-of-range, or invalid verdict output produces an invalid exam shown to agents as `no valid score` with the reason. New corpus results retain the latest 500 entries in `meta.corpus_exams`; they do not stamp one result onto every rule. The existing last-ten passing-exam calculation reads historical exam events and is not reset or forked. A historical hypothetical cached-cost scenario remains archival rather than a current measured claim.

If fresh payload generation fails, the fixed fallback payload receives an answer key before encoding. If key extraction also fails, the round trip is preserved as an invalid/no-score artifact; the old holistic fallback can no longer publish fidelity.

## Cleanup

`cleanup_rulebook.py request-options` builds A's strict source-specific response schema and parameter-compatible routing option. Every adopted id is a required assignment property. `compile-draft` rejects missing/extra assignments and unknown/orphan/duplicate groups, derives ordered `source_ids`, validates the candidate, and only then emits the candidate eligible for B audit. `prepare` reads an explicit frozen source, compiled A replacement JSON, and Agent B audit JSON. It validates exact adopted-source coverage, requires the audit to pass with no omissions/meaning changes/operational text and to name the exact source/candidate hashes, then emits immutable original/candidate/audit files, a full applied-ledger candidate, an exact diff, and manifest hashes with `pending_iso` status. The applied candidate retains every prior record and history, marks superseded adopted and legacy proposed/reverted records historical with their prior status recorded, and appends newly numbered adopted cleanup rules. It never defaults to production paths.

`cleanup_rulebook.py apply` requires an external approval receipt naming the exact source and full applied-ledger hashes and refuses changed source, changed replacement, or missing approval. A successful apply records the approval hash in the bundle manifest. Live snapshot/model calls/application remain separate approval gates.

## Collaboration inbox

Upstash Redis REST is transport, private backup, and session storage, not the authority that writes experiment history. Queue creation is idempotent and atomic. The courier claims the oldest item under a lease, fsyncs its stable id into a gitignored local inbox spool, and only then acknowledges Redis. The loop alone imports deduplicated spool ids into canonical `state/collaboration.json`, then writes a private outbox snapshot for later courier publication. A replay is harmless, a stale owner cannot ack a new lease, and no Redis exception enters the loop path. Each turn separately writes sanitized `state/public-collaboration.json`; `/human` reads the private loop-owned Redis snapshot.

- Research records retain requester, original question, status, findings, limitations, citations, error, and answer turn. The OpenRouter `openrouter:web_search` server tool is bounded to five total results. Retrieved content is evidence only.
- ASK records remain open indefinitely. Moderation accepts only an answer for an existing open id; delivery contains the original question and verbatim answer and changes the record to delivered.
- Pending and dismissed suggestions are omitted from public state. An approved record may be delivered once as an `optional_suggestion` object outside the motion parser.

No accounts, OAuth, admin panel, or general identity layer exists.

## `/human`

`viewer/api/human-session.js` compares one environment password using constant-time equality and creates an opaque 256-bit Redis session. The secure, HttpOnly, SameSite=Strict cookie has a 30-minute absolute lifetime. Reads do not extend that lifetime. Logout deletes the server session and expires the cookie.

Authenticated endpoints expose open questions, private suggestions, and read-only cleanup bundles. Mutations are restricted to answer, approve, and dismiss commands with idempotency keys. The cleanup apply operation is not available from these generic actions.

After the reviewed pending cleanup bundle reaches `main`, the authenticated inbox fetches its single structured `review.json` (original hash, A candidate, B audit, exact full-ledger diff, and `pending_iso` status) from the repository. This is review-only; it exposes no apply endpoint.

## Public Try It

Vercel handlers build the same adopted-only language payload as Python. Encode returns its version/hash; decode refetches canonical state and returns `409 rulebook_changed` before any model call if either value differs. Browser responses never contain rule text or credentials.

All public model calls require `OPENROUTER_PUBLIC_API_KEY`. There is no fallback to the private experiment key. Provider response classification separates verified monthly allowance exhaustion from authentication, rate, network, and provider failures. The production $20 monthly limit, reset, separate identity, and WAF controls remain an approval-gated acceptance requirement.

## X delivery

`tweet.py` persists a stable source-derived id and attempt count before each request. It sends only X, `x_title`, and a maximum of 250 characters with the stable idempotency header. State becomes posted only after an explicit X-specific post or job receipt. Dry mode does not attempt or advance anything. Unconfirmed HTTP responses and ambiguous timeouts retain the same identity; attempt three blocks the item, and later field notes continue without consuming blocked-item budget.

Public corrections, the explainer, pin, and each follow remain individual exact approval gates and require real-profile verification.

## Deployment and acceptance

The viewer remains static HTML plus small Vercel functions. `/human` rewrites to `human.html`. Redis, password/session, public OpenRouter key, WAF, deployment, loop pause/resume, cleanup application, paid production tests, X actions, feature push/PR, and `main` integration are all separate planned stops.

Offline tests prove contracts but not the live product. Production acceptance requires the deployed commit, visible real paths, desktop and 375px coverage, session expiry/restart, cross-turn exact-once delivery, hostile/failure cases, approved X results, numbered screenshots, one continuous video, independent read-only receipts, and cleanup. Every matrix row is PASS, FAIL, or BLOCKED; any debris, duplicate, stuck queue, warning, missing evidence, or incomplete approved action prevents overall PASS.
