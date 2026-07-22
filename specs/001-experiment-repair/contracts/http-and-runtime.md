# HTTP and Runtime Contracts

All JSON endpoints reject non-JSON bodies, unknown action types, oversized text,
missing idempotency identifiers where required, and methods outside the contract.
Errors are stable machine codes plus short human-safe messages. No endpoint
returns secrets, Redis keys, pending/dismissed suggestion text, or private queues
without a valid human session.

## Public submission

### `POST /api/suggestion`

Request:

```json
{
  "text": "Short visitor suggestion",
  "idempotency_key": "browser-generated-uuid"
}
```

Response `202`:

```json
{
  "id": "uuid",
  "status": "pending_review",
  "message": "Your suggestion was submitted for review."
}
```

Rules:

- Normalize line endings and trim outer whitespace; preserve internal text.
- Reject empty, oversized, duplicate, or non-string content.
- HTML/script/prompt-injection text is stored as inert text and escaped at render.
- Repeating an idempotency key returns the original id/status, not a second item.
- Submission never appears publicly and never enters an agent prompt.

## Human session

### `POST /api/human-session`

Request: `{"password":"..."}`.

Success `204` sets an opaque persistent cookie with `Secure`, `HttpOnly`,
`SameSite=Strict`, `Path=/`, and `Max-Age=1800`. The server-side session has the
same non-sliding 30-minute absolute expiry. Failure is generic `401`.
Password and cookie values never appear in responses or logs.

### `GET /api/human-session`

- `200 {"authenticated":true,"expires_at":"..."}` for a valid session.
- `401 {"authenticated":false}` for missing, expired, revoked, or malformed state.

### `DELETE /api/human-session`

Revokes the server-side session, clears the cookie, and returns `204`. Repeating
logout is safe.

## Human inbox

### `GET /api/human-inbox`

Requires a valid session. Returns only:

```json
{
  "asks": [
    {"id":"uuid","requester":"A","request_turn":540,"question":"...","status":"awaiting_iso"}
  ],
  "suggestions": [
    {"id":"uuid","text":"...","submitted_at":"...","status":"pending"}
  ],
  "cleanup": {
    "bundle_id":"uuid",
    "source_rulebook_hash":"sha256",
    "replacement_hash":"sha256",
    "a_replacement":"...",
    "b_audit":"...",
    "exact_diff":"...",
    "status":"pending_iso"
  }
}
```

The cleanup object is read-only; `/human` cannot apply it. No private response
may be cached publicly. Unauthenticated calls are `401` with
no count, timing detail, or item existence signal.

## Human actions

### `POST /api/human-action`

Requires a valid session and an idempotency key.

Answer request:

```json
{"action":"answer_ask","id":"uuid","answer":"Iso's verbatim answer","idempotency_key":"uuid"}
```

Moderation request:

```json
{"action":"moderate_suggestion","id":"uuid","decision":"approved","idempotency_key":"uuid"}
```

`decision` is `approved` or `dismissed`. Closed ids, contradictory repeated
actions, and missing ids return `409` without mutation. Identical retries return
the original accepted receipt. Success `202` means queued for the loop, not yet
delivered or public.

## Cleanup generation contract

The A request uses `response_format.type=json_schema`, `strict=true`, and
provider routing with `require_parameters=true`. Its source-specific schema is:

```json
{
  "assignments": {"rule-NNN": "group-NNN", "rule-MMM": "__exclude__"},
  "groups": [{"id": "group-NNN", "text_en": "Cleaned language law"}],
  "exclusions": [{"source_id": "rule-MMM", "reason": "operational"}]
}
```

`assignments` must contain every and only adopted source id as required object
properties. Every retained assignment must reference one defined unique group,
every defined group must be referenced, and every `__exclude__` assignment must
have exactly one allowed `operational`, `fragment`, or `contradiction` receipt.
Code derives ordered `source_ids` and `excluded_sources`; A cannot supply them.
Any schema, routing, assignment, exclusion, group, text, or compiled-candidate
failure stops before B and produces no cleanup bundle.

## Try It

### `POST /api/encode`

Request: `{"text":"..."}`.

Success includes `journey_id`, `encoded`, `orig_tokens`, `enc_tokens`,
`delta_pct`, `rulebook_version`, and `rulebook_hash`.

### `POST /api/decode`

Request:

```json
{
  "encoded":"...",
  "rulebook_version":"0.NNN",
  "rulebook_hash":"sha256"
}
```

