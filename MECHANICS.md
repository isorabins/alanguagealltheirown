# Mechanics

## One invariant

Only the current adopted rule set may govern encoding and decoding, and every public status must match verified state.

`rulebook.py` produces two intentionally different views:

- the language view contains only adopted ids and text plus a deterministic version/hash;
- the legislature view contains all statuses so proposals and failures remain visible history.

Ordinary exams, Try It, and Conversation use the language view. Agent deliberation sees both views with clear labels. A future proposal-specific trial must be explicit; proposed material never enters an ordinary exam implicitly.

## Turn sequence

`run_turn.sh` rebases the VPS checkout onto current `main`, gives the collaboration courier a strict eight-second best-effort pull, runs one turn, gives the courier a strict eight-second best-effort push, then commits and pushes generated state if anything changed. Courier failure is ignored and cannot cancel the turn. X delivery is not invoked by this path. The separate 19-payload transfer battery remains off the scheduled path; it is not imported, executed, prompted, measured, or rendered by an ordinary turn.

On a normal turn `loop.py`:

1. atomically loads canonical state;
2. reconciles only the atomic local inbox spool into `state/collaboration.json`;
3. resolves at most the oldest queued lookup/research request;
4. runs either one legislative agent turn or the existing every-third-turn ordinary exam;
5. after every 32 completed ordinary exams, runs one six-message Conversation without changing ordinary cadence or averages;
6. atomically persists canonical JSON, writes the private courier outbox, and generates the sanitized public snapshot.

All JSON replacement uses a temporary file, file sync, atomic rename, and directory sync. Stable hashes use canonical JSON.

## Legislature

Every new A/B call receives a strict JSON Schema generated from the canonical role and open-motion state. DeepSeek A may return one typed `PROPOSE`, `REPEAL`, or `REVISE` motion; Kimi B may return one typed `ADOPT`, `REJECT`, or focused `REQUEST`. An open motion constrains the schema to its one exact target, and B cannot omit the audit motion while that target remains open. Deliberation must contain a substantive English fragment rather than punctuation-only filler. `MEASURE`, `LOOKUP`, `RESEARCH`, and `ASK` use bounded typed arrays, and natural-language deliberation has no operative authority.

Pydantic validates the provider response locally. A structural failure gets at most two regeneration attempts against the unchanged state; exhaustion records one structural-failure receipt, mutates no rule, and retains the same next actor. A validated action enters the existing single-writer state machine directly, without live regex or prose extraction.

Each attempted legislative turn persists an authoritative post-state receipt containing the attempted action, result/reason, exact changed and unchanged rule ids, current open motion, adopted count, adopted-language hash, rulebook hash, and next actor. The first run after cutover appends one reconciled cutover receipt without rewriting earlier events or rules. Request assembly renders the current machine state/latest receipt as authoritative, derives B's latest accepted typed `REQUEST` only when it targets that current open motion, and does not replay canonical prior events into a fresh legislative request. A revision, structural failure, restart, or no-motion outcome leaves that derived feedback eligible; a newer eligible request supersedes it, and settlement or a different open target omits it.

Persistence stays complete while model rendering is compact. The single prompt assembler keeps `COMPLETE LEGISLATURE` as the full rule/status view, then projects current state without its duplicate `rule_states` array. The latest structured receipt retains turn, actor, result/reason, attempts, changed ids, open motion, adopted count/hash, rulebook version/hash, and next actor; the one active-feedback projection retains only its target, exact focus, and request turn. Duplicated attempted actions, unchanged ids, the rulebook change counter, and all prior events remain in canonical JSON but not the fresh legislative request. These deterministic omissions never replace the canonical Pydantic models or event records.

Recent development-exam events remain complete in canonical persistence and directly renderable public history. Scoring V2 events keep the meaning pass, compression success, semantic coverage, critical failures, inventions, message-body savings, and exact decoded evidence separate. Invalid judge results remain evaluator evidence but never become benchmark failures or replace the prior valid V2 baseline. None are replayed into a fresh legislative request. The structured-response schema describes the existing substantive English requirement on `deliberation`; local minimum length, alphanumeric check, retry count, model, and provider routing remain unchanged.

