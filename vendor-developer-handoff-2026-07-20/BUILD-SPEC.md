# Feature Specification: Experiment Repair and Public Collaboration

**Feature Branch**: Planned `codex/experiment-repair` (not created during specification)

**Created**: 2026-07-20 WITA

**Status**: Draft — ready for planning; implementation requires Iso's approval of spec, plan, and tasks

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
| [OpenRouter key limits](https://openrouter.ai/docs/api/api-reference/api-keys/create-keys) | Official documentation | Public Try It spend boundary | A dedicated key can enforce a monthly USD limit | Aligned |
| [Upload-Post text API](https://docs.upload-post.com/api/upload-text/) | Official documentation | X confirmation, idempotency, and threading | Use confirmed results and stable idempotency; do not rely on automatic threading | Aligned |
| [NVIDIA NIM FAQ](https://docs.api.nvidia.com/nim/docs/product) | Official documentation | Considered free public inference alternative | Free developer endpoints are for prototyping/testing, not public end-user production | Rejected for public Try It |

**Ignored / Outdated Sources**: `PRD-remove-caps.md` is historical and unrelated to this repair. The old dumb-script benchmark, Slack ASK bridge, `:online` research suffix, standalone Composition exam, power-grid framing, and broad novelty/growth claims are superseded. Historical records containing them remain untouched.

**Open Documentation Conflicts**: None. The local audited checkout is `820ae90`; remote `main` was verified at `5551f6f` (turn 537) and is 13 state-only commits ahead. Implementation must begin from a clean worktree based on current remote `main`, then recheck state before editing.

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

### Edge Cases

- A status changes while an exam or Try It request is in progress.
- An agent issues multiple motions, a forbidden role motion, a no-op motion, or a malformed reference.
- The cleanup output omits an adopted rule, silently changes meaning, or contains operational instructions disguised as language law.
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

- **FR-001**: The system MUST maintain one canonical rule ledger with explicit adopted, proposed, rejected, and historical/superseded states.
- **FR-002**: Ordinary encoding, decoding, Try It, and Conversation use MUST receive only the adopted rule set.
- **FR-003**: A proposed rule MUST enter an exam only through an explicitly labeled proposal-specific trial.
- **FR-004**: Rejected and superseded material MUST remain available to the legislature and public history without affecting language use.
- **FR-005**: Corpus exam results MUST be presented as corpus-level evidence and MUST NOT imply individual rule attribution without a proposal-specific trial.
- **FR-006**: The active dumb-script comparison MUST be removed from runtime measurement, prompts, economics, and current public surfaces while its historical record remains intact.
- **FR-007**: Agent A MUST use DeepSeek as the inventor and may propose, revise, or measure at most one focused idea per turn, but MUST NOT vote.
- **FR-008**: Agent B MUST use Kimi as the auditor and may critique, adopt, reject, or request a focused revision/test, but MUST NOT introduce an unrelated rule.
- **FR-009**: Forbidden role actions and repeated settled motions MUST NOT change state, history, or public revision counts.
- **FR-010**: Both agents MUST share a concise constitution containing the stranger-decodability requirement, measurement discipline, public-history commitment, 50% target, and affordability/access mission.
- **FR-011**: The shared constitution MUST NOT contain active dumb-script framing, power-grid/gigawatt claims, or unsupported novelty/traffic-growth claims.
- **FR-012**: The normal loop MUST be paused and the current rulebook preserved before the one-time cleanup pass.
- **FR-013**: DeepSeek A MUST author one cleaned active rulebook and Kimi B MUST audit it; Iso MUST receive an exact diff before any application.
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

### Scope and Non-Goals

- No product-code implementation occurs during specification/handoff work.
- No live-loop turn, paid test, production state repair, deploy, push, X action, follow, pin, credential change, or billing change is authorized by this specification alone.
- No database-backed rate limiter, snapshot/version database, general authentication framework, Slack bridge, automatic visitor-to-agent injection, second judge, judge retry system, or permanent governance verb expansion is in scope.
- No new dumb-script or competitor baseline is introduced.
- No manual human rewriting of language rules is allowed; humans shape the experiment and curate context, while agents author and adopt language law.
- Directive overuse, shorthand conflicts, and token-aware substitution are language questions for the agent cleanup/evolution process, not separate software features.

### Key Entities

- **Rule Record**: Stable rule identity, canonical text, status, provenance, history, and applicable corpus/proposal-specific evidence.
- **Rulebook Snapshot**: Immutable pre-cleanup artifact or identifiable adopted-language version used for a specific journey.
- **Exam Event**: Payload, rulebook version, encoded/decoded material, answer key, complete judge verdicts, fidelity validity, and corpus-level savings.
- **Research Request**: Stable id, requester/turn, original question, lifecycle status, cited result, limitations, sources, cost/error metadata, and delivery turn.
- **Human Ask**: Stable id, requester/turn, original question, awaiting/answered state, Iso's verbatim answer, and delivery history.
- **Visitor Suggestion**: Stable id, submitted text, moderation state, approval/delivery state, and public outcome where approved.
- **Conversation Artifact**: Scenario, adopted rulebook version, alternating messages, models, total usage, and outcome judgment.
- **Try It Journey**: Encode/decode correlation, rulebook version, allowance/provider state, and visible result.
- **Public Delivery Record**: Field note identity, platform, attempt count, idempotency identity, confirmation id, posted/blocked state, and error receipt.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In a status-fixture battery, 100% of ordinary exam/Conversation/Try It prompts contain every adopted rule and zero proposed, rejected, or reverted rule text.
- **SC-002**: Searches of current runtime, prompt, economics, and public-page output find zero active dumb-script comparison claims while historical records remain accessible.
- **SC-003**: Synthetic role tests show zero state changes from A votes, B unrelated proposals, repeated settled motions, or malformed/no-op actions.
- **SC-004**: Cleanup produces an immutable pre-cleanup artifact, A's replacement, B's audit, and an exact human-readable diff; production remains unchanged until an approval receipt exists.
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

## Assumptions

- Implementation begins from a clean worktree based on current `origin/main`, not the stale audited checkout.
- The loop remains live and state may continue advancing until an approved implementation gate deliberately pauses it.
- DeepSeek v3.2 remains available for inventor/encoder/judge duties and Kimi remains available for auditor/stranger duties; planning must verify exact current provider slugs before tasks.
- The existing public site and deployment path remain the delivery surface; planning must verify current project linkage, credentials, and runtime before implementation.
- The `/human` password is a single project-admin secret remembered by the browser and stored only in the deployment environment; reasonable brute-force and session protections may be added without creating an account system.
- Public suggestion volume is initially low; moderation, not autonomous content filtering, is the authority boundary.
- Old exam, dumb-script, field-note, and rulebook artifacts remain append-only history even when their current presentation is retired or corrected.
- The $20 public inference allowance is a hard monthly boundary, not a spending target.
- The pinned X explainer, correction, follows, credential/cap changes, deployment, loop pause/resume, and cleaned-rulebook application are separate live/public/account actions requiring the workspace's exact approvals at their implementation gates.

## Definition of Done and Planned Stops

The feature is complete only when all P1–P3 journeys and success criteria pass, the implementation-state ledger is current, evidence is attached to tasks, and the intended branch is committed with no unexplained dirty files. Production acceptance additionally requires verified live page journeys and approved X/account actions.

### Required Production Acceptance Test

The final test MUST be performed through the real deployed user-visible surfaces. Backend tests, logs, API receipts, or source inspection may independently confirm the result after a visible action, but cannot substitute for the human journey. Before testing, record the deployed commit, environment, public URL, current rulebook version, available sessions/permissions, test data, cleanup path, and every approval boundary.

Create an evidence matrix before the run with one row per feature or failure state. Every row MUST name the visible action, expected visible result, required screenshot, supporting read-only receipt, cleanup requirement, and final `PASS`, `FAIL`, or `BLOCKED` state. Capture a numbered screenshot for every meaningful step and one continuous video covering the cross-turn human workflow; pause or obscure recording during password or secret entry.

The production run MUST prove, one feature at a time:

1. The public page is serving the intended deployed commit and current rulebook version.
2. DeepSeek A can propose or revise one focused idea but cannot vote; Kimi B audits A's latest idea but cannot introduce an unrelated rule; settled or malformed motions cannot change state.
3. Ordinary encoder, decoder, Conversation, and Try It prompts contain the complete adopted set and no proposed, rejected, reverted, research, human, or visitor text, confirmed by an independent read-only receipt after the visible journey.
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

Historical integrity MUST be checked after the run: rejected/proposed history remains available, the last-ten average was not reset, pre-cleanup artifacts remain immutable, and no false posted/delivered status was introduced. Finish by removing disposable test data through the approved visible path and checking that no stuck queue item, duplicate post, unexplained dirty file, or silent health warning remains.

Run at most three complete repair-and-retest loops. Stop earlier if the same blocker survives two loops or if access, approval, production identity, or a required visible surface is unavailable. The only permitted final reports are `PASS`, `FAIL`, or `BLOCKED`; a visually correct page cannot override a failed state, delivery, security, persistence, or receipt row.

The implementation plan MUST include planned stops before:

1. Pausing or resuming the production loop.
2. Applying the cleaned rulebook.
3. Creating/changing production credentials, limits, or deployment secrets.
4. Deploying the public site or changing production behavior.
5. Publishing the correction or pinned explainer, pinning a post, or following accounts.
6. Merging or pushing to `main`.

## Implementation State Ledger

**Closeout Status**: Not started

| Date | Current Implementation Pass | Official / Production Path State | Remaining Contract Gaps |
|------|-----------------------------|----------------------------------|-------------------------|
| 2026-07-20 | Specification and audit handoff only | Production unchanged; remote state observed at turn 537 | Clarify/plan/tasks, approvals, clean worktree, implementation, evidence, deploy/public gates |
