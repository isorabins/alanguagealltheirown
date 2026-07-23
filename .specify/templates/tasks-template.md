---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL unless the
feature specification, plan, or constitution gates require them. Negative
acceptance tests, production-equivalence checks, and human-visible acceptance
evidence are mandatory when named in the contract.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Runway Preflight**: Include tasks that verify every login, credential,
permission, session, test account, test data item, human surface, approval,
rollback path, cleanup path, and evidence artifact needed to reach the
Definition of Done. If a dependency is not approved or available, mark the exact
planned stop before implementation continues.

**Documentation Context**: Include tasks that verify the documentation context
manifest in spec.md and plan.md has been read, conflicts are resolved or marked
as planned stops, and official/current docs for the selected implementation
surfaces are available before code edits.

**Implementation Drift Prevention**: Include tasks or checkpoints that require
every in-flight user request or shorthand instruction to map to an active task,
gate, or acceptance check before action. Requests outside the approved contract
become spec updates or planned stops, not implementation shortcuts.

**Convergence Closeout**: Include tasks that keep `spec.md` and `tasks.md` in
sync with the actual acceptance state. If a beta, staging, proxy, dry-run, or
alternate transport path passes before the official production path, the final
tasks must record the current implementation pass, the production planned stop,
and remaining contract gaps before closeout.

**Runtime Boundary Gates**: For migrations, replacements, live-facing workflows,
agent tool use, side-effecting systems, multiple runtimes/workers, or production
state outside the repo, include tasks for the architecture-fit decision, single
product invariant, legacy/bypass inventory, negative acceptance tests,
production-equivalence checks, and skeptical architecture review before happy
path implementation proceeds.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

<!--
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.

  The __SPECKIT_COMMAND_TASKS__ command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/

  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment

  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools
- [ ] TXXX Read the documentation context manifest in `spec.md` and `plan.md`
      and verify every source needed for implementation is reachable
- [ ] TXXX Create the Definition-of-Done runway preflight/access matrix from `plan.md`
- [ ] TXXX Record the single product invariant and legacy/bypass inventory from `plan.md`
- [ ] TXXX Record implementation request mapping rules and out-of-contract stop
      conditions in the feature evidence report

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T004 Setup database schema and migrations framework
- [ ] T005 [P] Implement authentication/authorization framework
- [ ] T006 [P] Setup API routing and middleware structure
- [ ] T007 Create base models/entities that all stories depend on
- [ ] T008 Configure error handling and logging infrastructure
- [ ] T009 Setup environment configuration management
- [ ] TXXX Resolve or mark planned stops for every documentation conflict in
      the `plan.md` Documentation Conflict Check
- [ ] TXXX Verify official/current docs for every selected framework, API,
      vendor, deployment target, data store, auth provider, and integration
      surface named in `plan.md`
- [ ] TXXX Verify all dependencies in the runway preflight are available,
      pre-approved, intentionally planned stops, or blocked with owner/action
- [ ] TXXX Write negative acceptance tests that prove forbidden legacy/bypass
      paths cannot perform the old side effect
- [ ] TXXX Verify every retained legacy path is removed, disabled by default,
      read-only, boxed behind an explicit legacy flag, or proven unable to
      affect the new workflow
- [ ] TXXX Define the production-equivalence checks for reviewed commit,
      deployed files, migrations/schema, env/flags, services/workers/crons, and
      old hooks/jobs

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T011 [P] [US1] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 1

- [ ] T012 [P] [US1] Create [Entity1] model in src/models/[entity1].py
- [ ] T013 [P] [US1] Create [Entity2] model in src/models/[entity2].py
- [ ] T014 [US1] Implement [Service] in src/services/[service].py (depends on T012, T013)
- [ ] T015 [US1] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T016 [US1] Add validation and error handling
- [ ] T017 [US1] Add logging for user story 1 operations

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [ ] T018 [P] [US2] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T019 [P] [US2] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 2

- [ ] T020 [P] [US2] Create [Entity] model in src/models/[entity].py
- [ ] T021 [US2] Implement [Service] in src/services/[service].py
- [ ] T022 [US2] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T023 [US2] Integrate with User Story 1 components (if needed)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 (OPTIONAL - only if tests requested) ⚠️

- [ ] T024 [P] [US3] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T025 [P] [US3] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 3

- [ ] T026 [P] [US3] Create [Entity] model in src/models/[entity].py
- [ ] T027 [US3] Implement [Service] in src/services/[service].py
- [ ] T028 [US3] Implement [endpoint/feature] in src/[location]/[file].py

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX Run all negative acceptance tests and attach evidence that the old
      forbidden path is impossible
- [ ] TXXX Run production-equivalence checks and attach evidence that live code,
      schema, env, services/workers/crons, and boxed legacy paths match the
      reviewed contract
- [ ] TXXX Run the gate-ordered Definition of Done and record PASS/PLANNED_STOP/BLOCKED
- [ ] TXXX Review implementation evidence for in-flight user requests and verify
      each maps to an approved task/gate or documented planned stop
- [ ] TXXX Run convergence closeout checkpoint and update `spec.md`
      Implementation State Ledger when the accepted path is beta, staging,
      proxy, dry-run, or otherwise short of official production
- [ ] TXXX Verify `tasks.md` records the current implementation pass, production
      planned stop, and remaining contract gaps before closeout
- [ ] TXXX Update the evidence report with the documentation sources actually
      used during implementation and any source changes discovered during build
- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX [P] Additional unit tests (if requested) in tests/unit/
- [ ] TXXX Security hardening
- [ ] TXXX Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (if tests requested):
Task: "Contract test for [endpoint] in tests/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/integration/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Do not edit implementation code when the needed documentation source is
  missing, stale, or conflicts with the approved contract unless the conflict is
  recorded as a planned stop or the contract is updated first
- During implementation, map each new user request to an active task/gate before
  acting; outside-contract requests require artifact updates or planned stops
- Before closeout, do not rely on evidence reports alone when a beta/staging/
  proxy/dry-run path passed before production; update spec.md and tasks.md
- Do not start happy-path completion work while a required invariant or
  legacy/bypass retirement gate is failing
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
