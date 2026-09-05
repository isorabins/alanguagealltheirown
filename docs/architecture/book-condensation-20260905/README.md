# The full book, condensed and tested

**21,492 → 4,142 tokens: 80.7% smaller.** The candidate has 14 sections and 2,979 operative words, down from 15,052. These are the full adopted book and current compiled candidate, measured using the experiment's DeepSeek token-probe method—not estimates and not the earlier 12-rule fixture.

Read [the condensed book](BOOK.md). It is a **provisional editorial candidate**, not the active language. [The conflict review](REVIEW.md) names the proposed changes instead of silently treating them as equivalent. All 83 adopted records are accounted for: 78 map into candidate sections; five contain only procedural statements retained in source history. [The coverage ledger](coverage.tsv) maps the individual obligations, exceptions and conflicts.

## What the tests showed

Three revisions were compared through real DeepSeek encoding and fresh Kimi decoding, using the entire old book and the same 22-case input. Old and candidate received the same experiment prompts, models, temperatures and output ceilings. A separate authored decoder fixture exercised five compression mechanisms. No production state was changed.

| Evidence | Old book, final comparison | Current candidate |
|---|---:|---:|
| Operative book tokens | 21,492 | 4,142 |
| Literal/marker assertions | 73/78 | 78/78 |
| Expected 22 output lines | Yes | Yes |
| Raw-source delimiter count checks | 0/3 | 3/3 |
| Exact decoder diagnostic lines | 0/15 | 6/15 |
| Encoded payload tokens; original = 320 | 332 | 373 |

The shorter book reduces the language instructions supplied to models. It **does not yet make this message shorter**: the current candidate's encoded message is 16.6% larger than the original. The old book is 3.8% larger in this run. These are different measurements.

The first candidate echoed transmission wrappers. The second still emitted unwanted definition contents and lost directive markers in list compression. The final candidate clarifies sender/receiver roles, consumes definitions, and explicitly preserves directive prefixes. Its normal reconstruction retains the checked facts, relationships and markers without added wrappers; complete manual reading found no changed action or invented factual content in this sample. This is limited evidence, not a general fidelity score.

The stricter checks still expose failures:

- Pattern/list/macro diagnostic decoding retains wrappers on nine of fifteen lines.
- The encoder leaves the allocation verb outside the required full allocation bundle.
- It leaves `then` outside the temporal bundle and uses list items without required identifier backticks.

The old book also behaves inconsistently across the three comparisons. We retain every attempt rather than selecting a favorable baseline. [The results receipt](comparison-results.json) includes all outputs, counts, versions and usage. Large raw prompts and provider receipts are retained in the ignored local evidence archive identified there.

## What is protected and what is not proved

Offline checks verify the frozen source hash, all 83 records, legal compilation, referenced clauses and unchanged canonical source. Targeted corruptions demonstrate sensitivity of all 81 literal/marker/delimiter assertions. The independent reviewer read all 83 adopted texts and verified the preservation fixes; see [the review receipt](cold-review.md).

Substring checks can still miss a reversed instruction or an added fact. Manual reading covers this particular reconstruction, not all possible inputs. This is **not atomic testing of every language rule**, a full development/held-out benchmark run, or a C/B adoption gate. Mandatory encoder syntax already has observed failures.

Two ambiguous shortcuts—templates and definition-free prefix reuse—are disabled in the candidate and explained in the review. Other provisional decisions address incompatible preservation rules, overlapping spans, escaping, aliases and expansion order. These choices need resolution before adoption; neither compiler success nor a shorter book authorizes replacing the experiment's language.

## Cost, source and delivery

This phase used **$0.12091884160**, bringing the shared local-test spend to **$0.50342281725 of the approved $1.00**. All 36 HTTP attempts in this phase have settled receipts; none is outstanding. No API credential is stored in these artifacts.

Automatic review initially blocked the provider comparison on a privacy premise. An anonymous download of the repository's public source at commit `493a464359c4d11ca8562930b30ca1fe817b4d1e` matched the local file byte for byte (`53ffb801…abc2`), resolving that premise; the bounded comparison was subsequently approved. Only public language text, its editorial condensation and synthetic examples were sent to the experiment's existing provider.

**Recommendation:** keep this as the concrete reference candidate and fix the demonstrated syntax/compliance failures before connecting it to automatic cleanup. The original rulebook, pending motion, archive and active language are unchanged. Future automation was not redesigned in this phase.

## Reproduce locally

From this checkout:

```sh
python3 tests/acceptance/book-condensation/check_candidate.py
python3 tests/acceptance/book-condensation/compare.py --offline
```

These checks are free and do not apply the candidate. `check_candidate.py --write` rebuilds only the review artifacts after an intentional book edit; a changed source hash requires a fresh source review. Paid `compare.py` requires an in-process `OPENROUTER_API_KEY`, a new evidence directory, and the existing shared budget ledger; see its CLI. Do not start a new budget ledger to bypass an exhausted allowance. The private bootstrap script used the existing managed secret loader and wrote no secret file.
