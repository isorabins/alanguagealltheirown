# Decision Coverage and Recommended Build Sequence

## Coverage

Every agreed item from the 2026-07-20 review is represented in `BUILD-SPEC.md`.

| Review decision | Contract coverage | State |
|---|---|---|
| Adopted-only language; preserve proposed/rejected history | FR-001–005, SC-001 | Specified, not built |
| Remove dumb-script language from active project, preserve history | FR-006, SC-002 | Specified, not built |
| DeepSeek inventor + Kimi auditor + separate Kimi stranger | FR-007–010, SC-003 | Specified, not built |
| Keep 50% target and affordability “why”; remove power/novelty overclaims | FR-010–011 | Specified, not built |
| One simple A cleanup, B audit, exact Iso diff gate | FR-012–014, SC-004 | Specified, not run |
| Validate exact judge item coverage | FR-015, SC-005 | Specified, not built |
| Stateful cited RESEARCH, non-blocking and non-legislative | FR-016–018, SC-006 | Specified, not built |
| Public ASK + simple password `/human` + remembered question | FR-019–021, SC-006 | Specified, not built |
| Moderated visitor suggestions below agents | FR-022–024, SC-007/011 | Specified, not built |
| Replace Composition with judged multi-turn Conversation | FR-025–026, SC-008 | Specified, not built |
| Pin Try It to one rulebook version | FR-027, SC-009 | Specified, not built |
| Separate public key, $20 monthly cap, graceful exhaustion | FR-028–029, SC-009/010 | Specified, not configured |
| Selective page collapse | FR-030, SC-011 | Specified, not built |
| Refresh README and MECHANICS | FR-031, SC-013 | Specified, not updated |
| Publish explicit field-note correction | FR-032, SC-014 | Specified, approval-gated |
| Confirmed/idempotent X posting; three tries then blocked | FR-033–034, SC-012 | Specified, not built |
| X single-post maximum 250 characters | FR-035, SC-012 | Specified, not built |
| Approved, verified, pinned X explainer | FR-036, SC-014 | Specified, approval-gated |
| One approved curated X follow pass | FR-037, SC-014 | Specified, approval-gated |
| Leave rolling average and cached-economics idea alone | FR-038–039, SC-015 | Explicit no-change |
| Directive overuse, shorthand conflicts, token-aware substitution | Scope/non-goals + cleanup story | Agents resolve in cleanup/evolution, not new harness machinery |
| Recorded production acceptance: every feature, login, persistence, failures, hostile inputs, mobile/desktop, evidence, and cleanup | SC-016 + Required Production Acceptance Test | Binding DoD; not run |

## Smallest Recommended Sequence

1. **Plan from current remote state.** Verify provider/model slugs, timer/deploy shape, and choose one minimal durable collaboration inbox. Produce `plan.md`, `tasks.md`, and Spec Kit analysis; stop for approval.
2. **Repair the experimental boundary offline.** Add adopted-only rendering, explicit proposal trials, corpus-level evidence, exact judge coverage, enforced A/B permissions, and remove the active dumb-script path. Prove all negative cases on fixtures.
3. **Gate the one-time cleanup.** After approval, pause the loop, snapshot state, run one A cleanup and one B audit, and show Iso the exact diff. Do not apply it without the separate gate.
4. **Add collaboration and native-use paths.** Build the minimal durable RESEARCH/ASK/suggestion lifecycle and judged Conversation without letting outside text write law.
5. **Harden existing public paths.** Pin Try It versions, isolate and cap spend, fix X receipts/retries/length, selectively collapse the page, and update docs.
6. **Verify, then gate live/public actions.** Human-test the deployed page, verify key metadata, and separately approve correction, explainer/pin, follows, deployment, loop resume, and main integration.

This order is intentionally dependency-driven: do not polish or add participation on top of a rule boundary that still cannot say what was tested.

## Known Planning Risk

The public collaboration features need durability across Vercel requests and VPS turns. Do not use the current `state/pending-notice.txt` as a shared mailbox and do not make serverless handlers write canonical state; that recreates overwrite/race failures. The plan must pick a small durable inbox with stable ids and idempotent consume/ack semantics.
