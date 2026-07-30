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
  window carries their outcome receipt;
- project lookup findings include two complete evidence records instead of a
  mid-record prefix;
- prompt request JSON is compact rather than indented.

The exact paused turn-1211 rehearsal is 68,063 characters: 53,969 system,
14,094 user, 13,962 recent-window, and 3,172 delivery characters. The delivered
findings projection is 1,307 of 11,248 characters and retains the complete
rule-090 record plus the next matched canonical receipt. The schema remains
B/open-`rule-132`; its `deliberation` field retains `minLength=12` and
`pattern=[A-Za-z0-9]` and now states the same substantive requirement.

No canonical artifact, model, retry count, cadence, provider routing,
credential, limit, public surface, DNS, or X behavior changes.
