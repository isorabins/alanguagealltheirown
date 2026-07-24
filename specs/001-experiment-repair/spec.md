# Feature Specification: Experiment Repair and Public Collaboration

**Feature Branch**: `codex/experiment-repair` (published to draft PR 1; not merged)

**Created**: 2026-07-20 WITA

**Status**: Public application deployed; launch-first core-runtime activation approved with the existing rulebook preserved and cleanup deferred

**Input**: Repair the experimental contract of “A Language All Their Own,” preserve its history, add bounded public collaboration, and make every public claim match verified state. This specification consolidates Iso's line-by-line decisions from the skeptical audit completed on 2026-07-20.

## Documentation Context

| Source | Type | Relevance | Key Constraint / Decision | Conflict Status |
|--------|------|-----------|---------------------------|-----------------|
| `AUDIT-FINDINGS-2026-07-20.md` | Audit receipt / user decision ledger | Primary contract source | Contains the evidence, agreed repairs, explicit non-actions, and human gates from the review | Aligned; local and gitignored by design |
| `HANDOFF-AUDIT-2026-07-18.md` | Prior audit brief | Original audit questions and safety boundary | Required a skeptical read-only audit before changes | Aligned; audit completed |
| `PROGRESS.md` | Append-only project history | Records requested features, shipped work, and historical claims | Preserve history; do not rewrite old results or interventions | Aligned; latest remote state continues beyond audited checkout |
| `PRD-conversation-and-composition.md` | Prior specification | Defines Conversation, Composition, RESEARCH, and ASK concepts | Conversation retained and judged; Composition dropped; RESEARCH/ASK design superseded by this spec | Conflict resolved |
| `MECHANICS.md` and `README.md` | Public/operational documentation | Current explanations are materially stale | Refresh only after repaired behavior is verified | Conflict resolved by FR-030 |
| `loop.py`, prompts, state files, Try It endpoints, viewer, and `tweet.py` | Current implementation | Establishes actual runtime boundaries and failure modes | Preserve the loop cadence and stranger invariant while repairing status, roles, state, and delivery truth | Aligned with specified repairs |
| `.specify/memory/constitution.md` | Governance | Controls contract, approval, worktree, evidence, and live-change gates | Plan/tasks and approval precede implementation; user-visible paths require human-app-testing evidence | Aligned |
| [OpenRouter web-search server tool](https://openrouter.ai/docs/guides/features/server-tools/web-search) | Official documentation | Current RESEARCH capability | Use current server-tool behavior; deprecated `:online` design is forbidden | Conflict resolved |
| [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs) | Official documentation | Coverage-complete cleanup response | Use strict JSON Schema plus parameter-compatible routing; prompt-only source coverage is forbidden after two observed omissions | Conflict resolved by FR-013 |
| [OpenRouter key limits](https://openrouter.ai/docs/api/api-reference/api-keys/create-keys) | Official documentation | Public Try It spend boundary | A dedicated key can enforce a monthly USD limit | Aligned |
| [Upload-Post text API](https://docs.upload-post.com/api/upload-text/) | Official documentation | X confirmation, idempotency, and threading | Use confirmed results and stable idempotency; do not rely on automatic threading | Aligned |
| [NVIDIA NIM FAQ](https://docs.api.nvidia.com/nim/docs/product) | Official documentation | Considered free public inference alternative | Free developer endpoints are for prototyping/testing, not public end-user production | Rejected for public Try It |
| [Crabbox v0.40.0](https://github.com/openclaw/crabbox/releases/tag/v0.40.0) and pinned local snapshot | Official release/source | Remote disposable desktop, outer recording, proof, TTL, and cleanup | Pin verified commit/checksum; use X11 desktop; exclude Semaphore; do not execute repository installers | Aligned with FR-048–FR-055 |
| [Cloudflare Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/) and [Hetzner pricing](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/) | Official provider documentation | Durable coordinator and bounded hourly desktop cost | Free-tier coordinator where eligible; one CPX32 Germany lease; `$2` hard new-infrastructure ceiling | Aligned with approved pilot envelope |

**Ignored / Outdated Sources**: `PRD-remove-caps.md` is historical and unrelated to this repair. The old dumb-script benchmark, Slack ASK bridge, `:online` research suffix, standalone Composition exam, power-grid framing, and broad novelty/growth claims are superseded. Historical records containing them remain untouched.

**Open Documentation Conflicts**: None. The original audit observed `5551f6f`
(turn 537); the 2026-07-21 read-only preflight observed remote `main`
`6c515362ef4059844a7d2aead3b96af4627a1f81` at turn 636. The feature worktree
remains intentionally isolated until the approved paused rebase gate.

## User Scenarios & Testing

### User Story 1 - Trust the Experiment (Priority: P1)

As a visitor or researcher, I can tell exactly which rules constitute the tested language and can trust that exams, scores, and labels describe the state that was actually used.

**Why this priority**: Every later feature is misleading if proposed or rejected material still enters ordinary exams or if public labels overstate what was tested.

**Independent Test**: Inspect a frozen state containing adopted, proposed, rejected, and reverted rules; run an ordinary exam through a scratch copy; verify that only adopted rules reach encoder and decoder, history remains intact, and the public representation matches the same state.

**Acceptance Scenarios**:

1. **Given** rules in multiple statuses, **when** an ordinary exam runs, **then** only adopted rule text governs encoding and decoding.
2. **Given** a proposed rule, **when** no explicitly labeled proposal trial is running, **then** that rule is absent from the exam contract.
3. **Given** rejected or superseded material, **when** the legislature reviews history, **then** the material remains visible as history but cannot affect the tested language.
4. **Given** a judge response with a missing, duplicate, or out-of-range answer-key item, **when** fidelity is calculated, **then** the exam is invalid and no fidelity score is published.

---

### User Story 2 - Observe Genuine Legislative Tension (Priority: P1)

As a visitor, I see an inventor and an auditor with genuinely distinct jobs rather than two copies repeating the same motions.

**Why this priority**: The public premise depends on meaningful back-and-forth and defensible language authorship.

**Independent Test**: Feed synthetic turns containing allowed and forbidden motions to each role and verify that the inventor can create/refine ideas, the auditor can critique/decide, settled motions are not repeated, and forbidden role actions do not change state.

**Acceptance Scenarios**:

1. **Given** DeepSeek Agent A's turn, **when** it proposes or revises one idea, **then** the idea may enter legislative state without A casting a vote.
2. **Given** Kimi Agent B's turn, **when** it audits A's latest idea, **then** it may adopt, reject, or request a focused revision/test but cannot introduce an unrelated rule.
3. **Given** a settled motion, **when** either agent repeats it, **then** the repetition cannot change state, history, or revision counts.
4. **Given** the shared constitution, **when** either agent receives a turn, **then** it retains the 50% target and affordability mission without dumb-script, power-grid, or unsupported novelty/growth framing.

---

### User Story 3 - Repair the Rulebook Without Rewriting History (Priority: P1)

As Iso, I can review one agent-authored cleanup of the active language before it changes production, while preserving the complete pre-cleanup artifact.

**Why this priority**: The current adopted set contains duplicate, incomplete, contradictory, and operational text; ordinary evolution should not continue on that foundation.

**Independent Test**: On a snapshot, have inventor A return one cleaned active rulebook and auditor B review it; produce an exact before/after diff; verify no production state changes before Iso's approval.

**Acceptance Scenarios**:

1. **Given** the pre-cleanup rulebook, **when** cleanup begins, **then** the original is preserved immutably.
2. **Given** A's cleaned rulebook and B's audit, **when** the pass completes, **then** Iso receives an exact diff before any application.
3. **Given** no approval, **when** the cleanup pass ends, **then** the normal loop remains paused and production state is unchanged.
4. **Given** every adopted source id, **when** A authors the cleanup draft, **then** each id occupies one schema-required assignment slot and the candidate's `source_ids` are derived deterministically rather than trusted from model output.

---

### User Story 4 - Use the Language in a Judged Conversation (Priority: P2)

As a visitor, I can watch DeepSeek and Kimi use the adopted language across a real multi-turn task and see whether they reached a correct, concrete outcome.

**Why this priority**: This demonstrates native use directly and replaces the overlapping one-message Composition proposal.

**Independent Test**: Give two fresh speakers the adopted rulebook and one real scenario; verify an alternating multi-turn conversation, then independently judge the final agreement against the scenario's required outcome.

**Acceptance Scenarios**:

1. **Given** a real work scenario and adopted rulebook, **when** the Conversation runs, **then** DeepSeek and Kimi alternate through the defined exchange using the language.
2. **Given** the completed exchange, **when** it is judged, **then** the page shows whether the agents reached correct, concrete next steps.
3. **Given** the superseded Composition proposal, **when** implementation scope is reviewed, **then** no standalone Composition path is built.

---

### User Story 5 - Ask for Evidence and Human Judgment (Priority: P2)

As an agent, I can request cited research or ask Iso for judgment without blocking the loop, losing the original question, or giving outside text authority to legislate.

**Why this priority**: It makes the stated collaboration real while preserving agent authorship and prompt-injection boundaries.

**Independent Test**: Submit one RESEARCH and one ASK request in scratch state; verify durable correlated records, non-blocking behavior, public status, delivery of question plus answer, and zero automatic rule/state mutation.

**Acceptance Scenarios**:

1. **Given** a concise RESEARCH request, **when** evidence returns, **then** the same record contains the stable id, asker, original question, status, findings, limitations, citations, and answer turn.
2. **Given** untrusted research content, **when** it is delivered, **then** it is clearly bounded as evidence and cannot cast votes or mutate rules/state directly.
3. **Given** an open ASK, **when** a visitor views the site, **then** the question shows `awaiting Iso` until answered.
4. **Given** Iso's authenticated answer, **when** the next eligible turn runs, **then** the requesting agent receives its original question and Iso's verbatim answer together.
5. **Given** no answer, **when** turns continue, **then** the loop never blocks or auto-answers.

---

### User Story 6 - Contribute a Moderated Visitor Suggestion (Priority: P2)

As a visitor, I can suggest an idea prominently beneath the agent windows, while Iso controls whether any public submission reaches agent context.

**Why this priority**: Audience participation is compelling, but direct anonymous prompt injection would compromise the experiment.

**Independent Test**: Submit a suggestion; verify it remains private and absent from agent context until Iso approves it; approve one; verify at most one clearly delimited optional suggestion appears on the next eligible turn.

**Acceptance Scenarios**:

1. **Given** an unreviewed suggestion, **when** the loop runs, **then** the text never enters agent context or the public site.
2. **Given** Iso's approval, **when** the next eligible turn runs, **then** at most one suggestion is delivered as optional context, not a rule or instruction.
3. **Given** an approved suggestion, **when** its lifecycle progresses, **then** its public record can show approval, delivery, and resulting agent action or non-action.

---

### User Story 7 - Try the Language Safely (Priority: P2)

As a visitor, I can encode and decode against one consistent rulebook version, and I receive an honest message if the public monthly allowance is exhausted.

**Why this priority**: A version race can create false failures, while uncapped public inference can create surprise spend.

**Independent Test**: Exercise a normal Try It run, force a rulebook-version change between encode/decode, and simulate an exhausted monthly allowance; verify the three distinct user outcomes.

**Acceptance Scenarios**:

1. **Given** a successful encode, **when** decode begins with the same rulebook version, **then** the normal journey completes.
2. **Given** the rulebook changed after encode, **when** decode begins, **then** the visitor is asked to encode again rather than receiving a false language failure.
3. **Given** the public monthly allowance is exhausted, **when** a visitor opens or submits Try It, **then** the page explains that the allowance will reopen after reset and does not look broken.
4. **Given** a provider failure unrelated to allowance, **when** the request fails, **then** it is not mislabeled as a monthly-cap condition.

---

### User Story 8 - Read an Honest, Focused Public Record (Priority: P3)

As a first-time visitor, I see the most interesting current material without scrolling through expanded archives, and every public channel accurately reports delivery and project status.

**Why this priority**: Presentation should follow experimental truth, not conceal or outrun it.

**Independent Test**: Complete desktop and mobile journeys through the page and X delivery simulations; verify selective disclosure, truthful note state, bounded retries, accurate docs, and approval gates for public actions.

**Acceptance Scenarios**:

1. **Given** the public page, **when** it loads on desktop or mobile, **then** newest and decision-relevant content is open while repetitive reference/history is collapsed.
2. **Given** a dry run or failed X request, **when** delivery state updates, **then** the note is not marked posted.
3. **Given** an ambiguous X retry, **when** the same note is retried, **then** it cannot create a duplicate.
4. **Given** three failed attempts, **when** the next delivery run occurs, **then** the note becomes visibly blocked and later notes may continue.
5. **Given** generated X copy, **when** it is submitted, **then** it is a single post of no more than 250 characters unless Iso separately approves a thread.

---

### User Story 9 - Run Evidence-Grade Acceptance Without Taking Over Iso's Mac (Priority: P1)

As Iso, I can keep using my visible Mac while the full human browser journey runs on a disposable remote desktop and returns auditable screenshots, one continuous outer video, proof receipts, and verified cleanup.

**Why this priority**: The required production run is long, crosses browser-process restarts, and cannot depend on Iso surrendering his screen or remembering to terminate paid infrastructure.

**Independent Test**: Run a fresh off-production fixture on one disposable remote X11 desktop; visibly close and relaunch the browser while one outer MP4 continues, collect the proof bundle, verify the lease/cost/TTL controls, destroy the lease, and repeat the workflow from the reusable skill without project-specific secrets.

**Acceptance Scenarios**:

1. **Given** a disposable remote desktop, **when** the browser process is closed and relaunched, **then** one uninterrupted outer video still covers the entire visible sequence.
2. **Given** the test runner, **when** screenshots and receipts are produced, **then** every file maps to an acceptance row and secrets are absent from arguments, logs, screenshots, video, and bundles.
3. **Given** a stalled runner or lost local connection, **when** the lease reaches its TTL or cost boundary, **then** coordinator-owned cleanup prevents an indefinite paid machine.
4. **Given** the pilot ends or fails, **when** closeout runs, **then** zero active leases remain and actual new-infrastructure spend is no more than `$2`.
5. **Given** a different repository with a visible browser journey, **when** Codex invokes the reusable skill, **then** it can repeat the preflight, remote desktop, evidence, and teardown pattern without this project's credentials or assumptions.

### Edge Cases

- A status changes while an exam or Try It request is in progress.
- An agent issues multiple motions, a forbidden role motion, a no-op motion, or a malformed reference.
- The cleanup output omits an adopted rule, silently changes meaning, or contains operational instructions disguised as language law.
- The cleanup draft assigns a source to an unknown group, leaves a group unreferenced, duplicates a group id, or arrives from a provider that did not enforce the required schema.
- The judge returns duplicate, missing, nonnumeric, or out-of-range item identifiers.
- Research returns no sources, unsupported claims, raw prompt-injection text, or a proposed rule.
- Multiple RESEARCH, ASK, human answers, or visitor suggestions arrive before the next turn.
- Iso submits an answer twice, answers a closed id, or leaves an ASK unanswered indefinitely.
- A visitor floods suggestions or submits secrets, personal data, links, or hostile instructions.
- The simple human password is wrong, brute-forced, missing from the environment, or the remembered session expires.
- The public inference allowance is exhausted mid-journey or the provider returns a transient error.
- X accepts a post but the response times out, returns an asynchronous receipt, or confirms only some requested platforms.
- A blocked X note sits ahead of newer notes; dry runs and failures must not consume the two-per-day public budget.
- The evolving remote state advances between planning, implementation, cleanup approval, and deployment.
- The local recording stream disconnects while the remote desktop or browser remains alive.
- The browser crashes or is restarted while the outer desktop recording must continue.
- Provider identity, region, machine size, projected cost, or coordinator authority differs from the approved envelope.
- A TTL label exists but no durable cleanup owner is active.
- A secret-entry screen, protected profile, or diagnostic bundle risks exposing a credential.

## Boundary & Invariants

**Single Product Invariant**: Only the current agent-adopted rule set may govern encoding and decoding, and every public status or claim must match verified state.

**Forbidden Old Behavior / Side Effect**: Proposed/rejected text entering ordinary exams; dumb-script claims remaining active; humans or unreviewed visitors directly writing rules; role-violating motions changing state; unconfirmed X delivery advancing state; public Try It using uncapped private experiment credentials; or any live/public change occurring without the required approval.

**Legacy And Bypass Inventory**:

| Surface | Current / Old Behavior | New Allowed Behavior | Required Proof |
|---------|------------------------|----------------------|----------------|
| Rulebook renderer | Adopted, proposed, and rejected remnants can enter the tested bundle | Ordinary exams and language use receive adopted rules only | Captured scratch requests plus status-fixture tests |
| Per-rule history | Corpus exams stamp shared results onto many rules | Corpus results remain corpus-level; proposal trials are explicit | State diff and public-label inspection |
| Dumb control | Active script, prompts, economics, and site comparison | Historical records only | Repository search and public-page inspection |
| Agent legislature | Same model, prompt-only leans, unenforced actions | DeepSeek inventor and Kimi auditor with enforced permissions | Negative synthetic motion tests plus transcript inspection |
| Cleanup | Broken state evolves continuously | One paused, preserved, agent-authored cleanup with human diff gate | Immutable snapshot, A output, B audit, exact diff, approval receipt |
| Judge | Counts returned verdicts without exact item coverage validation | Publishes scores only for complete one-to-one item coverage | Duplicate/missing/out-of-range test battery |
| Research | Unbuilt/deprecated `:online` PRD | Stateful cited evidence, non-blocking and non-legislative | Durable request/answer record and negative mutation test |
| ASK | Unbuilt Slack bridge PRD | Public question lifecycle and simple password-protected human response | Visible open/answered journey and exact delivery receipt |
| Suggestions | No public submission path | Moderated optional context only | Unapproved-submission negative test and approved-delivery receipt |
| Composition/Conversation | Unbuilt overlapping specs; Conversation unjudged | Judged multi-turn Conversation only | Six-message artifact plus outcome judgment |
| Try It | Independent live-rulebook fetches; shared/unverified spend protection | Same-version journey; dedicated $20 monthly public boundary | Forced-version mismatch, key metadata, exhausted-cap UI |
| X delivery | State advances without confirmed success; thread and retry gaps | Confirmed, idempotent, bounded single-post delivery | Dry/failure/timeout simulations and live receipt after approval |
| Documentation/page | Stale docs and over-expanded low-value material | Current verified docs and selective disclosure | Search checks plus desktop/mobile human-app-testing evidence |

**Negative Acceptance Scenarios**:

1. **Given** proposed, rejected, visitor, research, or human text, **when** an ordinary encode/decode contract is built, **then** none of it can become language law without an agent proposal and valid adoption.
2. **Given** missing credentials, approval, verified cleanup diff, or deployment access, **when** a live/public stage begins, **then** execution stops safely before changing production or publishing.
3. **Given** a dry run, provider failure, ambiguous timeout, or partial platform success, **when** X bookkeeping runs, **then** no false posted state is recorded.
4. **Given** the free NVIDIA developer key, **when** a public Try It backend is configured, **then** that key is rejected as an allowed production credential.

**Production Equivalence Need**: Core behavior must be proven first against scratch copies and synthetic fixtures using the same code paths and state shapes as production. User-visible acceptance additionally requires the real deployed page, the real password-protected human journey, current provider key metadata, a full Try It journey, and X receipts where public actions are approved. Beta/dry-run evidence must remain labeled incomplete until the production-equivalent path passes.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST maintain one canonical rule ledger with explicit adopted, proposed, rejected, repealed, and historical/superseded states.
- **FR-002**: Ordinary encoding, decoding, Try It, and Conversation use MUST receive only the adopted rule set.
- **FR-003**: A proposed rule MUST enter an exam only through an explicitly labeled proposal-specific trial.
- **FR-004**: Rejected, repealed, and superseded material MUST remain available to the legislature and public history without affecting language use.
- **FR-005**: Corpus exam results MUST be presented as corpus-level evidence and MUST NOT imply individual rule attribution without a proposal-specific trial.
- **FR-006**: The active dumb-script comparison MUST be removed from runtime measurement, prompts, economics, and current public surfaces while its historical record remains intact.
- **FR-007**: Agent A MUST use DeepSeek as the inventor and may propose, repeal, revise, or measure at most one focused idea per turn, but MUST NOT vote.
- **FR-008**: Agent B MUST use Kimi as the auditor and may critique, adopt, reject, or request focused work on one add/repeal proposal, but MUST NOT introduce an unrelated rule or originate repeal.
- **FR-009**: Forbidden role actions and repeated settled motions MUST NOT change state, history, or public revision counts.
- **FR-010**: Both agents MUST share a concise constitution containing the stranger-decodability requirement, measurement discipline, public-history commitment, 50% target, and affordability/access mission.
- **FR-011**: The shared constitution MUST NOT contain active dumb-script framing, power-grid/gigawatt claims, or unsupported novelty/traffic-growth claims.
- **FR-012**: The current rulebook MUST remain byte-identical through the launch-first core-runtime activation. The optional one-time cleanup remains paused and separately approval-gated; it is no longer a prerequisite for resuming the repaired loop.
- **FR-013**: DeepSeek A MUST author one cleaned active rulebook through a strict coverage-complete draft: every adopted source id is a required assignment key, A either maps it to A-authored cleaned group text or explicitly excludes it as operational, fragmentary, or contradictory, and deterministic code derives each candidate rule's `source_ids` plus the complete exclusion receipt; missing/extra assignments, unjustified exclusions, unknown/orphan/duplicate groups, schema-incompatible routing, or candidate validation failure MUST stop before Kimi. Kimi B MUST audit the compiled candidate, treat only documented non-language exclusions as intentional rather than silent omissions, and Iso MUST receive an exact diff before any application.
- **FR-014**: Cleanup MUST NOT require a new permanent bureaucracy of supersede/archive operations beyond the minimal normal governance contract.
- **FR-015**: Fidelity MUST be calculated only when the judge returns every answer-key item exactly once with no duplicates or out-of-range identifiers; otherwise the exam is invalid.
- **FR-016**: RESEARCH MUST create a durable, append-only, correlated request/answer record containing stable id, requester, turns, question, status, evidence, limitations, citations, and errors where applicable.
- **FR-017**: RESEARCH MUST be non-blocking, answer at most one oldest open request per turn, and deliver the original question together with the cited result.
- **FR-018**: Research content MUST be treated as untrusted evidence and MUST NOT directly vote, write a rule, or mutate state.
- **FR-019**: ASK MUST create a durable public question lifecycle showing requester, turn, original question, awaiting/answered status, Iso's verbatim answer, and answer/delivery turns.
- **FR-020**: Iso MUST be able to answer from a private `/human` surface protected by one remembered password; the feature MUST NOT introduce user accounts, OAuth, or a general identity system.
- **FR-021**: An unanswered ASK MUST remain open indefinitely without blocking or auto-answering; an answered ASK MUST deliver the original question and verbatim answer together on the next eligible turn.
- **FR-022**: Visitors MUST be able to submit short suggestions directly beneath the live agent windows.
- **FR-023**: Pending and dismissed suggestions MUST remain private and absent from agent context; only Iso-approved suggestions may be published or delivered.
- **FR-024**: At most one approved suggestion per eligible turn may be delivered as clearly optional context; it MUST NOT be represented as a rule or instruction.
- **FR-025**: Standalone Composition MUST remain unimplemented and documented as superseded by a judged multi-turn Conversation.
- **FR-026**: Conversation MUST give DeepSeek and Kimi only the adopted rulebook and a real scenario, preserve the exchange, and produce an outcome judgment against concrete scenario requirements.
- **FR-027**: Try It decode MUST verify that the rulebook version matches the preceding encode; a mismatch MUST request re-encoding without attempting decode.
- **FR-028**: Public Try It MUST use a credential separate from the private experiment with a verified $20 monthly spending limit and automatic monthly reset.
- **FR-029**: Try It MUST distinguish monthly allowance exhaustion from other provider failures and show a clear reopening message rather than a broken state.
- **FR-030**: The public page MUST keep newest/decision-relevant content open and collapse repetitive reference/history content by default, with mobile behavior included.
- **FR-031**: README and MECHANICS MUST be updated after verification to describe current boundaries, agents/models, exams, collaboration, costs, deployment, and human interventions without stale dumb-script or old-state claims.
- **FR-032**: The historical field-note overclaim MUST receive an explicit public correction that preserves and references the original record.
- **FR-033**: X notes MUST be marked posted only after confirmed delivery; dry runs and failures MUST NOT advance delivery state or consume successful-post budget.
- **FR-034**: X retries MUST reuse a stable idempotency identity, stop automatically after three failures, mark the note blocked, surface blocked count, and allow later notes to continue.
- **FR-035**: Automated X copy MUST be a single post no longer than 250 characters; deliberate threads require separate Iso approval.
- **FR-036**: After core repairs are live, the project MUST prepare one concise X explainer for Iso's approval, then publish, verify, and pin it only after public-action approval.
- **FR-037**: The project MUST prepare a small researched X follow list with reasons; only accounts individually approved by Iso may be followed, and ongoing follow automation is forbidden.
- **FR-038**: The existing last-ten passing-exam average MUST remain unchanged and naturally roll forward; no new measurement subsystem is in scope.
- **FR-039**: The hypothetical cached economics scenario MAY remain unchanged for now; real caching measurement is deferred until sustained agent conversation exists.
- **FR-040**: Collaboration Redis I/O MUST run only in a bounded, exception-safe courier; a missing, failed, or hung courier MUST NOT cancel an ordinary loop turn.
- **FR-041**: The courier MUST use atomic local transport spools and stable-id retries while the loop remains the sole writer of canonical `state/collaboration.json` history.
- **FR-042**: Agent A MAY originate one repeal motion against an adopted rule; only Agent B may adopt, reject, or request focused work on that repeal, and a ratified repeal MUST leave full history while removing the target from the adopted language.
- **FR-043**: At most one add or repeal proposal MAY be open at once; cleanup MUST terminalize legacy proposed/reverted records without losing their original status or history before this guard reaches production.
- **FR-044**: Invalid exams MUST render to agents as `no valid score (<judge reason>)` and MUST never display a null value as a numeric fidelity score.
- **FR-045**: Legislative history rationale MUST be derived from the paragraph containing the exact matched motion line, including REQUEST and REPEAL families.
- **FR-046**: Operational preservation evidence MUST distinguish unchanged pre-existing state from the one committed empty public-collaboration scaffold using a baseline-aware check.
- **FR-047**: The corpus-exam metadata cache MUST retain only its latest 500 entries, and dead active-economics stubs MUST be removed without changing the historical last-ten calculation.
- **FR-048**: The production acceptance browser MUST run on a disposable remote Linux X11 desktop that does not take control of Iso's visible Mac.
- **FR-049**: The remote desktop MUST produce one continuous outer MP4 across ordinary browser-process close and relaunch, plus numbered screenshots and a proof bundle that map to the acceptance matrix.
- **FR-050**: The repository MUST own visible actions, assertions, row mapping, pass/fail rules, receipts, and cleanup; Crabbox MUST own only lease, remote desktop, and evidence transport plumbing.
- **FR-051**: The pilot MUST pin Crabbox v0.40.0 by verified release checksum/commit, exclude the Semaphore provider, and repeat dependency/advisory review immediately before installation.
- **FR-052**: The remote path MUST use one coordinator-owned lease with one active-lease limit, eight-hour TTL, `$2` maximum new-infrastructure spend, and fail-closed provider, target, identity, and cost checks.
- **FR-053**: Credentials MUST enter only through an external protected environment profile with an explicit name allowlist; secret values MUST NOT appear in chat, repository files, skill files, command arguments, screenshots, video, logs, or proof bundles.
- **FR-054**: The pilot MUST verify teardown through coordinator and provider readbacks and MUST NOT pass with an active lease, stuck cleanup, unknown spend, or unverified secret hygiene.
- **FR-055**: A reusable local Codex skill MUST reproduce the remote human-testing pattern for another repository, include only necessary scripts/references and `agents/openai.yaml`, pass `quick_validate.py`, and pass a fresh realistic off-production forward test.
- **FR-056**: The launch-first activation MUST sync the repaired runtime to the current reviewed `main`, configure the existing collaboration, human-review, and separately capped public-inference dependencies, keep X delivery disabled, resume the loop with the existing rulebook, and stop or re-pause immediately if the first observed turn changes state outside the normal loop path or emits a health/invariant warning.

### Scope and Non-Goals

- No product-code implementation occurs during specification/handoff work.
- No live-loop turn, paid test, production state repair, deploy, push, X action, follow, pin, credential change, or billing change is authorized by this specification alone.
- No database-backed rate limiter, snapshot/version database, general authentication framework, Slack bridge, automatic visitor-to-agent injection, second judge, judge retry system, or governance expansion beyond the approved minimal repeal path is in scope.
- No new dumb-script or competitor baseline is introduced.
- No coordinator portal, custom domain, artifact publication service, multi-provider platform, or Semaphore integration is in scope.
- No manual human rewriting of language rules is allowed; humans shape the experiment and curate context, while agents author and adopt language law.
- Directive overuse, shorthand conflicts, and token-aware substitution are language questions for the agent cleanup/evolution process, not separate software features.

### Key Entities

- **Rule Record**: Stable rule identity, canonical text, status, provenance, history, and applicable corpus/proposal-specific evidence.
- **Repeal Motion**: A distinct pending motion targeting one adopted rule; it has rationale/provenance/history but never enters language law.
- **Rulebook Snapshot**: Immutable pre-cleanup artifact or identifiable adopted-language version used for a specific journey.
- **Exam Event**: Payload, rulebook version, encoded/decoded material, answer key, complete judge verdicts, fidelity validity, and corpus-level savings.
- **Research Request**: Stable id, requester/turn, original question, lifecycle status, cited result, limitations, sources, cost/error metadata, and delivery turn.
- **Human Ask**: Stable id, requester/turn, original question, awaiting/answered state, Iso's verbatim answer, and delivery history.
- **Visitor Suggestion**: Stable id, submitted text, moderation state, approval/delivery state, and public outcome where approved.
- **Conversation Artifact**: Scenario, adopted rulebook version, alternating messages, models, total usage, and outcome judgment.
- **Try It Journey**: Encode/decode correlation, rulebook version, allowance/provider state, and visible result.
- **Public Delivery Record**: Field note identity, platform, attempt count, idempotency identity, confirmation id, posted/blocked state, and error receipt.
- **Remote Acceptance Lease**: Approved provider/account, coordinator identity, machine/region, start/expiry, projected/actual cost, recording/proof paths, teardown state, and non-secret receipt metadata.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In a status-fixture battery, 100% of ordinary exam/Conversation/Try It prompts contain every adopted rule and zero proposed, rejected, reverted, repealed, historical, or pending-repeal text.
- **SC-002**: Searches of current runtime, prompt, economics, and public-page output find zero active dumb-script comparison claims while historical records remain accessible.
- **SC-003**: Synthetic role tests show zero state changes from A votes, B unrelated proposals, repeated settled motions, or malformed/no-op actions.
- **SC-004**: Cleanup proves schema-required assignment coverage for every adopted source id, then produces an immutable pre-cleanup artifact, A-authored compiled replacement, B's audit, and an exact human-readable diff; production remains unchanged until an approval receipt exists.
- **SC-005**: Judge tests covering complete, missing, duplicate, and out-of-range item sets publish a score only for the complete one-to-one case.
- **SC-006**: Every completed RESEARCH and ASK record retains its original question and correlated answer; requests survive process restarts and never block ordinary turns.
- **SC-007**: An unapproved visitor submission appears in zero public or agent surfaces; one approved submission appears at most once on the next eligible turn.
- **SC-008**: A Conversation artifact contains the full intended alternating exchange and a visible outcome judgment tied to concrete scenario requirements.
- **SC-009**: Try It passes normal, forced-version-mismatch, monthly-cap, and unrelated-provider-error journeys with four distinct correct user outcomes.
- **SC-010**: The public Try It key metadata proves a $20 monthly limit and is different from the private experiment credential before production acceptance.
- **SC-011**: Desktop and 375px mobile human-app-testing confirm that current/interesting material is open, long reference material is collapsed, suggestions sit directly beneath agent windows, and ASK states are understandable without developer context.
- **SC-012**: X delivery simulations prove that dry run/failure does not advance state, identical retries cannot duplicate, the fourth automatic attempt cannot occur, blocked notes do not freeze later notes, and automated copy is at most 250 characters.
- **SC-013**: README and MECHANICS match verified production behavior and contain none of the audit's enumerated stale claims.
- **SC-014**: The correction, pinned explainer, and curated follows are not treated as complete until each approved public action is verified on the real X profile.
- **SC-015**: After implementation, the last-ten passing-exam average continues to roll forward without a reset or parallel measurement subsystem.
- **SC-016**: A recorded production acceptance run assigns `PASS`, `FAIL`, or `BLOCKED` to every feature and proves each required visible journey with screenshots, one continuous cross-turn video, and independent read-only state receipts; the overall result is `PASS` only when every required row passes and no unexplained test debris or health warning remains.
- **SC-017**: Offline courier tests prove Redis exceptions, timeouts, replay, and restart cannot mutate canonical state outside the loop, lose a durable inbox record, duplicate delivery, or prevent the loop command from running.
- **SC-018**: Production-shaped rulebook tests prove legacy proposals are terminalized at cleanup, one-open enforcement works afterward, and a complete repeal lifecycle removes exactly one adopted rule while preserving its complete legislature history.
- **SC-019**: Focused tests and evidence prove invalid-score wording, exact motion-line rationale, 500-entry metadata retention, dead-stub removal, and baseline-aware state preservation.
- **SC-020**: A fresh remote fixture run produces one inspectable outer MP4 that begins before the first visible action, remains continuous across browser-process restart, and ends after final cleanup state.
- **SC-021**: The Crabbox pilot produces an auditable screenshot/proof bundle, verifies zero active leases after teardown, and reports actual new-infrastructure spend at or below `$2`.
- **SC-022**: Secret scanning and manual evidence inspection find zero credential values in repository changes, skill files, command history, logs, screenshots, video, or proof bundles.
- **SC-023**: The reusable skill passes structural validation and a fresh forward test for a second off-production visible browser fixture without project-specific credential names or acceptance assumptions.
- **SC-024**: One production turn completes on the repaired runtime after activation, advances beyond turn 650, leaves the pre-resume rulebook history intact except for a normal agent-authored turn outcome, keeps X delivery disabled, and leaves the timer active with no service, queue, provider, or invariant warning.

## Assumptions

- Implementation begins from a clean worktree based on current `origin/main`, not the stale audited checkout.
- The loop remains live and state may continue advancing until an approved implementation gate deliberately pauses it.
- DeepSeek v3.2 remains available for inventor/encoder/judge duties and Kimi remains available for auditor/stranger duties; planning must verify exact current provider slugs before tasks.
- The existing public site and deployment path remain the delivery surface; planning must verify current project linkage, credentials, and runtime before implementation.
- The `/human` password is a single project-admin secret remembered by the browser and stored only in the deployment environment; reasonable brute-force and session protections may be added without creating an account system.
- Public suggestion volume is initially low; moderation, not autonomous content filtering, is the authority boundary.
- Old exam, dumb-script, field-note, and rulebook artifacts remain append-only history even when their current presentation is retired or corrected.
- The $20 public inference allowance is a hard monthly boundary, not a spending target.
- Crabbox itself and the Cloudflare coordinator are expected to add no usage charge within free allowance; the single hourly Hetzner lease is created only for remote proof and is governed by the approved `$2` ceiling.
- Cloudflare and Hetzner account login/MFA/payment readiness remain external dependencies until verified; no account or credential creation is implied by the spend approval.
- The pinned X explainer, correction, follows, credential/cap changes, deployment, loop pause/resume, and cleaned-rulebook application are separate live/public/account actions requiring the workspace's exact approvals at their implementation gates.

## Definition of Done and Planned Stops

The feature is complete only when all P1–P3 journeys and success criteria pass, the implementation-state ledger is current, evidence is attached to tasks, and the intended branch is committed with no unexplained dirty files. Production acceptance additionally requires verified live page journeys and approved X/account actions.

### Required Production Acceptance Test

The final test MUST be performed through the real deployed user-visible surfaces. Backend tests, logs, API receipts, or source inspection may independently confirm the result after a visible action, but cannot substitute for the human journey. Before testing, record the deployed commit, environment, public URL, current rulebook version, available sessions/permissions, test data, cleanup path, and every approval boundary.

Create an evidence matrix before the run with one row per feature or failure state. Every row MUST name the visible action, expected visible result, required screenshot, supporting read-only receipt, cleanup requirement, and final `PASS`, `FAIL`, or `BLOCKED` state. Capture a numbered screenshot for every meaningful step and one continuous Crabbox outer-desktop video covering the cross-turn human workflow and browser-process restart; pause or obscure recording during password or secret entry.

The production run MUST prove, one feature at a time:

1. The public page is serving the intended deployed commit and current rulebook version.
2. DeepSeek A can propose, revise, or originate repeal of one focused idea but cannot vote; Kimi B audits A's latest add/repeal motion but cannot introduce an unrelated rule or originate repeal; one-open, settled, terminal, and malformed guards prevent unauthorized state change.
3. Ordinary encoder, decoder, Conversation, and Try It prompts contain the complete adopted set and no proposed, rejected, reverted, repealed, historical, pending-repeal, research, human, or visitor text, confirmed by an independent read-only receipt after the visible journey.
4. The cleanup workflow preserves the original, produces A's replacement, B's audit, and an exact diff, and stops visibly before application until Iso approves it.
5. RESEARCH preserves the original question, survives a restart or reload, returns cited evidence or an honest no-evidence state, reaches the correct agent exactly once, and never mutates language state directly.
6. ASK appears publicly as awaiting Iso, the correct and incorrect password paths behave safely, the authenticated session survives refresh and browser restart as designed, logout and session expiry work, private queues remain inaccessible publicly, and Iso's verbatim answer is correlated with the original question and delivered exactly once after a restart or reload.
7. A visitor suggestion appears directly below the agent windows, remains private before approval, handles approve/dismiss safely, survives restart or reload, publishes only when approved, and reaches agent context at most once as optional material.
8. The judged multi-turn Conversation completes through the visible surface and displays a concrete outcome judgment tied to the scenario requirements.
9. Try It visibly distinguishes a normal same-version journey, rulebook-version mismatch, exhausted monthly allowance, and unrelated provider failure.
10. The selective-collapse design, ASK states, suggestions, Conversation, and Try It complete on desktop and at 375px mobile width, not merely render without overflow.
11. README, MECHANICS, current page copy, and public labels match the behavior observed during the run; historical dumb-script evidence remains accessible while active dumb-script framing is absent.
12. Approved X actions show confirmed live results on the real profile: correction, single-post delivery, bounded retry/block behavior, explainer, pin, and approved follows. Provider receipts alone do not pass this row.

The run MUST also exercise hostile and failure inputs without expanding into a broad security program: wrong password, expired session, duplicate submission, rapid repeated requests, HTML/script text, prompt-injection language, provider timeout, missing research evidence, rulebook change during Try It, spending-cap exhaustion, and three failed X attempts. No input may execute, expose private moderation state, bypass approval, silently disappear, deliver twice, or become a rule automatically.

Historical integrity MUST be checked after the run: rejected/proposed/repealed history remains available, the last-ten average was not reset, pre-cleanup artifacts remain immutable, and no false posted/delivered status was introduced. Finish by removing disposable test data through the approved visible path and checking that no stuck queue item, duplicate post, unexplained dirty file, or silent health warning remains.

Run at most three complete repair-and-retest loops. Stop earlier if the same blocker survives two loops or if access, approval, production identity, or a required visible surface is unavailable. The only permitted final reports are `PASS`, `FAIL`, or `BLOCKED`; a visually correct page cannot override a failed state, delivery, security, persistence, or receipt row.

The implementation plan MUST include planned stops before:

1. Pausing or resuming the production loop.
2. Applying the cleaned rulebook.
3. Creating/changing production credentials, limits, or deployment secrets.
4. Deploying the public site or changing production behavior.
5. Publishing the correction or pinned explainer, pinning a post, or following accounts.
6. Merging or pushing to `main`.

## Implementation State Ledger

**Closeout Status**: Offline implementation PASS; current-deployment production acceptance FAIL (24 FAIL, 2 BLOCKED)

| Date | Current Implementation Pass | Official / Production Path State | Remaining Contract Gaps |
|------|-----------------------------|----------------------------------|-------------------------|
| 2026-07-20 | Specification and audit handoff only | Production unchanged; remote state observed at turn 537 | Clarify/plan/tasks, approvals, clean worktree, implementation, evidence, deploy/public gates |
| 2026-07-20 | Clean-worktree offline implementation passes 47 Python tests, 26 Node tests, 55-requirement coverage, API/HTML parse checks, state-hash preservation, diff/secret/bypass/privacy review, and Spec Kit convergence | Branch is local and unpushed; production state/site/loop/credentials/X are unchanged; every live DoD row is BLOCKED | Skeptical-review D1–D4 repairs approved for a second offline pass before T107; production gates remain unchanged |
| 2026-07-21 | D1–D4 corrected offline pass: 58 Python tests, 27 Node tests, 66-requirement coverage, desktop/375px local copy inspection, baseline-aware state preservation, and zero-gap Spec Kit convergence | Branch remains local and unpushed; read-only fetch observed remote generated state at turn 630; no production service, credential, loop, deployment, paid call, or X action changed | T107–T143; all 26 production acceptance rows remain BLOCKED |
| 2026-07-21 | Crabbox acceptance-infrastructure addendum drafted from official v0.40.0 source review; `$2` maximum new-infrastructure spend approved | No binary installed, account/credential created, coordinator deployed, lease provisioned, branch pushed, or production surface changed | Approve updated spec/plan/tasks; then T107–T117 before any production gate |
| 2026-07-21 | Crabbox v0.40.0 pilot PASS: reusable skill validated; remote fixture 26/26; one continuous 300-second outer MP4 visibly spans a browser-process restart; proof, cap, secret-audit, and teardown checks PASS | Draft branch/PR only; free workers.dev coordinator remains idle; zero leases/servers/SSH keys; product deployment, loop/state, credentials, X, and production acceptance unchanged | T118+ retain their exact immutable production/live gates; no full production acceptance result exists yet |
| 2026-07-21 | G4 snapshot PASS at production turn 650; timer paused and copied rulebook hash verified. First bounded DeepSeek cleanup output FAIL: exact adopted-source coverage validation rejected it; no Kimi call occurred | Production `main`, rulebook, deployment, credentials, and X remain unchanged; `language-loop.timer` is intentionally paused at the safe stop | T120 remains open; a new exact paid-call approval is required before any replacement attempt |
| 2026-07-21 | Second bounded DeepSeek cleanup output also FAIL: the minimal id/text-only request still omitted three required source ids; raw output and exact cost were preserved; no Kimi call occurred | Production remains clean, byte-identical, and paused at turn 650; cumulative G4 spend is `$0.012418691` | Prompt-only retries are retired. T144–T148 implement strict schema-required assignments and deterministic candidate compilation offline; T120 remains open and any later call requires a new exact phrase |
| 2026-07-21 | Third cleanup A PASS on strict exact coverage: all 23 source ids compiled exactly once. Kimi B then returned `REJECT` with one omission and five meaning-change findings; final validation stopped before bundle creation | Production remains clean, byte-identical, and paused at turn 650; actual cumulative G4 spend is `$0.019697541` (`$0.023336451` conservative) | T120 remains open. No retry, bundle, application, merge, deploy, loop resume, credential, DNS, or X action is authorized |
| 2026-07-21 | Approved Crabbox run against the current deployed site completed with 27 screenshots, a 120-second outer MP4, one browser restart, proof, spend, and teardown receipts | Overall FAIL: the old homepage returns 200 but `/human` returns 404; canonical matrix is 24 FAIL and 2 X-action BLOCKED. One CPX32 lease cost about `$0.01` and teardown verified zero active leases, servers, and matching SSH keys | Deploy and verify the reviewed feature through T121-T127 before a new full T128-T143 acceptance run; no production, loop, canonical state, or X action changed |
| 2026-07-22 | Offline acceptance-harness repair underway: external approval receipt required, failed matrix status propagated, browser foreground/pacing added, and optional WebVNC diagnostic corrected | The 2026-07-21 canonical product result remains FAIL; no production, provider, credential, deploy, loop, canonical-state, or X action changed | Complete T152 offline verification, then T120 and the existing serialized live gates still block deployment and a new production acceptance run |
| 2026-07-22 | Cleanup audit-rejection repair PASS offline: strict explicit exclusions now reconcile complete source accountability with removal of operational instructions/fragments; bound attempt-3 feedback is ready for one A revision | Production remains paused, clean, and unchanged; no provider call, bundle, credential, merge, deploy, loop resume, or X action occurred | Complete T156 verification, then obtain a new exact T120 paid-call approval for one feedback-bound DeepSeek revision and conditional Kimi audit |
| 2026-07-22 | Fourth cleanup A revision FAIL at local validation: the feedback-bound strict draft covered all 23 assignments but retained operational `rulebook` text in one active group; fail-closed validation stopped before candidate creation and the conditional Kimi call did not occur | Production remains clean, byte-identical, and paused at turn 650; actual cumulative G4 spend is `$0.021357557` (`$0.029000851` conservative) | T120 remains open. The single approved attempt is consumed; no retry, bundle, application, merge, deploy, loop resume, credential/configuration, DNS, Crabbox, or X action is authorized |
| 2026-07-22 | Preview acceptance checkpoint planned from a green offline baseline: 71 Python tests, 27 JavaScript tests, 6 acceptance-harness tests, and 78-requirement coverage | Target is an isolated Vercel Preview and one disposable Crabbox lease; production, `main`, loop/state, DNS, production credentials, and X remain excluded | T157-T166 require one exact preview approval envelope; cleanup/X/loop/canonical-state and production-only rows may remain `BLOCKED`, and a preview pass cannot close production DoD |
| 2026-07-22 | Isolated Preview acceptance partial: final permitted remote attempt passed rows 1–7, including browser restart and real Try It; local follow-up suite passes 7 harness, 28 JavaScript, 71 Python, and 78-requirement coverage | Preview `dpl_F4hbURLyYz6n6AfXV8CG7F9Xd2jA` is Ready; production `dpl_6rrcd4YdGMTYkcUdEUsCQan7qQCS` remains unchanged. Preview data and the CPX32 lease were cleaned; post-release coordinator/provider reads show zero live resources and estimated infrastructure spend `$0.05` | Preview checkpoint FAIL: row 8 used an invalid body-text assertion (repaired locally but not rerun), rows 9–12 are unrun, and the required outer MP4 did not flush. The approved three-run envelope is exhausted; a new exact approval is required before a further remote run. Production gaps remain unchanged. |
| 2026-07-22 | Separately approved Preview follow-up: rows 1–8 passed through the visible browser; the outer recording is a valid 180-second MP4; the local suite remains 7 harness, 28 JavaScript, 71 Python, and 78-requirement coverage | Production `dpl_6rrcd4YdGMTYkcUdEUsCQan7qQCS` remains unchanged. Follow-up Preview data deleted 13 keys; post-release coordinator/provider reads show zero live resources and `$0.06` cumulative estimated infrastructure spend | Preview checkpoint remains FAIL: row 9 used an invalid `#cast` assertion scope (corrected locally but not rerun); rows 10–12 are unrun. The follow-up one-run approval is consumed. Production gaps remain unchanged. |
| 2026-07-23 | Final separately approved Preview acceptance PASS: local actual-viewer preflight passed; the non-fail-fast remote matrix passed all 12 required rows; 23 numbered screenshots, proof bundle, and inspected 180.000-second cross-restart outer MP4 were captured | Isolated Preview `dpl_F4hbURLyYz6n6AfXV8CG7F9Xd2jA` remains Ready; Preview cleanup deleted 12 keys with zero remaining; released CPX32 server returns 404; coordinator has zero active leases and reports `$0.07` cumulative estimated infrastructure spend | Preview is review-ready on draft PR #1 only. No merge, `main`, Production deploy/alias/routing/credential change, canonical-state application, loop resume, or publication occurred; all Production gates remain planned stops. |
| 2026-07-23 | Explicitly approved Production release: draft PR #1 merged at `0cc16b5`; the corrected `viewer/` deployment is public at `alanguagealltheirown.com`; Crabbox recorded a 180-second, one-restart non-mutating Production inspection | Public `/` and `/human` are HTTP 200. The 26-row inspection is 18/26 PASS: public routes/surfaces render, while loop-dependent cleanup/RESEARCH/ASK, failure-state, and X rows remain inactive. Lease cleanup verified zero resources and `$0.08` cumulative coordinator estimate | Production is publicly reachable, but this is not full Production acceptance. T120 and the active-loop/canonical-state/X gates remain open; no application credential, canonical-state, loop, or X action occurred. |
| 2026-07-24 | Iso explicitly changed the launch sequence: activate the repaired core runtime with the existing rulebook unchanged, configure the missing Production dependencies, keep X disabled, and verify one real turn | Exact approval `launch-alato-core-with-existing-rulebook-20260724-l4v8` authorizes the bounded launch-first activation; cleanup generation/application and X remain deferred | Complete T168–T176. Full cleanup and X acceptance remain separate optional/public gates and do not block the core-live result. |