Only one add or repeal motion may remain open. A ratified repeal moves its adopted target out of the language while preserving its complete history; the repeal rationale never becomes language law. Wrong-role actions, malformed ids, duplicate live proposals, overflow proposals, and settled votes remain reason-coded state-machine rejections.

## Cost accounting

At structured-protocol cutover, the existing `meta.spend_usd` value is retained as `spend_usd_historical_estimate`. Every successful private OpenRouter response after that point, including a structurally invalid response that triggers regeneration, adds the response's returned `usage.cost` exactly once to `spend_usd_provider_exact_since_cutover`. The `$25` tripwire uses the labeled historical estimate plus that provider-returned exact total. Missing or invalid `usage.cost` fails closed; no static per-model price participates in new accounting.

Production `run()` also binds the gitignored VPS-local `state/cost-receipts.local.json` ledger. It atomically records each successful response id and `usage.cost` before the call returns, deduplicates an identical id/cost retry, rejects missing or conflicting ids, and reconciles a ledger-ahead crash back into `meta` on restart. A new ledger takes its base from the already-persisted exact post-cutover total; an existing ledger that conflicts with persisted metadata fails closed. Offline transfer/test calls do not bind this ledger.

## Ordinary exam and judge

Every third turn selects the next row from the corrected five-message registry in `benchmarks/v2.json`. The V2 registry joins its atomic keys to the unchanged source messages in `benchmarks/v1.json`; the V1 file and historical events remain immutable. A V1 cursor starts a fresh V2 cycle at B1, then the durable cursor advances B1 through B5 and increments a cycle only after B5. The encoder and foreign Kimi decoder both receive the same captured adopted-language text.

Each new receipt records benchmark id/name/version/cycle, language version/hash, original, encoding, decode, token counts, atomic verdicts and evidence, and the prior valid V2 turn for that benchmark. Meaning pass requires every atom to survive and zero inventions; compression success additionally requires positive message-body savings. Critical failure is a severity label, not a weight. V1 fidelity and V2 results are never compared, and historical events are never rewritten.

Frozen English is a separate one-time operator path in `frozen_english.py`, not a turn type. Its checked contract pins the corrected benchmark digest plus encoder, decoder, judge, tokenizer, compression/decoder/grader instructions, temperatures, and 4,000-token ceiling for each B1-B5 record. Only those named inputs make a stored control stale. The command previews without provider access by default; live execution requires an explicit bounded cap, keeps provider calls out of CI, and atomically writes `baselines/frozen-english-v2.json` without touching `state/`.

The viewer admits the paired 20-exchange projection only when one complete Scoring V2 cycle has valid B1-B5 results with meaning pass, compression success, 100% semantic coverage, and no inventions, and all five frozen-English records are current and meaning-safe. The fixed model uses 40 messages of 1,000 ordinary-English tokens, 780 accumulated-history copies, Claude Sonnet 4.6 reference prices, and the current rulebook with two cache writes and 38 reads. ALATO and frozen English are projected separately against the same plain-English reference; the displayed ALATO value is interpreted only through their control-adjusted percentage-point difference. Every value is hypothetical communication-layer arithmetic, not measured telemetry or an API-bill claim.

For keyed exams, `rulebook.score_judgment` requires a one-to-one set of item ids `1..N`, each exactly once and each with a valid verdict. Missing, duplicate, nonnumeric, out-of-range, or invalid verdict output produces an invalid exam shown to agents as `no valid score` with the reason. New corpus results retain the latest 500 entries in `meta.corpus_exams`; they do not stamp one result onto every rule. Public cycle averages appear only after B1 through B5 all have valid results in one cycle. The separate transfer battery remains the generalization check for the known overfitting trade-off.

## Cleanup

`cleanup_rulebook.py request-options` builds A's strict source-specific response schema and parameter-compatible routing option. Every adopted id is a required assignment property. `compile-draft` rejects missing/extra assignments and unknown/orphan/duplicate groups, derives ordered `source_ids`, validates the candidate, and only then emits the candidate eligible for B audit. `prepare` reads an explicit frozen source, compiled A replacement JSON, and Agent B audit JSON. It validates exact adopted-source coverage, requires the audit to pass with no omissions/meaning changes/operational text and to name the exact source/candidate hashes, then emits immutable original/candidate/audit files, a full applied-ledger candidate, an exact diff, and manifest hashes with `pending_iso` status. The applied candidate retains every prior record and history, marks superseded adopted and legacy proposed/reverted records historical with their prior status recorded, and appends newly numbered adopted cleanup rules. It never defaults to production paths.

