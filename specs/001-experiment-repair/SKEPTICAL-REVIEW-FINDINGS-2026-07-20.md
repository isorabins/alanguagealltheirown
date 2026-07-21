# Skeptical Review Findings — experiment-repair branch

**Reviewer:** Claude (the builder being audited last round; roles reversed by Iso's instruction)
**Date:** 2026-07-20
**Target:** branch `codex/experiment-repair` at `bfc97b7`, baseline `96e681f`
**Method:** ran the handoff's minimum commands; read `rulebook.py`, `loop.py` (core paths),
`collaboration.py` (RedisRest/sync_remote), `cleanup_rulebook.py` (hash bindings), `tweet.py`
(receipt model), `viewer/api/decode.js`, `_collaboration.js` (session/cookies); executed
adversarial probes against `apply_authorized_motion` and `render_window` in scratch. No pushes,
no deploys, no paid provider calls, no live turns, no state mutation.

## Verdict

**BLOCKED — agreeing with the handoff's own call — plus one HIGH defect that must be fixed
before the production-equivalence pass, and one design question only Iso can answer.**
The architecture is genuinely good: the contamination boundary, authority model, judge
validator, hash-bound cleanup, and receipt-based X delivery are real improvements, honestly
tested offline. The defects below are specific and fixable.

## Independent test results (recomputed, not trusted)

- `python3 -m unittest discover -s tests/python` → **47/47 pass**
- `node --test tests/js/*.test.js` → **26/26 pass**
- `tests/acceptance/check_contract_coverage.py` → PASS, 55 requirements traced, 133 tasks
- `git diff --check` → only trailing-whitespace noise in `.specify/` templates
- `git diff --name-only 96e681f..HEAD -- state viewer/state.js` → **NOT empty** (see F6)

## Findings, worst first

### F1 — HIGH: a Redis outage can kill live turns

`sync_remote()` (collaboration.py:172) wraps ONLY the `RedisRest()` constructor in
try/except — that catches missing configuration, nothing else. `grep -c "except requests"
collaboration.py` → **0**. Every network method calls `response.raise_for_status()` and can
raise `requests.ConnectionError` / `Timeout` / `HTTPError` uncaught. `loop.py:518` calls
`sync_remote()` at the top of EVERY turn, before the agent turn and exam. On the VPS with
Upstash configured, any Redis outage or network blip raises inside `loop.py` → the turn dies.
A sustained outage stops the experiment until Redis recovers. This violates the branch's own
contract that collaboration never blocks the loop.
**Fix:** wrap all RedisRest network I/O (or the `sync_remote` body after construction) so any
exception degrades to the local state and logs. Audit `process_one_research` (loop.py:520)
for the same exposure — I did not read its error handling.

### F2 — DESIGN GAP (Iso must decide): agents can never repeal adopted law

`apply_authorized_motion` allows ADOPT/REJECT only when a rule's status is `proposed`
(rulebook.py:156). Once adopted, a rule is permanently beyond the agents' reach — no revert,
no repeal, no sunset. The `reverted` status accepted by REVISE (line 175) is unreachable dead
code: nothing can set it. So a bad adopted rule can only ever be removed by the human-gated
cleanup pass. The spec never states this as a decision. It may be intended (cleanup as the
only amendment process) — but the old system had reverts and the agents used them.
**Fix:** either document "no agent repeal — cleanup is the only amendment path" as an explicit
approved rule of the game, or add a B-side REPEAL motion with its own guards. Delete the dead
`reverted` branch either way.

### F3 — MEDIUM: A's "one focused idea at a time" is prose, not enforcement

Demonstrated in scratch: A stacked three PROPOSE motions across three turns — all accepted
(`proposal_recorded` ×3). Nothing in `apply_authorized_motion` blocks a new PROPOSE while
another proposal is open; the constraint exists only in `prompts/agent_a.md` ("exactly one
focused language idea at a time"). This is precisely the "roles in prose, not enforced
checks" failure the original audit dinged the old system for. Mitigation exists: B's
`not_latest_focused_proposal` guard bounds damage, and my probe confirmed the queue DRAINS
newest-first (after the latest proposal settles, the next-newest becomes actionable — old
proposals are delayed, not permanently stranded). But A can still flood, and old proposals
can starve behind a productive A.
**Fix:** one line — reject PROPOSE with reason `proposal_already_open` while any rule is
`proposed`. This also makes B's latest-proposal guard nearly unreachable, simplifying reasoning.

### F4 — MEDIUM: invalid exams show "decode fidelity None/100" to the agents

Reproduced: an exam event with `fidelity: None` (invalid judge output) renders in the agents'
window as `decode fidelity None/100` (loop.py:186 — `e.get('fidelity', 'invalid')` never
defaults because the key EXISTS with value None). The entire point of judge validation was
"publish no valid score"; instead the agents read a nonsense number-like token. The public
page handles null correctly ("unparseable", index.html:519); the agents' own view does not.
**Fix:** render `no valid score ({judge_reason})` when fidelity is None.

### F5 — LOW: motion rationale records the wrong "why"

`loop.py:248` calls `rationale_for(text, text.splitlines()[-1])` — the LAST line of the
message, not the motion line. Whenever the motion is not the final line, the recorded
rationale comes from whatever paragraph ends the message. History quality bug; every future
"why did they adopt this" reading inherits it. Old code passed the matched verb line.
**Fix:** pass the actual motion line (available from `_motion_lines`; expose it on the receipt).

### F6 — LOW: the handoff's operational-truth claim contradicts its own check

Handoff: "verify state files are unchanged." The handoff's own command returns
`state/public-collaboration.json` — a NEW file seeded `{"asks":[],"research":[],"suggestions":[]}`.
Additive scaffold, not a mutation of experiment history — but the claim as written is false,
and a reviewer who runs the command without reading the diff would flag it as a violation.
**Fix:** amend the claim to "no existing state modified; one new empty scaffold added," or
seed the file at first runtime write instead of committing it.

### F7 — LOW housekeeping

- `meta["corpus_exams"]` grows unboundedly (loop.py:388) — meta.json rides forever; cap or rotate.
- `econ_line()` is a dead stub returning `""` — delete it and its call sites.
- `rationale_for`'s strip-regex doesn't know the new REQUEST verbs — REQUEST lines can leak
  into recorded rationales.

## What passed adversarial inspection (verified, not assumed)

- **Authority matrix:** A cannot vote; B cannot originate; multiple motions per message
  rejected; settled rules immune; unicode rule-ids normalized; nested verbs blocked; duplicate
  proposals blocked (case-insensitive); B locked to the latest open proposal. (Their tests +
  my probes.)
- **Contamination boundary:** ordinary exam encoder/decoder prompts are built from
  `render_language()` — adopted rules only — with version+hash captured per exam
  (loop.py:336-345, 384-385). Legislature view is separate and labeled. Old `render_rulebook`
  aliased to the adopted-only view so stale callers can't regress.
- **Judge validator:** exact 1..N coverage, duplicate/boolean/string/out-of-range ids
  rejected, verdict whitelist, invented must be a list; invalid → `fidelity: None`, no score
  published. Solid.
- **Fallback exams now get answer keys** extracted before the exam instead of holistic grading.
- **Decode version pinning:** decode requires client version AND hash, 400s when missing
  (decode.js:12-15). (Mismatch path read as far as the compare; full no-provider-call-on-race
  behavior deferred to the production pass.)
- **Session cookies:** `HttpOnly; Secure; SameSite=Strict`, timing-safe compare, absolute expiry.
- **Cleanup hash binding:** audit must carry `reviewed_source_hash` and
  `reviewed_candidate_hash` matching current snapshots; ledger stores source/candidate/
  applied/audit/diff hashes (cleanup_rulebook.py:42-98).
- **X delivery:** receipts require a real post id; dry runs never confirm; blocked-after-3
  with continuation. (Vendor shapes still need the live pass, as the handoff says.)
- **Sole writer:** no rule-status mutation outside `rulebook.py` + the hash-bound cleanup
  applier (repo-wide grep).
- **Model split is real:** Agent B and the stranger are Kimi; A/grader DeepSeek.

## Not covered (do not treat as passed)

Conversation exam logic (`conversation_exam.py`), full suggestion/ask sanitization and
public-leak paths in `_collaboration.js`/`human-action.js`, `human.html` flows, the rewritten
`viewer/index.html` beyond spot checks, research sidecar prompt-injection resistance beyond
design reading, everything the handoff's production matrix already marks BLOCKED (live Redis,
live X, paid try-it, VPS run, screenshots).

## Recommended order

1. F1 (turn-killing coupling) — before anything runs on the VPS.
2. F3 + F2 — one-line guard now; repeal question to Iso as a named decision.
3. F4, F5 — small correctness fixes inside the same commit.
4. F6, F7 — with the docs pass.
Then the production-equivalence pass the handoff already defines.
