# Roadmap — A Language All Their Own

This file holds implementation-ready work that is not yet part of the live
contract. Current behavior remains documented in [README.md](README.md) and
[MECHANICS.md](MECHANICS.md).

## P0 — Restore the agents' bounded feedback loop

**Status:** ready for implementation; this PRD changes documentation only.

**Decision:** keep prompt compaction, but restore two small, typed sibling
channels to every fresh legislative call:

1. **Active legislative feedback** — the unresolved instruction Agent B gave
   Agent A about the one open motion.
2. **Latest development-exam feedback** — the newest valid or invalid B1–B5
   benchmark receipt, tied to the exact language version it tested.

Do not restore the recent-event window. The defect is missing operative state,
not insufficient transcript replay.

### Why this is P0

Every Agent A and Agent B turn is a fresh stateless model call. Canonical state
currently preserves more evidence than the next call receives:

| Evidence | Canonical record | Fresh A/B prompt today | Consequence |
| --- | --- | --- | --- |
| B's exact typed `REQUEST.focus` | Saved under `PostStateReceipt.attempted_action.motion.focus` | Stripped by `prompt_receipt_projection()` | A knows that work was requested, but not what B asked it to fix. After A revises, fresh B also cannot reliably check its own request. |
| Latest ordinary exam | Saves benchmark identity, tested-language hash, token counts, fidelity, failed key items, and raw artifacts | Entirely absent | Neither legislator can learn from measured compression or semantic loss. |

This is a broken control loop, not merely a missing display field. Current
tests explicitly protect the omissions: the receipt-projection test excludes
`attempted_action`, and the production-shaped compaction test requires both the
attempted action and authoritative live-test receipt to be absent.

