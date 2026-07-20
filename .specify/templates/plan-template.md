# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `__SPECKIT_COMMAND_PLAN__` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Documentation Context & Source Alignment

<!--
  GATE: Must pass before task generation. Carry forward product/source-of-truth
  docs from spec.md, then add official/current technical docs for selected
  frameworks, APIs, vendors, deployment targets, data stores, auth providers,
  and integration surfaces. Prefer official docs and repo-local source over
  memory or unofficial articles. Record access date for web docs when recency
  matters.
-->

### Source-of-Truth Docs From Spec

| Source | Constraint / Decision | Plan Impact | Status |
|--------|-----------------------|-------------|--------|
| [path/URL/title] | [what must be honored] | [how plan reflects it] | [aligned / conflict resolved / planned_stop] |

### Official / Current Implementation Docs

| Technology / Surface | Official Source | Version / Date Checked | Required Best Practice | Plan Impact |
|----------------------|-----------------|------------------------|------------------------|-------------|
| [framework/API/vendor/etc.] | [URL or repo path] | [version/date] | [specific rule] | [decision/task/check affected] |

### Documentation Conflict Check

| Conflict | Sources | Decision | Owner / Stop Condition |
|----------|---------|----------|------------------------|
| [disagreement or gap] | [source refs] | [resolved decision or planned stop] | [owner/action] |

**Documentation Gate Result**: [PASS / PLANNED_STOP / BLOCKED]

## Single Product Invariant

[One sentence that must be true in production. For replacements, migrations,
agents, or side-effecting systems, every acceptance gate must trace back to this
invariant. Use N/A only when the feature has no runtime boundary or side-effect
risk.]

## Architecture Fit Gate

<!--
  GATE: Required before task generation for migrations, replacements,
  live-facing workflows, agent tool use, side-effecting systems, multiple
  runtimes/workers, or production state outside the repo.
-->

**Recommended Architecture**: [chosen architecture]

**Simplest Boring Alternative Considered**: [what simpler/official/cleaner path was considered]

**Existing Runtime Fit Decision**: [why the current runtime is fit, or why it is being replaced/narrowed]

**Switch Trigger**: [what evidence would force an architecture change]

**Owner-Visible Consequence If Wrong**: [what Iso or users would experience if the architecture choice is wrong]

**Skeptical Architecture Review**: [required/not needed; reviewer, date, and finding]

### Legacy And Bypass Inventory

| Surface | Old Behavior / Bypass | New Allowed Behavior | Retirement Action | Negative Proof |
|---------|-----------------------|----------------------|-------------------|----------------|
| [tool/runtime/file/cron/job/API/UI/etc.] | [what can happen now] | [what may happen after this feature] | [remove / disable by default / read-only compatibility / legacy flag / intentionally retained] | [test, visible proof, or read-only receipt] |

**Boundary Result**: [PASS / PLANNED_STOP / BLOCKED]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Gates determined based on constitution file]

## Gate-Ordered Definition of Done

<!--
  ACTION REQUIRED: Define completion in ordered gates. No later gate can
  compensate for an earlier failed gate.
-->

| Gate | Command Or Visible Action | Expected Result | Evidence Artifact | Stop Condition | Cleanup / Rollback |
|------|---------------------------|-----------------|-------------------|----------------|--------------------|
| Invariant gate | [negative test or real front-door attempt] | [old/forbidden path is impossible] | [test output/screenshot/log/read-only receipt] | [condition that stops work] | [rollback or cleanup] |
| Happy-path gate | [dry run or controlled flow] | [new path works] | [artifact] | [condition] | [cleanup] |
| Production-equivalence gate | [deployment/schema/env/service check] | [live runtime matches reviewed contract] | [checksums/migration status/service state/etc.] | [condition] | [rollback] |
| Visible acceptance gate | [human-visible workflow] | [actual product/user path works] | [screenshots/video/receipts] | [condition] | [cleanup] |
| Cleanup gate | [cleanup/closeout action] | [test state and old automations closed or intentionally retained] | [evidence report] | [condition] | [rollback] |

## Convergence Closeout Gate

<!--
  Required before closeout. If any beta, staging, proxy, dry-run, or alternate
  transport path passes before the official/production path, the Spec Kit
  artifacts must be updated before reporting done.
-->

| Trigger | Required Spec Update | Required Tasks Update | Evidence |
|---------|----------------------|-----------------------|----------|
| [beta/staging/proxy/dry-run path passes before official production path, or N/A] | [update spec.md Implementation State Ledger with current pass and production planned_stop] | [append/verify convergence tasks for remaining contract gaps] | [evidence report / receipts] |

## Production Equivalence Gate

<!--
  Required before live acceptance for any live-facing or production-dependent
  feature. Mark N/A only when there is no deployed/runtime surface.
-->

| Runtime Surface | Required State | Verification Command / Read-Only Check | Evidence |
|-----------------|----------------|-----------------------------------------|----------|
| Reviewed branch/commit | [commit id or N/A] | [command/check] | [artifact] |
| Deployed files/checksums | [expected state or N/A] | [command/check] | [artifact] |
| Database schema/migrations | [expected state or N/A] | [command/check] | [artifact] |
| Env/feature flags/secrets presence | [expected state or N/A] | [command/check without printing secrets] | [artifact] |
| Services/workers/crons/jobs | [expected state or N/A] | [command/check] | [artifact] |
| Legacy paths/hooks | [absent/boxed/retained with proof/N/A] | [negative check] | [artifact] |

## Definition-of-Done Runway Preflight

<!--
  ACTION REQUIRED: Walk the full path from implementation start to Definition of
  Done. If the desired run should finish without stopping for Iso, every required
  item must be available or explicitly pre-approved. If not, mark the planned
  stop before work starts.
-->

**Run Target**: [Autonomous to Definition of Done / Planned stop at gate X / Blocked]

| Dependency | Needed For | Status | Owner / Approval | Evidence Or Check |
|------------|------------|--------|------------------|-------------------|
| [login/credential/session/tool/test data/approval/etc.] | [DoD step or gate] | [available / pre-approved / planned_stop / blocked / not_needed] | [owner or approval phrase] | [how verified] |

**Preflight Result**: [UNATTENDED_READY / PLANNED_STOP / BLOCKED]

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (__SPECKIT_COMMAND_PLAN__ command output)
├── research.md          # Phase 0 output (__SPECKIT_COMMAND_PLAN__ command)
├── data-model.md        # Phase 1 output (__SPECKIT_COMMAND_PLAN__ command)
├── quickstart.md        # Phase 1 output (__SPECKIT_COMMAND_PLAN__ command)
├── contracts/           # Phase 1 output (__SPECKIT_COMMAND_PLAN__ command)
└── tasks.md             # Phase 2 output (__SPECKIT_COMMAND_TASKS__ command - NOT created by __SPECKIT_COMMAND_PLAN__)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
