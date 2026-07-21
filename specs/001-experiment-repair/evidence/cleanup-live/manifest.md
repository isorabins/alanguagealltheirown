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
