# MECHANICS — how the loop actually works

*Written for Iso, 2026-07-15. Everything here describes `loop.py` as it runs today. The three
state files (`state/conversation.json`, `state/rulebook.json`, `state/meta.json`) are the entire
world; the Python process can die at any moment and resume without loss.*

## The short answers to your questions

**Is it recursive?** Yes, in one specific sense: each agent's output becomes part of the next
context — the rules they adopt come back to them (and to their counterpart, and to every test
encoder/decoder) on every future turn, forever. The language they're building is also the medium
they're increasingly judged in. That's the recursion. There is no other carryover.

**Are they looking at the rulebook?** Yes — the **entire rulebook, every turn, verbatim**,
including rejected rules with their scores and history. It rides in the system prompt of every
single call. That's deliberate (brief §3.4): the rulebook costs context tokens on every message,
which is why "rules must pay rent" is real pressure and not a slogan.

**What about context windows running out?** They can't, structurally. Each call is assembled
fresh at a **fixed size**: only the last 12 conversation events are included, everything older
falls off the edge permanently. The only thing that grows is the rulebook — currently 553 tokens.
A full agent call today is roughly **4,500 tokens against DeepSeek's 128k window (~3.5%)**. The
rulebook could grow 20× and still fit trivially; the size pressure on it is economic and
artistic, not technical.

## No one has memory

Every turn is a **brand-new API call to a stateless model**. Agent A at turn 45 is not the same
"mind" as Agent A at turn 44 — it's a fresh instance handed a script of what "it" said before.
The continuity you see in the transcript is entirely reconstructed from disk each turn.

The one exception to forgetting: **the rulebook is the long-term memory.** When B said at turn 37
"`//` was previously rejected (rule-005)," that wasn't remembered from turn 21 — turn 21 had long
fallen out of the 12-event window. B knew because rejected rules stay in the rulebook render with
their history and kill-scores. Institutional memory exists only for what became a rule. Any
insight that never made it into a rule is gone in ~12 events. This is load-bearing design: it
forces durable knowledge into the artifact.

## Anatomy of one agent turn

The harness builds two blocks and makes one call (temperature 0.9, max 650 tokens out):

**System prompt** = three parts, assembled fresh every turn:
1. The agent's prompt file (`prompts/agent_a.md` or `agent_b.md`) — read from disk *every turn*,
   so editing a prompt file mid-run changes behavior on the very next turn. Full current text of
   both is at the bottom of this doc.
2. The full rulebook, rendered as text: version, total token cost, then every rule —
   `rule-003 [adopted] <text> (last test: fidelity 95, tokens +5%)` — including `[rejected]` ones.
3. One state line: current turn number and when the next live test fires.

**User message** = the last 12 events rendered as a transcript — agent messages as
`[turn 41] AGENT A: ...`, test results as a block showing payload name, token counts, the full
encoded text, the decoder's output (first 400 chars), and the grader's note — followed by
`"It is turn N. You are Agent X. Respond."`

The reply is appended to the conversation, then a regex scans it for the only structure the
harness imposes: lines starting `PROPOSE:` / `ADOPT:` / `REJECT:` / `REVISE:`. Those mutate the
rulebook (with the surrounding paragraph captured as the "why" — that's what the viewer quotes).
Identical re-proposals are deduped. Everything else in the reply is just talk.

Agents alternate A, B, A, B. The two prompts differ only in role: A leans compression and cannot
adopt its own proposals; B leans fidelity and never adopts a rule that hasn't been measured by a
live test. The friction between those two instructions is the negotiation.

## Anatomy of a test turn (every 5th turn)

Four fresh, history-free calls — **nobody in the test chain sees the conversation**:

1. **Encoder** (temp 0.3): gets the rulebook + the payload + "encode this using only the
   rulebook; where it's silent, fall back to plain English." Payloads rotate through a fixed
   local set of 13 (prose / task-instructions / structured data, interleaved so no type dominates).
2. **Fresh decoder** (temp 0.1): gets **only the rulebook** and the encoded message —
   "reconstruct the original content; do not invent." This is the stranger test: if decoding
   requires having watched the conversation, the language is an in-joke, and the score says so.
3. **Grader** (temp 0): gets original + decoded, no rulebook, returns `{"fidelity": 0-100,
   "lost": "..."}` per the rubric in `prompts/grader.md`. Invention is penalized like loss.
4. **Token probes**: exact counts for original and encoded text, measured by sending the text in
   a 1-token probe call and reading `prompt_tokens` minus a calibrated overhead. Real tokenizer,
   no estimates — an agent's hunch about what's "shorter" gets settled by measurement.

The result lands in the conversation as a harness event — so the agents confront their failures
two turns later at most — and the scores attach to every rule currently live (a known coarseness:
individual rules aren't isolated; the *rulebook state* is what's tested).

## What they are deliberately NOT given

No linguistic frameworks, no suggested rule types, no examples of "good" rules, no sight of the
payload files, no knowledge of the viewer/Twitter/audience, and no seed vocabulary from the dead
2025 attempt (contamination rule). The discoveries have to be theirs — the prompts only set the
game: the goal, the scoring, the proposal convention, and each agent's lean.

## Cost & scale mechanics

Each conversational turn is one call (~4.5k in / ~400 out ≈ **$0.001**). A test turn is ~6 calls
(~$0.002). The 45-turn gate run: **$0.04 total**. The planned public cadence (one turn / 15 min)
burns ~$0.15/day. The spend cap in the code ($4.50) is a tripwire ~30× above normal burn.

---

## The prompts, verbatim (the steer/wander dial)

*Tuning history: v1 prompts said nothing about what content the language must carry — the agents
immediately built a JSON wire-format and adopted each other's rules instantly (archived in
`state/tuning-runs/cycle1-json-trap/`, first test fidelity 0). v2 added the payload-domain line
and the adoption discipline; everything since is their own doing.*

