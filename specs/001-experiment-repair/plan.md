# Implementation Plan: Experiment Repair and Public Collaboration

**Branch**: planned `codex/experiment-repair` | **Date**: 2026-07-20 WITA | **Spec**: [spec.md](spec.md)

**Input**: Approved feature specification in `specs/001-experiment-repair/spec.md`.
This plan is not implementation or live-change approval.

## Summary

Repair the experiment boundary first by creating explicit adopted-only language
views, corpus/proposal evidence separation, exact judge validation, and enforced
DeepSeek-inventor/Kimi-auditor permissions. Then add one Upstash Redis
collaboration inbox feeding the existing VPS single-writer loop, a minimal
password-protected `/human`, stateful RESEARCH/ASK/suggestions, a judged
six-message Conversation, version-pinned/capped Try It, truthful X delivery, and
an honest selectively collapsed public record.

Implementation begins only after Iso approves this artifact set, in a clean
worktree based on the then-current `origin/main`. Offline code/tests stop before
every production, credential, deploy, public, X, loop, and `main` gate.

## Documentation Context & Source Alignment

### Source-of-Truth Docs From Spec

| Source | Constraint / Decision | Plan Impact | Status |
|---|---|---|---|
| `vendor-developer-handoff-2026-07-20/BUILD-SPEC.md`, `spec.md`, and `research-crabbox.md` | Original product contract plus 55 current requirements, 23 outcomes, and remote acceptance infrastructure | Binding scope, order, DoD, Crabbox oracle, and stops | original handoff preserved; Spec Kit addendum governs T108+ |
| `REQUIREMENTS-CHECKLIST.md` | Product ambiguity resolved | No clarify interview; technical research only | aligned |
| `CURRENT-STATE.md`, `SYSTEM-MAP.md` | Competing Vercel/VPS writers are forbidden | One Redis inbox; loop remains canonical writer | aligned |
| `PROGRESS-ISSUES.md` | Core truth before collaboration/polish | Gate order follows dependency sequence | aligned |
| `OPERATIONS-RUNBOOK.md` | No casual loop, provider, state, deploy, or X commands | Fixtures/stubs until exact live gates | aligned |
| `TESTS-EVALS-VERIFICATION.md` | Visible production evidence overrides backend-only claims | Matrix, screenshots, video, receipts, cleanup | aligned |
| `.specify/memory/constitution.md` v1.5.0 | Contract, runtime boundary, preflight, commits, convergence | Reflected in every gate and task phase | aligned |
| `loop.py`, `tweet.py`, `run_turn.sh`, `viewer/` | Existing Python/Vercel/static architecture | Repair in place; no framework rewrite | aligned |

Old PRDs, the Slack ASK bridge, Composition, `:online`, dumb-script product
framing, and broad novelty/power claims are historical only and were not used as
implementation contracts.

### Official / Current Implementation Docs

