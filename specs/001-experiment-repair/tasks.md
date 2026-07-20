# Tasks: Experiment Repair and Public Collaboration

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/http-and-runtime.md`, and `quickstart.md`

**Approval state**: Planning only. Do not execute T001 or later until Iso approves
this implementation contract. Every live/public task contains its own additional
stop; implementation approval does not grant those stops.

## Phase 1: Approved Setup and Preservation

**Purpose**: Start from current reality without touching the dirty planning checkout.

- [X] T001 Re-run `git ls-remote`, fetch current `origin/main`, record branch/upstream/divergence, and write the exact implementation baseline to `specs/001-experiment-repair/evidence/preflight.md`
- [X] T002 Create `/Users/isorabins/alex-workspace-worktrees/experiment-repair` on `codex/experiment-repair` from the verified remote commit and record clean status in `specs/001-experiment-repair/evidence/preflight.md`
- [X] T003 Copy only the approved `.specify/`, `specs/001-experiment-repair/`, `vendor-developer-handoff-2026-07-20/`, and project `AGENTS.md` artifacts into the feature worktree while preserving the dirty source checkout; record source/destination hashes in `specs/001-experiment-repair/evidence/preservation.md`
- [X] T004 Record the modified source-checkout `PROGRESS.md` and all unrelated dirty/untracked files as preserved user work in `specs/001-experiment-repair/evidence/preservation.md`
- [X] T005 Verify every repo and official source in `plan.md` is reachable/current and record any changed API behavior or planned stop in `specs/001-experiment-repair/evidence/documentation-context.md`
- [X] T006 Create the full dependency/approval/rollback/evidence runway matrix from `plan.md` in `specs/001-experiment-repair/evidence/runway-preflight.md`
- [X] T007 Commit only the approved planning and preservation artifacts on `codex/experiment-repair` and record the commit in `specs/001-experiment-repair/evidence/progress.md`

**Checkpoint**: Clean feature worktree exists; original dirty checkout is unchanged.

---

## Phase 2: Foundational Test and State Boundaries

**Purpose**: Build reusable fixture/evidence boundaries before story code.

- [X] T008 [P] Create mixed-status, malformed-judge, collaboration, timeout, cap, and X response fixtures in `tests/fixtures/`
- [X] T009 [P] Create a deterministic local HTTP stub for OpenRouter, Upstash, and Upload-Post responses in `tests/support/stub_server.py`
- [X] T010 Write failing atomic JSON write/restart tests in `tests/python/test_state_store.py`
- [X] T011 Implement temp-write/fsync/rename canonical JSON persistence and immutable snapshot hashing in `state_store.py`
- [X] T012 [P] Create cross-artifact FR/SC/task coverage validation in `tests/acceptance/check_contract_coverage.py`
- [X] T013 Run the foundational tests, inspect the diff, update `specs/001-experiment-repair/evidence/progress.md`, and commit the scoped foundation checkpoint

**Checkpoint**: Tests cannot mutate production paths and canonical fixture writes survive restart.

---

## Phase 3: User Story 1 - Trust the Experiment (Priority: P1)

**Goal**: Only adopted rules govern ordinary language use; invalid judge output cannot publish a score.

**Independent Test**: A frozen mixed-status fixture proves adopted-only prompts,
explicit proposal trials, corpus-only evidence, preserved history, and exact judge coverage.

- [X] T014 [P] [US1] Write failing adopted/language/legislature/proposal-trial view tests for FR-001–004 and SC-001 in `tests/python/test_rulebook_views.py`
- [X] T015 [P] [US1] Write failing corpus-vs-proposal evidence tests for FR-003–005 in `tests/python/test_exam_evidence.py`
- [X] T016 [P] [US1] Write failing complete/missing/duplicate/nonnumeric/out-of-range judge tests for FR-015 and SC-005 in `tests/python/test_judge_validation.py`
- [X] T017 [P] [US1] Write equivalent Vercel adopted-only and judge contract tests in `tests/js/rulebook-and-judge.test.js`
- [X] T018 [US1] Implement deterministic legislature, language, and single-proposal trial views plus version/hash generation in `rulebook.py`
- [X] T019 [US1] Implement exact answer-key coverage validation returning invalid/no-score on any malformed coverage in `rulebook.py`
- [X] T020 [US1] Replace ordinary loop encoder/decoder rulebook construction with the adopted language view and write corpus-level evidence only in `loop.py`
- [X] T021 [US1] Preserve legacy per-rule scores/history as labeled historical data while preventing new corpus score stamping in `loop.py` and `viewer/index.html`
- [X] T022 [US1] Port the same adopted-only version/hash and judge validator contract to `viewer/api/_lib.js` and `viewer/api/judge.js`
- [X] T023 [US1] Remove the active dumb-script import, prompt/economics/control event path, and `probe.py` run hook while retaining historical files/records in `loop.py`, `run_turn.sh`, and `viewer/index.html` (FR-006; SC-002)
- [X] T024 [US1] Run US1 tests and active-reference searches, attach captured prompt/state receipts to `specs/001-experiment-repair/evidence/us1-trust.md`, and verify the last-ten passing-exam calculation is unchanged (FR-038; SC-015)
- [X] T025 [US1] Inspect and commit the scoped US1 checkpoint with no production state files modified

**Checkpoint**: The experiment can truthfully say which rules were tested.

---

## Phase 4: User Story 2 - Observe Genuine Legislative Tension (Priority: P1)

**Goal**: DeepSeek A invents and Kimi B audits under enforced, non-overlapping permissions.

**Independent Test**: Synthetic allowed/forbidden motions show only one valid
focused action can mutate state and every no-op has a reason receipt.

- [X] T026 [P] [US2] Write failing A-vote, B-unrelated-proposal, repeated-settled, malformed-id, no-op, and multi-motion tests for FR-007–009 and SC-003 in `tests/python/test_motion_authority.py`
- [X] T027 [P] [US2] Write prompt contract tests for the shared constitution, 50% target, affordability mission, and forbidden framing in `tests/python/test_prompt_contract.py`
- [X] T028 [US2] Create the concise shared stranger/measurement/history/50%-target/access constitution with no dumb-script, power-grid, novelty, or traffic-growth claims in `prompts/constitution.md` (FR-010–011)
- [X] T029 [US2] Rewrite the inventor contract to one propose/revise/measure action and no votes in `prompts/agent_a.md`
- [X] T030 [US2] Rewrite the Kimi auditor contract to audit A's focused idea, vote/request focused work, and never originate unrelated rules in `prompts/agent_b.md`
- [X] T031 [US2] Set `MODEL_B` to verified `moonshotai/kimi-k2.6` while retaining the separate stateless Kimi decoder in `loop.py`
- [X] T032 [US2] Implement role/state/one-motion authority validation and reason-coded no-op receipts in `rulebook.py` and integrate it into `loop.py`
- [X] T033 [US2] Render accepted and rejected legislative action honestly without inflating revision counts in `viewer/index.html`
- [X] T034 [US2] Run US2 tests, inspect representative transcripts/no-op state diffs, attach `specs/001-experiment-repair/evidence/us2-roles.md`, and commit the scoped checkpoint

**Checkpoint**: Role differences are code-enforced rather than prompt theater.

---

## Phase 5: User Story 3 - Repair the Rulebook Without Rewriting History (Priority: P1)

**Goal**: Produce a one-time A-authored/B-audited cleanup bundle that cannot apply itself.

**Independent Test**: A copied fixture yields immutable original, replacement,
audit, manifest, and exact diff; source state remains byte-identical without approval.

- [X] T035 [P] [US3] Write failing snapshot/hash/source-mismatch/no-auto-apply tests for FR-012–014 and SC-004 in `tests/python/test_cleanup_rulebook.py`
- [X] T036 [P] [US3] Create cleanup fixtures containing duplicate, contradictory, incomplete, historical, and disguised-operational rules in `tests/fixtures/cleanup/`
- [X] T037 [US3] Create the bounded DeepSeek cleanup contract in `prompts/cleanup_a.md`
- [X] T038 [US3] Create the bounded Kimi audit contract in `prompts/cleanup_b.md`
- [X] T039 [US3] Implement snapshot-only cleanup bundle generation with explicit source/output paths and no production default in `cleanup_rulebook.py`
- [X] T040 [US3] Implement exact diff/manifest hashes and reject omitted adopted meaning or operational text in `cleanup_rulebook.py`
- [X] T041 [US3] Implement a separate apply subcommand requiring matching source/replacement hashes and an approval-receipt file in `cleanup_rulebook.py`
- [X] T042 [US3] Run the cleanup suite only with stubbed model outputs, prove production files unchanged, and attach `specs/001-experiment-repair/evidence/us3-cleanup-offline.md`
- [X] T043 [US3] Inspect and commit the scoped cleanup checkpoint without running paid calls or pausing the loop

**Checkpoint**: Cleanup mechanics are safe offline; live generation/application still stop at G4/G8.

---

## Phase 6: User Story 4 - Use the Language in a Judged Conversation (Priority: P2)

**Goal**: Preserve a six-message DeepSeek/Kimi native-use artifact and concrete outcome judgment.

**Independent Test**: A fixed scenario produces six alternating messages using
one adopted snapshot and a requirement-level verdict without rule/average mutation.

- [X] T044 [P] [US4] Write failing adopted-only, six-message alternation, judgment, persistence, and no-ledger/no-average-mutation tests for FR-025–026 and SC-008 in `tests/python/test_conversation_exam.py`
- [X] T045 [P] [US4] Create deterministic real-work scenario and judgment fixtures in `tests/fixtures/conversation/`
- [X] T046 [US4] Create speaker and concrete-outcome judge contracts in `prompts/conversation.md` and `prompts/conversation_judge.md`
- [X] T047 [US4] Implement the captured-snapshot six-message artifact and requirement-level judgment in `conversation_exam.py`
- [X] T048 [US4] Schedule Conversation once per 32 completed ordinary exams without changing ordinary exam cadence/average in `loop.py`
- [X] T049 [US4] Publish full Conversation artifacts and visible concrete judgments in `viewer/state.js` generation and `viewer/index.html`
- [X] T050 [US4] Run US4 tests including restart/persistence and attach `specs/001-experiment-repair/evidence/us4-conversation.md`
- [X] T051 [US4] Inspect and commit the scoped Conversation checkpoint without real provider calls

**Checkpoint**: Conversation is independently testable and Composition remains absent.

---

## Phase 7: User Story 5 - Ask for Evidence and Human Judgment (Priority: P2)

**Goal**: Durable non-blocking RESEARCH and ASK with exact question/answer correlation and a minimal `/human` lifecycle.

**Independent Test**: Requests survive process/browser restart, reach the correct
requester once, never enter motion parsing, and private queues reject unauthenticated access.

- [X] T052 [P] [US5] Write failing Redis REST enqueue/claim/lease/ack/idempotency/restart/concurrency tests in `tests/python/test_collaboration_inbox.py`
- [X] T053 [P] [US5] Write failing Vercel inbox/session/private-access/idempotency contract tests in `tests/js/collaboration-api.test.js`
- [X] T054 [P] [US5] Write failing RESEARCH oldest-one-per-turn, cited/no-evidence, requester-only, restart, and no-rule-mutation tests for FR-016–018 and SC-006 in `tests/python/test_research_lifecycle.py`
- [X] T055 [P] [US5] Write failing ASK unanswered/duplicate/closed-id/verbatim/exact-once/restart tests for FR-019–021 and SC-006 in `tests/python/test_ask_lifecycle.py`
- [X] T056 [P] [US5] Write failing wrong-password, cookie, refresh, browser-restart, 30-minute non-sliding expiry, logout, and private-queue tests for FR-020 in `tests/js/human-session.test.js`
- [X] T057 [US5] Implement namespaced Upstash REST atomic enqueue/claim/lease/ack/session primitives in `collaboration.py`
- [X] T058 [US5] Implement canonical `state/collaboration.json` schema, processed-id dedupe, safe reconciliation, and public sanitization in `collaboration.py` and `loop.py`
- [X] T059 [US5] Implement the matching server-only Vercel Redis/session client with no browser token exposure in `viewer/api/_collaboration.js`
- [X] T060 [US5] Create the bounded untrusted-evidence web-search contract in `prompts/research.md`
- [X] T061 [US5] Parse, persist, answer at most one oldest RESEARCH request, store citations/limitations/errors, and deliver original question+result to its requester only in `loop.py`
- [X] T062 [US5] Parse and persist ASK without blocking or auto-answering, reconcile human answers, and deliver original question+verbatim answer exactly once in `loop.py`
- [X] T063 [US5] Implement login/session-check/logout with opaque Redis sessions and secure persistent cookies in `viewer/api/human-session.js`
- [X] T064 [US5] Implement authenticated private ASK/suggestion reads plus read-only pending cleanup bundle/diff reads in `viewer/api/human-inbox.js`
- [X] T065 [US5] Implement idempotent ASK answer and moderation command validation in `viewer/api/human-action.js`
- [X] T066 [US5] Build the login, private inbox, read-only cleanup review/diff, answer, refresh, 30-minute expiry, and logout journeys without accounts/OAuth in `viewer/human.html` and route `/human` in `viewer/vercel.json`
- [X] T067 [US5] Render public ASK awaiting/answered/delivered states and RESEARCH citations/limitations from canonical state in `viewer/index.html`
- [X] T068 [US5] Run US5 tests and hostile text/private-access checks, attach `specs/001-experiment-repair/evidence/us5-research-ask.md`, inspect, and commit the scoped checkpoint

**Checkpoint**: Human collaboration works in production-shaped fixtures; Redis/session creation remains G5.

---

## Phase 8: User Story 6 - Contribute a Moderated Visitor Suggestion (Priority: P2)

**Goal**: Suggestions are prominent but private until Iso approves, then delivered once as optional context.

**Independent Test**: Pending/dismissed text appears in zero public/agent surfaces;
one approved id is published and delivered at most once after restart.

- [X] T069 [P] [US6] Write failing submit/duplicate/approve/dismiss/restart/optional-once/private-output tests for FR-022–024 and SC-007 in `tests/js/suggestion-api.test.js` and `tests/python/test_suggestion_lifecycle.py`
- [X] T070 [P] [US6] Add HTML/script, prompt-injection, secret-like text, rapid repeat, and oversized suggestion fixtures in `tests/fixtures/suggestions/`
- [X] T071 [US6] Implement length-bounded idempotent public suggestion enqueue with inert text handling in `viewer/api/suggestion.js`
- [X] T072 [US6] Place the suggestion form directly beneath the agent windows with honest pending-review copy in `viewer/index.html`
- [X] T073 [US6] Add approve/dismiss actions and durable status feedback to the private moderation UI in `viewer/human.html`
- [X] T074 [US6] Reconcile only approved suggestions into canonical state and keep pending/dismissed text private in `collaboration.py` and `loop.py`
- [X] T075 [US6] Deliver at most one approved suggestion as delimited optional context outside motion parsing and record action/non-action outcome in `loop.py`
- [X] T076 [US6] Render only approved/delivered/outcome suggestion lifecycle records publicly in `viewer/index.html`
- [X] T077 [US6] Run restart/concurrency/hostile-output/private-surface tests and attach `specs/001-experiment-repair/evidence/us6-suggestions.md`
- [X] T078 [US6] Inspect and commit the scoped suggestion checkpoint

**Checkpoint**: Audience input cannot become law or bypass moderation.

---

## Phase 9: User Story 7 - Try the Language Safely (Priority: P2)

**Goal**: One-version encode/decode journey with a separate $20 public boundary and truthful errors.

**Independent Test**: Normal, forced-version-change, monthly-cap, unrelated
provider error, restart, and private-key-rejection fixtures have distinct results.

- [X] T079 [P] [US7] Write failing same-version/mismatch/cap/provider-error/cold-start tests for FR-027–029 and SC-009 in `tests/js/try-it.test.js`
- [X] T080 [P] [US7] Write failing configuration tests that reject private-key fallback and require the separate public key name in `tests/js/public-key-boundary.test.js`
- [X] T081 [US7] Make encode use the adopted language view and return rulebook version/hash without client rule text in `viewer/api/encode.js`
- [X] T082 [US7] Make decode refetch canonical state and return `409 rulebook_changed` before a model call on version/hash mismatch in `viewer/api/decode.js`
- [X] T083 [US7] Route all Try It provider calls exclusively through `OPENROUTER_PUBLIC_API_KEY` in `viewer/api/_lib.js`
- [X] T084 [US7] Classify verified key-limit exhaustion as `allowance_exhausted` and all unrelated provider/network/auth failures separately in `viewer/api/_lib.js`, `encode.js`, `decode.js`, and `judge.js`
- [X] T085 [US7] Update the Try It client to carry version/hash and show distinct normal, re-encode, reopening, and provider-failure states in `viewer/index.html`
- [X] T086 [US7] Run production-shaped handler tests without paid calls and attach `specs/001-experiment-repair/evidence/us7-try-it.md`
- [X] T087 [US7] Inspect and commit the scoped Try It checkpoint; leave real key/cap/WAF work open for G5

**Checkpoint**: Public inference code is safe; no production key/config was created.

---

## Phase 10: User Story 8 - Read an Honest, Focused Public Record (Priority: P3)

**Goal**: Focused desktop/mobile public record, accurate docs, and confirmed bounded X delivery.

**Independent Test**: UI fixtures prove selective disclosure and truthful labels;
X simulations prove no false posted state, duplicate, implicit thread, or frozen later note.

- [X] T088 [P] [US8] Write failing dry/non-2xx/timeout-before/timeout-after/async/partial/idempotency/three-failure/later-note/length tests for FR-033–035 and SC-012 in `tests/python/test_tweet_delivery.py`
- [X] T089 [P] [US8] Write desktop/375px selective-disclosure and collaboration layout tests for FR-030 and SC-011 in `tests/js/public-page.test.js`
- [X] T090 [US8] Persist stable Upload-Post request/idempotency ids before attempts and confirm synchronous/asynchronous X receipts before posted state in `tweet.py`
- [X] T091 [US8] Enforce `x_title`, X-only platform, copy length at most 250, no implicit thread fields, three attempts then blocked, visible blocked count, and later-note continuation in `tweet.py`
- [X] T092 [US8] Ensure dry runs/failures do not move note watermarks or successful-post budget in `tweet.py`
- [X] T093 [US8] Keep newest/decision-relevant agent, exam, ASK, suggestion, Conversation, and X status open while collapsing repetitive history/reference sections in `viewer/index.html`
- [X] T094 [US8] Remove stale active dumb-script, role, experiment-status, and unsupported novelty/power/growth claims while preserving labeled history in `viewer/index.html`
- [X] T095 [US8] Prepare but do not publish the exact field-note correction draft and original-reference receipt in `specs/001-experiment-repair/evidence/x-correction-draft.md` (FR-032; SC-014)
- [X] T096 [US8] Prepare but do not publish one <=250-character X explainer and pin target in `specs/001-experiment-repair/evidence/x-explainer-draft.md` (FR-036; SC-014)
- [X] T097 [US8] Research and record a small candidate follow list with primary-source reasons but perform no follows in `specs/001-experiment-repair/evidence/x-follow-draft.md` (FR-037; SC-014)
- [X] T098 [US8] Verify the hypothetical cached economics scenario remains labeled and unchanged with no new measurement subsystem in `loop.py` and `viewer/index.html` (FR-039)
- [X] T099 [US8] After the implemented behavior passes offline verification, update current boundaries/models/exams/collaboration/cost/deploy/interventions in `README.md` and `MECHANICS.md` (FR-031; SC-013)
- [X] T100 [US8] Run US8 tests and stale-claim searches, attach `specs/001-experiment-repair/evidence/us8-public-record.md`, and verify Composition/Slack ASK/`:online` remain absent
- [X] T101 [US8] Inspect and commit the scoped public-record/X checkpoint without deploy or X actions

**Checkpoint**: Full contract is implemented and verified offline; production remains unchanged.

---

## Phase 11: Full Offline Review and Durable Feature Checkpoint

- [X] T102 Run every Python/Node/coverage test from `quickstart.md`, verify tests fail against the old baseline where meaningful, and save exact outputs in `specs/001-experiment-repair/evidence/offline-suite.md`
- [X] T103 Inspect the full diff for secret leakage, production state changes, stale bypasses, out-of-contract files, and user-work overlap; record findings in `specs/001-experiment-repair/evidence/offline-review.md`
- [X] T104 Re-fetch current official docs/model slugs and record any behavior drift or safe planned stop in `specs/001-experiment-repair/evidence/documentation-context.md`
- [X] T105 Run Spec Kit convergence for the offline pass and update the Implementation State Ledger in `specs/001-experiment-repair/spec.md` plus remaining production tasks in `specs/001-experiment-repair/tasks.md`
- [X] T106 Commit the complete offline implementation/evidence checkpoint locally and STOP for review before feature-branch push, PR, production, paid calls, credentials, or live actions

---

## Phase 12: Approval-Gated Production Preparation and Cutover

Every STOP below requires the exact immutable targets and one-time approval phrase
defined in `plan.md`. No earlier approval carries forward.

- [ ] T107 STOP and obtain approval to push `codex/experiment-repair` and open/update its review PR; then push only the reviewed feature commit and record branch/PR state in `specs/001-experiment-repair/evidence/production-gates.md`
- [ ] T108 Recheck live VPS/main/turn/timer/deploy state read-only and refresh rollback values in `specs/001-experiment-repair/evidence/runway-preflight.md`
- [ ] T109 STOP for G4 phrase, then pause `language-loop.timer`, verify it is inactive, fetch the final state commit, and create immutable state/commit/service receipts in `specs/001-experiment-repair/evidence/cleanup-live/manifest.md`
- [ ] T110 With the approved paid scratch-call cap, run one DeepSeek A cleanup and one Kimi B audit against only the copied snapshot; save original/replacement/audit/diff/hashes under `specs/001-experiment-repair/evidence/cleanup-live/` and verify production state is unchanged
- [ ] T111 STOP for G5 phrase; then create/link the single Upstash database, human session/password secrets, separate `$20` monthly-reset OpenRouter public key, and approved Vercel WAF rules without printing values; record names/metadata/connectivity in `specs/001-experiment-repair/evidence/credentials.md`
- [ ] T112 Verify the public and private OpenRouter key identities differ, the public limit/reset metadata is exact (SC-010), and all required environments/services/rollback assets pass the production-equivalence table in `specs/001-experiment-repair/evidence/production-equivalence.md`
- [ ] T113 Rebase the reviewed feature commit and pending cleanup bundle onto the now-paused current `origin/main` without applying the replacement, rerun the full offline suite, inspect the final state/code diff, and update `specs/001-experiment-repair/evidence/offline-suite.md`
- [ ] T114 STOP for G6 phrase naming the final SHA/bundle; then push/merge that reviewed commit to `main` while the loop stays paused and the old rulebook remains active; verify remote `main` exactly in `specs/001-experiment-repair/evidence/production-gates.md`
- [ ] T115 STOP for G7 phrase naming the final SHA and rollback deployment; then deploy `viewer/`, open the production URL, verify the deployed commit/version and every static/function route, and record `specs/001-experiment-repair/evidence/deployment.md`
- [ ] T116 Open deployed `/human`, visibly verify the original/A replacement/B audit/exact diff and `pending Iso` stop while the active rulebook hash is unchanged, then STOP for G8 phrase naming the exact bundle/hashes; apply only that reviewed replacement, verify preserved history/exact diff, push only the approved state receipt, and record `specs/001-experiment-repair/evidence/cleanup-live/application.md`
- [ ] T117 STOP for G9 phrase naming the SHA/snapshot; then resume the timer, observe one bounded production turn, and pause immediately on any invariant, duplicate, queue, provider, or health warning; record `specs/001-experiment-repair/evidence/loop-health.md`

**Checkpoint**: Core code/state/site are live only if every preceding gate passed.

---

## Phase 13: Required Production Acceptance and Public Actions

- [ ] T118 Complete the deployed-commit/access/session/test-data/failure-control/rollback/cleanup preflight, create one PASS/FAIL/BLOCKED row per feature/failure in `specs/001-experiment-repair/evidence/production-acceptance/matrix.md`, then STOP for G10 exact approval naming the bounded paid test budget, natural scheduled turns, temporary production failure-mode configuration/key swaps, test ids, and cleanup
- [ ] T119 Obtain an exclusive visible-desktop recording window, create the numbered screenshot plan, and start `specs/001-experiment-repair/evidence/production-acceptance/00-cross-turn-workflow.mp4` before the first visible action
- [ ] T120 Drive the deployed commit/version, A/B allowed and forbidden role behavior, adopted-only encoder/decoder/Conversation/Try It boundary, exact judge validation, and historical cleanup original/A/B/diff/application record visibly; pair each action with independent read-only prompt/state receipts in `specs/001-experiment-repair/evidence/production-acceptance/`
- [ ] T121 Drive the deployed `/human` login/wrong-password/refresh/browser-restart/30-minute-expiry/logout/private-access journey plus RESEARCH cited/no-evidence/restart/requester-only, ASK awaiting/verbatim/exact-once, suggestion pending-private/approve/dismiss/restart/optional-once, and six-message judged Conversation visibly across real turns, with screenshots/video/receipts in `specs/001-experiment-repair/evidence/production-acceptance/`
- [ ] T122 Drive Try It normal/version-mismatch/cap/provider-failure, page selective-collapse, public ASK/suggestion/Conversation states, and verified README/MECHANICS/page labels on desktop and 375px mobile through the deployed site, with screenshots/receipts in `specs/001-experiment-repair/evidence/production-acceptance/`
- [ ] T123 Exercise wrong/expired/duplicate/rapid/HTML/script/prompt-injection/timeout/no-evidence/rule-change/cap/three-X-failure cases through approved visible surfaces, verify no execution/leak/bypass/silent loss/duplicate/rule mutation, and update `specs/001-experiment-repair/evidence/production-acceptance/matrix.md`
- [ ] T124 STOP for the exact correction phrase; publish only the approved correction, verify it on the real X profile, and save screenshot/profile/provider receipts in `specs/001-experiment-repair/evidence/production-acceptance/x-correction.md`
- [ ] T125 STOP for the exact explainer phrase; publish only the approved <=250-character single post, verify it on the real X profile, and save receipts in `specs/001-experiment-repair/evidence/production-acceptance/x-explainer.md`
- [ ] T126 STOP for the separate pin phrase naming the verified explainer post id; pin it, verify the live profile, and save receipts in `specs/001-experiment-repair/evidence/production-acceptance/x-pin.md`
- [ ] T127 For each candidate account, STOP for an individual exact follow phrase; follow only approved accounts, verify each live profile state, and save one receipt per account in `specs/001-experiment-repair/evidence/production-acceptance/x-follows.md`
- [ ] T128 Audit every screenshot for location/target/state, inspect the continuous video, retake weak evidence while state exists, and finalize the evidence guide in `specs/001-experiment-repair/evidence/production-acceptance/README.md`
- [ ] T129 Remove disposable test data through the approved visible path, verify historical integrity/rolling average/pre-cleanup hashes, empty leases/queues, no duplicate posts/deliveries, no dirty production files, and no silent timer/site warnings; record `specs/001-experiment-repair/evidence/production-acceptance/cleanup.md`

**Bounded loop**: Run at most three complete repair/retest loops; stop when the
same blocker survives two loops or any required access/approval/surface is missing.

---

## Phase 14: Convergence and Closeout

- [ ] T130 Assign final PASS/FAIL/BLOCKED to every matrix row and prohibit overall PASS if any row, evidence item, cleanup item, queue, duplicate, warning, or approved X result is incomplete in `specs/001-experiment-repair/evidence/production-acceptance/matrix.md` (SC-016)
- [ ] T131 Run Spec Kit convergence and update `specs/001-experiment-repair/spec.md` Implementation State Ledger plus `specs/001-experiment-repair/tasks.md` with actual production pass, planned stops, and remaining gaps
- [ ] T132 Run final tests, inspect final diff, commit scoped closeout/evidence updates, and verify clean feature/VPS worktrees in `specs/001-experiment-repair/evidence/closeout.md`
- [ ] T133 Report branch, commit, push/PR/main state, remaining dirty files, deployed commit, live URL, loop state, X state, and exact PASS/FAIL/BLOCKED result in `specs/001-experiment-repair/evidence/closeout.md`

---

## Dependencies and Execution Order

- Setup and preservation (T001–T007) require plan approval and block everything.
- Foundation (T008–T013) blocks all user stories.
- US1 (T014–T025) and US2 (T026–T034) establish the experiment invariant.
- US3 (T035–T043) depends on US1/US2 rule views and role contracts.
- US4 (T044–T051) depends on US1 adopted-only views and US2 models.
- US5 (T052–T068) establishes the collaboration store and `/human`; US6 depends on it.
- US7 (T079–T087) depends on US1 adopted-only views but not US5/US6.
- US8 (T088–T101) depends on truthful state from US1–US7.
- Offline review (T102–T106) blocks every external/live task.
- Production tasks are strictly sequential at each STOP. No public acceptance row can start before the deployed commit, loop, credentials, and cleanup states are verified.
- X correction, explainer, pin, and follows remain per-item gates and cannot be batched into a blanket approval.

## Parallel Opportunities

- Fixture/test authoring tasks marked `[P]` may run concurrently only when they
  edit distinct files and do not inspect/modify production state.
- No live gate is parallelizable. Pause, snapshot, cleanup, apply, credential,
  main, deploy, resume, and X actions are deliberately serialized.
- Human desktop/video acceptance uses one exclusive visible session and is
  deliberately serialized to preserve continuous evidence.

## Independent Story Acceptance

| Story | Independent proof |
|---|---|
| US1 | Mixed-status prompts + exact judge/corpus evidence battery |
| US2 | Allowed/forbidden synthetic motion state diffs |
| US3 | Immutable original/A/B/diff bundle with no apply |
| US4 | Six-message captured-snapshot artifact + concrete judgment |
| US5 | Restart-safe RESEARCH/ASK + complete `/human` session lifecycle |
| US6 | Pending-private, moderated, optional-once suggestion lifecycle |
| US7 | Four distinct Try It outcomes + separate-key boundary |
| US8 | Desktop/mobile disclosure + X delivery failure/receipt state machine |

## Requirement Traceability

| Contract keys | Primary tasks |
|---|---|
| FR-001, FR-002, FR-003, FR-004, FR-005, FR-006 | T014–T024 |
| FR-007, FR-008, FR-009, FR-010, FR-011 | T026–T034 |
| FR-012, FR-013, FR-014, FR-015 | T016–T019, T035–T043 |
| FR-016, FR-017, FR-018, FR-019, FR-020, FR-021 | T052–T068 |
| FR-022, FR-023, FR-024, FR-025, FR-026 | T044–T051, T069–T078 |
| FR-027, FR-028, FR-029, FR-030, FR-031 | T079–T087, T089, T093–T100 |
| FR-032, FR-033, FR-034, FR-035, FR-036, FR-037 | T088, T090–T097, T124–T127 |
| FR-038, FR-039 | T024, T098 |
| SC-001, SC-002, SC-003, SC-004, SC-005 | T014–T043, T120 |
| SC-006, SC-007, SC-008, SC-009, SC-010 | T044–T087, T112, T121–T122 |
| SC-011, SC-012, SC-013, SC-014, SC-015 | T024, T088–T100, T122–T127 |
| SC-016 | T118–T133 |

## Implementation Strategy

The MVP is US1 plus US2: repair what counts as the language and who may change
it before adding participation. Complete US3 next so the existing state can be
cleaned safely. Then add US4–US7, finish the honest public/X surface in US8, and
stop at the complete offline checkpoint. Production work proceeds only through
the serialized live gates.

## Format Validation

All 133 tasks use the required checkbox, sequential task id, optional `[P]`,
story label only in story phases, and an explicit file or evidence path.
