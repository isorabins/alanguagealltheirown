# G4 Immutable Snapshot Manifest

Date: 2026-07-21 WITA

## Approval and pause

- Exact G4 approval received in the current conversation for production
  `75cd45704f3fd74906c3ee4edb53e81187b6ff2a` / turn 650.
- Immediately before pause: VPS `main` and upstream both matched that commit,
  the worktree was clean, and `language-loop.timer` was active/waiting.
- Immediately after pause: timer inactive/dead, service inactive/dead with last
  exit status 0, head unchanged, and worktree clean.
- The unit remains enabled but stopped. Resumption still requires G9.

## Immutable copied source

- Production source: `/root/alanguagealltheirown/state/rulebook.json`
- Feature evidence copy: `source-rulebook-turn-650.json`
- Exact file SHA-256 on both sides:
  `5938df47b587aabfb9fe7231c07d12b315a3ac3f7bdcbfee73b076fe219e4933`
- Canonical JSON snapshot hash:
  `57fbf58ea571eb6de76059e46da5ceb3eb918f6f8c047e7b23a8d01e46c85606`
- Copied version `0.249`, change count 249, 123 historical/current records,
  23 adopted source rules.

## Safe-stop state

The first A output failed validation before a candidate bundle could be formed.
Production remained byte-identical at the source file hash above. No apply
command, Kimi call, merge, deploy, credential change, or X action occurred.
The timer remains paused as explicitly approved.

Attempt 2 used the approved minimal id/text-only payload and preserved the raw
response before validation, but its candidate omitted three of 23 required
source ids. The validator stopped before Kimi. Cumulative G4 paid-call spend is
`$0.012418691`; production remains unchanged and paused. Because exact source
coverage failed twice, the contract's repeated-blocker rule stopped further
calls until the later schema-bound approach was implemented and approved.

Attempt 3 used the revised strict schema. A passed exact coverage for all 23
sources, but B returned `REJECT` with semantic findings. Final validation
stopped before a bundle existed. Actual cumulative G4 spend is `$0.019697541`
and conservative cumulative accounting is `$0.023336451`; production remains
unchanged and paused. No retry is authorized.

Attempt 4 used the feedback-bound revision contract against the same immutable
source, exact attempt-3 candidate, and rejected Kimi audit. The schema-shaped A
draft failed local operational-text validation, so the conditional Kimi call
did not occur and no candidate or bundle exists. Actual cumulative G4 spend is
`$0.021357557` and conservative cumulative accounting is `$0.029000851`;
production remains unchanged, clean, and paused. No retry is authorized.