| Technology / Surface | Official Source | Checked | Required Best Practice | Plan Impact |
|---|---|---|---|---|
| Vercel storage | https://vercel.com/docs/marketplace-storage | 2026-07-20 | Upstash Redis is the current standard KV integration | Single durable inbox |
| Upstash Redis REST | https://upstash.com/docs/redis/features/restapi | 2026-07-20 | Transactions/scripts are atomic; pipelines are not | Atomic enqueue/claim/ack/moderate actions |
| Vercel WAF | https://vercel.com/security/web-application-firewall | 2026-07-20 | Platform path/IP limits, not a custom limiter framework | Coarse abuse protection planned stop |
| OpenRouter web search | https://openrouter.ai/docs/guides/features/server-tools/web-search | 2026-07-20 | `openrouter:web_search`; plugin/`:online` deprecated | Bounded RESEARCH tool |
| OpenRouter keys | https://openrouter.ai/docs/api/api-reference/api-keys/create-keys | 2026-07-20 | Per-key USD limit and monthly reset metadata | Dedicated $20 public key |
| OpenRouter structured outputs | https://openrouter.ai/docs/guides/features/structured-outputs and https://openrouter.ai/docs/guides/routing/provider-selection | 2026-07-21 | Strict `response_format.json_schema` is the supported shape; `provider.require_parameters=true` prevents routing to an endpoint that ignores it | Require all adopted ids as schema properties; compile model mapping/text into candidate locally |
| DeepSeek V3.2 | https://openrouter.ai/deepseek/deepseek-v3.2 | 2026-07-20 | Slug `deepseek/deepseek-v3.2` | A/encoder/judge |
| Kimi K2.6 | https://openrouter.ai/moonshotai/kimi-k2.6 | 2026-07-20 | Slug `moonshotai/kimi-k2.6` | B/stranger/Conversation |
| Upload-Post text | https://docs.upload-post.com/api/upload-text/ | 2026-07-20 | Stable idempotency/request id, poll async, inspect `results.x`, use `x_title`; long text auto-threads | Confirmed bounded X state machine |
| Crabbox release/source | https://github.com/openclaw/crabbox/releases/tag/v0.40.0 plus `/Users/isorabins/.codex/vendor-snapshots/openclaw-crabbox/v0.40.0` | 2026-07-21 | Pin verified tag commit and macOS arm64 checksum; review source; never execute repository installers | Verified binary install plus reusable remote-test plumbing |
| Crabbox desktop/security/lifecycle | https://crabbox.sh/commands/desktop.html and pinned `docs/features/` source | 2026-07-21 | Linux X11 outer recording survives browser relaunch; env forwarding is allowlist-only; direct Hetzner TTL is not durable cleanup | Coordinator-owned lease, protected profile, proof audit, teardown receipt |
| Cloudflare Workers/Durable Objects | https://developers.cloudflare.com/workers/platform/pricing/ | 2026-07-21 | Small coordinator can remain in free allowance; isolate worker/config from upstream defaults | One shared-token worker, one active lease, no portal/custom domain |
| Hetzner pricing | https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/ | 2026-07-21 | CPX32 Germany hourly cost supports an eight-hour run below `$1` before minor extras | `$2` hard new-infrastructure ceiling, one lease, teardown after proof |

### Documentation Conflict Check

| Conflict | Sources | Decision | Owner / Stop Condition |
|---|---|---|---|
| Handoff recorded turn 537; remote advanced | handoff vs synchronized git state | Read-only preflight observed remote `main` `6c515362ef4059844a7d2aead3b96af4627a1f81`, turn 636; feature rebase still waits for the approved paused gate | Recheck again at T118 and pause gate |
| Vercel KV historical naming | older ecosystem vs current Vercel docs | Use Upstash Redis Marketplace/REST, never obsolete Vercel KV API | Recheck docs before credentials gate |
| Spec excludes database rate-limiter but requires reasonable brute-force protection | scope/non-goal vs `/human` assumption | Use Vercel WAF; do not build Redis limiter framework | BLOCKED if current plan cannot enforce approved rule |
| Existing Vercel key is shared/unverified | live env vs FR-028 | Add separate public key only after credential/cap approval | planned stop |

**Documentation Gate Result**: PASS for offline implementation; external account
and credential facts remain explicit planned stops.

## Single Product Invariant

Only the current agent-adopted rule set may govern encoding and decoding, and
every public status or claim must match verified canonical state.

## Architecture Fit Gate

**Recommended Architecture**: Repair the existing Python loop and static Vercel
site in place. Add one Upstash Redis inbox/session store shared through server-side
REST through a standalone bounded courier. The courier writes only atomic local
transport spools; the loop materializes those bounded events into append-only
`state/collaboration.json` and remains the sole writer of canonical experiment
history.

**Simplest Boring Alternative Considered**: A tiny SQLite inbox on the VPS is
simpler locally, but would require exposing and operating a new public VPS API for
Vercel. Managed Redis is the simpler whole-system path because both runtimes can
use it without another service, framework, or database admin surface.

**Existing Runtime Fit Decision**: Fit. The loop already owns state, cadence,
provider calls, publication, and git history; Vercel already owns public/static
functions. Narrow interfaces are safer than a framework rewrite.

**Switch Trigger**: Reconsider Redis only if official availability/cost blocks
deployment, atomic scripts cannot pass concurrency/restart tests, or sustained
volume requires relational querying. None is true today.

**Owner-Visible Consequence If Wrong**: Lost or duplicate answers/suggestions,
private moderation text appearing publicly, false delivery claims, or a stalled
loop. Any such result fails the invariant gate and blocks deploy.

