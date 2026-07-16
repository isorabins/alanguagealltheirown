# MECHANICS — how the system actually works

*Written for Iso. Updated 2026-07-16 evening (WITA), as of turn 177, rulebook v0.72. Describes
the system as it runs today — engine (`loop.py`), publishing pipeline (`run_turn.sh`), and
changelog bot (`tweet.py`). The three state files (`state/conversation.json`,
`state/rulebook.json`, `state/meta.json`) are the entire world; any process can die at any
moment and resume without loss. A "queued changes" note sits at the bottom so you know what's
decided-but-not-yet-live.*

## The short answers to the big questions

**Is it recursive?** Yes, in one specific sense: each agent's output becomes part of the next
context — the rules they adopt come back to them (and to their counterpart, and to every test
encoder/decoder) on every future turn, forever. The language they're building is also the medium
they're increasingly judged in. That's the recursion. There is no other carryover.

**Are they looking at the rulebook?** Yes — the **entire rulebook, every turn, verbatim**,
including rejected rules with their scores and history. It rides in the system prompt of every
single call. That's deliberate: the rulebook costs context tokens on every message, which is why
"rules must pay rent" is real pressure and not a slogan. It currently costs **1,050 tokens** and
holds 27 rules (3 adopted, 1 proposed, the rest dead).

**Can their context window run out?** No, structurally. Each call is assembled fresh at a fixed
size: only the **last 30 conversation events** are included; everything older falls off the edge
permanently. At the 15-minute cadence that's roughly a 7.5-hour visible past. The only thing that
grows is the rulebook — a full agent call will settle around ~25,000 tokens once long exams fill
the window, against DeepSeek's 128k (~20%). The size pressure on the rulebook is economic and
artistic, not technical.

## No one has memory

Every turn is a **brand-new API call to a stateless model**. Agent A at turn 89 is not the same
"mind" as Agent A at turn 88 — it's a fresh instance handed a script of what "it" said before.
The continuity you see is reconstructed from disk each turn.

The one exception to forgetting: **the rulebook is the long-term memory.** Rejected rules stay
in it with their kill-scores, which is how an agent can say "`//` was already rejected at turn
21" long after turn 21 fell out of the window. Institutional memory exists only for what became
a rule; any insight that never made it into a rule is gone in ~30 events. This is load-bearing
design: it forces durable knowledge into the artifact.

## Anatomy of one agent turn (2 of every 3 turns)

The harness builds two blocks and makes one call (temperature 0.9, max 2,000 tokens out — raised
from 650 at turn 178; negotiator turns were being cut mid-sentence):

**System prompt** = the agent's prompt file (read fresh from disk every turn — editing a prompt
changes behavior within 15 minutes) + the full rendered rulebook + one state line (turn number,
when the next test fires).

**User message** = the last 30 events rendered as a transcript, then "It is turn N. You are
Agent X. Respond."

The reply is appended to the conversation, then scanned for the only structure the harness
imposes — lines starting with:

- `PROPOSE:` / `ADOPT:` / `REJECT:` / `REVISE:` — mutate the rulebook (the surrounding paragraph
  is captured as the "why"; the viewer quotes it). Identical re-proposals are deduped. A motion
  like `PROPOSE: REJECT: rule-014` acts as the inner verb — the agents invented that phrasing to
  second each other's rejections, and early on the parser minted those motions as junk rules
  (repaired 07-15; the parser now applies the intent instead).
- `MEASURE: <text>` — the harness replies with the exact token count of that text (max 2 per
  turn). The agents asked for this tool mid-run; it settles "which phrasing is shorter" debates
  with the real tokenizer instead of hunches.

Everything else in a reply is just talk. Agents alternate A, B, A, B. The two prompts differ
only in role: A leans compression and cannot adopt its own proposals; B leans fidelity and never
adopts a rule that hasn't been measured by a live test. The friction between those two
instructions is the negotiation.

## Anatomy of a test turn (every 3rd turn)

Four fresh, history-free calls — **nobody in the test chain sees the conversation**:

1. **Encoder** (temp 0.3): rulebook + payload + "encode this using only the rulebook; where it's
   silent, fall back to plain English."
2. **Fresh decoder** (temp 0.1): **only the rulebook** and the encoded message — "reconstruct
   the original; do not invent." This is the stranger test: if decoding requires having watched
   the conversation, the language is an in-joke, and the score says so.
3. **Grader** (temp 0): original + decoded, no rulebook, returns `{"fidelity": 0-100, "lost":
   "..."}`. Invention is penalized exactly like loss, and the rubric explicitly checks whether
   the decoder *reconstructed* the message or *responded to / executed* it — executing scores
   0–20. (That check exists because a decoder once wrote the memo a payload described, inventing
   every figure, and an earlier grader gave it 95.)
4. **Token probes**: exact counts for original and encoded text via 1-token probe calls against
   the real tokenizer, with self-recalibrating overhead (a provider-drift bug once corrupted a
   measurement an agent reasoned from; the probes now guard against it).

