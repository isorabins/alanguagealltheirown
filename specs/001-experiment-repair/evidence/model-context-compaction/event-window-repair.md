# Legislative Event-Replay Removal

Date: 2026-07-30 WITA
Fixed point: `4da2d28287f3412a45c9195cb1dcdc9b89890b42`
Approval baseline: OpenRouter key usage `$8.328790335`
Approval: `$1` additional provider spend and up to three prompt-only
review/PR/deploy/retry cycles
State: **PAUSED / THREE APPROVED CYCLES EXHAUSTED**

Exact approval receipt:

> APPROVE LIVE CHANGE: resume A Language All Their Own from paused turn 1212
> using current deployed main and the existing production OpenRouter key; allow
> up to $1 additional provider spend for turn 1213 and up to three prompt-only
> repair, PR, deploy, and retry cycles; pause on state, service, or invariant
> warnings; do not change model, routing, validator, protocol, cadence,
> credentials, UI, DNS, or X; after one valid B receipt, verify the live system
> and leave the normal timer running

## Turn-1213 warning stop

The deployed 68,180-character prompt still exhausted all three Kimi responses
with `string_too_short at deliberation`. The authoritative receipt recorded
`result=structural_failure`, `attempts=3`, no changed rule ids, open
`rule-132`, and B retained as next actor. Exact provider cost was
`$0.017273050`.

The timer was paused before turn 1214. The rulebook hash remained
`8bcd8c49d62581f30c5d0bf676451dbc44c6dd8af8fdbf1940b5bc115059fb45`.
`lookup-1202-b` restored to `answered` with 11,248 findings characters, 10
citations, no delivery turn, and zero canonical deliveries.

## Production-shaped isolation

Every row used the unchanged production Kimi model, provider routing, strict
B/open-`rule-132` schema, validator, two retries configuration, and temperature.
No diagnostic output was applied to state.

| Prompt variant | Chars | Prompt tokens | Deliberation | Validation | Cost |
|---|---:|---:|---:|---|---:|
| Full prompt plus fixed public stem | 68,499 | 17,145 | 1 | FAIL | `$0.0129707500` |
| Full system, no event window | 54,393 | 13,585 | 363 | PASS | `$0.0046028724` |
| Fourteen test/measure/notice events | 57,567 | 13,722 | 1 | FAIL | `$0.0101059000` |
| Latest test receipt only | 54,576 | 12,879 | 1 | FAIL | `$0.0091371400` |
| No event replay + example, pass 1 | 54,585 | 13,622 | 281 | PASS | `$0.0046303580` |
| No event replay + example, pass 2 | 54,585 | 13,622 | 323 | PASS | `$0.0043107648` |
| No event replay + example, pass 3 | 54,585 | 13,622 | 274 | PASS | `$0.0044036256` |

The first full-system/no-window pass isolated event replay as the differentiator.
Reintroducing even one canonical test receipt reproduced the one-character
failure. The final prompt passed three consecutive production-shaped calls at
the unchanged sampling temperature.

## Cycle-1 exact-replay stop

The first request cryptographically bound to implementation commit `27410aa`
used the expected 54,585-character prompt but failed local validation: Kimi
returned `motion` as a prose string and used invalid `type`/`id`/`content`
fields in a request object. The remaining two calls were stopped, the timer
remained inactive, and no production state or repository changed.

Immutable request fingerprint:

- system SHA-256:
  `c5747814153f9f99551e92aad7c04109586e08b97076b97968be9e1bbd80c329`;
- user SHA-256:
  `787212787499c76a125edc4804700d621dc67849261b965663abc3f6afd7310b`;
- request-options SHA-256:
  `9cd8b5e2122a89e9cdfd13c69cff8ec562668be00ae4abad38f21ddd662cfbf8`;
- complete request-body SHA-256:
  `d993f4917b86deb9ffef001d2e42d63b49fc50751b7691381bbb66d9f6dce8cb`.

The diagnostic process stopped on validation before emitting its response id
or returned cost. The immediately authenticated shared-key total remained
`$8.424876299`, so no additional amount was observable at that checkpoint.
Cycle 2 keeps schema and validation unchanged and adds a role/state-specific
complete-object shape example to the leading prompt contract.

## Cycle-2 exact-replay stop

The first exact request at implementation commit `408b727` used a
54,908-character prompt. OpenRouter response
`gen-1785458651-xExN1RIIyixCeutMuTuF` cost `$0.009833100` and returned a
schema-shaped object, but its `deliberation` value was the single letter `T`.
Local validation stopped the cycle with `string_too_short at deliberation`;
the remaining two calls were not made.

Immutable request fingerprint:

- system SHA-256:
  `0f2b6e9485e90d070fc8c49f736b50666c8f660d6f1b77d2ce0282d89ea53ffd`;
- user SHA-256:
  `787212787499c76a125edc4804700d621dc67849261b965663abc3f6afd7310b`;
- request-options SHA-256:
  `9cd8b5e2122a89e9cdfd13c69cff8ec562668be00ae4abad38f21ddd662cfbf8`;
- complete request-body SHA-256:
  `218a47dc4eabb1e77e79fb8159f5a52c38b216301b068e5df49779f424608310`.

The retained Agent B role prompt still described the superseded prose
transport (`REQUEST-TEST: ...`, `MEASURE: ...`) while the constitution,
schema, validator, and leading contract required typed objects. Cycle 3 removes
that contradictory transport wording from Agent B's prompt and states the
already-canonical object shapes; no schema, validator, protocol, model, routing,
retry, temperature, or state behavior changes.

