# Sol high local compaction comparison — 2026-09-06

Sol produced shorter encoded messages, but Astra's retained candidate preserved
more required meaning on every tested message. Neither candidate passed any of
the five complete meaning tests. Both remain unadopted.

## Approved intent and authority

Iso explicitly clarified that B's cleanup comments are advisory: C may correct or
dismiss them and owns the final editorial decision. A B rejection must not veto
adoption. The existing strict meaning exams remain required. Iso then requested
Sol (`gpt-5.6-sol`, high reasoning) for a local compaction and judgment comparison.

This trial used that authority, with the same full frozen source as the prior live
Astra attempt. It did not change production code, live model configuration, or the
active book. The current production admission module still contains a final B
approval gate that conflicts with this clarification; that implementation repair
remains outstanding. The local shadow helper already supports C overruling B.
Its C-call ceiling was set to three in the trial process only, leaving room for a
structural correction and a subsequent C final decision. Sol needed two calls;
B raised no objections, so no post-advisory revision was needed.

## Real provider evidence

| Measurement | Sol high | Saved Astra medium draft |
|---|---:|---:|
| Operative book tokens in this trial | 4,098 | 3,826 |
| Book reduction from 21,492 tokens | 80.93% | 82.20% |
| B semantic comments | Pass, no findings | Prior review: six findings |
| Fully passing meaning exams | 0 / 5 | 0 / 5 |
| Valid judgments | 5 / 5 | 5 / 5 |
| Required meaning coverage range | 86–93% | 90–97% |
| Total original message tokens | 2,259 | 2,259 |
| Total encoded message tokens | 1,907 | 2,541 |
| Aggregate message-body savings | 15.58% | −12.48% |

| Frozen message | Sol coverage | Astra coverage | Sol encoded tokens | Astra encoded tokens |
|---|---:|---:|---:|---:|
| B1 Event | 87% | 90% | 413 | 792 |
| B2 Equipment | 93% | 97% | 399 | 434 |
| B3 Farming | 89% | 93% | 353 | 476 |
| B4 Retail | 90% | 94% | 331 | 394 |
| B5 Software | 86% | 90% | 411 | 445 |

Sol's draft measured 4,102 tokens before the application representation assigned
rule IDs; the actual applied representation measured 4,098. It has 17 contracts
and exactly three nonoperative ideas. No tokens were estimated from character
length: the existing DeepSeek probe mechanism measured both books and messages.
The small difference from Astra's earlier 3,828 count is retained honestly rather
than replacing the measurements from this fresh trial.

The frozen source hash is
`6f30e9f940dd013e97b1335d02ce1e0163c781e553443f538c4da9f53aecaed8`.
The saved Astra candidate hash is
`8ff5ad08f64bb8cad062b5d9b81a3d186673397f320aef6af083d3467eeac383`.
Sol's final candidate hash is
`2a2d2fd62ddd528c6a1575031245cae34eedde574c19d107c09dce7bacb4f65b`.

## Limits and setup history

This is one sample of each book, not a statistical model ranking. The Astra draft
was retained from the earlier run; it had not received a post-B revision because
its two-call allowance was exhausted. Sol got up to three calls, although only two
were used. Both first drafts had the same exclusion/assignment structural error.
The encoder, decoder, grader, frozen messages, and existing strict judge/repair
logic were held constant for the fresh exams. Message behavior depends on those
models as well as the book; the scores do not isolate C as the sole cause.

The first local runner stopped after Sol completed because the runner's test meta
lacked cost-accounting cutover fields. The completed response and successful
Codex terminal receipt survived. After initializing local accounting, the exact
request-bound response was replayed without a new model generation or charge.
The initial runner failure, replay, correction, and all raw judgments remain in
the evidence folder. No model failure was hidden or relabeled as success.

Sol ran on the Mac using Codex 0.153.0 and the existing ChatGPT login. Paid Kimi and
DeepSeek requests went through a task-specific SSH bridge using the existing
server session's reserving transport and turn writer lock. The bridge made no
canonical state changes. API cost for this trial was $0.1170360473; the shared $2
session stood at $0.27707658435 at the final trial request. That shared total may
increase as the independently running experiment continues. Codex subscription
usage is separate from API dollars; no claim of free subscription usage.

## Evidence and next decision

The adjacent [machine-readable receipt](sol-comparison-20260906-receipt.json)
contains measurements, hashes, and failures. Full prompts, response receipts,
both books, all ten exam events, and the local runner are retained under
`tests/acceptance/local-c/.evidence/sol-comparison-20260906/` (ignored local data).

Use Sol for the requested next C iteration, but do not describe this model swap as
solving compaction. Feed the demonstrated meaning losses into the next revision
and require the same five tests before adoption. Production migration to Sol high
and correction of the B veto remain unimplemented by this local experiment.
