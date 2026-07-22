# Cleanup Audit Rejection Repair — 2026-07-22

Result: **PASS offline; no provider call or production write.**

## Root cause

Attempt 3 solved transport coverage but exposed a contradictory semantic rule:
the compiler forced every adopted source id into an active cleanup group, while
the contract also required operational/test instructions and fragments to be
removed from language law. That forced A to retain or falsely attribute
non-language content, and Kimi correctly rejected the candidate.

The concrete turn-650 cases are:

| Source | Disposition | Reason |
|---|---|---|
| `rule-075` | exclude | operational performance/priority rationale |
| `rule-077` | exclude | incomplete demonstration fragment |
| `rule-085` | exclude | incomplete example instruction fragment |
| `rule-099` | exclude | operational rulebook-maintenance instruction |

## Repair

The strict A schema still requires every adopted source id as an assignment key.
A can now map real language law to a cleaned group or assign the reserved
`__exclude__` value with one exact reason: `operational`, `fragment`, or
`contradiction`. Deterministic code requires assignments and exclusion receipts
to match exactly, derives retained `source_ids` plus ordered
`excluded_sources`, and rejects silent, duplicate, unknown, or unjustified
exclusions before Kimi.

The Kimi prompt now treats a documented valid non-language exclusion as an
intentional disposition, not an omission. `operational_text` means operational
material that still remains in active candidate rules. A new
`revision-context` command binds Kimi's rejected audit to the exact prior source
and candidate hashes and emits only bounded, delimited critique data for one A
revision.

## Proof

- Focused cleanup suite: PASS, 18/18.
- The immutable turn-650 source and prior structured draft compile locally when
  the four sources above are explicitly excluded; all 23 adopted ids remain
  accounted for exactly once across retained and excluded receipts.
- None of the four excluded ids appears in active candidate `source_ids`.
- The real attempt-3 source/candidate/audit hashes pass the new
  `revision-context` binding check.
- Full Python suite: PASS, 71/71.
- JavaScript app suite: PASS, 27/27.
- Acceptance-harness suite: PASS, 6/6.
- Contract coverage: PASS, 78 requirements and sequential T001–T156.
- `git diff --check`, bypass searches, and changed-diff secret-shape scan: PASS.
- No OpenRouter request, production state write, bundle creation/application,
  branch push, credential/configuration change, deploy, loop resume, Crabbox
  lease, or X action occurred.

Read-only production verification at 2026-07-22 08:47 WITA confirmed
`language-loop.timer` and `language-loop.service` inactive, the VPS worktree
clean at `75cd45704f3fd74906c3ee4edb53e81187b6ff2a`, and rulebook SHA-256 still
`5938df47b587aabfb9fe7231c07d12b315a3ac3f7bdcbfee73b076fe219e4933`.
The public homepage still returned HTTP 200 and `/human` still returned Vercel
404. These checks were read-only.

T120 remains open. A new paid call should occur only after an exact live-change
approval for one DeepSeek revision using this bound feedback and one conditional
Kimi audit under the existing additional/cumulative spend caps.
