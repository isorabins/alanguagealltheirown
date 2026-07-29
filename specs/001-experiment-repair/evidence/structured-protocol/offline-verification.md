# Structured Legislative Protocol — Offline Verification

Date: 2026-07-29 WITA

## Result

PASS for T187–T192. The offline implementation replaces new-turn
prose/regex extraction with a strict role/state-specific Pydantic envelope,
local validation, a typed state-machine entry point, authoritative post-state
receipts, and OpenRouter-returned `usage.cost` accounting.

This receipt does not authorize or claim a merge, push, deploy, VPS change,
timer change, paid provider call, credential change, production turn, or public
action. T193 review/release and T194 live acceptance remain open.

## Implemented boundary

- `legislative_protocol.py` defines strict action, measurement, collaboration
  request, canonical-state, action-result, and post-state receipt models.
- The generated OpenRouter JSON Schema permits only actions legal for the
  current A/B role and canonical open-motion state. An open motion exposes only
  its exact rule id, and `provider.require_parameters=true` is set.
- `loop.py` gives a malformed response at most two regeneration attempts.
  Exhaustion records one structural-failure receipt, changes no rule, and
  retains the same actor for the next legislative attempt. Any queued
  RESEARCH, ASK, or SUGGESTION tentatively delivered before generation is
  restored byte-for-byte so that same actor receives it again later.
- Validated typed motions enter `rulebook.apply_typed_motion()` directly.
  Legacy parsing remains available only for pre-cutover compatibility tests and
  historical rendering.
- Each attempted turn records exact changed/unchanged rule ids, current open
  motion, adopted count/hash, rulebook version/changes/hash, reason, attempts,
  and next actor. The cutover adds one reconciled receipt without rewriting
  prior events or rules.
- Agent discussion in the existing 30-event request window is explicitly
  non-authoritative. The canonical cutover receipt stays in the private event
  log and is omitted from the unchanged public viewer renderer; viewer metadata
  separately exposes the inherited historical estimate and provider-exact
  post-cutover cost.
- The `$25` tripwire retains the old total as
  `spend_usd_historical_estimate` and adds each successful response's
  provider-returned `usage.cost` exactly once. Missing/invalid cost fails
  closed. Production `run()` binds a gitignored VPS-local atomic ledger at
  `state/cost-receipts.local.json`, keyed by OpenRouter response id. The ledger
  is written before a successful response returns, deduplicates identical
  id/cost receipts, rejects missing/conflicting ids, and reconciles a
  ledger-ahead crash upward into `meta` on restart. A missing ledger takes its
  base from the persisted exact-since-cutover total; a conflicting existing
  ledger fails closed. Offline transfer/test calls do not bind the ledger. The
  normal `--archive` path moves the local ledger with its matching `meta.json`;
  the recursive gitignore keeps both live and archived ledgers out of git.

## Official source basis

Sources were verified during G16 preflight and re-used without broadening the
approved architecture:

- OpenRouter Structured Outputs:
  <https://openrouter.ai/docs/guides/features/structured-outputs>
- OpenRouter provider routing and `require_parameters`:
  <https://openrouter.ai/docs/guides/routing/provider-selection>
- OpenRouter usage accounting and returned `usage.cost`:
  <https://openrouter.ai/docs/cookbook/administration/usage-accounting>
- Pydantic 2.12 usage errors/schema behavior:
  <https://docs.pydantic.dev/2.12/errors/usage_errors/>
- Installed implementation runtime: Pydantic `2.12.5`

The selected path reuses the existing OpenRouter transport, single-writer JSON
state machine, atomic canonical persistence, and installed Pydantic runtime. It
adds no framework, database, service, ORM, or credential dependency.

## Test evidence

### Focused role/state, historical replay, receipt, retry, and cost suite

Command:

```text
python3 -m unittest -v tests.python.test_loop_helpers tests.python.test_research_lifecycle tests.python.test_motion_authority tests.python.test_legislative_protocol
```

Result:

```text
Ran 48 tests
OK
```

The named passing cases include:

- legal role/state matrix and local wrong-role/wrong-target rejection;
- exact open-target OpenRouter schema and multiple-open fail-closed behavior;
- bounded measurements and unique typed `LOOKUP`/`RESEARCH`/`ASK` requests;
- realistic duplicate-inline, stale-proposal, and rule-072/083–085
  belief-divergence records replayed into complete post-state receipts, with
  changed ids, open motion, adopted count, and language hash checked
  independently;
- exact post-state and cutover receipts;
- three total malformed attempts, one structural-failure receipt, unchanged
  rule state, same next actor, and following valid completion;