The regression was introduced while removing duplicate prompt bulk. Commit
[`3773732`](https://github.com/isorabins/alanguagealltheirown/commit/3773732074e469735ce2adab9bdfb2a619bdfeed)
created the compact receipt projection; commit
[`5cd0169`](https://github.com/isorabins/alanguagealltheirown/commit/5cd01697c01e74f95ff70e0ada9f631207d0d447)
removed legislative event replay during [PR #18](https://github.com/isorabins/alanguagealltheirown/pull/18).
The compaction goal was correct. Its regression contract protected absence
instead of protecting the minimum meaning the agents need.

### Product outcome

After this work:

- A receives B's exact bounded request about the still-open motion.
- After A revises, B receives that same request and can judge whether A met it.
- The request disappears only when superseded or when that motion is adopted
  or rejected.
- A and B receive the latest bounded development-exam result until the next
  ordinary exam replaces it.
- The receipt explains that B1–B5 are repeating development benchmarks, what
  fidelity and savings mean, and that deltas compare only with the previous
  valid run of the same benchmark.
- Raw messages, encodings, decodes, answer keys, grader JSON, deliberation,
  unchanged ids, event replay, and sealed holdout material remain out of the
  prompt.
- Canonical events, state, and hashes remain unchanged by projection.

### Scope

Build:

- typed prompt-only models and pure projectors for both channels;
- deterministic lifecycle derivation from canonical receipts/events;
- explicit component and combined serialized-size budgets;
- one permanent interpretation block shared by both agent prompts;
- unit, prompt-integration, multi-turn lifecycle, manifest, and CI regression
  coverage;
- current-contract updates in `README.md` and `MECHANICS.md` when the feature is
  implemented;
- one approval-gated, no-state production-shaped Kimi smoke after the offline PR
  is green and before any release.

Do not build or do in this work package:

- full event replay or conversation memory;
- changes to canonical event/state shapes unless a migration is separately
  justified;
- automatic legislative action based on a receipt;
- a claim that a whole-language exam proves one rule caused an outcome;
- provider calls in unit/integration tests;
- live loop, timer, X, Redis, Vercel, deployment, or generated-state changes;
- a public-repo copy of a sealed transfer payload or answer key.

## Contract 1 — Active legislative feedback

The projector must scan authoritative post-state receipts for the **currently
open motion**, not merely copy the latest receipt. A revision is a new latest
receipt, but it does not resolve B's earlier request.

Minimum model-facing shape:

```json
{
  "latest_transition": {
    "turn": 1234,
    "actor": "A",
    "motion_kind": "REVISE",
    "target_rule_id": "rule-135",
    "result": "accepted",
    "reason": "motion_applied"
  },
  "active_request": {
    "turn": 1232,
    "target_rule_id": "rule-135",
    "focus": "Distinguish this from rules 036 and 090 and preserve binding words that prevent ambiguity."
  },
  "current_open_motion": {
    "kind": "add",
    "target_rule_id": "rule-135",
    "proposed_turn": 1228
  },
  "next_actor": "B"
}
```

Lifecycle rules:

| Event | Required result |
| --- | --- |
| B returns a valid `REQUEST` | Its exact `focus`, request turn, and target become active. |
| A's next fresh call | Receives the active request exactly once in the assembled prompt. |
| A returns `REVISE` | The request remains active with its original turn and target. |
| B's next fresh call | Receives the same active request exactly once for comparison with A's revision. |
| B returns a newer `REQUEST` for that motion | New request supersedes the old one. |
| B returns `ADOPT` or `REJECT` | The motion settles and active feedback clears. |
| Structural failure or a valid no-motion turn | The unresolved request remains active; neither outcome counts as settlement. |
| A proposes a repeal and B requests work | The same lifecycle applies to the open repeal. |
| Target changes or no matching open motion exists | Old focus must not leak or masquerade as current feedback. |

The projection retains the exact request focus because the existing input
schema already bounds it to 1,000 characters. It excludes full deliberation,
measurements, collaboration requests, rule text, unchanged ids, and unrelated
receipt history.

## Contract 2 — Latest development-exam feedback

This is the minimum complete run receipt shown to both legislators. It is a
projection of the newest canonical ordinary `test` event, not a replacement
for that full event.

```json
{
  "feedback_contract_version": "prompt-feedback-v1",
  "benchmark_scope": "development",
  "exam_turn": 1245,
  "benchmark": {
    "id": "B3",
    "name": "Farming data",
    "version": "v1",
    "cycle": 1
  },
  "tested_language": {
    "version": "adopted-8b2b84e5a6dd",
    "hash": "8b2b84e5a6dd41b2c45eef9a3dac6de8a5d753ecc32e4df7d9ebd48c2efa04c9"
  },
  "current_language": {
    "version": "adopted-8b2b84e5a6dd",
    "hash": "8b2b84e5a6dd41b2c45eef9a3dac6de8a5d753ecc32e4df7d9ebd48c2efa04c9",
    "matches_tested_language": true
  },
  "original_tokens": 435,
  "encoded_tokens": 326,
  "body_savings_pct": 25,
  "judgment_valid": true,
  "invalid_reason": null,
  "outcome": "semantic_loss",
  "fidelity_pct": 95,
  "keyed_facts_survived": 21,
  "keyed_facts_total": 22,
  "invented_fact_count": 0,
  "previous_valid_same_benchmark": {
    "turn": 1179,
    "fidelity_pct": 68,
    "body_savings_pct": 29
  },
  "delta_from_previous_valid_same_benchmark": {
    "fidelity_pct_points": 27,
    "body_savings_pct_points": -4
  },
  "failed_items_total": 1,
  "failed_items_included": 1,
  "failed_items_omitted": 0,
  "failed_items": [
    {
      "item_id": 10,
      "verdict": "MISSING",
      "fact": "Use prescription map with tag \"v4_final\".",
      "note": "The decoded message omitted the updated prescription-map tag."
    }
  ],
  "invented_fact_summary": null,
  "primary_loss_summary": "The instruction to use the updated prescription map tagged v4_final was missing."
}
```

That example is derived from the real B3 event at turn 1245. Under this
benchmark's explicit definition of important information, `95` means 21 of 22
equally weighted keyed facts survived, with no invented-fact penalty. It is
therefore 95% fidelity to the benchmark's identified important facts; it is not
a claim that a model measured every possible human interpretation of
importance.

Semantics are fixed:

- `body_savings_pct` is positive savings: the existing event's
  `-token_delta_pct`.
- `outcome = complete` only when the judgment is valid and fidelity is 100.
- `outcome = semantic_loss` when the judgment is valid and fidelity is below
  100. Do not add a duplicate `semantic_loss_pct`; fidelity and item counts are
  the numeric result.
- `outcome = unknown`, `fidelity_pct = null`, and both deltas are `null` when
  the judge is invalid.
- An invalid run still reports mechanically valid token counts and body
  savings, but it does not replace the benchmark baseline. Include
  `baseline_retained_turn` pointing to the previous valid same-benchmark run.
- Baselines and deltas compare B3 with the previous valid B3, B4 with B4, and
  so on—never with the most recent exam of a different message.
- `primary_loss_summary` names the most damaging observed loss;
  `failed_items` is the bounded authoritative list behind it.
- Exact tested and current language hashes are always present. When they differ,
  `matches_tested_language` is false and the prompt must say the evidence is
  about an older language.
- An ordinary exam evaluates the entire adopted language. It may establish
  that a tested language included a rule; it may not claim that rule caused the
  result. Causality requires an explicit proposal trial or ablation.

### Permanent prompt interpretation

Both role prompts must receive one shared instruction block with this meaning:

> B1–B5 are fixed, repeating development benchmarks. Use them to improve the
> language, but compare a result only with the previous valid result for the
> same benchmark id. Fidelity is the code-computed percentage of keyed facts
> that survived, with invented facts penalizing the denominator; the keyed facts
> are equally weighted. Body savings measures only original versus encoded
> message tokens and excludes rulebook cost. `semantic_loss` means at least one
> scored fact failed despite a valid judgment. `unknown` means the judge was
> invalid, so no score, delta, or new baseline exists. The tested-language hash
> identifies the rulebook the exam actually used. A whole-language result is not
> proof that any individual rule caused it.

The instruction belongs beside the typed receipt, not duplicated in every
event or improvised by each agent.

## Bounds and failure behavior

Use named constants and compact JSON (`ensure_ascii=False`, compact separators):

| Budget | Required cap |
| --- | ---: |
| `MAX_ACTIVE_LEGISLATIVE_FEEDBACK_JSON_CHARS` | 3,000 |
| `MAX_EXAM_FEEDBACK_JSON_CHARS` | 4,500 |
| `MAX_COMBINED_FEEDBACK_JSON_CHARS` | 7,500 |
| Active request focus | exact, already limited to 1,000 input characters |
| Failed items | at most 4, whole items only |
| Failed-item fact | 240 characters |
| Failed-item note | 240 characters |
| Primary loss summary | 600 characters |

Truncate optional exam details deterministically at item boundaries and report
included/omitted counts. Never emit partial JSON or silently truncate the
request focus. If required scalar identity fields cannot fit, prompt assembly
fails closed before any provider call.

The production-shaped fixture must continue recording the whole assembled
prompt character count and remain at or below 70% of the old full-history
prompt. Component caps protect local growth; the ratio protects the complete
assembled request from a future "small pieces, large total" regression.

## Protect the transfer test

The five B1–B5 messages are now repeating **development benchmarks**. Agents
may legitimately learn from them; they are not a holdout.

The existing 19-payload transfer battery is also committed in this public
repository, and its current runner lacks frozen per-payload answer keys. It is
useful public generalization evidence, but it cannot prove performance on a
secret unseen set.

The release-grade transfer claim therefore requires a new operator-held sealed
set created outside this repository and outside project lookup:

- payloads, answer keys, grader diagnostics, and item-level failures never
  enter git, canonical conversation events, collaboration records, prompts, or
  model-visible receipts;
- only the operator triggers it after approval;
- agents may receive only an aggregate public result after the evaluation is
  permanently closed, never training feedback from the sealed items;
- offline CI uses synthetic `HOLDOUT_SENTINEL` fixtures to prove exclusion; it
  never imports the real holdout;
- this feature must not modify or run `transfer_test.py`.

## Exact regression suite to build

Use deterministic fixtures and mocked providers. These are test names and
required assertions, not illustrative suggestions.

### Pure projections — `tests/python/test_prompt_feedback_projection.py`

| ID | Exact test | Required assertion |
| --- | --- | --- |
| L01 | `test_request_focus_survives_b_to_a_exactly` | B's quote-heavy `FOCUS_SENTINEL` appears byte-for-byte with original request turn and target. |
| L02 | `test_request_focus_survives_revision_for_next_b` | After A `REVISE`, active focus remains unchanged while `latest_transition` becomes the revision. |
| L03 | `test_newer_request_supersedes_active_focus` | Second request replaces first; old sentinel is absent. |
| L04 | `test_adopt_clears_active_focus` | Accepted `ADOPT` settles the matching motion and returns `active_request: null`. |
| L05 | `test_reject_clears_active_focus` | Accepted `REJECT` settles the matching motion and returns `active_request: null`. |
| L06 | `test_unrelated_motion_never_inherits_focus` | A later target cannot receive an earlier target's focus. |
| L07 | `test_structural_failure_preserves_unresolved_focus` | Action-less structural-failure receipt changes latest transition but does not clear focus. |
| L08 | `test_no_motion_preserves_unresolved_focus` | A valid no-motion receipt does not count as settlement. |
| L09 | `test_repeal_request_uses_same_focus_lifecycle` | Requested repeal focus survives revision and clears only on repeal adoption/rejection. |
| L10 | `test_all_legislative_action_shapes_project_without_stale_focus` | `PROPOSE`, `REVISE`, `REPEAL`, `REQUEST`, `ADOPT`, `REJECT`, no-motion, cutover, and structural failure return the declared shape. |
| L11 | `test_legislative_projection_excludes_nonoperative_bulk` | Deliberation, measurements, collaboration requests, changed/unchanged id arrays, rule text, and unrelated history sentinels are absent. |
| L12 | `test_legislative_projection_is_bounded_deterministic_and_non_mutating` | Hostile escaping remains valid JSON under 3,000 chars; repeated output is identical; canonical receipt/event hashes are unchanged. |
| E01 | `test_valid_complete_exam_projects_complete_outcome` | Valid 100-fidelity event produces `complete`, exact identity/counts, and no failed items. |
| E02 | `test_valid_loss_exam_projects_fidelity_and_failed_items` | Real-shaped 21/22 fixture produces `semantic_loss`, fidelity 95, the missing item, and the primary summary. |
| E03 | `test_invalid_judgment_is_unknown_and_retains_baseline` | Fidelity/deltas are null, reason is explicit, prior valid baseline turn remains, and baseline state is not replaced. |
| E04 | `test_exam_delta_uses_previous_valid_same_benchmark_only` | B3 ignores a newer B2 result and computes +27 fidelity/-4 savings from prior valid B3. |
| E05 | `test_exam_projection_labels_older_tested_language` | Different current hash is present with `matches_tested_language: false`; no text implies current language was tested. |
| E06 | `test_exam_projection_truncates_only_at_item_boundaries` | Oversized audit includes at most four complete items, valid JSON, exact included/omitted counts, and stays under 4,500 chars. |
| E07 | `test_exam_projection_excludes_raw_and_holdout_payloads` | Original, encoding, decode, answer key, grader JSON, `RAW_SENTINEL`, and `HOLDOUT_SENTINEL` are absent. |
| E08 | `test_exam_projection_is_deterministic_and_non_mutating` | Repeated projection bytes match and canonical event/meta hashes remain identical. |
| E09 | `test_transfer_events_are_not_eligible_exam_feedback` | A newer transfer/holdout-shaped event is ignored; newest ordinary development exam remains selected. |
| E10 | `test_feedback_component_and_combined_caps_fail_closed` | Each component and combined JSON cap is enforced before a mocked provider can be called. |

### Prompt contract — `tests/python/test_prompt_feedback_contract.py`

| ID | Exact test | Required assertion |
| --- | --- | --- |
| P01 | `test_b_request_focus_reaches_next_a_prompt_once` | After B requests `FOCUS_SENTINEL`, next A system+user prompt contains it exactly once. |
| P02 | `test_a_prompt_keeps_open_target_and_strict_revise_schema` | Same A request contains canonical open target and a schema allowing only `REVISE` for that target. |
| P03 | `test_focus_reaches_next_b_prompt_once_after_a_revision` | Fresh B sees original focus exactly once after A revises. |
| P04 | `test_settled_focus_is_absent_from_later_prompts` | Both roles omit the old focus after adoption and after rejection. |
| P05 | `test_latest_exam_feedback_reaches_a_and_b_until_replaced` | A and B each receive the same bounded exam receipt; a newer ordinary exam replaces it. |
| P06 | `test_invalid_exam_prompt_is_explicitly_unknown` | Prompt contains invalid reason, null fidelity/deltas, and retained baseline—never `None/100` or a numeric fake score. |
| P07 | `test_stale_exam_hash_is_labeled_without_causal_claim` | Tested/current hashes differ visibly and forbidden phrases such as `rule caused` are absent. |
| P08 | `test_structural_retry_reuses_identical_feedback_projection` | Every retry receives byte-identical feedback and unchanged canonical hashes. |
| P09 | `test_collaboration_input_remains_conditional_and_exact_once` | Delivered collaboration appears once; absent delivery yields no collaboration payload; feedback channels remain unchanged. |
| P10 | `test_production_prompt_keeps_required_semantics_and_compaction_ratio` | Required sentinels are present; forbidden bulk absent; component/combined caps hold; total chars are recorded; compact prompt is ≤70% of legacy fixture. |
| P11 | `test_prompt_assembly_makes_no_network_or_provider_call` | Patched HTTP/provider functions are never called. |
| P12 | `test_shared_interpretation_block_defines_benchmarks_metrics_and_causality` | Both roles receive one identical block defining B1–B5, fidelity, body savings, invalid baseline behavior, same-id comparison, tested hash, and no causal claim. |

### Actual state-machine lifecycle — `tests/python/test_prompt_feedback_lifecycle.py`

| ID | Exact test | Required assertion |
| --- | --- | --- |
| S01 | `test_propose_request_revise_adopt_exam_feedback_lifecycle` | Run actual typed Python state machine through A propose → B request → A prompt → A revise → B prompt → B adopt → hash change → mocked ordinary exam → A then B prompts. Focus persists then clears; exam persists until replacement. |
| S02 | `test_rejection_clears_focus_without_changing_adopted_language` | Rejection settles proposal, clears focus, retains history, and leaves adopted-language hash unchanged. |
| S03 | `test_repeal_lifecycle_removes_active_text_but_retains_history` | Adopted repeal removes text from language view, preserves rule/history in legislature, clears focus, and changes hash only on ratification. |
| S04 | `test_invalid_then_valid_exam_keeps_and_replaces_same_id_baseline` | Broken B3 judge leaves old B3 baseline; later valid B3 compares to that baseline and then replaces it. |
| S05 | `test_restart_reconstructs_feedback_from_canonical_state` | Serialize/reload fixtures between every turn; derived feedback and hashes match the uninterrupted run. |

### Readable manifest and CI

Add `tests/python/test_prompt_feedback_manifest.py` with one
`test_prompt_feedback_manifest` that names and asserts these invariants:

- adopted language present;
- complete legislature present;
- authoritative current machine state present;
- active legislative feedback present, bounded, persistent across revision,
  and cleared on settlement;
- latest development-exam feedback present and bounded;
- delivered collaboration present only when delivered;
- strict role/open-motion schema correct;
- full event replay, raw test bodies, duplicate canonical payloads, and holdout
  sentinels absent.

Add `.github/workflows/offline-regression.yml` and
`tests/python/test_offline_ci_contract.py`:

| ID | Exact test | Required assertion |
| --- | --- | --- |
| C01 | `test_ci_runs_on_pr_manual_and_code_pushes` | Workflow has `pull_request`, `workflow_dispatch`, and `push` to `main`. |
| C02 | `test_ci_paths_cover_feedback_code_tests_prompts_and_workflow` | Filters include core Python, prompts, benchmarks, tests, viewer/API, and workflow files. |
| C03 | `test_ci_ignores_generated_state_only_turns` | Filters exclude `state/**`, logs, and `viewer/state.js`, so scheduled state-only commits do not run CI. |
| C04 | `test_ci_commands_are_the_offline_gates` | Workflow runs the exact Python, Node, and historical coverage commands below and contains no deploy/provider step. |

Exact CI gates:

```bash
python3 -m unittest discover -s tests/python -p 'test_*.py'
node --test tests/js/*.test.js
python3 tests/acceptance/check_contract_coverage.py
```

Current verified offline baseline on `origin/main` commit `935bd8b` on
2026-07-31: 144 Python tests passed, 36 Node tests passed, and historical
coverage reported 115 requirements and 210 sequential task ids. The historical
Spec Kit checker remains green but is not the semantic contract for this normal
maintenance feature.

## Implementation sequence and release gates

1. Add the new regression fixtures/tests first and prove they fail for the
   current missing channels.
2. Add typed prompt-only models and pure projectors. Keep canonical models and
   stored events byte/hash-stable.
3. Integrate both projections into the single `assemble_legislative_prompt()`
   path and add the shared interpretation block.
4. Replace absence-based compaction assertions with the semantic manifest,
   forbidden-bulk assertions, named caps, and ≤70% production-fixture ratio.
5. Update `README.md` and `MECHANICS.md`; add offline GitHub CI; record focused
   and full-suite receipts in the implementation PR.
6. Stop at a green, reviewable offline PR. Do not merge, deploy, restart the
   timer, mutate state, or call a provider.
7. With explicit approval, run one production-shaped Kimi request off-live:
   exact assembled prompt, no canonical writes, no timer, one capped paid call.
   It must accept the two receipts and return the strict current-state schema.
8. Merge/release/restart and any sealed holdout run are separate approval gates.

## Acceptance criteria

- Fresh A receives B's exact request focus for the still-open target.
- Fresh B receives the same focus after A revises; it clears only on
  supersession or settlement, not on structural failure/no-motion.
- Fresh A and B receive the latest bounded B1–B5 exam feedback with exact tested
  and current language identity.
- A valid 21/22 result is represented as 95 fidelity and `semantic_loss`; an
  invalid judgment is `unknown` with no score/delta/baseline replacement.
- Deltas compare only with the previous valid result for the same benchmark id.
- No full event window, raw original, encoding, decode, answer key, grader JSON,
  deliberation, unchanged-id list, or sealed holdout evidence enters a fresh
  prompt.
- Projection is deterministic, cap-safe, valid JSON, and leaves canonical
  state/events/meta byte/hash-identical.
- The production-shaped prompt remains ≤70% of the old full-history fixture.
- All focused tests and all three offline gates pass in GitHub CI.
- The implementation PR records exact test evidence and remains unmerged until
  review; provider smoke, deploy, restart, and holdout run remain separately
  approved.

## Supporting evidence

Current code and tests:

- [`legislative_protocol.py`](legislative_protocol.py#L436) — current compact
  receipt/request projections omit `attempted_action`.
- [`loop.py`](loop.py#L558) — the one current legislative prompt assembler uses
  only the latest compact receipt; [`test_turn()`](loop.py#L901) persists the
  complete ordinary-exam event and same-benchmark deltas.
- [`rulebook.py`](rulebook.py#L89) — keyed fidelity is computed in Python;
  [`REQUEST`](rulebook.py#L246) leaves the motion open and returns control.
- [`tests/python/test_model_context_compaction.py`](tests/python/test_model_context_compaction.py#L228)
  — current projection and production-shaped compaction assertions.
- [`tests/python/test_exam_evidence.py`](tests/python/test_exam_evidence.py#L75)
  — current same-benchmark and invalid-judge protections.
- [`benchmarks/v1.json`](benchmarks/v1.json) — the frozen repeating B1–B5
  development registry.
- [`TRANSFER-TEST.md`](TRANSFER-TEST.md) and
  [`transfer_test.py`](transfer_test.py) — the public 19-payload battery and its
  current runner, which does not supply frozen per-payload answer keys to the
  keyed grader.

Historical repair evidence:

- [Event-window repair receipt](specs/001-experiment-repair/evidence/model-context-compaction/event-window-repair.md)
  — why the unbounded event window was removed and what the compact request kept.
- [Offline compaction verification](specs/001-experiment-repair/evidence/model-context-compaction/offline-verification.md)
  — production-shaped size and non-mutation proof used for the compaction.
- [Review and release receipt](specs/001-experiment-repair/evidence/model-context-compaction/review-and-release.md)
  — reviewed delivery boundary for the compact prompt path.
- [PR #18](https://github.com/isorabins/alanguagealltheirown/pull/18),
  [commit `5cd0169`](https://github.com/isorabins/alanguagealltheirown/commit/5cd01697c01e74f95ff70e0ada9f631207d0d447),
  and [commit `3773732`](https://github.com/isorabins/alanguagealltheirown/commit/3773732074e469735ce2adab9bdfb2a619bdfeed)
  — exact historical changes that compacted away the semantic channels.

Observed examples:

- [Rule 135 lifecycle, turns 1228–1242](https://github.com/isorabins/alex-workspace/blob/0ecb5e42be9a781dca472406b9ecce6ed89a0322/learning/a-language-all-their-own-code/lessons/0002-the-whole-machine.html#L134-L231)
  — B's focus is canonically present but absent from the compact prompt; the
  lesson also documents why turn 1242 is whole-language evidence, not causality.
- [`state/conversation.json`](state/conversation.json) at turn 1245 — the real
  B3 435→326 token, 21/22, fidelity-95 receipt used in the example above.
- [Current mechanics](MECHANICS.md#legislature) — explicitly states that prior
  events and recent live-test events do not enter fresh legislative requests;
  this section must change only when implementation changes reality.

## P1 — Project conversation-cost savings across 20 exchanges

**Status:** parked until the active fixed-benchmark and Field Notes acceptance
monitor is terminal; this roadmap entry changes documentation only.

**Outcome:** Add a seventh headline metric to the public viewer with the exact
short label `projected cost savings · 20 exchanges`. The number is a
transparent deterministic hypothetical for two Claude Sonnet 4.6 agents using
the language continuously, retaining their full conversation, and caching the
current rulebook in both system prompts. It is not current OpenRouter telemetry
and must be described as projected conversation-cost savings, not total
API-bill savings.

### Fixed comparison model

- Reference model: Claude Sonnet 4.6.
- Twenty exchanges means 40 generated messages: Agent A sends and Agent B
  replies once per exchange.
- Baseline English message length is 1,000 tokens per generated message.
- Every invocation carries the full prior transcript. Only the static rulebook
  prefix is cached.
- Each agent has its own five-minute cache: two initial cache writes, then 38
  cache reads.
- Reference prices per million tokens are `$3` input, `$15` output, `$3.75`
  five-minute cache write, and `$0.30` cache read.
- The encoded-message fraction comes from the latest completed B1-B5 cycle:
  `R = 1 + avgTokenDeltaPct / 100`.
- The rulebook size is the positive live `rulebook.kernel_tokens` value already
  supplied to the viewer's `render(S)`.
- Shared base instructions, tools, reasoning tokens, and unrelated application
  work are excluded because they are identical or outside the communication
  layer.

### Deterministic calculation

```text
N = 40
M = 1,000
H = N * (N - 1) / 2 = 780 accumulated-history message copies
R = 1 + completedCycle.avgTokenDeltaPct / 100
S = rulebook.kernel_tokens

plain_input_tokens  = H * M
plain_output_tokens = N * M
plain_cost = (plain_input_tokens * 3 + plain_output_tokens * 15) / 1,000,000

encoded_input_tokens  = plain_input_tokens * R
encoded_output_tokens = plain_output_tokens * R
rulebook_cache_cost = S * (2 * 3.75 + 38 * 0.30) / 1,000,000
encoded_cost =
  (encoded_input_tokens * 3 + encoded_output_tokens * 15) / 1,000,000
  + rulebook_cache_cost

projected_savings_pct =
  round(100 * (plain_cost - encoded_cost) / plain_cost)
```

Return no percentage until both a completed benchmark cycle and a positive
rulebook-token count exist; render `forming` in that state. Do not substitute
provider receipts or assume automatic caching of growing message history.

### Viewer treatment

Implement the calculation as a small pure helper in `viewer/index.html` near
`latestCompletedBenchmarkCycle`, using the existing `completedCycle` and
`rb.kernel_tokens` values. Place the new metric beside the existing savings
metrics.

Immediately below the metrics/legend, add a restrained expandable explanation
that names Claude Sonnet 4.6, 40 messages averaging 1,000 English tokens, full
history retention, the current rulebook cached in two system prompts, and the
latest completed five-benchmark cycle as the compression source. It must state
that this is a fixed comparison model, not the experiment's actual API bill;
the expanded details must expose the two cache writes and 38 reads.

### Acceptance

Focused JavaScript tests must:

1. Extract and execute the pure projection helper.
2. Pin the 40 messages, 780 accumulated-history copies, two cache writes, 38
   reads, and Claude Sonnet 4.6 prices.
3. Prove that `avgTokenDeltaPct: -32` plus `kernel_tokens: 1654` rounds to
   `31%` projected savings.
4. Prove missing completed-cycle or positive rulebook-token data produces the
   `forming` state.
5. Verify the public projection label and fixed Claude/cache explanation.

Both established Python and JavaScript suites must pass. Local desktop and
exact 375px inspection must show no crowding or horizontal overflow.

### Delivery boundary

Before implementation, run a focused `grilling` session with Iso. Resolve the
decision tree one question at a time, with a recommended answer for each
decision and current project facts researched instead of asked. Explicitly
settle whether this hypothetical belongs as a headline public metric, the
20-exchange and 40-message model, the 1,000-token baseline, full-history and
cache assumptions, the fixed Claude Sonnet 4.6 pricing reference, what the
percentage may and may not claim, the `forming` state, viewer explanation,
acceptance evidence, and the exact viewer-only/no-live boundary. Record the
agreed answers here or in a linked durable contract. Do not create the feature
branch or change code until Iso confirms shared understanding.

Implementation must then start in a fresh worktree and feature branch from
freshly fetched `origin/main` because generated turn commits continue advancing
`main`. Produce one coherent viewer-and-test-only commit. Do not alter benchmark
generation or history, rulebook calculation, prompts, state schema, OpenRouter
accounting, provider choice, `state/`, `viewer/state.js`, Field Notes, X
publishing, timers, VPS, Vercel production, DNS, credentials, or
acceptance-monitor artifacts. Do not make provider calls, spend project money,
merge, deploy, or claim the metric is live under this roadmap item alone.

### Reopen and release gates

Reopen only after the fixed-benchmark and Field Notes acceptance monitor
reaches `completed` or `blocked`, its evidence is reconciled, and this item is
selected as the next project gate. Use the existing frontend, quality, and
human-app-testing workflows for implementation and local responsive proof.
Production merge/deploy requires separate current approval.

**Current recommendation:** Keep this parked until the active monitor is
terminal, then build it as a viewer-only change because the fixed model adds
real-world meaning without contaminating the running experiment.

## P2 — Let Agent C learn from accumulated exam failures

**Status:** parked; not part of the current shadow-cleanup build.

After the basic Agent C → Agent B cleanup path passes reliably, explore giving
Agent C the development-exam failures accumulated since its previous cleanup.
The purpose is to ground its three creative experiment ideas in what is
actually failing. Decide the exact evidence shape later; do not expose sealed
holdout data or let this roadmap item expand the current cleanup scope.
