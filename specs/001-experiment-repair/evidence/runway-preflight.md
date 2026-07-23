# Approval, Rollback, and Evidence Runway

| Gate | Depends on | Authorized action | Rollback / safe stop | Required evidence |
|---|---|---|---|---|
| G0 | approved spec/plan/tasks | offline implementation only | discard feature worktree | local tests, scoped commits |
| G1-G3 | clean remote baseline | preservation, invariant, offline features | source checkout remains untouched | hashes, fixtures, offline receipts |
| G3A | approved Crabbox addendum and T107 branch/PR gate | verified local CLI, reusable skill, repo runner, off-production fixture | remove only scoped local artifacts after review | checksum, dependency, skill validation, fixture evidence |
| G3B | exact coordinator/provider/lease phrase | isolated Cloudflare coordinator and one CPX32 Germany lease within `$2` | coordinator teardown plus provider zero-lease verification | browser-restart MP4, proof bundle, TTL/cap/spend/teardown receipts |
| G4 | exact pause/paid-cleanup phrase | pause timer; two bounded scratch model calls | keep old rulebook active; restart only by later gate | service/snapshot hashes, A/B/diff bundle |
| G5 | exact credential phrase | create Redis/password/session/public-key/WAF configuration | remove new resources or restore prior environment | metadata without secret values |
| G6 | exact SHA/bundle phrase | integrate reviewed commit to `main` | known pre-change commit | remote SHA and clean diff |
| G7 | exact deploy phrase | deploy viewer/functions | named prior deployment | route and deployed-SHA receipt |
| G8 | exact cleanup-apply phrase | apply reviewed replacement only | immutable pre-cleanup snapshot | original/A/B/diff/hash/application receipt |
| G9 | exact resume phrase | resume timer and observe one turn | immediately pause on warning | timer, turn, state, provider health |
| G10 | exact bounded acceptance phrase | real production acceptance and temporary failure controls | restore all keys/config/test data | row-level PASS/FAIL/BLOCKED matrix, screenshots, continuous video |
| G11 | one exact phrase per X action | correction, explainer, pin, or individual follow | no implicit retry or additional action | real profile and provider receipts |
| G12-G13 | all prior evidence | visible acceptance and closeout | overall result remains BLOCKED/FAIL if anything is incomplete | cleanup, independent receipts, convergence |

On 2026-07-21 Iso approved the contract checkpoint `d23dae4` and T107–T117,
including the same draft PR, least-privilege Cloudflare/Hetzner setup, isolated
coordinator, and at most one CPX32 Germany lease with an eight-hour TTL and a
hard `$2` ceiling. The approval excludes product deployment, production loop or
state changes, product credentials, DNS, X actions, provider switching, merge,
and any push to `main`; any identity, security, billing, or cleanup uncertainty
is a hard stop.

## T118 current production readback

Checked read-only at 2026-07-21 15:35 WITA:

| Boundary | Verified current value | Rollback / stop |
|---|---|---|
| VPS checkout | clean `main` at `75cd45704f3fd74906c3ee4edb53e81187b6ff2a`, matching upstream; commit subject `turn 650` | do not pause if head or cleanliness changes before approval is acted on |
| Timer | `language-loop.timer` loaded, enabled, active/waiting; last trigger 15:30 WITA exited 0; next trigger 15:45 WITA | G4 pauses timer; old rulebook remains active; resume requires G9 |
| State snapshot hashes | meta `0176bbb2cac25a52afa4808bdc2e0e3b5e00133a9685dc20680c07a6b48c2373`; rulebook `5938df47b587aabfb9fe7231c07d12b315a3ac3f7bdcbfee73b076fe219e4933`; conversation `694b353861d1bbda12e3dafa4d6cc68ffd4306393f59075246c1ec56861882a5`; tweet state `12cebb0cbe043c4abe4279597af20fb1d03f6a684b7d9ecd1c0c688814255421` | G4 copies after pause and fails closed if the approved head is no longer current |
| Reviewed feature | draft PR 1 head `83cdfa47a4646acb8e9430e550cd08dc5347332a`; not merged | production remains on old `main` through cleanup review |
| Production deploy | Vercel `dpl_6rrcd4YdGMTYkcUdEUsCQan7qQCS`, Ready; `alanguagealltheirown.com` HTTP 200 | exact rollback deployment for future G7 |
| Production env | only `OPENROUTER_API_KEY` exists by name in Vercel Production | G5 creates separate scoped resources; no value inspected or printed |
| Scratch cleanup spend | one DeepSeek V3.2 cleanup plus one Kimi K2.6 audit; recommended hard cap `$1.00` total | stop before a call that could exceed cap; production key currently has no provider-side key cap, so the runner must enforce this cap locally |

Current official OpenRouter list prices observed for budgeting were DeepSeek
V3.2 `$0.2288/$0.3432` and Kimi K2.6 `$0.67/$3.39` per million input/output
tokens. The `$1.00` two-call ceiling is deliberately conservative. No paid call,
pause, deployment, credential, state, or X action occurred during T118.
