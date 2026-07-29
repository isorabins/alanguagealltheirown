# Structured Legislative Protocol — G16 Preflight

Date: 2026-07-29 WITA

## Run target

Implement, independently review, merge, activate, and live-verify the bounded
structured legislative protocol and provider-returned cost accounting. Leave
the timer active only after the natural B/test/A sequence passes. Preserve raw
history and canonical state except for valid agent-authored governance.

## Verified starting boundary

- `origin/main` and VPS: `5d44005c763533fd238f160e9cf8d1b2bbd1893a`
- Canonical turn: `1165`
- Events: `2212`
- Tests run: `382`
- Last legislative actor: `A`; next legislative actor: `B`
- Open proposal: `rule-129`, proposed at turn 1165
- Rule statuses: 22 adopted, 1 repealed, 1 proposed, 24 rejected, 76 historical
- Adopted-language hash: `6d1b39ca6d9cb092c7a8c07098e499967a2eae26cdcd595dc7ad0cb056adb01c`
- VPS repository: clean and aligned with `origin/main`
- `language-loop.timer`: enabled but intentionally inactive since 2026-07-29 10:04:29 UTC
- Pydantic: `2.12.5` on both Mac and VPS
- Private OpenRouter key actual usage read: available; provider-side key limit: absent and excluded from this repair
- Existing application estimate: `$4.137152`; exact key-level usage observed during preflight: `$7.184518119`

## Architecture and reuse decision

Reuse the repository's proven OpenRouter strict JSON Schema pattern from
`cleanup_rulebook.py`, Pydantic already installed in both runtimes, the existing
single-writer state machine, atomic JSON persistence, and normal PR/VPS release
path. Add one narrow `legislative_protocol.py`; do not introduce Instructor,
Guardrails, an ORM, a service, a database, or a generalized agent framework.

The acceptance oracle is not "JSON parsed." It is exact agreement among the
state-specific action schema, independently computed canonical post-state,
persisted receipt, next assembled request, provider `usage.cost`, and live
repository/service state.

The requirements checklist passes 12/12 items. FR-001–068, SC-001–034, and
T001–194 are sequential and fully mapped in `tasks.md`. The existing contract
coverage executable still intentionally expects T001–185 and remains red until
the approved T192 implementation updates and runs that executable against the
new contract.

## Representative proof

- `cleanup_rulebook.py` already sends `response_format.type=json_schema`,
  `strict=true`, and `provider.require_parameters=true`.
- Both production models currently advertise response-format support through
  OpenRouter.
- The current state can generate the exact intended canary: B must address only
  open `rule-129`, turn 1167 remains an ordinary test, and turn 1168 exercises A.
- Read-only VPS and OpenRouter key endpoints succeeded without exposing secret
  values.

## Dependencies

| Dependency | Needed for | Status | Evidence |
|---|---|---|---|
| Clean implementation worktree | Offline build | available | `codex/alato-structured-protocol` at `5d44005` |
| Existing Spec Kit contract | Scope/control | available | Phase 24 / FR-062–068 / SC-029–034 |
| Pydantic 2.12.5 | Local/runtime validation | available | Mac and VPS import/version checks |
| OpenRouter Structured Outputs | Provider constraint | available | official docs plus existing project implementation |
| Private API key | Natural paid turns | available | authenticated read-only usage check |
| Actual `usage.cost` | Cost truth | available | OpenRouter usage-accounting contract |
| GitHub PR/merge path | Release | available; live merge awaits exact approval | current origin access |
| VPS SSH/repo/systemd | Activation/rollback | available; writes await exact approval | clean read-only state/service receipt |
| Canonical snapshot | Rollback | available at live gate | turn/hash boundary above |
| Human app surface | Acceptance | not needed | backend transport only; public smoke is read-only |
| Provider key management credential | Hard account limit | excluded | not preflighted; no credential/key-limit change |
| Rejected-rule compression | Context cost | excluded | explicitly deferred |
| Vercel/DNS/X | Delivery | not needed/prohibited | no public asset or route change |

## Acceptance gates

- `code_review=include`
- `human_app_testing=not applicable`
- `surface=live VPS canonical loop plus public read-only turn/state smoke`
- `review window=Iso's next morning in WITA`

## Known stop

Exact G16 live-change approval is required before product-code implementation
is launched unattended or any branch push/PR merge/VPS/timer/paid validation
action occurs:

`APPROVE LIVE CHANGE: alato-structured-protocol-cost-and-receipts-20260729-turn1165-g16`

The approval envelope and prohibitions are defined in `plan.md`. Without the
exact phrase, readiness remains `NOT_READY` for the requested live outcome.