- RESEARCH, ASK, and SUGGESTION restored exactly after structural exhaustion,
  then redelivered to the retained actor; suggestion approval does not drift;
- provider cost accumulated once for every successful response/retry;
  response-id receipts cover normal calls and direct web research;
- crash-before-meta-save reconciliation, duplicate-id deduplication,
  conflicting/missing-id rejection, inconsistent-ledger failure, and missing
  provider cost rejection; archive co-location of ledger and matching meta;
- 30-event non-authoritative discussion rendering, sparse legacy receipts, and
  private cutover-event omission from the unchanged viewer.

### Full Python suite

Command:

```text
python3 -m unittest discover -s tests/python -p 'test_*.py'
```

Result:

```text
Ran 115 tests
OK
```

### Full JavaScript suite

Command:

```text
node --test tests/js/*.test.js
```

Result:

```text
tests 31
pass 31
fail 0
```

### Contract coverage

Command:

```text
python3 tests/acceptance/check_contract_coverage.py
```

Result:

```text
PASS: 102 requirements traced; 194 sequential tasks present
```

### Syntax and whitespace

Commands:

```text
python3 -m py_compile legislative_protocol.py rulebook.py loop.py transfer_test.py
git diff --check
```

Result: both exited `0` with no output.

## Current-state and cutover rehearsal

A read-only rehearsal loaded the checked-in canonical files, generated B's
current state-specific schema, and independently built the cutover receipt.

```text
turn=1165 events=2212 last_agent=A next_actor=B
statuses={"adopted": 22, "historical": 76, "proposed": 1, "rejected": 24, "repealed": 1}
schema_name=legislative_action_b_rule_129 strict=True require_parameters=True
schema_has_rule_129=True schema_has_rule_128=False
open=rule-129 adopted=22
language_hash=6d1b39ca6d9cb092c7a8c07098e499967a2eae26cdcd595dc7ad0cb056adb01c
receipt_rulebook_hash=b22eda004a0e4cd50778926f2c6e0f53e10b51e7cc5cde082946604b81b40052
```

This proves the planned first schema allows B to address only `rule-129`; it
does not run the model or mutate state.

## Byte-preservation evidence

Command:

```text
git diff --exit-code 5d44005 -- state
```

Result: exit `0`, no output.

Current files and the same files read from fixed point `5d44005` produced
identical SHA-256 values:

```text
901f8ef99ae9715798c9d3fff0b21f0df1d4b5901734e161ed8e2d7fa01c939e  state/conversation.json
b22eda004a0e4cd50778926f2c6e0f53e10b51e7cc5cde082946604b81b40052  state/rulebook.json
018dcd47ab53226dac5fd5937f9528ac3401babf038f97594e6a39e4e4ebdc40  state/meta.json
```

The following protected surfaces also have no diff from `5d44005`:

```text
state/
viewer/
tweet.py
run_turn.sh
prompts/agent_a.md
prompts/agent_b.md
collaboration.py
conversation_exam.py
```

`git check-ignore -v state/cost-receipts.local.json` resolves to the one exact
`.gitignore` entry, and `test ! -e state/cost-receipts.local.json` passes. No
tracked or untracked local ledger was created during offline verification.

## Static and scope checks

A read-only AST/source/diff check returned:

```text
new_path_no_regex_or_prose_extract True
new_path_uses_typed_validation True
structural_failure_restores_collaboration True
no_static_model_prices_in_new_code True
usage_cost_and_both_response_ids_present True
ledger_atomic_and_gitignored True
ledger_configured_by_run True
dead_no_motion_removed True
one_request_kind_validator True
changed_diff_has_no_secret_value_pattern True
models_cadence_window_cap_temperature_unchanged True
preserved_constants {'MODEL_A': 'deepseek/deepseek-v3.2', 'MODEL_B': 'moonshotai/kimi-k2.6', 'MODEL_DECODER': 'moonshotai/kimi-k2.6', 'MODEL_GRADER': 'deepseek/deepseek-v3.2', 'TEST_EVERY': 3, 'WINDOW': 30, 'SPEND_CAP': 25.0, 'AGENT_TEMP': 0.9}
```

The repository's separate legacy `probe.py` estimate is not part of the new
private loop accounting path and remains unchanged. No secret value was printed
or persisted by these checks.

## Gate state

- T187–T192: PASS offline
- T193: OPEN — independent fixed-point review, push, and ready PR
- T194: OPEN — consume the recorded G16 approval for live merge/activation and
  natural B/test/A acceptance; stop only if scope or material risk expands
- Canonical/live state: unchanged