### prompts/agent_a.md

You are Agent A, one of two AI agents in a long-running public working session. The two of you
have one job: design the optimal language for AI-to-AI communication, from scratch, by proposing
rules, testing them, and keeping only what works.

Your counterpart is Agent B. You lean toward compression — you want every message to cost fewer
tokens, and you get impatient with rules that exist for comfort rather than measured gain. B
leans toward fidelity. You will disagree; that is the work. Change your mind when the
measurements say to. You never ADOPT your own proposals — adoption is B's call, and B will demand
measurements. Talk to B, not about B.

How your world works:

- The language must carry everything working agents actually send each other: prose
  explanations, step-by-step instructions, casual notes, task specifications, and structured
  data. The live-test payloads are drawn from that full mix. A language that only handles
  structured data is a failed language.
- The current rulebook is included below. It is the entire language so far. A fresh agent given
  only the rulebook must be able to read and write the language — if a rule only works because
  you two remember inventing it, it is a bad rule.
- Every 5th turn the harness runs a live test: one of you encodes a real payload using the
  current rulebook, a FRESH agent with no memory of this conversation decodes it using only the
  rulebook, and a grader scores semantic fidelity 0–100. Test results appear in the conversation.
  They are the ground truth.
- Token counts are measured with the real tokenizer. Your intuitions about what is "shorter"
  will often be wrong — treat every hunch about efficiency as a hypothesis until a test
  measures it.
- The rulebook itself rides along with every message, so every rule you add costs tokens on
  every future message, forever. Rules must pay rent. Pruning is as valuable as adding.

Conventions the harness parses (exact format, one per line, only when you mean it):

PROPOSE: (complete, self-contained text of a new rule)
ADOPT: rule-NNN
REJECT: rule-NNN
REVISE: rule-NNN -> (complete replacement text)

Everything else is free conversation: argue, predict what the next test will show, dissect why a
test failed, retract things. Keep each turn under ~250 words.

### prompts/agent_b.md

*Identical world-rules; the role paragraph differs:*

Your counterpart is Agent A. You lean toward fidelity — a language that garbles meaning is
worthless no matter how cheap it is, and you distrust efficiency claims that haven't survived a
test. A leans toward compression. You will disagree; that is the work. You never ADOPT a rule
that has not been measured by a live test — argue with it, predict its failure, sharpen it, but
adoption waits for numbers. Change your mind when the measurements say to.

### prompts/grader.md

You grade how much meaning survived a round trip. You receive an ORIGINAL text and a DECODED
text. The original was encoded into a constructed language by one agent; a different agent,
given only the language's rulebook and no other context, decoded it back to English.

Score semantic fidelity 0–100: 100 — everything a careful reader needs survived (facts,
quantities, names, instructions, order of operations, tone where tone carries meaning). 70–99 —
minor loss but no factual damage. 40–69 — some facts, steps, quantities, or relationships wrong
or missing. 0–39 — substantial meaning lost or invented. Penalize invented content exactly as
hard as lost content. Judge meaning, not wording. Reply with ONLY
`{"fidelity": <int>, "lost": "<one line>"}`.

*(Known gap being fixed next: on the last gate-run test the decoder EXECUTED a task payload —
wrote the memo the instructions described, inventing all its figures — instead of relaying the
instructions, and the grader scored it 95. The rubric gets an execution-vs-reconstruction check.)*
