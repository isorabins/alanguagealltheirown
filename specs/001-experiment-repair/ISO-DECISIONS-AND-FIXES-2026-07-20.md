# Iso's decisions on the skeptical review — fix list for Codex

**Date:** 2026-07-20, from Iso's review conversation with Claude.
**Companion:** `SKEPTICAL-REVIEW-FINDINGS-2026-07-20.md` (finding ids F1–F7 referenced below).
**Scope:** these are decided changes, not suggestions. Implement on this branch before the
production-equivalence pass. Update the existing Spec Kit contract and offline evidence for
these changes; all live gates and the rest of the approved scope remain unchanged.

**Offline status (2026-07-21):** D1–D4 are implemented and verified in the local feature
worktree. Nothing has been pushed, deployed, connected to production services, or run on the
production loop; T107 remains the first open gate.

---

## D1 — Decouple Redis from the loop entirely (resolves F1). DECIDED.

Iso's call: "take the Redis check off the heartbeat." The loop must take turns with zero
network dependency on Upstash.

**Required design — the courier pattern:**
- `loop.py` makes NO Redis/network calls for collaboration. It reads and writes ONLY the
  canonical file (`state/collaboration.json`) plus separate local transport spool files.
  Remove the `sync_remote(...)` call from `run()` and any RedisRest use from the turn path.
- A standalone `collab_sync.py` does all Redis I/O. It may write only atomic local inbox and
  recovery spools; it may never write canonical collaboration history. The loop imports the
  spools, deduplicates stable ids, and remains the sole writer of canonical history.
- Invoke the courier from `run_turn.sh` through a strict wall-clock timeout and `|| true`:
  - BEFORE `loop.py`: pull new answers/moderation/suggestions into the local inbox spool.
  - AFTER `loop.py`: publish the loop-authored private snapshot, new agent requests, and
    delivery receipts for the website.
- Every network operation is exception-safe and idempotent. A failure before a spool commit
  changes no local file; a failure after a durable spool/canonical receipt preserves that
  receipt for retry. A dead or hung courier may delay collaboration but may NEVER cancel a turn.

**Answer-delivery latency under this design (Iso asked):** unchanged in practice. The courier
runs at the top of every 15-minute cycle, immediately before the loop — an answer Iso submits
on the website lands in the local file on the next cycle and reaches the requesting agent
that same turn. If Redis is down, turns continue normally and the answer simply arrives on
the first cycle after Redis recovers. Delivery degrades; the experiment never stops.

## D2 — Agents CAN remove rules. Add a repeal path (resolves F2). DECIDED.

Iso's words: "I'd like them to be able to remove rules that start to feel redundant…
the point is they can add or remove them as they want. I don't want to control the
experiment." The current no-repeal design is rejected.

**Required design — repeal flows through the same invent/judge grammar as adoption:**
- Agent A (inventor) may originate a repeal as its one focused motion, e.g.
  `REPEAL: rule-NNN -> <why it should leave the language>`. This creates a repeal proposal
  (subject to the same one-open-proposal rule as D3).
- Store the repeal proposal as a distinct pending motion on its adopted target, with its own
  type, target, rationale, provenance, and history. Repeal text is never language law.
- Agent B (auditor) ratifies or refuses it with its existing ADOPT/REJECT/REQUEST verbs,
  under the same latest-focused-proposal constraint.
- On ratified repeal: the rule's status becomes `repealed` — OUT of `render_language()` and
  `language_payload()` (it leaves the tested language and the entry fee), but it remains in
  the legislature view and its full history is preserved. `repealed` is terminal for the
  rule id; re-introducing the idea requires a fresh PROPOSE (which the duplicate check
  should NOT block for repealed texts — only for live ones; adjust the dedup accordingly
  or document that re-proposal needs changed wording).
- Delete the unreachable `reverted` branch (F2's dead code) as part of this change.
- Update `prompts/constitution.md`, `agent_a.md`, `agent_b.md`, and the public page's
  how-it-works copy so the repeal power is documented everywhere the other verbs are.
- Tests: repeal lifecycle (A originates, B ratifies, language view shrinks, history intact,
  kernel recount), B cannot originate repeal, repeal of non-adopted rules rejected,
  repealed rules immune to further motions.

## D3 — Enforce one open proposal at a time in code (resolves F3). DECIDED.

Reject any PROPOSE (and REPEAL origination) while another proposal is open, with receipt
reason `proposal_already_open`. The inventor's "one focused idea" stops being prose.
Update A's prompt so the agent understands the receipt it will see. During the approved
cleanup application, terminalize legacy `proposed` and `reverted` records as historical while
preserving their original status and full history; otherwise the existing backlog would block
all future proposals forever.

## D4 — Small fixes (resolves F4–F7). DECIDED, bundle in one commit.

1. **F4:** agents' window must never show `fidelity None/100`. When fidelity is None render
   `no valid score ({judge_reason})`.
2. **F5:** record motion rationale from the actual motion line, not the message's last line.
   Expose the matched line on the MotionReceipt and pass it to `rationale_for`. Include the
   REQUEST verb family in `rationale_for`'s strip pattern.
3. **F6:** amend the handoff's operational-truth claim to "no existing state modified; one
   new empty scaffold added (`state/public-collaboration.json`)". Change the check to a
   baseline comparison that can see committed files; the claim and command must agree.
4. **F7:** cap `meta["corpus_exams"]` (keep the last 500 entries); delete the dead
   `econ_line()` stub and its call sites.

## Confirmations for Codex (context, no action)

- Redis remains the store for the website features (human page sessions, suggestion
  moderation, ask/answer exchange). Iso confirmed that scope is approved. D1 changes WHERE
  it is touched from, not whether it exists.
- The rest of the skeptical review's PASS list stands as verified; the production
  matrix's BLOCKED rows still gate go-live exactly as the handoff defines.