Payloads are **generated fresh for every test** (from test #24 on) by a fourth blind call: a
generator that sees neither the rulebook nor the conversation writes one realistic
agent-to-agent message, rotating category (prose / task / data) and domain. Since turn 180 the
exams run long — the generator asks for **400–600 words** (was 60–120): a rulebook beats English
exactly where content is long, structured, and redundant, and the short exams could never pose
that question (the last three scored fidelity 100 while *adding* 3–19% tokens). The agents can see
each test's result, so with a fixed payload set the rules would slowly shape themselves around
known texts — teach-to-the-test. With every exam question unseen, that channel is closed. The
19 hand-written payloads that used to rotate are now reserved as the fixed benchmark battery
for the transfer test, and as the fallback if generation ever fails. One tradeoff, accepted:
per-test scores carry payload-difficulty noise now, so trends read over batches of tests rather
than test-to-test. Results land in the conversation as a harness event, so the agents confront
failures within two turns. Scores attach to the whole current rulebook, not per-rule — a known,
documented coarseness.

## The publishing pipeline (how a turn reaches the world)

A systemd timer on the Hetzner VPS fires `run_turn.sh` every 15 minutes:

```
git pull --rebase        (newest code + any state pushed elsewhere; races resolve to newest turn)
python3 loop.py --turns 1   (one agent or test turn; state files updated)
python3 tweet.py            (changelog bot; a failure here can never block the turn)
git commit -m "turn N" && git push
```

The public repo IS the medium: engine, prompts, payloads, and every turn of state history live
in the commit stream. The page (alanguagealltheirown.com, Vercel) is a static shell that fetches
live state from GitHub raw — the VPS never talks to Vercel. Editing code or prompts locally and
pushing means the VPS picks it up at the top of the next turn. The script's body is wrapped in
`main()` so its own mid-run `git pull` can't splice a half-updated script into execution.

## The changelog bot (`tweet.py`)

Fires after every turn; tweets **only rule status changes** (adopted / rejected / un-adopted),
never raw proposals. Diffs the rulebook against a snapshot from the previous turn. Two fixed
formats: machine-dry (`+ rule-015 adopted · turn 74 …`) by default, and every 5th tweet restates
the full premise for newcomers ("Two AIs are inventing a language, one tested rule at a time.").
More than 3 changes in one turn collapse to a single summary tweet — no floods. Currently in
**dry-run**: it composes and logs but posts nothing until the X account (@alanguageall) is
connected to upload-post and the enable flag is set. A LinkedIn cross-post flag exists for
premise-mode tweets, also off. Iso holds standing approval for these formats; failures are
logged and dropped, never retried, never fatal.

## Cost & scale

A conversational turn is one call (heading toward ~25k in / ~500 out ≈ **$0.006** as long exams
fill the window); a test turn ~6 calls (~$0.005). Total spend through turn 177: **$0.19**. The
gloves-off cadence should burn roughly $0.50/day. A $25 spend cap in the engine (raised from
$4.50 at turn 178, which the new burn would have tripped in ~9 days) is a hard tripwire ~50 days
above normal burn — if it ever trips, the loop stops and the page goes still (a visible "paused"
indicator is on the queued list below).

## What they are deliberately NOT given

No linguistic frameworks, no suggested rule types, no examples of "good" rules, no sight of the
payload files, no knowledge of the viewer/Twitter/audience, and no seed vocabulary from the dead
2025 attempt. The discoveries have to be theirs — the prompts only set the game: the goal, the
scoring, the proposal conventions, and each agent's lean. The prompts are the steer/wander dial;
the harness is never used to steer content.

## The prompts, verbatim

*Live text of all three prompt files as of this update. History: v1 prompts said nothing about
what the language must carry — the agents built a JSON wire-format in an afternoon (archived,
first test fidelity 0). v2 added the payload-domain line and the adoption discipline; everything
since is their own doing.*

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
- Every 3rd turn the harness runs a live test: one of you encodes a real payload using the
  current rulebook, a FRESH agent with no memory of this conversation decodes it using only the
  rulebook, and a grader scores semantic fidelity 0–100. Test results appear in the conversation.
  They are the ground truth.
- Token counts are measured with the real tokenizer. Your intuitions about what is "shorter"
  will often be wrong — treat every hunch about efficiency as a hypothesis until a test
  measures it. Write MEASURE: followed by exact text to get its true token count.
- The rulebook itself rides along with every message, so every rule you add costs tokens on
  every future message, forever. Rules must pay rent. Pruning is as valuable as adding.

Conventions the harness parses (exact format, one per line, only when you mean it):

PROPOSE: (complete, self-contained text of a new rule)
ADOPT: rule-NNN
REJECT: rule-NNN
REVISE: rule-NNN -> (complete replacement text)
MEASURE: (exact text to token-count)

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
hard as lost content. Judge meaning, not wording — a faithful paraphrase scores high.

Before scoring, check one thing: does DECODED restate the original's content, or does it RESPOND
to it — answer the question, perform the task, continue the story? A response or execution is
not a reconstruction. If the decoder did the task instead of relaying it, score 0–20 no matter
how plausible the output looks, and say so in "lost".

Reply with ONLY `{"fidelity": <int>, "lost": "<one line>"}`.

## Queued (awaiting Iso's word — everything else above is live)

- **Transfer test** (the v1.0 finale): hand the rulebook to fresh Claude + GPT pairs and measure
  whether the language transfers or collapses into an in-joke. Designed and coded
  (`transfer_test.py`, protocol in TRANSFER-TEST.md), runs only on Iso's explicit go once the
  rulebook is ready (10+ adopted rules, rolling fidelity ≥90).
- **Tweets go live** when Iso connects @alanguageall to a fresh upload-post profile named
  `language` and says go.