## Cycle-3 exact-replay stop

The first exact request at implementation commit `5cd0169` used a
54,777-character prompt. OpenRouter response
`gen-1785458855-mTBirmpTCa5XVoYRU8Dn` cost `$0.009867800` and returned the
single letter `I` in `deliberation`. Local validation again stopped the cycle
with `string_too_short at deliberation`; the remaining two calls were not made.

Immutable request fingerprint:

- system SHA-256:
  `d607f3e31d844ea6e6a6767f1ea7011bb6b6a424f04f288feb0752fe22aeba0a`;
- user SHA-256:
  `787212787499c76a125edc4804700d621dc67849261b965663abc3f6afd7310b`;
- request-options SHA-256:
  `9cd8b5e2122a89e9cdfd13c69cff8ec562668be00ae4abad38f21ddd662cfbf8`;
- complete request-body SHA-256:
  `912264bf87931f0f5c31611a7bb702fac1727ce0a695a67b26e0cabfde368cee`.

The pre-call authenticated total was `$8.446316879`; the call's returned cost
was `$0.009867800`. The immediate post-call key endpoint had not yet reflected
that receipt, so the conservative approval delta is `$0.127394344` when the
returned cost is added to the authenticated `$0.117526544` delta. That leaves
at least `$0.872605656` below the approved `$1` ceiling. The worst-case guard
reserved `$0.478927200` before the call for all remaining diagnostic and live
attempts and therefore passed without approaching the ceiling.

All three approved prompt-only cycles are exhausted. No PR was opened, nothing
was deployed, and the timer remains inactive at canonical turn 1213. A further
provider call, PR, deployment, timer resume, or change to schema, validator,
protocol, model, routing, or another excluded subsystem requires new approval.

## Current cycle-3 candidate

The fresh legislative call will retain:

- the shared constitution and role prompt;
- adopted language and `COMPLETE LEGISLATURE`;
- authoritative current state/latest receipt;
- bounded collaboration input;
- the unchanged state-specific schema and local validator.

It will not replay prior canonical events. Those events remain byte-complete in
canonical persistence and public history. A deterministic leading contract
requires one public `Public audit:` sentence and provides one non-operative
complete-object shape example.

Named response receipts in this recovery envelope total `$0.0871353608`.
The conservative shared-key delta, including cycle 3's returned cost before it
appeared at the key endpoint, is `$0.1273943440`. The `$0.0402589832`
difference is shared-key usage not attributable to the named receipts,
including the cycle-1 exact replay whose process stopped before emitting its
returned receipt. The conservative remaining allowance is `$0.8726056560`
before the `$1` ceiling. No model, routing, schema, validator, retry,
temperature, cadence, credential, UI, DNS, X, rule, research, or canonical-event
mutation occurred during diagnosis.

## Offline implementation verification

The exact paused-state turn-1214 rehearsal is 54,777 characters: 54,504 system
and 273 user. It begins with the tested mandatory contract, contains the
complete B/open-`rule-132` schema, complete legislature, authoritative state,
and a 3,108-character bounded collaboration delivery, and contains no event
replay. The full canonical lookup remains 11,248 findings characters while the
model projection is 1,318.

- focused protocol/collaboration/compaction suite: 60 passed;
- full Python: 130 passed;
- JavaScript: 31 passed;
- contract coverage: 115 requirements / 210 sequential tasks;
- compile, whitespace, and canonical state/prompt/viewer/provider-boundary
  preservation: PASS.

## Approved deterministic deliberation fallback

Date: 2026-07-31 WITA

Exact approval receipt:

> APPROVE LIVE CHANGE: continue A Language All Their Own from paused turn 1213
> using branch codex/alato-model-context-compaction and the existing production
> OpenRouter key; allow the narrowly scoped deterministic deliberation fallback
> for otherwise valid typed actions, the public stale-runtime notice, one PR
> and merge to main, production deployment, and one live B turn with up to
> $0.30 additional provider spend; do not change model, routing, cadence,
> credentials, DNS, or X; pause on any other validation, state, service, or
> invariant warning; after one valid B receipt, verify the live site and system
> and leave the normal timer running

The approved fallback is local and non-operative. It applies only when every
strict validation error is confined to a missing, shorter-than-minimum, or
punctuation-only `deliberation` field. Before substitution, the unchanged
state-specific validator must accept the complete typed `motion`,
`measurements`, `requests`, and envelope. Any other error still enters the
unchanged bounded retry path.

The harness derives one fixed public sentence from the already-validated role
and motion. Canonical history stores that sentence and an explicit
`deliberation_fallback` receipt containing only the fallback source and bounded
validation reason; raw invalid provider prose is not persisted.

Pre-deployment verification:

- focused fallback/protocol/compaction/loop suite: 42 passed;
- full Python: 134 passed;
- JavaScript: 32 passed;
- contract coverage: 115 requirements / 210 sequential tasks;
- whitespace and typed-action preservation: PASS;
- production timer and service: inactive;
- production main: `4da2d28287f3412a45c9195cb1dcdc9b89890b42`;
- canonical turn: 1213, next legislative actor B;
- rulebook SHA-256:
  `8bcd8c49d62581f30c5d0bf676451dbc44c6dd8af8fdbf1940b5bc115059fb45`.

No provider call, PR, merge, deployment, timer resume, model/routing/cadence
change, credential change, DNS action, or X action occurred during this
pre-deployment implementation and verification.
