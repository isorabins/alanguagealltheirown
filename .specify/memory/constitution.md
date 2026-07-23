<!--
Sync Impact Report
Version change: 1.4.0 -> 1.5.0
Modified principles: Expanded VIII. Acceptance Beats Summary with artifact closeout convergence.
Added sections: Beta/proxy convergence closeout workflow step.
Removed sections: None.
Templates requiring updates: AGENTS.md updated; .specify/templates/spec-template.md updated; .specify/templates/plan-template.md updated; .specify/templates/tasks-template.md updated; .specify/templates/commands/specify.md updated; .specify/templates/commands/plan.md updated; .specify/templates/commands/tasks.md updated; .specify/templates/commands/implement.md updated; .specify/templates/commands/analyze.md updated; .specify/templates/commands/converge.md updated.
Follow-up TODOs: None.
-->

# Alex Workspace Spec Kit Constitution

## Core Principles

### I. Contract Before Implementation
Every build/change PRD must produce a Spec Kit spec, plan, and tasks before
implementation. The approved artifact set is the implementation contract.
Agents must not start code edits from a loose idea, chat summary, or implied
intent when the work changes software, automation, agents, workflows,
dashboards, websites, data pipelines, or integrations.

### II. Scope Is Explicit
Allowed changes, non-goals, affected files/systems, external effects, and stop
conditions must be named in the spec or plan. Nearby opportunities are not
permission to expand the work. Any scope change requires updating the Spec Kit
artifact first.

During implementation, every new user request or shorthand instruction must be
mapped to an active Spec Kit task, gate, or acceptance check before action. If
it fits the approved contract, proceed only through that mapped gate. If it
implies adjacent infrastructure, legacy systems, new live surfaces, new external
effects, or a different operational path, stop and update the Spec Kit artifacts
or record a planned stop before acting.

### III. Approval Gates Are Real
Implementation may begin only after Iso approves the spec/plan/tasks contract,
unless Iso explicitly says to skip approval for that exact task. Live,
external-facing, destructive, account/security, financial, publish, deploy, DNS,
bulk-send, or production-impacting work still requires the workspace approval
rules in `AGENTS.md`.

### IV. Interview Before Contract
Before writing or updating a PRD, lead Iso through a short interview that locks
the outcome, user, scope, non-goals, acceptance checks, approval boundaries, and
known risks. Ask only the questions that materially change the contract.

### V. Documentation Context Before Contract
Before writing a PRD or implementation plan, agents must run a bounded
documentation-context gate. The gate must search the repo and known workspace
indexes for existing source-of-truth materials such as prior specs, product
notes, architecture notes, progress logs, runbooks, vendor handoffs, API
contracts, and user-provided docs. It must record what was read, what was
ignored as irrelevant, and any conflict between the docs and the proposed
contract.

For implementation decisions involving external libraries, APIs, platforms,
frameworks, vendors, laws, or current service behavior, the plan must add
official/current documentation references before tasks are generated. Prefer
official docs and repo-local source over blogs, memory, or model recall. A
missing or conflicting source-of-truth is a planned stop or clarification, not a
reason to invent behavior. The documentation context must be carried through
spec, plan, tasks, and implementation so the build uses the same references it
was planned against.

### VI. Runtime Boundary Before Feature Scope
For migrations, replacements, live-facing workflows, agent tool use,
side-effecting systems, multiple runtimes/workers, or production state outside
the repo, the contract must prove the chosen runtime can make the desired
behavior the only available behavior before feature scope is accepted.

The plan must record the architecture-fit decision, the simplest boring
alternative considered, the single production invariant, the legacy/bypass
inventory, and negative acceptance tests that prove forbidden old behavior
cannot happen. If the existing runtime still exposes a path that can perform
the forbidden side effect, implementation must first remove, disable, box, or
explicitly retain that path with proof that it cannot affect the new workflow.
Happy-path tests cannot compensate for an unretired dangerous bypass. A
skeptical architecture review is required before tasks when the work involves
live external sends, agent tool use, legacy migration, multiple runtimes or
workers, or production state outside the repo.

### VII. Clean Worktree For New Features
New implementation features should start in a clean git worktree before code
edits. Default to `/Users/isorabins/alex-workspace-worktrees/<feature-slug>` on
branch `codex/<feature-slug>`. If a clean worktree cannot be created, stop and
report the blocker. Do not stash unrelated user work just to make progress.

### VIII. Acceptance Beats Summary
Done means the acceptance checks in the contract pass. Agent summaries,
confidence, green tests alone, or "looks good" are not enough. The plan must
define the real user-facing or operational verification path when applicable.

