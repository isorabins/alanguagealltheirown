# Cleanup Attempt 4 — Feedback-Bound A Revision Rejected Locally

Date: 2026-07-22 WITA

Result: **FAIL at A validation; T120 remains open.**

The approved DeepSeek V3.2 revision was schema-bound to the immutable turn-650
source plus the exact attempt-3 candidate and rejected Kimi audit. The source,
prior candidate, and prior audit hashes were respectively
`57fbf58ea571eb6de76059e46da5ceb3eb918f6f8c047e7b23a8d01e46c85606`,
`251277000330b11f508db518dc40bd024209da6d75c5adfe12da3f63201bed10`, and
`17746877ddb24125cb2afe3939ae202a7aee0cbdc3a3c337a5ef5355a77f6713`.

DeepSeek returned all three required schema fields, 23 assignments, 17 groups,
and three explicit exclusions. The deterministic compiler then rejected the
draft because the active group `rulebook_maintenance` retained the operational
term `rulebook`. The fail-closed boundary stopped before candidate creation.
The conditional Kimi K2.6 audit was therefore not called, and no bundle or diff
was created.

The one provider call cost `$0.001660016` by provider metadata and
`$0.005664400` under conservative accounting. Cumulative G4 spend is now
`$0.021357557` actual and `$0.029000851` conservative, below the approved
`$0.10` additional and `$0.12` cumulative ceilings. The raw response was saved
atomically outside the repository with mode 0600 before parsing; its SHA-256 is
`0908fdcc0b6e974dadc2b9c6417cc3abddfb303838c7f768e49d46a75a1ae31e`.

Post-stop readback verified `language-loop.timer` and its service inactive,
production `main` clean at
`75cd45704f3fd74906c3ee4edb53e81187b6ff2a`, and the rulebook file still at
SHA-256 `5938df47b587aabfb9fe7231c07d12b315a3ac3f7bdcbfee73b076fe219e4933`.
No production state, credential, configuration, deployment, DNS, Crabbox, X,
merge, main-push, or loop-resume action occurred. The single approved attempt
is consumed; no retry is authorized.
