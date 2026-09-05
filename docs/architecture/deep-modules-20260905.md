# ALATO deep-module rebuild

Status: built and verified locally; production rollout not performed. Iso confirmed on 2026-09-05 WITA: preserve
behavior and fix demonstrated bugs. All four review recommendations are in scope.
Source baseline: 493a464359c4d11ca8562930b30ca1fe817b4d1e.

## Behavior Spine

| ID | Source / owner | Promise | Proof |
|---|---|---|---|
| B1 | README Current contract / models + deterministic authority | A proposes; B alone adopts/rejects; only adopted language governs ordinary encoding/decoding. | Role/state matrix and native legislative-turn tests. |
| B2 | README receipts + approved crash repair / code | A completed turn has matching history, language, actor, exam cursor and delivery state after restart. | Faults at every canonical save, recovery twice, real run restart. |
| B3 | MECHANICS Ordinary exam / judge + code | Invalid judge evidence cannot become language failure or replace a valid baseline; valid retests drive the existing derived fault lifecycle. | Raw judge evidence through result, baseline and fault replay. |
| B4 | README Collaboration / human + code | Moderation remains human-owned; replies and bounded evidence retain exact-once delivery and private/public separation. | Existing lifecycle suite plus turn rollback/recovery. |
| B5 | Current Observatory + approved snapshot repair / code | Show a coherent current story, truthful freshness and intact history; never mix revisions as one state. | Controlled read races and real local page. |
| B6 | README / code + operator | Retain provider-cost receipts, schedule, models, prompts, cleanup authority and isolated X publishing. | Unchanged policy/config diff audit and regression suite. |

## Behavior packet

Rule: concentrate the implementation behind complete-turn persistence, public
snapshot, legislative-transition and development-exam evidence seams.

Core flow: the scheduled runner loads the existing experiment, obtains the normal
model response, validates/applies it, durably completes that turn, and projects a
coherent public view. Restart recovers completed work before selecting the next
actor. Tests begin with the same saved state and raw responses as production.

Examples: interruption after history save recovers the matching rules/actor;
structural exhaustion leaves the language and delivery eligibility unchanged;
invalid judge spans leave the prior valid baseline untouched; one GitHub refresh
cannot combine turn N history with turn N+1 language; unavailable refresh keeps a
labeled last-known view and the complete archive remains accessible.

Invariants: B1–B6. Current bugs and obsolete documentation are not permanent
behavior. Preserve user-visible layout and ordinary outcomes. Try It remains
disabled. No new experiment policy or generic exam framework.

Agent authority: module design, reversible implementation, offline tests, local
browser fixtures and commits. Production release, live model calls, scheduler
changes and migration on the VPS are not authorized by this build request.

Open product questions: none after Iso's scope confirmation. The implementation
will produce a migration/rollback preflight before requesting live rollout.

## Coverage ledger (local acceptance)

| Seam | Caller / real adapter | Variants | Required evidence | Status |
|---|---|---|---|---|
| Turn persistence | run / local filesystem | legacy import, success, failure before/after each write, repeated recovery, overlap, malformed pending journal | real saved state, actor/hash/cursor/delivery agreement | PASS — controlled local adapter tests; production unverified |
| Legislative transition | agent_turn / provider + tokenizer | proposal, revision, vote, rejection, no motion, exhausted structure, requests/delivery | same production seam and preserved role matrix | PASS — controlled local adapter tests; production unverified |
| Development exam | test_turn / model + token calls | invalid spans/literals, valid critical failure, valid retest, baseline/cursor | raw response through public event and fault admission | PASS — controlled local adapter tests; production unverified |
| Public snapshot | viewer / GitHub + deployed files | cold load, consistent revision, moving main, delayed old refresh, missing optional files, offline fallback, progress | controlled fetch tests and local browser | PASS — controlled local adapter tests; production unverified |
| Preserved paths | courier, human actions, cleanup, Conversation, transfer, X | existing authority/failure/lifecycle branches | full Python/Node regression; diff audit | PASS — controlled local adapter tests; production unverified |

External evidence remains unverified until a separately authorized rollout.

## Delivery clarification from Iso

Iso additionally requires a plain-language map of every meaningful module's small
interface behavior, protected behavior tests, and a reliable path from a future
plain-language behavior request to the responsible module and preserved contracts.
Deliver one project entry guide referencing adjacent typed interfaces and behavior
tests; avoid a second drifting implementation specification. Expose inputs,
outcomes, failures and invariants. Tests must protect behavior, not internal call
order or file layout except where persistence/recovery makes ordering observable.


## Final evidence — 2026-09-05 WITA

- **239 Python tests pass**, including native module contracts, the real Python
  runner with fault injection, a temporary Git-origin shell retry, notice deletion,
  unrelated staged-work preservation, and optional public-trace repair.
- **84 Node tests pass**, including the actual public reader with controlled fetch
  adapters and existing HTTP/session/privacy suites. CI now also triggers on
  changes to the scheduled shell. No test suite was disabled.
- Historical traceability: **115 requirements, 210 sequential tasks**. This is
  traceability evidence, not a substitute for the behavior tests.