`cleanup_rulebook.py apply` requires an external approval receipt naming the exact source and full applied-ledger hashes and refuses changed source, changed replacement, or missing approval. A successful apply records the approval hash in the bundle manifest. Live snapshot/model calls/application remain separate approval gates.

`legacy_motion_repair.py` is a separate metadata-only migration for the live deadlock. `prepare` terminalizes proposed and reverted records on a copied source, records each prior status, refuses any pending repeal, proves every adopted record plus the adopted-language version/hash is exact, and emits original/replacement/diff/manifest hashes. `apply` requires a matching external approval receipt, rejects source or artifact drift, and treats a retry after the replacement write as idempotent. It does not run semantic cleanup, change adopted text, increment the language version, or default to production paths.

## Collaboration inbox

Upstash Redis REST is transport, private backup, and session storage, not the authority that writes experiment history. Queue creation is idempotent and atomic. The courier claims the oldest item under a lease, fsyncs its stable id into a gitignored local inbox spool, and only then acknowledges Redis. The loop alone imports deduplicated spool ids into canonical `state/collaboration.json`, then writes a private outbox snapshot for later courier publication. A replay is harmless, a stale owner cannot ack a new lease, and no Redis exception enters the loop path. Each turn separately writes sanitized `state/public-collaboration.json`; `/human` reads the private loop-owned Redis snapshot.

- `LOOKUP` and deterministically detected internal questions read bounded evidence from canonical project state and core documentation. They make no provider or web call. Evidence is delivered for the requesting agent to interpret; a miss creates one correlated `ASK Iso`.
- Outward `RESEARCH` records retain requester, original question, route, status, findings, limitations, citations, error, and answer turn. The OpenRouter `openrouter:web_search` server tool is bounded to five total results. Malformed or uncited output is no evidence, and retrieved content is evidence only.
- An eligible lookup/research row is marked and recorded through the same exact-once lifecycle as before, but its model-facing delivery is capped deterministically: the original id, question, and route remain exact while findings, limitations, and safe HTTP citations are trimmed within a fixed serialized budget with explicit original/included/omitted metadata. The complete canonical row and canonical delivery record remain full. If structural validation exhausts, the pre-delivery collaboration state is restored byte-for-byte; the retained actor's later attempt regenerates the same bounded projection rather than reinserting the full result.
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

`tweet.py` persists a stable source-derived id and attempt count before each request. Its
independent hourly service attempts one deterministic rule update or queued field note
per run and reserves no more than two delivery slots per UTC day. Delivery state lives
under `/var/lib/alanguagealltheirown-x`, outside the Git checkout. It sends only X,
`x_title`, and a maximum of 250 characters with the stable idempotency header. State
becomes posted only after an explicit X-specific post or job receipt. Unconfirmed HTTP
responses and ambiguous timeouts retain the same identity; attempt three blocks the
item, and later items remain eligible.

The core timer does not call `tweet.py`, and X failure cannot change or stop it. Replies,
DMs, follows, pins, deletions, edits, threads, and other platforms are outside this
publisher.

## Deployment and acceptance

The viewer remains static HTML plus small Vercel functions. `/human` rewrites to `human.html`. Redis, password/session, public OpenRouter key, WAF, deployment, loop pause/resume, cleanup application, paid production tests, X actions, feature push/PR, and `main` integration are all separate planned stops.

Offline tests prove contracts but not the live product. Production acceptance requires the deployed commit, visible real paths, desktop and 375px coverage, session expiry/restart, cross-turn exact-once delivery, hostile/failure cases, approved X results, numbered screenshots, one continuous video, independent read-only receipts, and cleanup. Every matrix row is PASS, FAIL, or BLOCKED; any debris, duplicate, stuck queue, warning, missing evidence, or incomplete approved action prevents overall PASS.