The server refetches canonical state. A mismatch returns:

```json
{"error":"rulebook_changed","message":"The language changed. Encode your message again."}
```

with `409` and no model call. Monthly public-key exhaustion returns
`429 allowance_exhausted` with reopening copy. Provider/network/auth failures
return `502 provider_failure` and are never labeled allowance exhaustion.

All Try It model calls use only `OPENROUTER_PUBLIC_API_KEY` and the adopted
language view.

## Loop collaboration contract

Before the turn, a bounded courier may copy Redis commands into an atomic local
inbox spool. Courier failure or timeout is non-fatal. At the start of a turn, the loop:

1. imports stable-id records from the local inbox spool into canonical state;
2. selects at most one eligible human answer or approved suggestion for the
   current agent;
3. checks the id against canonical `processed_inbox_ids`;
4. includes the original question plus verbatim answer, or one clearly delimited
   optional suggestion, outside the rule/motion grammar;
5. calls the agent;
6. parses motions only from the agent's response, never the supplied evidence;
7. atomically writes canonical state and the delivery receipt;
8. writes a local outbox snapshot for later courier publication.

The courier acknowledges Redis only after its local inbox receipt is durable.
If a call or write fails, no partial delivery receipt is published. Expired
leases retry; spool and canonical id dedupe prevent a second recorded delivery.
Only the loop writes `state/collaboration.json`; neither the courier nor Vercel does.

## Agent output grammar

Agent A accepted motions:

```text
PROPOSE: <one complete focused rule>
REPEAL: rule-NNN -> <why this adopted rule should leave the language>
REVISE: rule-NNN -> <complete replacement>
MEASURE: <one line>
RESEARCH: <one concise question>
ASK: <one concise question for Iso>
```

Agent B accepted motions:

```text
ADOPT: rule-NNN
REJECT: rule-NNN
REQUEST-REVISION: rule-NNN — <focused reason>
REQUEST-TEST: rule-NNN — <focused test>
RESEARCH: <one concise question>
ASK: <one concise question for Iso>
```

Only one focused legislative motion is accepted per turn. RESEARCH and ASK are
requests, not legislation. Forbidden, duplicate, malformed, unrelated, settled,
or overflow motions produce a no-op receipt with no version/history change.
Only one add or repeal proposal may remain open at a time. For a pending repeal,
Agent B's ADOPT ratifies the repeal and marks its target `repealed`; REJECT leaves
the target adopted; REQUEST asks for focused work; repeal text never enters the
language view.

## Research result contract

The researcher receives the original question as data and may use only the
OpenRouter `openrouter:web_search` server tool with bounded result counts. Its
stored response must contain:

```json
{
  "findings": "...",
  "limitations": ["..."],
  "citations": [{"title":"...","url":"https://..."}],
  "no_evidence": false
}
```

Missing usable sources sets `no_evidence: true`; citations are never invented.
The entire result is delimited as untrusted evidence and bypasses the motion
parser.

## Conversation contract

One artifact contains a blind scenario, concrete requirements, one captured
adopted rulebook version/hash, six alternating messages, exact model slugs and
usage, and a separate requirement-level outcome judgment. Neither speaker sees
legislative history, proposed/rejected rules, research, ASK answers, or visitor
text. Conversation cannot mutate the rule ledger or rolling exam average.

## X delivery contract

Before any network call, validate copy length `<= 250`, persist stable
`request_id`/`idempotency_key`, and set state `attempting`. Send only X with both
fallback `title` and X-specific `x_title`; do not supply thread/first-comment
fields.

Success requires a confirmed `results.x.success` plus URL/id, or a confirmed
asynchronous status read using the same request id. Ambiguous responses remain
pending for receipt polling. A failed attempt increments `attempts`; attempt 3
sets `blocked`; attempt 4 is impossible. Later notes are scanned independently.

Dry run returns the request preview without changing attempt, posted, blocked,
daily-success, or watermark state.

## Public snapshot contract

`viewer/state.js` and raw GitHub JSON expose only canonical, sanitized state.
They may show:

- adopted language and historical proposed/rejected records;
- valid corpus exams and explicitly labeled invalid/proposal trials;
- RESEARCH/ASK lifecycle text that has entered canonical history;
- approved suggestion lifecycle and outcome;
- Conversation artifacts and confirmed/blocked X delivery state.

They never expose pending/dismissed suggestions, session records, Redis metadata,
password material, provider keys, private moderation queues, or uncorrelated
inbox commands.
