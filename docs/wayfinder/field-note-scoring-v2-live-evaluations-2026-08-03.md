# Field note: Scoring V2 production evaluations after release

## Why this note exists

Production Scoring V2 exams are not consistently returning usable 100%
semantic-coverage results. That sentence combines two materially different
conditions: some provider judge outputs violate the evaluation evidence
contract and are invalid, while other judges are valid and truthfully expose
meaning lost by the language. The next diagnosis must keep those classes
separate.

This note extends the completed 12-hour timeline at
`/Users/isorabins/CrabboxEvidence/alato-roadmap-live-20260801/monitoring/timeline.md`.
It does not replace the authoritative Scoring V2 resolution in issue #31 or
the release contract in issue #35.

## Current production sample

The last 20 scheduled V2 exams visible in canonical state through turn 1497
(cycles 7–10) contained 10 valid and 10 invalid judge results. Two valid exams,
B1 at turns 1440 and 1470, reached 100% semantic coverage and compression
success. The other valid exams produced 86–97% coverage or, for B1 at turn
1485, 97% coverage.

Preparation of this note used read-only canonical state and service receipts.
It made no provider call and changed no live state.

## Class 1: evaluator/judge conformance failures

The deterministic validator quarantined all ten unusable judge results and
preserved their prior valid V2 baselines:

- B2.12 returned `deterministic_conflict` in cycles 7, 8, 9, and 10.
- B4.28 returned `deterministic_conflict` in cycles 7 and 8.
- B4.26 returned `fabricated_evidence` in cycles 9 and 10.
- B1.16 and B3.16 each produced one `deterministic_conflict`.

These are not proof that a language rule failed. They mean the provider judge's
verdict/evidence combination was not acceptable under the evidence contract.
The public event truthfully records the invalid reason, leaves score fields
null, does not replace a valid baseline, and does not emit legislative failure
feedback.

Canonical invalid events retain the rejected reason but not the rejected item
array as a scored result. The diagnosis should determine whether existing
provider receipts expose enough raw evidence to explain the repeated B2/B4
patterns. If not, lost invalid-output observability is itself a narrow
diagnostic finding; it is not permission to relax validation.

## Class 2: valid evaluations exposing language-fidelity failures

The valid results support real product findings:

- B3.10 (`v4_final`) was `MISSING` in valid cycles 8, 9, and 10. B3.21 was also
  missing in cycle 10.
- B5.26 remained `CORRUPTED` in every valid cycle 7–10. B5.25 was additionally
  corrupted in cycles 7 and 9, and other B5 atoms were intermittently missing.
- B1 proved that 100% is attainable in cycles 7 and 9, then returned a valid
  97% result in cycle 10.

These results should drive diagnosis of original → encoded → decoded meaning
loss and the adopted rules that may address it. They should not be converted to
passes by broadening literals or reducing atom specificity without evidence
that the benchmark itself is wrong.

## Decision boundary for the next task

Start offline from exact canonical exam events and implicated code/atoms. For
judge invalids, inspect `prompts/grader_v2.md`, `score_judgment_v2`, evidence
span handling, literal-set validation, and the recurring B2/B4 atoms. For valid
sub-100 results, trace B3.10, B5.26, and one B1 pass/fail contrast through the
actual encoded and decoded text.

The desired direction is truthful improvement, not a cosmetically perfect
score. Recommend one bounded repair and its regression tests. Do not add a new
evaluation framework, provider calls in CI, an English control, unseen-test
service, transcript replay, or unrelated refactor.
