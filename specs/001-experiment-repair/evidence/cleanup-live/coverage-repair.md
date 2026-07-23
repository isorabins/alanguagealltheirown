# Cleanup Coverage Repair — Offline Receipt

Date: 2026-07-21 16:16 WITA

Result: **PASS offline; no provider call; T120 remains open.**

## Failure removed

Two prompt-only DeepSeek candidates omitted adopted source ids. The repaired A
contract uses OpenRouter's documented strict `json_schema` response format and
sets `provider.require_parameters=true`. A must assign each source id to an
A-authored cleanup group; local code validates the mapping and derives ordered
`source_ids`. Missing/extra assignments and unknown/orphan/duplicate groups stop
before any Kimi request.

Primary documentation checked on 2026-07-21:

- https://openrouter.ai/docs/guides/features/structured-outputs
- https://openrouter.ai/docs/guides/routing/provider-selection
- https://openrouter.ai/deepseek/deepseek-v3.2

## Production-shaped schema proof

Command:

```text
python3 cleanup_rulebook.py request-options \
  --source specs/001-experiment-repair/evidence/cleanup-live/source-rulebook-turn-650.json
```

Readback:

```text
type=json_schema
strict=true
required_count=23
property_count=23
required_set_equals_property_set=true
assignments.additionalProperties=false
provider.require_parameters=true
required_ids=rule-027,rule-028,rule-031,rule-032,rule-036,rule-037,
rule-044,rule-045,rule-046,rule-047,rule-049,rule-054,rule-071,rule-072,
rule-075,rule-077,rule-083,rule-084,rule-085,rule-088,rule-090,rule-099,
rule-103
```

This includes `rule-075`, `rule-085`, and `rule-099`, the three sources omitted
by attempt 2. Extra assignment properties are forbidden. The compiler, rather
than A, constructs the candidate coverage metadata in frozen source order.

## Test receipt

The new test module first failed to import the absent schema/compiler functions,
then passed after implementation.

```text
python3 -m unittest tests.python.test_cleanup_rulebook
Ran 12 tests in 0.011s — OK

python3 -m unittest discover -s tests/python -p 'test_*.py'
Ran 65 tests in 0.564s — OK

node --test tests/js/*.test.js
27 tests — 27 pass, 0 fail

python3 tests/acceptance/check_contract_coverage.py
PASS: 78 requirements traced; 148 sequential tasks present

git diff --check
PASS (no output)
```

Coverage includes strict schema keys, deterministic source ordering, valid
consolidation, missing/extra assignments, unknown/orphan/duplicate groups, and
operational-text rejection before audit.

## Unchanged live boundary

Read-only production verification after the offline tests:

```text
language-loop.timer: inactive
language-loop.service: inactive
VPS HEAD: 75cd45704f3fd74906c3ee4edb53e81187b6ff2a
VPS worktree: clean
rulebook SHA-256: 5938df47b587aabfb9fe7231c07d12b315a3ac3f7bdcbfee73b076fe219e4933
```

No OpenRouter request was made. The protected call ledger remains at attempt
2's terminal `failed_validation` record, completed `2026-07-21T08:03:33Z`, with
cumulative G4 paid-call spend `$0.012418691`. No production, deployment,
credential, X, coordinator, or provider state was changed. The timer remains
paused at Iso review.

## Protected execution preflight

The next-run wrapper is stored outside the repository with mode `0700`. It
requires an explicit `--execute` flag and the exact approved 40-character
feature commit; before either paid call it verifies the clean pushed feature
head, inactive timer/service, clean immutable production head, rulebook hash,
23-key schema, and spend projection. Raw provider responses are atomically
written to the protected profile before parsing. A failed A compile cannot
reach Kimi, and any prior structured-run output prevents a repeat.

```text
wrapper SHA-256: f6f6edae85960f4c53ff291a2286efc1bb88ee45ec7f9831f19b4fae6f97f72e
wrapper mode: 0700
offline preflight: PASS
providerCalls: 0
requiredAssignmentCount/propertyCount: 23/23
strict/requireParameters/exactKeyOrder: true/true/true
projected conservative two-call maximum: $0.032840330
```