Evidence reports supplement, but do not replace, Spec Kit artifacts. If a beta,
staging, proxy, dry-run, or alternate transport path passes before the official
production path, the contract cannot be closed until `spec.md` and `tasks.md`
record the current implementation pass, the official/production planned stop,
and remaining contract gaps. A reviewer must not need commits or chat history to
reconstruct completion state.

### IX. Definite Definition Of Done
Every implementation contract must define done in concrete, inspectable terms:
the final user/business state, required tests/checks, evidence artifacts,
cleanup state, and commit/PR state. Do not accept broad phrasing such as
"works", "fully migrated", "ready", or "all set" unless those words are backed
by specific verifiable conditions.

When the result touches a user-visible surface such as a website, app UI, admin
UI, Slack/chat, email, Drive/Docs, browser flow, public page, or agent workflow,
the contract must use `human-app-testing` standards: name the visible journey,
required screenshots or visible evidence, and read-only receipts that support
the visible proof. Backend logs, database rows, or green tests alone are not a
Definition of Done for user-visible behavior.

### X. Definition-of-Done Runway Preflight
Before implementation begins, the contract must include a runway preflight that
walks the entire path to the Definition of Done. It must identify every required
login, credential, role, permission, session, local tool, test account, test
data item, human-visible surface, API, deployment target, cleanup step, rollback
path, evidence artifact, and external approval needed to complete the contract.

Each dependency must be marked `available`, `pre-approved`, `planned_stop`,
`blocked`, or `not_needed`. An implementation can be treated as autonomous to
the Definition of Done only when every required item is available or explicitly
pre-approved. If Iso declines or defers approval for any item, that item must be
recorded as a planned stop before work starts. A runway preflight is not blanket
live approval; exact workspace approval rules still govern live, external,
destructive, security, financial, publishing, deploy, DNS, bulk-send, and
production-impacting actions.

### XI. Test, Review, Commit At Each Gate
Before any implementation gate or coherent checkpoint is marked complete, run
the relevant tests/checks, inspect the diff, update the evidence log, and commit
only the scoped changes for that gate. A gate cannot pass from prose alone; it
needs the named command, test, screenshot, API/read-only check, log excerpt, or
human-visible evidence required by the contract. Do not leave completed gates as
uncommitted dirty state.

### XII. Preserve Existing Work
Read the current repo state, local instructions, dirty worktree, and relevant
progress files before planning. Do not overwrite unrelated user work. When
continuing prior work, include a preservation check for the prior branch,
commit, artifact, or behavior.

## PRD Workflow

For every PRD or PRD-like request:
1. Run a short interview to lock the implementation contract.
2. Run the documentation-context gate. Record repo/workspace source-of-truth
   docs, official/current external docs needed for likely implementation
   decisions, conflicts, assumptions, and references that must be held during
   implementation.
3. If it can change implementation, create or update a Spec Kit spec under
   `specs/`.
4. Resolve scope-affecting ambiguity before planning.
5. For migration, replacement, agent, side-effecting, live-facing, multi-runtime,
   or production-state work, run the runtime-boundary gate: architecture fit,
   single product invariant, legacy/bypass inventory, negative acceptance tests,
   production-equivalence need, and skeptical architecture review if triggered.
6. Create a technical plan and task breakdown.
7. Define a concrete, gate-ordered Definition of Done before code edits.
8. Apply `human-app-testing` standards when the result is user-visible.
9. Run the Definition-of-Done runway preflight and record whether the feature is
   autonomous to done, blocked, or intentionally planned to stop at a gate.
10. Run a consistency pass using `$speckit-analyze` or a generated checklist.
11. Wait for approval before implementation unless explicitly waived.
12. Create a clean worktree before new feature implementation.
13. During implementation, map every new user request back to an active task,
   gate, or acceptance check before action. If no mapping exists, update the
   Spec Kit artifacts or record a planned stop before acting.
14. For each passed implementation gate or coherent checkpoint, commit the scoped
   changes and evidence before starting the next gate.
15. Before closeout, run a convergence checkpoint. If a beta, staging, proxy,
   dry-run, or alternate transport path passed before the official production
   path, update `spec.md` and `tasks.md` with the current implementation pass,
   the official/production planned stop, and remaining contract gaps.

If the PRD is only a non-implementation memo, put `Spec Kit: N/A` at the top and
state why.

## Governance

This constitution overrides looser planning habits in this workspace. Changes to
these rules should be deliberate and recorded in `AGENTS.md` or this file.

**Version**: 1.5.0 | **Ratified**: 2026-06-26 | **Last Amended**: 2026-06-29
