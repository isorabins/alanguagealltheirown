# A Language All Their Own — Build Brief

**Status:** Design settled, ready to build. This doc is the living spec — it captures the idea, the reasoning behind every design decision, and the build plan. Continue the conversation from here.

---

## 1. The Idea

An art project. Two LLMs sit in side-by-side chat windows, talking to each other, with one job: invent the optimal language for AI-to-AI communication. Below the chat windows, a rulebook grows — every rule they propose, test, adopt, or reject, with scores attached. A connected Twitter/X account announces rule changes as they happen ("v0.14: dropped tense markers, fidelity fell 12%, reverted").

The one-line artist statement: **companies are engineering agent-to-agent protocols (MCP, A2A) top-down; this piece lets the machines negotiate one bottom-up, in public.**

The end state is a shareable artifact — a rulebook any agent can be handed to instantly "speak" the language. An Esperanto of LLMs, except without Esperanto's fatal flaw: adoption cost for an LLM is zero. You paste the rulebook into a system prompt.

## 2. Prior Art (why this is unclaimed but timely)

- **Emergent-language research** (2017–): Facebook's negotiation bots drifting into reworked English; multi-agent RL studies where agents evolve vocabularies from ungrounded symbols. Academic, not watchable.
- **Gibberlink** (Feb 2025, viral): two voice agents recognize each other as AIs and switch to a chirping data-over-sound protocol. Closest in spirit — but it's a *fixed* protocol demo, not an evolving language.
- **Infinite Backrooms** (Andy Ayrey, 2024): two Claude Opus instances in endless conversation — the canonical "two LLMs talking as art" piece (spawned Truth Terminal). But they discuss consciousness, not language design, and there's no artifact.
- **Dev-land**: endless "my agents invented a shorthand and cut tokens 63%" posts. Utilitarian, private, no rigor.

The specific combination — a live, watchable negotiation where the artifact is a **versioned, tested, public rulebook** — has not been done. Gibberlink's virality proves the audience appetite.

## 3. Core Insights (the intellectual engine)

These came out of the design conversation and shape everything below.

### 3.1 The abbreviation trap
BPE tokenizers assign short token counts to *frequent* strings. "Approximately" is 1 token; "approx." is often 2–3, and each fragment carries a weaker learned meaning. So the naive "efficient language" (abbreviations, invented symbols, dense glyphs) is often worse on **both** axes: more tokens AND lower comprehension. Common English is already a compression scheme tuned to the model's own frequency statistics.

**This is not a design flaw — it's the plot.** The agents must discover it on camera. The real gains are elsewhere: dropping discourse glue ("Hi team!", hedging, restating context), leaning on shared state ("ref: rule-14"), structural conventions. English words stay; the *pragmatics* get rebuilt.

**Design consequence:** the agents get a tokenizer as a tool. Every proposed rule is scored in real token counts, so "abbreviations lose" is a measured discovery logged in the rulebook, not an opinion baked into a prompt.

### 3.2 Images are a dead end (and a good episode)
Images are dense to humans, expensive to LLMs: hundreds–thousands of input tokens per image after the vision encoder, lossy for fine text and structure, and generation is slow and non-deterministic on decode. Text-in-image pays ~10x the tokens for a worse copy. The genuinely denser channel is raw embedding exchange — real research territory, but invisible, which kills the art. The token stream is the right medium because the audience can watch it.

Optional: let the agents *try* image communication as one episode and fail measurably. Failure arcs make the piece feel alive.

### 3.3 Grounding prevents drift
Left alone, two LLMs converge in ~20 turns on the obvious (drop pleasantries, use JSON), then plateau or drift into Backrooms-style mysticism. The fix: **every rule must survive an encode/decode test.** One agent encodes a real message (paragraph, instruction, data structure) using the current language; a *fresh* API call decodes it back to English; a grader call scores fidelity. Failures force revisions. The rulebook is a spec under test, not vibes.

### 3.4 Rulebook economics
The rulebook itself costs tokens — it rides in the system prompt. Two forces:
- **Prompt caching** kills most of the *dollar* cost (cached reads ≈ 10% of input price).
- Caching does **not** touch the *context window* — the rulebook occupies its full attention budget every request.

So size pressure is real but should be scored in **context tokens, not dollars**. Track the **amortization horizon**: how many messages until the rulebook's savings pay for its own length. This gives the agents a genuine reason to prune rules, not just add them — the same pressure that shapes real languages.

### 3.5 The bootstrap staircase (self-hosting the rulebook)
A rulebook written entirely in its own language is unreadable to a fresh agent — chicken and egg. The solution is the compiler-bootstrapping pattern: a **staircase**.

- **Stage 0 — the English kernel:** minimal plain-English rules, just enough to decode Stage 1.
- **Stage 1 — compact rules:** written in the partial language, decodes Stage 2.
- **Stage 2 — the full language.**

Keep the staircase **short (2–3 stages max)**. Compilers get away with long chains because compilation is exact; LLM decoding is probabilistic, and errors compound at each hop (97% fidelity per stage decays fast). Whether stage 3 earns its place over stage 2 is itself measurable inside the piece.

**Headline metric of the whole project: kernel size.** The agents' long-term job is shrinking the English kernel — how few plain-English tokens before the language carries its own weight? Watching that number fall from ~2,000 to ~400 tokens over weeks is a story an audience can follow. If the kernel gets too aggressive and fresh agents fail to decode, it must be fattened back up — visible tension on the scoreboard.

