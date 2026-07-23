# New-Chat Implementation Handoff

Generated: 2026-07-20 WITA

Project: `/Users/isorabins/alex-workspace/projects/a-language-all-their-own`

Purpose: hand the audited repair program to a fresh Codex chat without asking it to reconstruct decisions from the conversation. This package contains a specification, not implemented work.

## Outcome First

Build nothing directly from the old PRDs. The binding contract is `BUILD-SPEC.md`: repair the experiment boundary first, then add the judged Conversation, stateful RESEARCH/ASK, moderated visitor suggestions, safe Try It, honest page/docs, and bounded X delivery.

The most important rule is simple: only adopted rules may govern ordinary encoding and decoding. Proposed/rejected rules stay available to the legislature and history, but are not part of the tested language.

## Reading Order

1. `README.md` — this orientation and exact next-chat start.
2. `BUILD-SPEC.md` — binding product contract; 39 requirements and 16 measurable outcomes, including the recorded production acceptance test.
3. `REQUIREMENTS-CHECKLIST.md` — specification quality gate.
4. `CURRENT-STATE.md` — audited checkout, current remote state, and what is not verified.
5. `SYSTEM-MAP.md` — current and target data flow.
6. `PROGRESS-ISSUES.md` — decision-to-requirement coverage and build order.
7. `OPERATIONS-RUNBOOK.md` — safety gates and deployment boundaries.
8. `TESTS-EVALS-VERIFICATION.md` — evidence required before any completion claim.
9. `SOURCE-INDEX.md` — authoritative source files and conflicts.

## Exact Next-Chat Instruction

Use this prompt in the new chat:

> Work from `/Users/isorabins/alex-workspace/projects/a-language-all-their-own/vendor-developer-handoff-2026-07-20/README.md`. Read the handoff in its stated order. Do not implement from chat history or the old PRDs. Continue the project-local Spec Kit workflow: run clarify only if a material product choice remains, then create `plan.md`, `tasks.md`, run analysis, and stop for my approval before implementation. Use a clean worktree based on the current remote `main`. Do not run the production loop, mutate production state, deploy, publish, change credentials or caps, or push/merge `main` without the explicit planned gate.

## Authority Order

1. Iso's current-chat instructions and workspace safety rules.
2. `BUILD-SPEC.md`.
3. `REQUIREMENTS-CHECKLIST.md` and the future approved `plan.md` / `tasks.md`.
4. `AUDIT-FINDINGS-2026-07-20.md` as evidence and decision history.
5. Current code/state.
6. Old PRDs and historical docs, only where not superseded.

If sources conflict, do not silently choose the old behavior. Update the Spec Kit contract or ask Iso at the planned gate.

## Current Delivery State

- Specification: drafted and validated for planning.
- Implementation: not started.
- Branch: local checkout remains `main` at `820ae90`.
- Remote: `refs/heads/main` was read-only verified at `5551f6f` (turn 537), 13 state-only commits beyond the audited checkout.
- Push / PR / deploy / public actions: none.
- New files: uncommitted `.specify/`, `specs/`, and this handoff folder.

## Non-Negotiable Stops

Stop for the required gate before pausing/resuming the live loop, applying a cleaned rulebook, changing production credentials/caps/secrets, deploying, publishing/correcting/pinning/following on X, or pushing/merging `main`.

Do not run `python3 loop.py` or `run_turn.sh` against real state during planning or tests. Work from scratch copies and fixtures until the production gate is explicitly approved.
