# Editorial review and proposed resolutions

This is an agent-authored candidate for review, not a C-authored cleanup, adopted revision, or proof of equivalence. The original archive, pending motion, and active experiment remain unchanged. The candidate condenses all 83 adopted records, not the earlier 12-rule local fixture. Historical records remain available in the original book.

## Approved work and limits

Write a smaller candidate; trace existing requirements; identify contradictions; compare old and new before any replacement. No production cutover or future automation redesign. Existing $1 local-test allowance is shared with the previous C tests, which spent $0.38250397565; it is not a fresh allowance. Paid comparison must reserve every request against that same durable budget.

BOOK.md is the readable proposed language. Its P01–P14 sections are compiled through the existing cleanup compiler into candidate.json. The metadata header is not transmitted to the models. The compiler's internal `adopted` status selects candidate rules in the isolated language view; it does not adopt them into canonical state. coverage.tsv maps every adopted record to named candidate clauses and identifies operational exclusions and changed interpretations. It is a semantic review ledger, not 83 automatically proved equivalences.

## Conflicts requiring judgment before adoption

The candidate uses these explicit provisional choices. There is no consistent interpretation that can preserve both sides of every contradiction.

| ID | Source problem | Candidate choice and consequence |
|---|---|---|
| R01 | 439 requires the entire directive/narrative line verbatim; 440 and structural compression change wording. | Preserve authority, facts, order and protected spans; allow specified compression outside them. This weakens literal whole-line preservation. |
| R02 | 441 permits `.8` for `0.8`; 588 requires exact preservation of numeric substrings. | Preserve `0.8` where measured protection applies; lose that numeric shortening permission. |
| R03 | Old ID rules mandate aliases and tokenizer-dependent handling; 615 supersedes all prior ID rules and bans internal replacement, while 665 permits identifier aliases. | Backtick standalone IDs; optional whole-token aliases with literal backticked definitions and strict savings. No internal rewriting or mandatory tokenizer-dependent aliasing. |
| R04 | Mandatory identifier and phrase boundaries overlap; old linked boundaries and delimiters conflict; 511 parentheses coexist with537 universal angle brackets. | Preserve the complete outer relationship literally, with contained-ID immunity but no inserted nested wrappers; angle brackets for descriptive attachments; later first-category linked boundary. Standalone ID wrapping is relaxed inside a larger exact phrase. |
| R05 | `<` is both comparison syntax and a wrapper; literal/nested delimiters lack an escaping grammar. | Keep affected source wording if representation is ambiguous. This preserves content but does not prove compliance with every mandatory-wrapper clause; exact grammar remains open. |
| R06 | Decoder must compare output to source it is never given. | Sender/evaluator compares both texts; receiver enforces literal expansion only. Do not claim the receiver proved equality to unseen input. |
| R07 | 547's third example deletes `if`/`because`, contrary to440/443 and its own omission categories. | Preserve explicit logical links; remove that example's permission to guess them. |
| R08 | 549 simultaneously consumes and reuses variable definitions, mixes positional and defined variables, and turns one placeholder plus three arguments into three lines. | Document its intended contract, but disable template encoding in this candidate until syntax is settled. A capability restriction, not deletion hidden as deduplication. |
| R09 | 444's noun alias underscores do not specify recovery of spaces vs literal underscores. | Use exact literal multiword definitions instead. This changes that encoding convention while preserving the content. |
| R10 | 524/668 examples show two occurrences despite a minimum of three;574 varies both quantity and target with a one-gap form and stray arguments;641/549 ID examples conflict with615. | Follow explicit repetition/arity rules; no hidden second variable; identifiers use the specific later ID protection law. Some historical example encodings become invalid. |
| R11 | 655's `$ token` cannot select an unknown earlier prefix and collides with641's identical list invocation. It also fails to carry any suffix. | Disable definition-free reuse; `$ item` requires an explicit list definition. Lose the two-instance shortcut until an unambiguous syntax is chosen. |
| R12 | Repeal/amendment prose remains adopted; some citations target non-adopted rules (635,647,649). | Remove five purely procedural rows from the operative candidate, keep the archive, rely only on actually adopted substantive text. Do not invent missing referenced law. |
| R13 | 668's whole-line macro priority also covers its supposedly distinct lists/patterns; exact source comparison is unclear before vs after added wrapper removal. | Prefer specific prefix/list or single-gap form, macro for general multi-variable whole lines; compare protected representation at expansion and original literal content after wrapper reconstruction. This is a clarified priority and verification stage. |

Two real comparisons exposed decoder echoing of encoding wrappers. The candidate now explicitly separates encoder-only wrapping from decoder-only expansion/unwrapping, consumes definition lines, and includes a complete decoding example. List prefixes explicitly retain source directive markers. This clarifies the intended decoding operation; it does not authorize a new compression mechanism.

P14 also conservatively disallows ambiguous/circular/undefined or conflicting compositions; the source lacks a complete grammar. This is a proposed interoperability restriction, not a claim that every previously possible combination remains valid.

## What the comparison can establish

An offline check proves source identity, complete record accounting, valid compilation, clause references, and that canonical source did not change. It does not prove semantic fidelity. Real provider comparison uses the existing experiment's encoder and foreign decoder, their current prompts/settings, the full adopted book versus this candidate, and the same frozen input. A fresh decoder sees only the encoded message and its book, never the source or expected literals.

The frozen input tests factual preservation, exact identifiers/numbers/times, logical links, ordering, directive markers and repetition. Literal checks have deliberately narrow claims; all-output semantics and encoded mandatory boundaries require review. Separately authored decoder fixtures exercise structural syntax, but they are diagnostic fixtures, not proof that the encoder chose those mechanisms. Neither one comparison nor a source mapping is atomic testing of every rule.

Recommended adoption position: review the specific restrictions above and the measured results first. Do not install this book merely because it is shorter or because a small sample passes. The next automation should learn from a reviewed reference candidate and these concrete counterexamples, after the language choices are settled.