**Acceptance Infrastructure Decision**: Use Crabbox v0.40.0 with the smallest
durable coordinator path: one isolated Cloudflare Durable Object and at most one
Hetzner CPX32 Germany X11 desktop lease. Keep the product journey and acceptance
oracle in the repository; keep generic lease, recording, proof, env allowlist,
and teardown mechanics in the local reusable skill.

**Simpler Alternative Rejected**: Local Playwright plus Xvfb/FFmpeg can record a
browser restart without taking over the visible desktop, but it does not meet
the requested remote failure boundary: the same Mac still owns execution and
cleanup. Direct Hetzner is also rejected because its TTL label is not a durable
termination owner when the local process dies.

**Acceptance Infrastructure Invariant**: No remote run starts unless provider,
account, coordinator, machine, region, projected cost, TTL, env-name allowlist,
evidence paths, and cleanup owner exactly match the approved manifest. Any
uncertainty fails closed before provisioning or browser action.

**Skeptical Architecture Review**: Required and completed 2026-07-20 by this
planning pass. Finding: PASS with conditions. Do not expose a VPS service, do not
let Vercel write canonical JSON, do not use destructive queue pops, and do not
add accounts/admin/database abstractions. Prove atomic inbox semantics and
canonical dedupe before collaboration UI work.

### Legacy And Bypass Inventory

| Surface | Old Behavior / Bypass | New Allowed Behavior | Retirement Action | Negative Proof |
|---|---|---|---|---|
| `render_rulebook` | Proposed text enters ordinary prompts | Typed legislature/language/proposal views | Replace all language callers; no legacy fallback | prompt fixture battery |
| Rule `scores` | Corpus score stamped per rule | Corpus evidence only; explicit proposal trial evidence | Preserve old fields as labeled history, stop writes | state diff + page labels |
| `probe.py` / run hook | Active dumb-script measurement/framing | Historical evidence only | Remove hook/import/current UI/prompt/economics path | runtime/page search |
| A/B prompts/parser | Same model/soft leans/unrestricted verbs | DeepSeek A inventor; Kimi B auditor; enforced permissions | Replace prompts and authority validator | forbidden-motion tests |
| Judge arithmetic | Incomplete/duplicate ids can score | Exact coverage or invalid/no score | Central validator used by loop and Try It | malformed matrix |
| `pending-notice.txt` | Single overwrite/remove mailbox | Harness notices only or retired; never collaboration queue | Box from collaboration paths | concurrency test/search |
| Vercel Try It | Shared key and version race | Dedicated capped key; version/hash check | Reject old key name in public handlers | env/key metadata + mismatch test |
| `tweet.py` | State can advance without confirmed X result | Idempotent confirmed receipt, 3-attempt block | Replace optimistic state path | timeout/partial/attempt-4 tests |
| Old docs/page | Stale roles/claims/expanded archive | Verified current copy and selective disclosure | Update only after behavior verification | visible desktop/mobile review |
| Direct production scripts | `loop.py`, `tweet.py`, deploy/apply can mutate live state | Explicit path/flags plus exact live gates | No execution during offline phase | command/evidence audit |
| Collaboration Redis calls in `loop.py` | Network outage or hang can cancel a turn | Bounded courier plus atomic local inbox/outbox spools | Remove Redis client/calls from loop path | exception/timeout/replay/restart tests |
| Legacy open proposals | Copied production proposals would permanently trip one-open guard | Cleanup terminalizes legacy proposed/reverted status with history receipt | Add migration to cleanup application | production-shaped cleanup/authority test |
| Prompt-only cleanup coverage | Two DeepSeek outputs omitted adopted source ids despite explicit lists; a later complete draft falsely had to retain operational/fractured sources to claim coverage | A returns schema-required per-source assignments plus cleaned groups or explicit reason-coded exclusions; code derives retained `source_ids` and `excluded_sources` | Retire free-form `rules[].source_ids` generation and silent omission | missing/extra assignment, exclusion mismatch, unknown/orphan/duplicate group tests |

**Boundary Result**: PASS for design; live retirement remains planned_stop until
the corresponding approved production gate.

## Technical Context

**Language/Version**: Python 3.12 on VPS; Node.js 24.x on Vercel; browser HTML/CSS/vanilla JS

