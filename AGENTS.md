# AGENTS.md - A Language All Their Own

Follow the parent workspace `AGENTS.md`.

## Normal maintenance mode

Iso deactivated the project-local Spec Kit workflow on 2026-07-31 WITA.
Existing `.specify/` and `specs/` artifacts are historical evidence, not active
bug-fix gates. Use the repository's normal inspect, test, review, PR, deploy,
and verify workflow. Spec Kit applies again only when Iso explicitly invokes it
for a future request.

## Agent skills

### Issue tracker

Planning issues live in this repository's GitHub Issues. See
`docs/agents/issue-tracker.md`.

### Domain docs

This is a single-context repository. Read `CONTEXT.md` and relevant decisions
under `docs/adr/` before changing domain behavior. See `docs/agents/domain.md`.

## Behavior changes and architecture

For a behavior request, refactor, bug fix, or onboarding review, start with
[the module interfaces and protected behaviors](docs/MODULES.md). Translate Iso's
plain-language intent into the owning interface and tests. Do not delete, skip or
weaken a protected expectation to accommodate implementation; tie any changed
expectation to an explicitly requested behavior change.
