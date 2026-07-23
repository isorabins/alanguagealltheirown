# Cleanup Attempt 3 — A Coverage Pass, B Audit Reject

Date: 2026-07-21 WITA

Result: **FAIL at B audit validation; T120 remains open.**

The approved strict DeepSeek V3.2 request returned a schema-conforming draft
with all 23 required assignments. The deterministic compiler produced 10
candidate rules covering all 23 source ids exactly once, including the three
ids omitted by attempt 2. Candidate SHA-256:
`251277000330b11f508db518dc40bd024209da6d75c5adfe12da3f63201bed10`.

The one conditional Kimi K2.6 audit then returned `REJECT`, not `pass`. It
covered all 23 ids but reported one omission and five meaning changes, chiefly
loss of exact alias thresholds/examples and rule-099's explicit enumeration.
It also identified rule-075 as operational performance rationale whose removal
was appropriate, while still requiring that exclusion to be explicit. The
final validator rejected the audit before bundle creation. No replacement was
applied.

Actual provider-metadata cost was `$0.000920740` for A through DeepInfra and
`$0.006358110` for B through Decart: `$0.007278850` additional and
`$0.019697541` cumulative G4. The fail-closed conservative accounting was
`$0.010917760` additional and `$0.023336451` cumulative, below both approved
ceilings.

Raw responses were atomically preserved outside the repository with mode 0600
before parsing. Their hashes match the sanitized receipt. A scan of the raw and
repository evidence found zero credential-token, authorization-header, or
protected-environment-value patterns.

Post-stop readback verified `language-loop.timer` and its service inactive,
production `main` still clean at
`75cd45704f3fd74906c3ee4edb53e81187b6ff2a`, and rulebook SHA-256 still
`5938df47b587aabfb9fe7231c07d12b315a3ac3f7bdcbfee73b076fe219e4933`.
Production state, deployment, credentials, DNS, X, and the old rulebook remain
unchanged.