**Primary Dependencies**: Existing Python `requests` 2.31; Node built-in `fetch`
and `crypto`; Upstash Redis REST; OpenRouter Chat Completions/server tools;
Upload-Post text/status API; pinned Crabbox v0.40.0 binary; isolated exact-pinned
Playwright acceptance package

**Storage**: Canonical JSON/git history, local atomic collaboration transport spools,
plus one Upstash Redis inbox/session store

**Testing**: Python `unittest`, Node `node:test`, fixture state, stub HTTP servers,
production-shaped local Vercel handlers, repository-owned Playwright visible
journeys on a Crabbox X11 desktop, continuous outer recording, and desktop/375px
human-app-testing evidence

**Target Platform**: Existing Hetzner Ubuntu VPS/systemd timer; Vercel Node 24
functions/static site; current X profile through Upload-Post; separate disposable
Hetzner CPX32 Germany acceptance desktop governed by an isolated Cloudflare
coordinator

**Project Type**: Single repository with a scheduled Python agent engine and
static/serverless web surface

**Performance Goals**: Collaboration endpoints return within 2 seconds excluding
provider calls; queue work is bounded to one research result and one eligible
delivery per turn; no change to 15-minute cadence; page remains usable at 375px

**Constraints**: No new general framework, no competing canonical writer, no
production state in tests, no uncapped public inference, no more than three X
attempts, no standalone Composition, no rolling-average reset; Redis failure or
a hanging courier cannot cancel an ordinary turn

**Scale/Scope**: Low-volume public art project; nine user stories, one human
operator, one loop worker, one Redis database, one Vercel project, one X profile,
and at most one disposable acceptance lease

## Constitution Check

### Pre-research

| Principle | Result | Evidence |
|---|---|---|
| Contract before implementation | PLANNED_STOP | Existing offline contract was approved; Crabbox addendum requires spec/plan/tasks approval before T107+ |
| Explicit scope and approvals | PASS | Non-goals and eleven planned stops below |
| Documentation context | PASS | Handoff order, source alignment, current official docs |
| Runtime boundary | PASS | Single invariant, bypass inventory, negative proofs, skeptical review |
| Clean worktree | PLANNED_STOP | Created only after plan approval from fresh `origin/main` |
| Acceptance/DoD/preflight | PASS | Gate tables, production run, evidence matrix |
| Preserve existing work | PASS | Dirty `main`, modified `PROGRESS.md`, and untracked spec/handoff recorded; no stash/overwrite |

### Post-design

PASS. Research, data model, runtime/HTTP contracts, and quickstart preserve the
single-writer boundary and contain no unresolved `NEEDS CLARIFICATION`. External
dependencies are planned stops, not assumed access.

## Gate-Ordered Definition of Done

