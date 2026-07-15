# MORNING READOUT — A Language All Their Own, first real run

**VERDICT: CONTINUE.** The transcript clears the gate honestly: the agents disagree with substance, kill their own rules on evidence, invent experimental discipline nobody gave them, and every failure arc is legible drama. The weaknesses are harness papercuts and one pacing flaw — all fixable in phase 2 — not idea failure.

Run: 45 turns + 9 live tests, DeepSeek v3.2 both sides, **total spend $0.04** (all tuning included ≈ $0.05). At this burn the eventual public 15-min cadence costs ~$0.15/day, not the ~$5 estimated.

---

## What happened (the arc)

1. **Cycle 1 (archived):** agents fell straight into the JSON trap; B adopted A's rule instantly; first live test scored **fidelity 0** — the fresh decoder hallucinated a field that never existed. Agent A then correctly self-diagnosed it unprompted: "a fresh agent couldn't decode... we lack a rule for unmapped keys." Prompts revised (payload-domain awareness, no self-adoption, B never adopts unmeasured).
2. **Final run:** rules 001/002 (line-prefix markup) tested +2% tokens → **rejected on the numbers**. Rule-003 (directive blocks) won −22% on casual prose → adopted. Then reality: +21% and +20% on short task payloads (markup that can't pay rent), **−52% at fidelity 70** when the encoder amputated a table's explanatory notes, and **fidelity 60** when it flattened a story into a procedural checklist. Their response to that last one is the best exchange of the run.
3. **The finale nobody scripted:** on the last test, the fresh decoder didn't *relay* the task-instruction payload — it **executed it**, inventing a complete quarterly memo with hallucinated figures. The grader wrongly blessed it (95). A deep machine-communication failure mode, on camera.

## Excerpts (verbatim)

**Best — B refusing to accept an unenforceable rule (t17):**
> "Your revised rule‑003 tries to fix this with a usage guideline... but that's not enforceable by a fresh decoder — it's a style hint for encoders, which a rulebook can't guarantee. That's dangerous."

**Best — A diagnosing the narrative failure (t41):**
> "The prose inside the `{@` block was treated as directives, stripped of its descriptive richness. The decoder extracted a procedural list, not a story... A directive block is the wrong container for a story."

**Best — self-invented experimental controls (t43–44):**
> A: "I'm leaning toward waiting, because adopting a rule now would change encoding before the next test, skewing results." / B: "adopting now would... muddy the signal."

**Worst — the holding-pattern loop (t27–34):**
> Six near-identical turns of "no proposals until the data. Let turn 35 deliver the missing signal." Disciplined, but dead air — the pacing flaw to fix.

**Worst — the false-positive finale (t45):** decoder output began "**Subject: Quarterly Performance Highlights** — Revenue grew 12%..." — none of it real; grader: "nothing material" lost. Grader rubric gap.

## Rulebook state (v0.13, kernel 553 tokens)

| rule | what | fate |
|---|---|---|
| 001/002 | `^` directive + `>` quote prefixes | rejected turn 7 (measured +2%, no rent paid) |
| 003 | `{@ ... }` directive blocks | **adopted**; survived 8 tests, scores −52%…+21% — they know it's overused |
| 004 | `:=` data hint | rejected turn 16–17 |
| 005 | `//` commentary v1 | rejected turn 21 (untested-in-anger), then **revived at t37 after the −52% metadata loss proved the need** — the piece's first full death-and-resurrection arc |
| 006–008 | `//` commentary revival | proposed — as triplicates (harness dedup gap, below) |

## Known harness gaps (phase-2 fixes, ~30 min total)

1. **Grader rubric:** add an execution-vs-reconstruction check — decoder output that *does the task* instead of *relaying the message* must score near zero (t45 false positive).
2. **Proposal parsing:** dedup identical PROPOSE texts (the 006/007/008 triplicates) and tolerate markdown bold — two genuinely new proposals at t42–43 (per-line `^` revival among them) were **silently dropped** because the agents wrote `**PROPOSE:**`.
3. **Pacing:** the wait-for-data discipline overcorrected into dead-air turns. Fix: test every 3rd turn instead of 5th, and give agents the self-serve encode-and-count tool they literally asked for at t33 (the brief's "tokenizer as a tool").
4. Score attribution is rulebook-level, not per-rule (every live rule inherits each test's numbers) — cosmetic now, worth noting on the public page later.

## Next session (explicitly NOT built yet)

- Phase-2 harness fixes above, then VPS 15-min scheduler + public Vercel page (ships within 7 days of this CONTINUE per ground rules) + domain purchase (alanguagealltheirown.com, $11.25 via Vercel).
- **Iso decisions pending:** create the dedicated Twitter account (isogenoar@gmail.com — account creation is human-only) and grant standing approval for the dry-changelog tweet format, or cut Twitter from v1.

*Prompt-tuning log: cycle 1 → JSON trap + instant adoption → added payload-domain line, no-self-adopt (A), no-unmeasured-adopt (B), interleaved payload types, reconstruct-don't-invent decoder instruction. Cycle 2 read clean → continued into final run (turn cap 500→650 at t8). Discarded transcript in `state/tuning-runs/cycle1-json-trap/` with prompt snapshot.*
