# Rule-legislation local evidence packet — 2026-09-02 WITA

## Result

The issue #70 Behavior Spine is implemented as one in-process rule-legislation
authority on `feat/rule-legislation-deep-module`. The candidate is intentionally
local/shadow only: no paid provider call, live-state migration, timer restart,
deployment, production activation, or merge was performed.

The module owns the immutable adopted-language snapshot, atomic rule-evidence
ledger, WITA calendar-month budget reservations and exact reconciliations,
experiment planning, A/B and C/B proposal workflows, and deterministic adoption.
The browser receives one version-bound public model and refuses legacy or
identity-mismatched state rather than reconstructing legislation.

## Ticket receipt

| Ticket | Integrated behavior | Interface evidence |
|---|---|---|
| #71 | One shadow authority serves immutable adopted-language snapshots | Identity stability, copy isolation, forbidden mutation, and shadow no-write tests |
| #72 | Shared atomic WITA monthly ledger enforces the fixed $30 ceiling before calls | Concurrent reservations, rollover, all-role/provider keys, exact fractional receipts, and reservation rejection tests |
| #73 | One atomic rule-evidence ledger preserves comparable evidence and rule identity | Atomic append/reload, isolation, bundled-result refusal, classification, and malformed receipt tests |
| #74 | Planner selects the cheapest useful matched experiment | Unknown/interacting prioritization, comparability, settled-question, duplicate, and unaffordable-plan tests |
| #75 | A visibly proposes; B audits every A candidate; neither model can adopt | Missing/stale/rejecting audit, direct-authority, malformed payload, fabricated hash, and target-type tests |
| #76 | C can propose only evidence-linked changes; B audits every C candidate | Complete source coverage, current-source identity, evidence linkage, output-ID collision, and B-gate tests |
| #77 | Module alone adopts the exact tested artifact | Exact artifact/hash, matched and held-out success, total successful-system token reduction including A/B, invalid judge, drift, and restart-order tests |
| #78 | Legislative callers consume module snapshots in shadow mode | A/B and C caller identity/context tests and no-authoritative-write shadow proof |
| #79 | Evaluation callers share the module snapshot and full token accounting | Development and Conversation caller identity plus canonical token-component tests |
| #80 | One generated public model drives the viewer | Runtime/archive identity gates, no client classification, legacy refusal, role/authority copy, and no provider-key exposure tests |
| #81 | Callers/effects mapped, duplicate browser authority removed, cold review repaired, full suites and human interface acceptance completed | This packet, final suite receipts, review receipt, and browser captures below |

All tickets are complete for the approved local/shadow integration unit. Live
cutover is deliberately outside their completion claim.

## Authority and effects map

```text
caller
  -> snapshot / submit_change / submit_evidence / plan_next / advance
  -> RuleLegislation
       -> adopted-language snapshot
       -> atomic evidence ledger
       -> atomic WITA budget ledger
       -> deterministic adoption record
  -> generated, identity-bound public model
```

| Caller or effect | Final local state | Cutover-held boundary |
|---|---|---|
| Development exam | Reads module version/rules; evidence tests bind it to the same identity | Actual provider execution and live evidence submission are not activated |
| Conversation exam | Reads the same snapshot and counts all canonical token components | Actual provider execution and live evidence submission are not activated |
| Legislative A/B turn | Prompt/context reads module snapshot; A proposes and B audits through typed module interfaces in tests | Existing live legacy mutation remains a compatibility seam until separately approved cutover |
| Agent C cleanup | Reads adopted snapshot and evidence context; C/B typed path is proven locally | Existing live cleanup application remains a compatibility seam until separately approved cutover |
| Project lookup/research | Reads module identity locally | Live provider-budget routing is not activated |
| Browser/bootstrap/archive | Uses only the module-generated public model; identity mismatch and legacy-only input fail closed | Production fetch/deployment was not exercised |
| Budget persistence | Module atomically owns reservations, exact receipts, model binding, and WITA month rollover | Real provider receipt/retry behavior was not exercised |
| Evidence/adoption persistence | Module atomically owns evidence and restores the latest adoption by durable sequence | No live state was migrated |
| `transfer_test.py` and `probe.py` | Remain manual provider utilities outside the active module path | Not run; their provider behavior is unverified |
| Historical repair/migration tools | Preserved as human-invoked maintenance tools | Not run; no destructive migration was authorized |
| X/collaboration outputs | Preserved as non-legislative external effects | Not run or changed into language authority |

Duplicate browser calculation and provider paths were removed. Legacy live
mutation paths were not removed because doing so would activate a production
authority cutover forbidden by issue #70 and this task's boundary.

## Sensitivity and review proof

- Red-first receipt: the exact-cost test initially exposed cent rounding
  (`0.01` versus `0.012345678901`); reconciliation now preserves the exact
  provider receipt.
- Negative seams cover snapshot mutation, mixed/bundled evidence, incomparable
  experiments, over-budget reservations, missing/stale audits, model claims of
  authority, artifact drift, success loss, non-savings, invalid judges, missing
  held-out evidence, provider-model mismatches, and malformed unhashable targets.
- Independent specification and standards reviewers examined the integrated
  diff against issue #70. Material findings were repaired in bounded batches:
  public fallback authority, response/model receipt binding, exact artifact
  hashing, C identity constraints, canonical token accounting, adoption restart
  ordering, dead provider/browser paths, and malformed candidate handling.

## Final automated verification

| Surface | Final receipt |
|---|---|
| Python | `python3 -m unittest discover -s tests/python -p 'test_*.py'` — 262 passed |
| Rule-legislation interfaces | `python3 -m unittest tests.python.test_rule_legislation_interface` — 32 passed |
| Node/browser contracts | `node --test tests/js/*.test.js` — 76 passed |
| Contract traceability | `python3 tests/acceptance/check_contract_coverage.py` — 115 requirements traced; exact T001–T210 sequence present |

All commands used local fixtures/stubs. No paid provider work ran.

## Human interface acceptance

The final generated local build was inspected in the in-app browser at desktop
and the tool's 375px viewport setting. Both showed the module authority and role
contract, adopted language, disabled Try It controls, and no horizontal overflow.
The mobile tool reported 375 physical pixels with a 469 CSS-pixel inner width
because its device scale was 0.8; the responsive containment checks still passed.

- `01-desktop-local.png`: desktop overview with authority, legislature, adopted
  language, and disabled provider-facing controls visible.
- `02-mobile-375-overview.png`: narrow overview with contained header, authority,
  legislature, and adopted-language layout.

The browser tool omits URL chrome from screenshots; the paired DOM receipt
identified the inspected origin as the read-only localhost build. Evidence is
therefore suitable for local acceptance, not production acceptance.

## Exact unverified stages and held gate

Unverified by design: real paid-provider execution; returned-provider model and
cost behavior; provider retries/timeouts; live legacy-to-module authority
cutover; live evidence and budget persistence recovery; migration of existing
state; production enforcement of the $30 ceiling; production browser fetch;
timer/live-loop restart; deployment; and merge to `main` or any release branch.

The human gate remains held. Iso must separately approve migration, production
authority activation, timer restart, deployment, paid work, any ceiling change,
and merge. There is no implementation blocker.

