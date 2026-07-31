# Benchmark fidelity diagnosis

- **Status:** Parked for detailed design
- **Captured:** 2026-07-31 WITA
- **Evidence snapshot:** commit
  `8fbbb4a9ed1f62f15cb2511601268c963fa2567c` (`turn 1257`)

## Purpose

The experiment is intended to discover whether two agents can create a shared
rulebook that carries meaning more efficiently than ordinary language. The
current five frozen benchmarks are a useful foundation, but their displayed
fidelity percentages do not yet answer that question reliably. This note
preserves the diagnosis reached on 2026-07-31 so a later design session can
settle the correction without reconstructing the audit.

This is not an approved build specification. It records what is wrong, what a
correct test needs to establish, and which choices remain open.

## Evidence reviewed

The audit used the pinned [`benchmarks/v1.json`](benchmarks/v1.json), the latest
B1–B5 events in [`state/conversation.json`](state/conversation.json),
[`prompts/grader.md`](prompts/grader.md), and `score_judgment()` in
[`rulebook.py`](rulebook.py). The interactive lesson was navigation only.

The recorded arithmetic matches the implementation:

| Benchmark | Recorded | Audit finding |
| --- | --- | --- |
| B1 Event prose | 23/24 = 96 | The alleged missing Monday deposit deadline is present in the decode. Under the current key this is 24/24. |
| B2 Equipment procedure | 24/27 = 89 | The judge correctly caught `22.5 → 225 MPa` and `20.3 → 203 MPa`, but equal weighting makes these action-changing errors look minor. The vessel identifier also lost its hyphen. |
| B3 Farming data | 21/22 = 95 | The missing `v4_final` prescription-map tag is real. The key nevertheless omits material context and duplicates or bundles some requirements. |
| B4 Retail prose | 24/25 = 96 | The decode loses the instruction to move the seafood only after the log pull and initial coil assessment. The key still bundles and repeats conditions. |
| B5 Software task | 32/32 = 100 | The perfect score is false. The decode drops the pre-check-success condition before the bandwidth branch and omits how long staging dataflows must remain paused. |

No benchmark recorded an invented claim. The scoring function counts every
survived answer-key item equally and adds inventions to the denominator. It
does not distinguish a harmless contextual omission from a tenfold pressure
error.

## Diagnosis

### The source of truth is uneven

Several answer-key items bundle facts that can fail independently, repeat the
same condition or identifier, omit material source meaning, or harden ambiguous
language into a more precise fact than the original supports. B5, for example,
turns the original's ambiguous `350 gigs` into `350 gigabits`; the original
also says two checksum digits were flipped even though only the final digit
changes. A judge cannot make the evaluation correct when its grading contract
is internally uneven.

### The judge can issue unsupported verdicts

The grader is told to locate decoded evidence, but the canonical event stores
only aggregate survived counts plus corrupted and missing summaries. The B1
and B5 errors show that structural coverage validation does not guarantee a
semantically correct verdict. Future verdicts need inspectable evidence.
Literal quantities, units, deadlines, and identifiers should not depend only
on a language model's impression.

### One percentage hides the failures that matter

The current number honestly means only "equal-weight answer-key coverage." It
does not mean that the reconstruction is safe to act on or that the most
important meaning survived. B2 is the clearest example: two tenfold pressure
corruptions cost only two of 27 equally weighted items, leaving a reassuring
89 even though the reconstructed procedure is operationally unusable.

### The frozen suite does not isolate the rulebook

B1–B5 can show whether a later rulebook regresses on familiar material. They
cannot by themselves show that the rulebook caused the performance. Strong
models may compress and reconstruct the same messages in ordinary English, and
the agents receive repeated benchmark feedback as the language evolves. A
small ordinary-English comparison and occasional unseen material are needed
before claiming that the rulebook itself generalizes or adds value.

### Compression has two different meanings

The current token delta describes the encoded message body. A real-world claim
also has to account for the rulebook context required by the encoder and
decoder. Message-channel compression can still be artistically and technically
interesting, but it must not be presented as total communication or API-cost
savings without a separate, explicit calculation.

## Working direction

The smallest credible structure appears to be:

- preserve the five frozen messages as a permanent regression suite after a
  human audit of each original and answer key;
- represent required meanings atomically, preserving conditions and scope, and
  identify the small subset whose loss or corruption changes the action;
- retain decoded evidence for every semantic judge verdict, with deterministic
  checks for exact values where practical;
- report critical pass/fail, ordinary semantic coverage, and compression as
  separate results instead of forcing them into one fidelity number;
- run an equivalent ordinary-English compression control so performance can be
  attributed to the rulebook rather than generic model summarization;
- use a small unseen check occasionally so the frozen regression suite is not
  mistaken for evidence of generalization; and
- report message-body savings separately from any total-cost or multi-exchange
  projection.

This direction should reuse the current benchmark runner, canonical event
history, grader, and viewer. It should not introduce a general-purpose
evaluation service or a large test corpus.

## Decisions intentionally left open

The detailed session still needs to settle what qualifies as critical, the
answer-key schema, which literals receive deterministic validation, how the
ordinary-English control gets an equivalent compression target, when unseen
material is introduced, whether the existing percentage remains visible, and
which token costs belong in the experiment's public claim. Those decisions
must be agreed before code, fixtures, or viewer copy change.

## Boundary

This note and its roadmap entry are documentation only. They do not authorize
changes to the five benchmarks, prompts, scoring, state schema, scheduled
experiment, providers, public viewer, timers, deployment, or published claims.