| Gate | Command Or Visible Action | Expected Result | Evidence Artifact | Stop Condition | Cleanup / Rollback |
|---|---|---|---|---|---|
| G0 Contract | Iso approves spec/plan/tasks | Clean worktree may be created; no live authority | approval receipt | no approval | leave planning files untouched |
| G1 Preservation | Create worktree from fresh `origin/main`; copy approved artifacts only | User dirty work preserved; branch clean | git receipts + manifest | source drift/conflict | remove only new empty worktree if approved |
| G2 Invariant | Run offline adopted-only, role, judge, bypass tests | Forbidden old paths impossible in fixtures | test logs/search receipts | any failure | revert scoped branch commit |
| G3 Offline features | Run collaboration, Conversation, Try It, X state-machine tests | All P1-P3 behavior passes with stubs/fixtures | test/evidence report | invariant regression | revert gate commit |
| G3A Local acceptance tooling | Install verified Crabbox binary; build/validate skill and repo runner against a fixture | Skill and runner pass without production access or paid lease | dependency, validation, fixture evidence | checksum/advisory/test failure | remove only created local artifacts after review |
| G3B Disposable remote proof | Exact approval provisions isolated coordinator and one capped lease | Outer recording spans browser restart; proof/TTL/cap/teardown pass | Crabbox pilot bundle + provider readbacks | identity/cost/TTL/secret uncertainty | coordinator teardown; verify provider zero leases |
| G4 Cleanup preview | After live gate, pause loop, snapshot exact state, request a strict coverage-complete A draft, compile/validate it locally, then run B audit on the copy | Schema coverage receipt plus original/A/B/diff exist; production unchanged | schema/request metadata, hashes, artifacts, diff | source/schema/provider/call/compile failure | keep snapshot; resume only after approval |
| G5 Credentials | Exact approval creates Redis/session/public OpenRouter/WAF config | Required names exist; key metadata proves separate $20 monthly cap | metadata receipts without values | access/cap mismatch | remove/disable newly created config by approved rollback |
| G6 Main integration | Exact approval pushes/merges reviewed code plus pending cleanup bundle to `main` while loop paused | Remote main equals reviewed commit; old rulebook remains active | GitHub/commit receipt | branch drift/tests fail | do not merge; revert commit if approved |
| G7 Deploy | Exact approval deploys that commit | Production `/human` visibly shows pending A/B/diff while active rulebook is unchanged | Vercel id + visible page | wrong commit/env/diff | promote prior deployment |
| G8 Cleanup apply | After visible review, exact approval applies reviewed hash and pushes only that state receipt | Canonical active rulebook equals approved replacement, history preserved | screenshots, state diff/commit | approval/hash/source mismatch | restore immutable snapshot |
| G9 Resume | Exact approval resumes loop | One bounded turn succeeds under new code/approved rulebook, no duplicates/warnings | timer/turn/read-only receipts | health/invariant failure | pause timer; retain snapshot |
| G10 Acceptance authorization | Exact approval names the production test budget, natural scheduled turns, temporary failure-mode configuration/key swaps, test data, rollback, and cleanup | Visible acceptance may exercise paid/hostile/failure states only within that envelope | approval + preflight matrix | any unnamed spend/mutation/failure control | restore final config and clean test state |
| G11 Public X | Per-item approvals for correction, explainer, pin, and each follow | Each approved result visibly exists on real profile | screenshots + profile/provider receipts | missing item approval or ambiguous receipt | no retry outside bounded state machine; approved reversal only |
| G12 Visible acceptance | Human executes every matrix row on deployed site desktop/mobile with continuous video | Every row PASS and independent receipts agree | numbered screenshots, video, matrix | any FAIL/BLOCKED or contaminated evidence | visible approved test cleanup |
| G13 Convergence/closeout | Run convergence, clean git/state/queues, verify live commit | No gaps, debris, duplicates, stuck work, warnings, or dirty files | updated spec/tasks/evidence, git/live receipts | any remaining gap | overall FAIL/BLOCKED |
| G14 Launch-first core activation | Under the exact 2026-07-24 approval, preserve the existing rulebook, configure the proven collaboration/human/public-inference dependencies, keep X disabled, sync the paused VPS to reviewed `main`, deploy from `viewer/`, resume, and observe one turn | Public surfaces respond, the repaired runtime advances beyond turn 650, the timer remains healthy, and no cleanup candidate is applied | launch-first preflight, credential metadata, deployment receipt, turn/state/service receipts | credential/cap mismatch, canonical hash drift before resume, wrong deploy root, provider/service/invariant warning | restore prior Vercel deployment, disable new Production targets if needed, re-pause timer, retain turn-650 snapshot |

## Explicit Planned Stops and Approval Text

Implementation approval does not grant any live gate. At each gate the operator
must present the exact target, current commit/state, rollback, and one-time phrase.
Recommended phrase forms are:

1. `APPROVE LIVE CHANGE: create the isolated crabbox-iso-pilot Cloudflare Durable Object coordinator and scoped provider credentials, then provision at most one Hetzner CPX32 Germany lease with an eight-hour TTL and $2 maximum new-infrastructure spend; no production application action; teardown after proof`
2. `APPROVE LIVE CHANGE: pause language-loop.timer for experiment-repair snapshot <turn>/<commit> and authorize one DeepSeek cleanup plus one Kimi audit on the copied snapshot with total cap <$amount>`
3. `APPROVE LIVE CHANGE: create or change the named Upstash, human-session, WAF, and $20 monthly public OpenRouter production configuration in the reviewed preflight`
4. `APPROVE LIVE CHANGE: push and merge reviewed commit <sha> with pending cleanup bundle <bundle-id> to main while the loop is paused and the old rulebook remains active`
5. `APPROVE LIVE CHANGE: deploy reviewed commit <sha> to alanguagealltheirown.com with rollback deployment <id>`
6. `APPROVE LIVE CHANGE: apply visibly reviewed cleanup bundle <bundle-id>/<hash> to rulebook snapshot <hash> and push only that approved state receipt`
7. `APPROVE LIVE CHANGE: resume language-loop.timer on main <sha> from snapshot <turn> with the reviewed per-turn, research, and Conversation spend bounds`
8. `APPROVE LIVE CHANGE: run production acceptance <run-id> on commit <sha> within <$amount>, using natural scheduled turns and the named temporary failure-mode configuration/key swaps, test ids, rollback, and cleanup in the approved matrix`
9. One exact phrase for the final correction copy and target X profile.
10. One exact phrase for the final explainer copy, then a separate exact phrase to pin the verified post id.
11. One exact phrase per researched X account to follow.

