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

The current authorization includes a `$2` maximum new-infrastructure ceiling but
still stops before the updated Spec Kit contract, T107 branch push/PR, provider
account/security work, coordinator deployment, or lease provisioning. No
production loop, state, application credentials, deployment, X account, or
`main` mutation is authorized by the Crabbox approval.
