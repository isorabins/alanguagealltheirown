# Data Model: Experiment Repair and Public Collaboration

## Authority boundary

`state/*.json` remains the canonical append-only experiment record and is written
only by the VPS loop or an explicitly approved one-time cleanup apply command.
Upstash Redis is a durable collaboration inbox and session store. Vercel may
enqueue visitor/human commands but cannot write canonical experiment history.

## Rule Record

| Field | Type | Rules |
|---|---|---|
| `id` | string | Stable `rule-NNN`; never reused |
| `text_en` | string | Canonical rule text |
| `status` | enum | `adopted`, `proposed`, `rejected`, `reverted` (legacy), `repealed`, `historical`, `superseded` |
| `proposed_turn` | integer | Original provenance |
| `history` | array | Append-only motion/no-op/status receipts |
| `proposal_evidence` | array | Only explicit proposal-trial evidence |
| `pending_repeal` | object/null | Distinct open motion with kind, target, rationale, provenance; never language text |

Corpus evidence is not stored on individual rule records. Existing historical
`scores` fields are preserved but labeled legacy and never used for new
per-rule claims.

### Rule views

- `legislature`: all statuses plus provenance/history.
- `language`: all and only adopted rule text.
- `proposal_trial`: adopted set plus exactly one labeled proposed rule.

At most one add proposal or pending repeal exists after cleanup. Cleanup records
the prior status of every legacy proposed/reverted rule before moving it to
`historical`. A ratified repeal moves its adopted target to `repealed`; that id
is terminal, but the same text may be proposed under a fresh id.

The language view has a deterministic `version` and `sha256` derived from ordered
adopted ids and text.

## Cleanup Draft

| Field | Type | Rules |
|---|---|---|
| `assignments` | object keyed by every adopted source id | Exact source-id key set; each value names one cleanup group |
| `groups` | array | Each item has one unique group id and non-empty A-authored `text_en` |

The source-specific JSON Schema requires every assignment key and forbids extra
keys. The deterministic compiler requires referenced group ids to equal the
defined group-id set, rejects operational text, and derives each compiled
candidate rule's ordered `source_ids`. The model never supplies authoritative
coverage metadata.

## Motion Receipt

| Field | Type | Rules |
|---|---|---|
| `turn` | integer | Canonical loop turn |
| `agent` | enum | `A` or `B` |
| `verb` | enum | `propose`, `revise`, `measure`, `adopt`, `reject`, `request_test`, `none` |
| `target_id` | string/null | Existing rule/proposal where required |
| `accepted` | boolean | Parser/role/state authority result |
| `reason_code` | string/null | Required for rejected/no-op motions |
| `state_changed` | boolean | Must be false for forbidden/repeated/malformed output |

Only A may propose/revise/measure. Only B may adopt/reject/request a focused
revision/test of A's current proposal. At most one accepted focused motion exists
per turn.

## Exam Event

| Field | Type | Rules |
|---|---|---|
| `turn` | integer | Stable canonical turn |
| `kind` | enum | `corpus` or `proposal_trial` |
| `rulebook_version` / `rulebook_hash` | string | Captured before calls |
| `proposal_id` | string/null | Required only for proposal trial |
| `payload`, `answer_key`, `encoded`, `decoded` | values | Full immutable artifact |
| `judge_items` | array | Exactly one item per answer-key id |
| `valid` | boolean | True only for exact answer-key coverage |
| `invalid_reason` | string/null | Missing, duplicate, nonnumeric, out-of-range, malformed |
| `fidelity` | integer/null | Null when invalid; never publicly scored |
| `token_delta_pct` | integer | Corpus-level evidence |

## Cleanup Bundle

| Field | Type | Rules |
|---|---|---|
| `bundle_id` | UUID | Stable immutable run id |
| `source_commit` / `source_rulebook_hash` | string | Exact production snapshot identity |
| `original_path` | path | Immutable copied input |
| `a_replacement_path` | path | Agent A output |
| `b_audit_path` | path | Agent B review |
| `diff_path` | path | Exact human-readable diff |
| `review_status` | enum | `pending_iso`, `approved`, `applied`, `rejected` |
| `approved_replacement_hash` | string/null | Set only after Iso approval receipt |
| `applied_commit` | string/null | Canonical application receipt |

Generation cannot apply. Application must reject a source/hash mismatch.

## Collaboration Canonical Record

Stored in `state/collaboration.json`:

```json
{
  "schema_version": 1,
  "research": [],
  "asks": [],
  "suggestions": [],
  "deliveries": [],
  "processed_inbox_ids": []
}
```

`processed_inbox_ids` may be compacted only into an equivalent immutable receipt
index; it cannot be dropped while the corresponding Redis item can retry.

## Collaboration Transport Spools