- Sensitivity: disabling recovery, forcing the wrong actor, admitting an invalid
  evidence span, and omitting full-history fallback each make protected tests fail.
  Mutations were in-process only; no mutant source was retained in the checkout.
- Independent read-only review found and closed recovery, archive, revision,
  fallback, shell-staging and null-journal defects. It found no remaining blocker
  in its final inspected changes. The later preview-highlight repair has a native
  regression and direct cold-load browser evidence.
- Preserved-code audit: provider calls, token accounting, automatic cleanup,
  research and Conversation orchestration retain identical function ASTs to the
  baseline. No prompt, benchmark, HTTP adapter, collaboration or X source changed.
- Browser acceptance used sanitized committed state at **turn 3738**, not a new
  live model run. Desktop and **375 CSS-pixel** mobile checks passed; no horizontal
  overflow or console warnings/errors were observed. The in-app viewport override
  includes a scrollbar, so a 390-pixel outer override yielded a measured 375-pixel
  content viewport. The temporary tab/server were closed and viewport reset.
- The generated startup script is **658 bytes**. The preview retains the true
  strongest strict pass (turn 1650, 43%) before the full archive loads. Full history
  exposes **7,108 public records**, including turn 1. Latest evidence remains
  turn 3738, 445→410 tokens, 97% coverage, strict failure. Its completed trace agrees.

Browser result: **PASS with evidence caveats**. Screenshots contain page headings
and target state, but omit browser chrome; the localhost URL and DOM/HTTP receipts
supply location. This was local read-only acceptance, not deployed acceptance,
logged-in moderation, a real provider evaluation or a recorded production journey.

Local evidence directory: `/private/tmp/alato-deep-module-acceptance/`.
These temporary artifacts are inspectable in this session; durable reproduction
lives in the committed tests. Screenshot guide:

| File | Claim / look for | Quality |
|---|---|---|
| `00-before-repair.png` | Initial narrow view with permanent checking and overflow; failure evidence. | Acceptable with localhost receipt. |
| `01-desktop.png` | ALATO heading, preserved turn 3738 and explicit unavailable live status. | Acceptable with localhost receipt. |
| `02-mobile.png` | Same status fits the measured 375-pixel content viewport. | Acceptable with viewport receipt. |
| `03-history.png` | Expanded Full transcript shows turn 1 after deployed-preview fallback. | Acceptable with URL and 7,108-record DOM receipt. |
| `04-current-evidence.png` | Cold preview already shows the true 43% best and the current 8% body savings/strict failure. | Acceptable with cold-load 30-record DOM receipt. |

The public trace keeps its existing receipt playback presentation; its "live"
phase labels in a screenshot are playback, not proof of current provider activity.
No video was required for this local reader check.

## Implementation decisions and limits

Keep the existing JSON format and single writer. A checked redo record provides
complete-turn recovery without a database migration. The completed public exam is
stored durably in an ignored local receipt as part of the turn; its public file is
rebuildable. Optional trace-publication failure remains fail-open. Human notices
are acknowledged with the committed turn, and different replacement notice text
is preserved. The writer requires a local POSIX filesystem; filesystem or machine
loss is not a backup guarantee.

The runner repairs projections before its cap check. The scheduled shell recovers
and preserves completed local work before pulling code, and commits only named
loop-owned paths, including consumed-notice deletion. Unrelated staged changes
remain untouched. Runtime completion timestamps are persisted with successful
turns; rebuilding a legacy projection without one leaves it unknown.

The reader pins repository head, then derives turn freshness from conversation
history at that same revision. A newer code or notes commit cannot make an old
turn look fresh. Once a full revision is visible, a failing newer refresh keeps
that complete revision. Cold preview includes the real headline exams and latest
A/B messages within its 30-event bound; it is never advertised as the full archive.

Reference checks: [Python documents atomic successful same-filesystem replacement](https://docs.python.org/3/library/os.html#os.replace);
[GitHub's commit endpoint supports a starting SHA and path filter](https://docs.github.com/en/rest/commits/commits#list-commits).
The multi-file recovery guarantee comes from this module's protocol and fault tests,
not from a claim that individual file replacement makes a whole turn atomic.

## Rollout boundary — proposed, not executed

This branch is for local review. The production timer pulls `main`, so merging the
code into `main` is part of production cutover and needs Iso's release approval.
Before that boundary, verify the actual host, checkout, timer/service, live Git
state and writer ownership. Preserve a coherent backup of canonical state,
collaboration, local cost receipts, pending redo, completed-exam receipt and notice.
Do not reset the experiment, change models, raise the cap or run paid acceptance
calls under this local-build authorization.

After an approved release, use the no-model `--recover` path to recover/rebuild,
verify one resumed scheduled turn and its public revision, and check adopted-language
identity, next actor, exam position, delivery state and exact cost receipts. Verify
the deployed desktop/mobile page and the public trace against that committed turn.
Generated bootstrap/preview/archive files are produced by the runner; this local
code commit does not replace production experiment state with the review fixture.

Rollback must stop writers, recover/drain any pending redo with the new code,
retain cost receipts and completed canonical turns, then restore reviewed code and
rebuild its compatible public projection. Never discard a journal or replace live
state with the older review baseline. Verify those conditions on the actual host
before approving a rollback; this document is not authorization to execute it.
