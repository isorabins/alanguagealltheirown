# Changing ALATO by behavior

Tell the agent what should happen differently, with an example if useful. You do
not need to name a file, choose an architecture, or enumerate test cases. The agent
owns translating that request into the smallest responsible module, protecting
unchanged behavior, and proving the result.

An **interface** is the small promise a module makes to its caller: what you give
it, what it produces, what it may change, and how it fails. The tables below are
an entry map. Types and adjacent docstrings define the precise interface; linked
behavior tests are the executable examples. Read implementation only when needed.

## The whole experiment

| Step | Module's job | What the next step can rely on |
|---|---|---|
| 1. Resume | Turn persistence | A coherent saved experiment, recovered before selecting another actor. |
| 2. Act | Legislature **or** development exam | One complete working outcome, produced from raw model responses. |
| 3. Save | Turn persistence | History, language, next actor, exam cursor and deliveries belong to the same turn. |
| 4. Publish | Public snapshot | Sanitized projections of that saved experiment. |
| 5. Read | Public reader | One coherent revision, with honest freshness and complete history. |

Collaboration supplies eligible human input to step 2. The existing runner also
owns cost accounting, the schedule and reviewed cleanup. Conversation and transfer
evaluations retain their separate meanings. X delivery runs independently.

The product-defining promises are [B1–B6](architecture/deep-modules-20260905.md#behavior-spine).
The experiment's domain words are in [CONTEXT.md](../CONTEXT.md).

## The four rebuilt modules

### Turn persistence — “Resume exactly where the completed turn left off”

**Give it:** a directory and the complete working `TurnState`. Use one exclusive
writer session across loading, model work and committing.

**Get:** `load(defaults)` returns recovered or legacy state; `commit(state)` makes
that whole outcome recoverable. A failed commit is indeterminate until reloaded.
The next load finishes prepared work before returning. An overlapping writer or
corrupt journal stops explicitly instead of guessing. Provider charges have their
own durable receipts; calls made before a turn is prepared can be retried.

The completed exam trace is saved durably with the turn before optional public
publication. Human notices are acknowledged only when their turn is committed.
The runner repairs derived files before attempting further work, even at the spend
cap. The scheduled shell preserves recovered state before its Git pull. Archive
uses the same writer lock and recovers pending work first. `archive(name)` retires
canonical and collaboration transport state recoverably. Couriers cannot overlap
that reset; old remote backups and duplicate retired records cannot repopulate the
new run. New collaboration input remains eligible under the existing moderation
rules. The local generation marker must be retained when restoring a reset run.

**Interface:** [TurnState / TurnStore](../turn_store.py).
**Protected examples:** [every interrupted write, corrupt journal and overlap](../tests/python/test_turn_store.py),
[real runner restart, next actor and archive](../tests/python/test_turn_recovery.py),
[terminal exam and language recovery](../tests/python/test_module_contracts.py),
[scheduled shell retry](../tests/python/test_public_exam_progress.py).

### Legislature — “Ask the correct agent and apply one lawful outcome”

**Give it:** saved experiment state, turn number, role resources, a provider adapter
and a token-count adapter. Call `take_turn(...)`; callers do not parse or complete
the motion themselves.

**Get:** `accepted`, `rejected`, or `structural_failure`, with the working state and
authoritative receipt updated together. A proposes/revises; B alone votes. The
module owns prompts, bounded eligible context, regeneration, validation,
measurements, language version/hash, delivery outcome and next actor. Exhausted
structure leaves language and delivery eligibility intact and retains the actor.
Provider/accounting failures propagate; the caller must not commit a partial turn.

`assemble_request(...)` is the inspection seam for the exact model-facing context.
It does not call a model or confer authority on supplied evidence.

**Interface:** [take_turn / LegislativeResources](../legislature.py).
**Protected examples:** [native structural exhaustion](../tests/python/test_module_contracts.py),
[role and motion authority](../tests/python/test_motion_authority.py),
[typed actions and receipts](../tests/python/test_legislative_protocol.py),
[context and delivery privacy](../tests/python/test_model_context_compaction.py).

### Development exam — “Turn raw model output into trustworthy evidence”

**Give it:** saved experiment state, turn number, frozen suite/model resources,
provider and token-count adapters. An optional local progress path enables a trace.

**Get:** `run_exam(...)` appends one canonical exam and advances its cursor. It
captures adopted language, encodes, decodes, resolves judge-selected lines to actual
text, validates the judgment, scores it and updates only valid comparison baselines.
Its return value is the optional completed public trace; the canonical result lives
in the working state. Invalid judge output is recorded as invalid, never admitted
as language failure. Provider failure aborts the turn. Trace failure is fail-open.

`validated_persisted_exam(...)` defensively rechecks historical evidence before
fault replay, including exact decoded spans and required literal constraints. The fault lifecycle remains owned by legislative protocol; this
module does not decide when a fault is selected, linked, reopened or resolved.

**Interface:** [run_exam / ExamResources](../exam_evidence.py).
**Protected examples:** [raw responses through baseline and fault replay](../tests/python/test_module_contracts.py),
[literal loss, line evidence, cursor and retests](../tests/python/test_exam_evidence.py),
[judge validation](../tests/python/test_judge_validation.py),
[safe trace lifecycle](../tests/python/test_public_exam_progress.py).

### Public snapshot — “Show one truthful, complete public story”

**Give the writer:** one saved `TurnState`, output root, completion timestamp and
public policy. `write_snapshot(...)` produces sanitized runtime, language, preview,
full history and a startup script capped at 2 KB. Failure is explicit; the runner
can rebuild the projections. Regeneration never advances the completion timestamp.
Legacy states without that timestamp do not invent one.

**Give the reader:** a fetch adapter and rendering callbacks. `createReader(...)`
returns `refresh()` and `refreshProgress()`. A refresh pins content to repository
head and gets turn freshness from history at that revision. A bounded preview retains the real headline exams and latest A/B messages
before full history arrives. Missing previews support old commits; unavailable GitHub
falls back to deployed preview **and then full history**. Malformed or late older
responses cannot overwrite a newer coherent view. Each snapshot callback reports
`complete`: false previews are labeled as incomplete in the page. If a canonical
preview succeeds but the full archive fails, the reader tries the deployed full
snapshot as a whole (with unknown live freshness), rather than mixing revisions.
An already complete last-good view survives a failed refresh. Unchanged revisions avoid
repeated full-archive downloads. The page checks for a new revision every minute.
Progress belongs to the displayed revision; missing, malformed and unavailable
states are explicit. Reading never calls a model.

**Interfaces:** [writer / PublicPolicy](../public_snapshot.py),
[reader](../viewer/public-state.js).
**Protected examples:** [revision races, fallback and full history](../tests/js/public-state.test.js),
[visible page and freshness](../tests/js/public-page.test.js),
[bounded startup and privacy](../tests/python/test_loop_helpers.py).

## Existing modules that retain their jobs

These are part of the map, not a claim that every file needed rewriting.

| Module / interface to start from | Small behavior promise | Existing protection |
|---|---|---|
| [Runner / provider and cost ledger](../loop.py): `run`, `call`, `token_count` | Choose scheduled work; preserve models/prompts/caps and exact returned provider charges. Delegate complete outcomes to the modules above. | [Loop helpers](../tests/python/test_loop_helpers.py), [prompt contract](../tests/python/test_prompt_contract.py), shell retry tests above. |
| [Legislative protocol](../legislative_protocol.py): typed action validation, receipt construction, derived feedback/faults | Decide which actions/evidence are eligible and derive current authority from canonical records. Never let prose become law. | [Protocol](../tests/python/test_legislative_protocol.py), [evidence replay](../tests/python/test_exam_evidence.py). |
| [Language representation](../rulebook.py): `language_payload`, `render_language`, `apply_typed_motion` | Distinguish adopted language from complete legislature; preserve authority and deterministic language identity. | [Views](../tests/python/test_rulebook_views.py), [motion authority](../tests/python/test_motion_authority.py). |
| [Collaboration](../collaboration.py): import, eligible delivery, public projection; [lookup](../project_lookup.py): `project_lookup` | Human moderation controls visibility; deliver eligible replies once; keep full private evidence while bounding prompt input. Internal questions use project evidence or ASK. | [ASK](../tests/python/test_ask_lifecycle.py), [research](../tests/python/test_research_lifecycle.py), [suggestions](../tests/python/test_suggestion_lifecycle.py), [inbox](../tests/python/test_collaboration_inbox.py). |
| [Courier](../collab_sync.py) and [HTTP collaboration adapters](../viewer/api/_collaboration.js) | Transport bounded inbox/outbox records. Browser actions cannot directly author canonical history. Session and moderation gates remain enforced. | [Collaboration HTTP](../tests/js/collaboration-api.test.js), [session](../tests/js/human-session.test.js), [suggestions](../tests/js/suggestion-api.test.js). |
| [Cleanup](../cleanup_rulebook.py), [shadow evaluation](../shadow_cleanup.py), runner cleanup entry | Compile and compare a proposed cleanup against captured language; only reviewed successful results apply; failures/quarantine preserve authority. | [Cleanup](../tests/python/test_cleanup_rulebook.py), [shadow](../tests/python/test_shadow_cleanup.py), [automatic cleanup](../tests/python/test_automatic_cleanup.py). |
| [Conversation](../conversation_exam.py): `run_conversation` | Six messages use captured adopted language; judge must cover each scenario requirement exactly once. | [Conversation exam](../tests/python/test_conversation_exam.py). |
| [Public progress](../public_exam_progress.py): writer/validator | Only safe fields and valid phase transitions become inspectable trace evidence. | [Progress](../tests/python/test_public_exam_progress.py), page tests above. |
| [Viewer](../viewer/index.html) and [startup](../viewer/startup.js) | Render the reader's evidence, accessible history and honest runtime states; keep Try It disabled. | [Public page](../tests/js/public-page.test.js). |
| [Public encode/decode/judge adapters](../viewer/api/encode.js) | Pin adopted language and isolate public key/allowance/error handling from private experiment credentials. The dormant adapter contract is distinct from enabling Try It. | [Try It](../tests/js/try-it.test.js), [key separation](../tests/js/public-key-boundary.test.js), [judge](../tests/js/rulebook-and-judge.test.js). |
| [X delivery](../tweet.py): `deliver` | Separate idempotent delivery state, explicit eligibility, bounded slots; never part of the experiment timer. | [Tweet delivery](../tests/python/test_tweet_delivery.py). |
| [File primitives](../state_store.py): atomic JSON/hash | One-file atomic replacement and deterministic identities; complete-turn atomicity belongs to TurnStore. | [File primitives](../tests/python/test_state_store.py). |
| [Legacy repair](../legacy_motion_repair.py) | Inspect/repair historical motion artifacts under its own operator workflow. | [Legacy repair](../tests/python/test_legacy_motion_repair.py). |

Manual [transfer evaluation](../transfer_test.py), [provider probe](../probe.py),
and [local Try It server](../tryit/serve.js) are operator tools, outside the
scheduled turn. Their live integrations are not covered by this refactor's offline
acceptance. Changes to those paths need task-specific evidence; do not assume the
main regression suite proves them.

## How a future behavior request becomes a change

1. Restate the requested observable difference with one before/after example.
   Identify the owning row above and the relevant B1–B6 promises. Ask only if a
   material product choice is unresolved; the agent owns engineering choices.
2. Read that interface, its types/docstrings and linked behavior tests. Add or
   update a test through the same seam the real caller uses, starting with native
   input. Show that the old behavior fails the new expectation.
3. Change the implementation. Preserve unrelated expectations. Never delete,
   skip or weaken a protected behavior test merely to make a refactor pass.
   If the requested behavior supersedes an expectation, explain that connection.
4. Verify the caller and real adapter as far as authorized, then run relevant
   regression checks. Report fixture-backed, local-browser and production evidence
   separately. Update the adjacent interface and this routing map if ownership moved.

The repository's [offline CI](../.github/workflows/offline-acceptance.yml) discovers
all Python and Node tests, including the new interface contracts. This is executable
regression protection, not a claim that remote branch-protection settings changed.
The historical coverage checker checks traceability; it is not semantic proof.