The courier atomically writes a local inbox spool containing stable-id Redis
commands and an optional private recovery snapshot. The loop alone imports that
spool into canonical collaboration history. After canonical writes, the loop
atomically writes an outbox snapshot for the courier to publish. Spools are
transport receipts, not canonical experiment history, and are gitignored.

## Research Request

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Stable correlation id |
| `requester` / `request_turn` | enum/integer | A or B and original turn |
| `question` | string | Original text, immutable |
| `status` | enum | `open`, `researching`, `answered`, `no_evidence`, `failed`, `delivered` |
| `answer_turn` / `delivery_turn` | integer/null | Lifecycle receipts |
| `findings` / `limitations` / `citations` | values | Bounded evidence result |
| `errors` | array | Honest failures, no fabricated evidence |
| `delivered_to` | enum/null | Must equal requester |

At most one oldest open request is attempted per turn. Research text is never
passed to the motion parser.

## Human Ask

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Stable correlation id |
| `requester` / `request_turn` | enum/integer | Original asker |
| `question` | string | Original text, immutable |
| `status` | enum | `awaiting_iso`, `answer_pending`, `answered`, `delivered` |
| `answer` | string/null | Iso's verbatim response |
| `answer_submitted_at` | timestamp/null | Inbox receipt |
| `answer_turn` / `delivery_turn` | integer/null | Canonical receipts |

Duplicate or closed-id answers are rejected without mutation. Unanswered asks do
not expire or block turns.

## Visitor Suggestion

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Stable submission id |
| `text` | string | Plain text, short bounded length |
| `submitted_at` | timestamp | Server timestamp |
| `moderation` | enum | `pending`, `approved`, `dismissed` |
| `moderated_at` | timestamp/null | Human action receipt |
| `delivery` | enum | `not_eligible`, `ready`, `delivered` |
| `delivery_turn` / `delivered_to` | values | Exactly-once receipt |
| `outcome` | string/null | Agent action/non-action summary after delivery |

Pending and dismissed records remain private. Only approved records may be
materialized into canonical/public state, and at most one can be delivered on an
eligible turn.

## Inbox Item (Redis)

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Stable id; primary dedupe key |
| `kind` | enum | `suggestion`, `ask_answer`, `suggestion_moderation`, `session` |
| `payload` | JSON | Length-limited, escaped only at render time |
| `status` | enum | `ready`, `leased`, `acked`, `rejected` |
| `created_at` / `updated_at` | timestamp | Server timestamps |
| `lease_until` / `attempts` | values | Crash-safe consumption |
| `idempotency_key` | string/null | Retry correlation, never a secret |

### Inbox transitions

```text
new --atomic enqueue--> ready --atomic claim--> leased
leased --canonical receipt saved--> acked
leased --lease expiry/no canonical receipt--> ready
ready/leased --validation/closed-id failure--> rejected
```

## Human Session (Redis)

| Field | Type | Rules |
|---|---|---|
| `session_hash` | string | Hash of opaque cookie id; raw id exists only in cookie |
| `created_at` / `expires_at` | timestamp | Absolute bounded lifetime |
| `last_seen_at` | timestamp | Optional audit field, no sliding extension beyond max |
| `revoked_at` | timestamp/null | Logout receipt |

Cookie attributes: `Secure`, `HttpOnly`, `SameSite=Strict`, explicit `Path=/`,
and persistent `Max-Age=1800`. Sessions have a 30-minute absolute lifetime and
do not slide. No user/account/role record exists.

## Conversation Artifact

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Stable artifact id |
| `turn` | integer | Trigger turn |
| `scenario` / `requirements` | values | Blind real-work task and concrete outcome checks |
| `rulebook_version` / `rulebook_hash` | string | One captured adopted snapshot |
| `messages` | array | Six alternating DeepSeek/Kimi messages |
| `models` | object | Exact model slugs |
| `usage` | object | Token/cost receipt |
| `judgment` | object | Requirement-level verdict plus overall result |

Conversation artifacts do not mutate rules or enter the rolling ordinary-exam
average.

## Try It Journey

The server does not persist visitor content. Encode returns a generated journey
id, adopted rulebook version/hash, encoded text, and token figures. Decode must
present that version/hash; the server refetches current canonical state and
returns `409 rulebook_changed` without a model call on mismatch.

## X Delivery Record

| Field | Type | Rules |
|---|---|---|
| `note_id` | string | Stable field-note identity |
| `copy` | string | At most 250 characters |
| `request_id` / `idempotency_key` | string | Stable across retries |
| `attempts` | integer | 0–3 |
| `state` | enum | `pending`, `attempting`, `posted`, `blocked` |
| `provider_receipt` | object/null | Confirmed URL/id or async status |
| `last_error` | string/null | Sanitized failure detail |
| `posted_at` | timestamp/null | Only after confirmation |

Dry runs do not increment successful-post budget or change `posted` state.
