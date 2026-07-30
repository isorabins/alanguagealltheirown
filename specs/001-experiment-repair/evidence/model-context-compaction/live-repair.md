# Deterministic Model-Context Compaction — Turn-1210 Live Repair

Date: 2026-07-30 WITA
Approval:
`APPROVE LIVE CHANGE: alato-model-context-compaction-20260730-turn1208`
State: **PAUSED / REPAIR IN REVIEW**

## Fail-closed canary

PR #15 merged as
`e8a25a61caa03c92f2b99bc4a8b5974fb719eff1`. The paused VPS
fast-forwarded cleanly and passed 124 Python tests, 31 JavaScript tests, and
110-requirement / 202-task coverage with every pre-resume canonical and
cost-ledger hash unchanged.

Starting the existing timer invoked B at turn 1210. All three provider responses
completed normally, but local validation rejected each for
`string_too_short at deliberation`. The authoritative receipt recorded:

- `result=structural_failure`;
- `attempts=3`;
- `changed_rule_ids=[]`;
- open add motion `rule-132`, proposed at turn 1204;
- `next_actor=B`;
- adopted count/hash unchanged at 23 /
  `fa5d68abca3e42cf5a80a5ea093df68bcae4d913c7d01a02c9c571547cb9e18e`.

Exact-once restoration passed live: `lookup-1202-b` returned to `answered`,
retained all 11,248 findings characters and 10 citations, has no delivery turn,
and has zero canonical delivery records. The timer was paused before the next
boundary; the one-shot service is inactive after success.

## Cost and provider evidence

Authenticated private-key usage moved from `$8.243953482` to `$8.295098582`,
an exact `$0.051145100` delta. The application ledger moved by the same amount.
The remaining allowance inside the approved `$0.10` envelope is
`$0.048854900`.

OpenRouter generation metadata for the three completed Kimi K2.6 responses:

| Provider | Prompt tokens | Completion tokens | Cost | Finish |
|---|---:|---:|---:|---|
| Crusoe | 21,398 | 404 | `$0.0163926` | `stop` |
| Together | 21,423 | 234 | `$0.0267606` | `stop` |
| Crusoe | 21,420 | 137 | `$0.0079919` | `stop` |

The failure was therefore structured field content, not a provider timeout or
truncated response.

## In-scope repair

OpenRouter's official
[Structured Outputs guidance](https://openrouter.ai/docs/guides/features/structured-outputs)
recommends clear descriptions on schema properties. The repair adds a
description that mirrors the unchanged local 12-character/alphanumeric
deliberation validator. It also removes deterministic model-window duplication:

- full encoded/decoded live-test artifacts remain canonical, while the recent
  window carries their size-bounded outcome receipt;
- project lookup findings include up to two complete evidence records, with
  explicit included/omitted counts and zero records rather than partial JSON
  when even one record exceeds the prompt bound;
- prompt request JSON is compact rather than indented.

The exact paused turn-1211 rehearsal after fixed-point remediation is 68,040
characters: 53,980 system, 14,060 user, 13,928 recent-window, and 3,108
serialized delivery characters. The delivered findings projection is 1,318 of
11,248 characters and retains the complete
rule-090 record plus the next matched canonical receipt. The schema remains
B/open-`rule-132`; its `deliberation` field retains `minLength=12` and
`pattern=[A-Za-z0-9]` and now states the same substantive requirement.

No canonical artifact, model, retry count, cadence, provider routing,
credential, limit, public surface, DNS, or X behavior changes.

## Turn-1211 warning stop and diagnostic

The first repaired normal-cadence canary still failed closed at turn 1211 with
three `string_too_short at deliberation` results. All three DeepInfra
generations finished with `stop`; their prompt-token counts were
17,295 / 17,333 / 17,333 and their exact costs were `$0.012862100`,
`$0.013423350`, and `$0.002769650`. The timer was immediately paused.
Canonical rules remained unchanged, and `lookup-1202-b` again restored to
`answered` with 11,248 findings characters, 10 citations, no delivery turn,
and zero canonical delivery records.

Authenticated provider usage reached `$8.324153682`, or `$0.080200200` above
the approved baseline. One non-state-changing, 839-token structured diagnostic
then tested the model-policy-safe wording “concise public-facing audit summary,
not private reasoning.” Kimi returned a locally valid action with a
174-character deliberation on its first response for `$0.000580890`.
Provider usage is now `$8.324734572`: `$0.080781090` used and `$0.019218910`
remaining inside the exact `$0.10` envelope.

The final prompt-only correction uses that verified wording in the existing
`deliberation` property and at the end of the user request. It does not rename
the field, weaken validation, alter the action envelope, or change any retry,
model, provider, cadence, state, public, credential, or limit behavior.
Against the paused turn-1211 state, the resulting projected turn-1213 B request
is 68,174 characters (53,980 system + 14,194 user), still below SC-037's
70,000-character ceiling. The intervening normal-cadence turn 1212 remains a
scheduled test turn; the last comparable turn-1209 test cost `$0.004029361650`.

## Fixed-point repair review

The first repair review found two size-bound gaps before publication: one
oversized project record could fall back to partial JSON, and audit strings
were count-limited but not character-limited. The remediation uses one shared
project-evidence prefix, fits only whole records, reports included and omitted
counts, bounds each corrupted/missing/invented category, and bounds grader-loss
text while preserving the complete canonical event.

Post-remediation verification:

- focused protocol/collaboration/compaction suite: 59 passed;
- full Python: 129 passed;
- JavaScript: 31 passed;
- contract coverage: 113 requirements / 206 sequential tasks;
- compile and `git diff --check`: PASS;
- exact paused turn-1211 rehearsal: 68,040 characters;
- model/provider/routing/retries/cadence and canonical state: unchanged.

The fixed-point Standards and Spec reviewers independently returned **PASS** at
code head `935286cc2d24eaef35aa2399c7cd453cc9e28e7d`. Standards confirmed valid
whole-record JSON, a shared producer/consumer prefix, a 1,788-character hostile
audit receipt, unchanged canonical event hash, and no security or runtime
finding. Spec confirmed FR-075–076 / SC-037 alignment, the unchanged
`require_parameters=True` structured-output route, and preservation of every
stated exclusion. Design Fidelity remains not applicable because there is no
frontend change.
