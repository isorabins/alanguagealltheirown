# Deterministic Model-Context Compaction — Offline Verification

Date: 2026-07-30 WITA
Fixed point: `9f21b0e8aae717edd1727bb21938e4a0f95fe35b`
Result: **PASS offline**

## Delivered boundary

- Full `CanonicalLegislativeState`, `LegislativeRequest`,
  `PostStateReceipt`, event JSON, rulebook JSON, research rows, and canonical
  delivery records remain complete.
- The transient model request omits only the duplicate `rule_states` array.
- Recent-window and latest-receipt projections contain exactly turn, actor,
  result/reason, attempts, changed ids, open motion, adopted count/hash,
  rulebook version/hash, and next actor. `attempted_action`,
  `unchanged_rule_ids`, and `rulebook_changes` remain canonical but are not
  repeated in the receipt projection.
- One `assemble_legislative_prompt()` helper is used by `agent_turn` and the
  regression tests. `COMPLETE LEGISLATURE`, role/state OpenRouter schema,
  models, limits, and the substantive-deliberation validator are unchanged.
- A lookup/research delivery is deterministically bounded to 3,000 findings
  characters, 800 limitations characters, four safe HTTP citations within a
  fixed character budget, exact original correlation fields, and explicit
  original/included/omitted counts. The projection trims escaped content
  further when needed to remain within 8,000 serialized characters. The full
  canonical row and delivery record remain intact.
- Structural exhaustion still restores the complete pre-delivery collaboration
  state and retains the same actor. The later eligible attempt records one
  canonical delivery and regenerates the same bounded model projection.
- Projection is completed before any lifecycle mutation. A projection failure
  leaves the eligible row and canonical delivery log byte-for-byte unchanged.

No model, provider, web, VPS, service, production, or external application was
called by this implementation or its acceptance regression.

## Test-first reproduction

The new production-shaped test first failed to import the not-yet-implemented
projection boundary:

```text
ImportError: cannot import name 'MAX_RESEARCH_DELIVERY_JSON_CHARS'
Ran 1 test
FAILED (errors=1)
```

After implementation and fixed-point review remediation, the dedicated file
passes all seven behavioral claims, including exact correlation identity,
hostile JSON escaping, and fail-before-mutation rollback:

```text
python3 -m unittest -v tests.python.test_model_context_compaction
Ran 7 tests
OK
```

## Production-shaped prompt receipt

The fixture has 127 rules, 30 recent events, Agent B next, open add motion
`rule-132`, and a 14,048-character answered project lookup. It independently
assembles the old unprojected material only as a comparison oracle, then calls
the same compact assembler used by `agent_turn`.

| Measure | Result |
|---|---:|
| Unprojected prompt | 142,844 characters |
| Projected prompt | 76,038 characters |
| Reduction | 66,806 characters / 46.77% |
| Complete legislature retained | 36,605 characters |
| Full findings retained canonically | 14,048 characters |
| Findings delivered to model | 3,000 characters |
| Full/safe bounded citations | 10 / 4 |
| Bounded delivery JSON | 4,466 characters |

The generated OpenRouter schema contains `rule-132` and no unrelated
`rule-126` target. The projected prompt contains the complete proposed
`rule-132` legislature record but contains no `rule_states`,
`attempted_action`, or `unchanged_rule_ids`.

Fixture hashes before prompt assembly:

```text
rulebook  57ed703de5c852d368e6a69c8561cadb9b9c64be2a6cb12f305db4516474f64e
events    75605228ce49be16c1f885e9bc9b6f5d7585beb718f00e5ebbfcfba92fa29ab8
research  98b58692328e71e265d7f2d1183b37f01a5e25743c9970aad76bc41851ef93ba
```

Tests assert prompt assembly leaves the rulebook and event hashes identical.
Direct projection leaves the research hash identical. Delivery then produces
the exact pre-Phase-25 canonical lifecycle result: the full row gains only
`delivered`/recipient/turn fields and the full prior delivery record is
appended; only the returned model value is bounded.

## Verification

Environment:

```text
Python 3.14.5
Node v22.23.1
```

Focused protocol/collaboration/compaction suite:

```text
python3 -m unittest -v \
  tests.python.test_model_context_compaction \
  tests.python.test_loop_helpers \
  tests.python.test_collaboration_inbox \
  tests.python.test_research_lifecycle \
  tests.python.test_legislative_protocol

Ran 54 tests
OK
```

Full Python:

```text
python3 -m unittest discover -s tests/python -p 'test_*.py'
Ran 124 tests
OK
```

Full JavaScript:

```text
node --test tests/js/*.test.js
tests 31
pass 31
fail 0
```

Contract:

```text
python3 tests/acceptance/check_contract_coverage.py
PASS: 110 requirements traced; 202 sequential tasks present
```

Compile, preservation, and whitespace:

```text
python3 -m py_compile *.py tests/python/*.py
git diff --exit-code 9f21b0e -- state prompts viewer rulebook.py \
  conversation_exam.py project_lookup.py tweet.py run_turn.sh
git diff --check
```

All exited `0` with no output. Source checks confirm
`MAX_STRUCTURAL_RETRIES = 2`, deliberation still requires 12 characters plus
an alphanumeric character, models remain DeepSeek v3.2/Kimi K2.6,
`TEST_EVERY = 3`, `WINDOW = 30`, `SPEND_CAP = 25.00`, and
`AGENT_TEMP = 0.9`.

## Remaining gate

T202 is intentionally open. The first offline implementation checkpoint was
committed as `3773732074e469735ce2adab9bdfb2a619bdfeed`; fixed-point findings,
their remediation, and current commit/push/PR state are recorded in the
manager-owned review-and-release evidence. VPS sync, normal-cadence resume,
at-most-`$0.10` provider validation, and the natural B/open-`rule-132` receipt
remain manager-owned and unverified here.