Phrase placeholders must be replaced with verified immutable values. Paraphrases,
blanket approvals, and approval from another agent do not pass a gate.

The exact phrase
`APPROVE LIVE CHANGE: launch-alato-core-with-existing-rulebook-20260724-l4v8`
authorizes G14 as one bounded execution envelope. It supersedes cleanup-first
sequencing only: T120 cleanup generation/application and all X actions remain
deferred. It does not authorize DNS, public posting, or destructive history
rewrites.

## Convergence Closeout Gate

| Trigger | Required Spec Update | Required Tasks Update | Evidence |
|---|---|---|---|
| Any offline/preview/dry-run pass before production | Update Implementation State Ledger with exact pass and planned stop | Mark completed tasks and remaining production rows | scoped commit/test report |
| Deployed core passes before X approvals | Record site pass but overall BLOCKED on SC-014/016 | Leave X and final acceptance tasks open | deployment/site evidence |
| Any production row fails | Record FAIL/BLOCKED and latest safe state | Add only in-scope repair/retest task status; max three loops | matrix + receipts |

## Production Equivalence Gate

| Runtime Surface | Required State | Verification Command / Read-Only Check | Evidence |
|---|---|---|---|
| Reviewed branch/commit | Exact approved SHA, clean worktree, rebased on paused main | `git status`, `git rev-parse`, diff/stat | receipt |
| Deployed files/checksums | Vercel deployment built from same viewer files/SHA | `vercel inspect`, public asset/API checks | deployment receipt |
| Inbox schema | Expected namespace/scripts and empty test leases | read-only Redis metadata/count checks | sanitized receipt |
| Env/flags/secrets | Names present; no values printed; public key cap metadata exact | Vercel env names and OpenRouter metadata | redacted receipt |
| Services/workers/jobs | Timer intentionally paused/resumed at named gate; one worker only | `systemctl show/list-timers` | service receipt |
| Legacy paths/hooks | Probe hook absent; Vercel cannot write canonical JSON; no old key fallback | searches and negative tests | test receipt |
| Public/X surface | Correct domain/deploy/profile/post ids | visible browser/profile plus read-only receipts | screenshots |

## Definition-of-Done Runway Preflight

**Run Target**: Planned stop after the reusable Crabbox skill, off-production
forward test, capped remote lifecycle/recording proof, and verified teardown.
Production completion requires each later exact live/public approval.