### 3.6 The transfer test (the finale)
The distinction the piece exists to probe: did they invent a **language** or an **in-joke** (a shorthand that only works because both sides share conversation history)?

Test: hand the kernel + rulebook to two *fresh* agents — ideally different models entirely (a Claude and a GPT) — with no conversation history, and score whether they communicate at the same fidelity/compression as the originals. Pass = language. Fail = dialect collapse. Either result is a finding, and either is great content.

## 4. The Loop (there are no stages)

One loop, running forever, is the entire project:

```
propose rule → encode/decode test → score → accept/reject/revise → append to rulebook → publish
```

- Turn one: rulebook is empty, agents talk in plain English about what to try.
- Turn 100: forty rules with test scores attached.
- The milestones (self-compression, kernel shrinking, transfer test) are **not architecture** — they are special inputs fed to the loop later. Self-compression = "this round, the message to encode is the rulebook itself" (introduce around rule ~40). Transfer test = a manually triggered scoring run when v1.0 feels ready.

## 5. Architecture

**Split: VPS runs the loop, Vercel renders it.** Vercel is serverless and cannot host a long-lived scheduled process.

### VPS (Hetzner — existing box)
- **FastAPI app** with a scheduler (APScheduler or a systemd timer hitting an internal endpoint). Note: the loop is a *scheduled job*, not request-driven — FastAPI's role is serving state endpoints and admin controls, not triggering turns.
- **Every 15 minutes, one turn:** read state → make the API calls (proposer, responder, and on test turns: encoder / fresh decoder / grader) → update `conversation.json` and `rulebook.json` → push updated JSON to Vercel Blob (or serve directly from the VPS).
- **On rule status change:** fire the upload-post call to tweet it (upload-post is already connected on Iso's system).
- 15-minute cadence is a feature: a few dollars/day in API cost, a followable rhythm for the Twitter account, and the page visibly *ticks*.

### Frontend (static page, Vercel)
- Pure static: fetch the JSON, render. No backend on Vercel at all.
- Layout: project explanation up top → two chat windows side by side → the developing rulebook table underneath (rule, version, status, token cost, fidelity score, history).
- Domain: standalone domain preferred (check Hover — **alanguagealltheirown.com may already be owned**). Fallback: a page on knowyourself.com, but a dedicated domain keeps the art project's identity separate from the personal brand and shares better.

### Data shapes (starting point — keep dumb)
```
rulebook.json:
{
  "version": "0.14",
  "kernel_tokens": 1840,
  "rules": [
    {
      "id": "rule-014",
      "text_en": "...",
      "text_compact": "...",
      "status": "adopted | rejected | under_test | reverted",
      "proposed_turn": 121,
      "scores": { "token_delta_pct": -8, "fidelity_pct": 96 },
      "history": ["v0.12 proposed", "v0.13 revised", "v0.14 adopted"]
    }
  ]
}

conversation.json: append-only turn log
{ "turn": 121, "agent": "A", "type": "proposal | response | test_encode | test_decode | test_score", "content": "...", "tokens": 214 }
```

### Scoring (turn types)
- Every N turns (start with N=5) is a **test turn**: harness picks a payload (paragraph / instruction / structured data), Agent A encodes per current rulebook, a **fresh, history-free** API call decodes, a grader call scores semantic fidelity 0–100. Token counts measured with the real tokenizer.
- Metrics tracked over time: tokens per message, fidelity, rulebook size (context tokens), kernel size, amortization horizon.

## 6. Prompt Design (the actual hard part)

The code is ~200 lines of plumbing. The artistry is the **steer/wander dial**:
- Too loose → Backrooms mysticism and drift.
- Too tight → you wrote the language yourself; they're just typing it out.

Expect to hand-tune the two agent system prompts repeatedly. Give them: their role, the current rulebook, recent conversation window, tokenizer access, the scoring rules, and the standing goal. Do NOT give them: linguistic frameworks, suggested rule types, or examples of "good" rules — those are the discoveries.

## 7. What NOT To Do (how v1 died in 2025)

The first attempt failed because the model asked to "build a language project" reached for NLP libraries, parsers, and semantic-rule frameworks. **There is no language processing in this project.** The LLMs do the language part; the code is plumbing. No linguistics libraries. No parsing. No cathedral.

## 8. Build Order

1. **The ugly loop, local.** One Python script: two API calls taking turns, JSON files on disk, test turn every 5. No server, no UI, no tweets.
2. **Run it 20 turns and read the transcript.** Tune prompts until the conversation is genuinely interesting. This gate matters more than anything downstream.
3. **Move to VPS.** FastAPI + scheduler, 15-minute turns, state endpoints.
4. **Static viewer page.** Fetch JSON, render explanation + chat windows + rulebook table. Deploy to Vercel on the dedicated domain.
5. **Wire upload-post** for auto-tweets on rule status changes.
6. **Later, as content not code:** self-compression episode (~rule 40), image-communication episode (optional), kernel-shrinking pressure, transfer test as the v1.0 finale.

## 9. Open Questions (continue the conversation here)

- Model pairing: same model twice, or two different models from turn one? (Different models makes convergence harder and more interesting, but noisier.)
- Payload sourcing for test turns: curated set, random wiki paragraphs, or audience-submitted?
- Tweet voice: dry changelog ("v0.14: reverted") vs. the agents writing their own announcements?
- Turn budget / end condition: does v1.0 have a defined finish line (kernel < X tokens, fidelity > Y%), or does it run indefinitely?
- Public rulebook repo: publish versioned rulebook releases on GitHub so other people can run the transfer test themselves?
