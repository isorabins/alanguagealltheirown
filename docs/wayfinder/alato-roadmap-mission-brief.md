# ALATO roadmap Wayfinder mission brief

This is the durable evidence packet for the ALATO roadmap Wayfinder. It exists
so a later medium-reasoning interview can make decisions from the same facts as
the initial high-reasoning read instead of reconstructing the project from chat.

Canonical map: [Wayfind the ALATO roadmap without regressions](https://github.com/isorabins/alanguagealltheirown/issues/29)

## Confirmed destination

Produce a small, ordered, implementation-ready decision contract for the three
known ALATO roadmap changes, with a semantic regression contract that preserves
the current autonomous and public system. Wayfinding ends when the decisions,
dependencies, tests, and release boundaries are clear; implementation and live
changes remain outside the map.

Confirmed by Iso on 2026-08-01 WITA. The ordered contracts are active-request
repair, benchmark correction, corrected exam feedback, and the 20-exchange cost
projection.

## Confirmed interview decisions

### Active legislative feedback lifecycle

Active legislative feedback is Agent B's exact typed request for the current
open motion. It survives Agent A's revision, structural retries or failures,
process restarts, and unrelated no-motion outcomes. A newer request supersedes
it; adoption or rejection of the matching motion clears it. No transcript or
event-window replay is restored.

### Benchmark result model

Each benchmark reports critical-meaning pass/fail, total semantic coverage,
and message-body savings as separate results. A run qualifies as successful
compression only when every critical meaning survives, semantic coverage is
100%, and the decode invents nothing. A high average never overrides an
action-changing failure.

### Control and unseen-test boundary

Each corrected B1-B5 message receives one matched ordinary-English control run,
stored as a versioned frozen baseline. Scheduled turns continue to run one
ALATO development exam only. The five controls are rerun only if a benchmark,
model, tokenizer, compression instruction, or token budget changes.

No recurring unseen-test system is built. Before a major generalization claim,
the operator manually runs three private messages, one prose, one procedure,
and one task, through matched ALATO and English paths. Their answer keys are
written before execution; the messages stay outside the repository and agent
feedback; only the aggregate result may become public.

### Twenty-exchange projection boundary

The projection remains unavailable until one complete corrected B1-B5 cycle
qualifies under the benchmark result model. It then shows ALATO and the matched
frozen-English projection side by side. ALATO's added value is only the
control-adjusted difference, not its standalone percentage against uncompressed
English. Every number remains a fixed hypothetical rather than provider
telemetry or an API-bill claim.

### Regression and release boundary

Regression protection reuses the existing Python and Node runners plus one
small path-filtered GitHub Actions workflow. Roughly ten end-to-end semantic
scenarios exercise the real prompt assembler and state machine; CI makes no
provider calls and no new testing framework is introduced. After offline gates
pass, one separately approved off-live real-model smoke may check the exact
assembled prompt. Merge, deployment, timer, provider, X, and live-state actions
remain separate release steps.

## Evidence snapshot

- Repository snapshot: `749806b40c9ac1f0dede0fda35f2ab13169669f0`
  on 2026-08-01 WITA, containing generated state through turn 1316.
- Roadmap source: `ROADMAP.md` on `main`, plus open documentation PR
  `Document benchmark fidelity diagnosis` at `ca723e4b5d7b07833cf7ce8cc59c4fac41c855ae`.
- Regression history: `3773732` and `5cd0169`, merged through `Recover valid
  legislative turns and expose paused runtime`.
- Offline baseline at the snapshot: 144 Python tests, 36 Node tests, and the
  historical 115-requirement/210-task coverage check all passed.
- Current Claude Sonnet 4.6 standard global prices in the cost roadmap still
  match Anthropic's price sheet effective 2026-05-12: $3 input, $15 output,
  $3.75 five-minute cache write, and $0.30 cache read per million tokens.
  Primary source, accessed 2026-08-01:
  https://www-cdn.anthropic.com/files/4zrzovbb/website/5678bc2f5978e5bcd4f1fe7c14b2c72284dcf9f8.pdf

## Current system at decision resolution

The Python loop is the sole canonical writer. Every scheduled turn rebases the
VPS checkout onto `main`, pulls collaboration best-effort, performs one
legislative action or development exam, atomically writes JSON state, and
commits generated state back to `main`.

Canonical state is complete and git-backed. Redis is transport for human and
visitor collaboration, not authority. X publishing is an independent hourly
service with state outside the checkout, so it cannot stop or mutate the core
loop. The public viewer is static HTML plus Vercel functions and reads sanitized
state from `main`; its production deployment is a separate release surface.

This creates one unusual delivery constraint: `main` advances with generated
turn commits while feature work is open. Every implementation branch must begin
from a fresh fetch, avoid generated state, rebase before review, and keep merge,
timer, VPS, Vercel, provider, X, and live-state actions as explicit release
gates.

## Verified regression

Prompt compaction preserved complete canonical records but removed operative
meaning from fresh legislative prompts.

At turn 1316, canonical state contained an active request for `rule-149`:

> Test whether replacing 'and', 'or', 'but' with '+', '/', '!' reduces tokens
> without causing ambiguity in mixed lists and conditional logic before
> adoption.

An offline assembly of the next Agent A prompt from that exact snapshot showed:

- active request present in canonical state: yes;
- active request present in the fresh Agent A prompt: no;
- latest B1 exam at turn 1314 present in canonical history: yes;
- its turn, benchmark name, and result present in the fresh prompt: no; and
- assembled prompt size: 61,209 characters.

The regression arrived in two steps. `3773732` introduced a compact receipt
projection that excluded `attempted_action`, which removed B's typed
`REQUEST.focus`. `5cd0169` then removed the recent event window, which also
removed bounded development-exam feedback.

The suite passed because it protected storage integrity and prompt size while
asserting the missing meaning as desired absence. It still tests that the
unused `render_window()` helper can render an exam, but the real
`assemble_legislative_prompt()` path explicitly asserts that the event window
and live-test receipt are absent. This is a semantic acceptance failure, not a
lack-of-test-count failure.

## Roadmap inventory and corrected dependency order

### Restore active legislative feedback

This is a small, urgent repair. Derive the one active request from canonical
receipts for the current open motion and include it in the real assembled
prompt for A, then B after revision, until supersession or settlement. Do not
restore transcript replay.

### Make B1-B5 measure rulebook performance

The open diagnosis shows false B1 and B5 verdicts, tenfold B2 pressure errors
hidden by equal weighting, uneven answer keys, and no ordinary-English control.
This is not implementation-ready, but it is bounded: correct the five fixtures,
separate critical failure from semantic coverage and compression, retain
verdict evidence, add one equivalent English control, and keep unseen material
operator-held.

### Restore development-exam feedback to the legislators

This is currently bundled into the first roadmap item, but it should not ship
before the benchmark correction. Feeding known-untrustworthy scores back to the
legislators would make the repaired control loop learn from false evidence.

### Project conversation cost across 20 exchanges

The formula and current Claude prices are mechanically coherent. At the
snapshot, completed cycle 5 averaged 31.8% body reduction and the adopted
language used 2,013 tokens, producing the roadmap's rounded 31% projection.
That number can coexist with action-changing semantic failures, so it should
not become a headline metric until the benchmark's critical-fidelity gate is
credible. It must remain a fixed hypothetical, never actual provider savings.

Recommended order:

1. Restore active legislative feedback.
2. Correct the B1-B5 measurement contract.
3. Feed the corrected development-exam receipt to the legislators.
4. Add the 20-exchange projection only when the qualifying meaning-preservation
   rule is explicit.

## Minimal regression contract

The roadmap's proposed 44 new tests are disproportionate to these changes.
Use one small semantic suite around the real prompt assembly and state machine:

1. A current open motion carries B's exact request into the next A prompt.
2. The same request survives A revision and reaches B.
3. Supersession replaces it; adoption or rejection clears it.
4. Structural failure, restart, and an unrelated target do not clear or leak it.
5. The latest qualifying development-exam receipt reaches both roles and is
   replaced only by the next qualifying receipt.
6. Invalid or older-language evidence is labeled truthfully.
7. Canonical state and event hashes remain unchanged by projection.
8. Raw payloads, answer keys, deliberation, transcript replay, and holdout data
   remain absent.
9. Component caps and the complete assembled-prompt ratio fail closed before a
   provider call.
10. GitHub CI runs the established offline commands for code changes and ignores
    generated state-only turns.

Prefer scenario tests that cover a full lifecycle over a matrix of overlapping
projection tests. The production-shaped fixture must call
`assemble_legislative_prompt()`; helper-only tests are insufficient.

## Completed thirty-minute interview

Iso confirmed all six recommended decisions on 2026-08-01 WITA:

1. Confirm the proposed destination and the four-step dependency order.
2. Confirm the minimum behavior the active-feedback repair must preserve.
3. Settle the benchmark result model: critical pass/fail, semantic coverage,
   and message-body savings as separate outputs.
4. Settle the English control and operator-held unseen-test boundary.
5. Settle when the 20-exchange projection is allowed to appear and what it may
   claim.
6. Confirm the ten-point regression contract and release boundaries.

## Completed Scoring V2 decision

Iso approved [Review one concrete corrected B1-B5 evidence contract](https://github.com/isorabins/alanguagealltheirown/issues/31)
on 2026-08-01 WITA. Its resolution is the authoritative Scoring V2 contract:
corrected atomic meanings, evidence-backed verdicts, invalid-judge handling,
V1/V2 history, matched frozen English baselines, and the manual unseen-test
boundary. The decision ticket and parent map are closed with no remaining fog.

The receipt, comparative viewer, and regression-policy tickets were closed as
mis-scoped Wayfinder work because Iso already settled their product decisions.
Their exact schemas, tests, and execution waves now belong in `$to-spec` and
`$to-tickets`; the Wayfinder map authorizes no implementation or live change.

## Out of scope

- A general evaluation platform or large benchmark corpus.
- Restoring full transcript or event-window replay.
- Replacing the existing single-writer, git-backed state model.
- Implementing roadmap code, changing prompts or benchmarks, calling a
  provider, changing live state, merging, deploying, restarting timers, or
  publishing a new public claim during Wayfinding.