| Dependency | Needed For | Status | Owner / Approval | Evidence Or Check |
|---|---|---|---|---|
| Current remote main | Worktree/rebase | available; `72badf9` at synchronized planning baseline, recheck required | implementer | `ls-remote`/fetch receipt |
| Dirty local `main` user work | Preservation | available, must not be stashed/overwritten | implementer | status + manifest |
| Clean worktree path/branch | Implementation | PASS; isolated `codex/experiment-repair` worktree | Iso approved plan | worktree list/status |
| Reviewed feature push/PR | Repository runner checkpoint | PASS; draft PR 1 on the feature branch | T107 approval received | `evidence/production-gates.md` |
| Crabbox v0.40.0 binary | Local acceptance plumbing | PASS; checksum-verified binary installed | Iso approved Crabbox with `$2` ceiling | `evidence/crabbox/install.md` |
| Local pinned Crabbox snapshot | Review/skill reference | available | implementer | clean exact-tag checkout + snapshot receipt |
| Cloudflare account/API access | Durable coordinator | PASS; Workers-Scripts-only token stored externally and coordinator deployed | account/security approval received | `evidence/crabbox/pilot/coordinator-deploy.json` |
| Hetzner account/project/token | Disposable X11 desktop | PASS; isolated project/token used and provider returned to zero resources | exact G3B phrase received | `evidence/crabbox/pilot/hetzner-cleanup.json` |
| Crabbox coordinator/lease | Remote proof | PASS; free idle coordinator retained, disposable lease released | exact live-change phrase received | `evidence/crabbox/pilot/` |
| `$2` new-infrastructure ceiling | Remote proof | pre-approved | Iso, 2026-07-21 WITA | current conversation + cost receipt |
| VPS SSH and repo | Snapshot/timer/state | available read-only; writes planned_stop | Iso live phrase | service/git receipts |
| Vercel project/domain | Deploy/human/Try It | available read-only; deploy/env planned_stop | Iso live phrase | project/deploy receipt |
| Upstash database/tokens | Collaboration | planned_stop; not created | Iso account/live phrase | env-name/connectivity receipt |
| Human password/session secret | `/human` | planned_stop; not created | Iso/live phrase; secret manager/environment only | names/health check, never value |
| Separate public OpenRouter key | Try It | planned_stop; absent | Iso/live phrase | key hash/limit/reset metadata |
| Private experiment key | Loop/research/Conversation | available historically; no value inspected | existing production | name/provider health receipt |
| Upload-Post/X profile | X delivery | available historically; every action planned_stop | Iso per item | profile/provider receipts |
| Browser desktop/mobile surfaces | Visible acceptance | remote fixture PASS on X11 at desktop and 375px; production remains separately gated | implementer | pilot screenshots and matrix receipt |
| Continuous recorder | Cross-turn evidence | PASS; one 300-second H.264 outer-desktop MP4 visibly spans browser restart | implementer | `evidence/crabbox/pilot/video-inspection.json` |
| Natural test data and cleanup | Acceptance | design available; live use planned_stop | implementer/Iso for public effects | matrix ids/cleanup plan |
| Rollback state/deployment/commit | Every live gate | must be captured immediately before gate | implementer | hashes/deployment id |

**Preflight Result**: PASS for the remote-pilot target; T107–T117 completed with
the free coordinator idle and provider resources at zero. The production target
remains NOT_READY and no production DoD can be claimed without G4–G12 approvals
and evidence.

## Project Structure

### Documentation (this feature)

```text
specs/001-experiment-repair/
├── spec.md
├── plan.md
├── research.md
├── research-crabbox.md
├── data-model.md
├── quickstart.md
├── contracts/http-and-runtime.md
├── tasks.md
└── evidence/                     # created during implementation/acceptance
```

### Source Code (repository root)

```text
loop.py                           # orchestration, canonical single writer
collaboration.py                  # inbox client + canonical lifecycle/dedupe
rulebook.py                       # explicit rule views, motion authority, judge validation
cleanup_rulebook.py               # snapshot-only generate/apply commands with hard gates
conversation_exam.py              # six-message judged artifact
tweet.py                          # confirmed/idempotent/bounded X delivery
run_turn.sh                       # loop wrapper; probe hook retired
prompts/
├── constitution.md
├── agent_a.md
├── agent_b.md
├── research.md
├── cleanup_a.md
├── cleanup_b.md
├── conversation.md
└── conversation_judge.md
state/
└── collaboration.json            # canonical lifecycle history; production untouched offline
viewer/
├── index.html
├── human.html
├── vercel.json
└── api/
    ├── _lib.js
    ├── _collaboration.js
    ├── suggestion.js
    ├── human-session.js
    ├── human-inbox.js             # asks, moderation, read-only cleanup review
    ├── human-action.js
    ├── encode.js
    ├── decode.js
    └── judge.js
tests/
├── fixtures/
├── python/
├── js/
└── acceptance/
    └── production/               # repo-owned visible journey and evidence oracle
```

**Structure Decision**: Preserve the existing small mixed Python/static/Vercel
repository. Add narrow modules only where they create a testable authority
boundary; do not introduce a web framework, ORM, account system, or separate
service.

## Complexity Tracking

No constitution violation is requested or justified. The one new managed store
is the minimum cross-runtime durability boundary; all other architecture remains
in place.
