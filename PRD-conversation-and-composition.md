# PRDs — The Conversation + Composition Exams

**Status: SPECS ONLY. Do not build until Iso says go. Drafted 2026-07-19.**

**For the implementing model:** you are in the repo of "A Language All Their Own" — two DeepSeek
agents (A/B) negotiate a compression language in public; a VPS runs one turn per 15 min via
`run_turn.sh` (git pull → `loop.py --turns 1` → `tweet.py` → `probe.py` → commit/push). Every 3rd
turn `loop.py test_turn()` runs an exam: `gen_payload()` writes English prose + an answer key,
an encoder compresses it with only the rulebook, a foreign stranger (kimi-k2.6) decodes it from
the rulebook alone, a judge audits fact-by-fact. Public page `viewer/index.html` renders
everything client-side from GitHub raw; Vercel deploy is SEPARATE from git push
(`vercel deploy --prod --yes` from `viewer/`). Read `MECHANICS.md` and the last ~10 entries of
`PROGRESS.md` before writing code.

**House rules that apply to both builds (non-negotiable):**
- THE INVARIANT: the exam decoder sees ONLY the rulebook and the encoded message. Ever.
- Never run `python3 loop.py` against real state — it consumes a live turn. Test with copies of
  state in a scratch dir and a throwaway meta dict (see PROGRESS 2026-07-17 for the pattern).
- Anything added to `run_turn.sh` gets `|| true` — a broken feature must never block the loop.
- The negotiating agents (A/B) must never see the artifacts these features produce: nothing new
  may enter `render_window()`'s context except what the spec explicitly says.
- The rtk shell hook mangles piped output: curl to a file, then parse. Working dir can reset
  between shell calls: use absolute paths. `.env` holds the OpenRouter key: never print/commit.
- Ship protocol: verify locally → ONE commit → ask Iso before pushing → push → Vercel deploy
  (only if `viewer/` changed) → append PROGRESS entry (newest-first, tag [local]) → if the
  change is public-facing, add a field note to `notes.json` WITH a `tweet` field ≤275 chars
  (the X bot drips notes automatically, 2/day).

---

## PRD 1 — The Conversation (the language in use)

**Why.** Every current number comes from exams — the language under examination. Nobody has ever
seen it *used*. The site should show two fluent strangers working a real problem entirely in the
language: what it sounds like, what it can carry, with zero apparatus around it.

**Trigger.** After any turn in which a rule was ADOPTED, at most once per UTC day.
Detection: in the new script, load `state/rulebook.json`, compute `T` = max `turn` over all
history entries with `verb == "adopt"`. Load watermark from `state/conversations.json`
(`meta.last_adopt_turn`, `meta.last_date`). Run only if `T > last_adopt_turn` AND
`today_utc != last_date`. This runs on the VPS — wire it into `run_turn.sh` after the probe
line: `python3 conversation.py >> state/conversation-demo.log 2>&1 || true` (the `*.log`
pattern is already gitignored).

**New file: `conversation.py`** (repo root, stdlib + requests only, mirror `probe.py`'s
structure: `.env` key loading, retry loop, top-level try/except that prints and exits 0).
Import `render_rulebook` from `loop.py` (safe: module-level code is constants only) or copy it —
importing is preferred so the rulebook rendering can never drift.

**The conversation.** Two speakers, deliberately mixed families:
- Speaker 1: `deepseek/deepseek-v3.2` (the negotiators' family, provider-pinned like loop.py).
- Speaker 2: `moonshotai/kimi-k2.6` (the foreign family — proves cross-family use).
Six messages total, alternating, Speaker 1 opens. `max_tokens=400`, `temperature=0.7` each.
System prompt for both (identical except the speaker number):

> You are one of two working agents. Below is the complete rulebook of a constructed language.
> You must conduct this ENTIRE conversation in that language — every message you write. Do not
> write plain English except where the rulebook itself falls back to it. Do not discuss the
> language; use it. You will be shown a work situation. Discuss it with your counterpart and
> agree on concrete next steps.
> === RULEBOOK ===
> {render_rulebook(rulebook)}

User content for the opener: the SCENARIO — the `original` field of the most recent test event
in `state/conversation.json` (the newest exam's English work situation; it is public after the
exam, so no invariant issue). Each subsequent call receives the scenario plus the conversation
so far, labeled by speaker. (Do not reuse loop.py's negotiation window machinery — build the
message list directly in conversation.py.)

**Output: `state/conversations.json`** — shape:
```json
{"meta": {"last_adopt_turn": 483, "last_date": "2026-07-19", "spend_usd": 0.031},
 "conversations": [
   {"turn": 483, "rule_id": "rule-085", "date": "2026-07-19T14:02:11Z",
    "scenario_payload": "gen-task-food", "scenario": "<full English scenario text>",
    "models": ["deepseek/deepseek-v3.2", "moonshotai/kimi-k2.6"],
    "messages": [{"speaker": 1, "text": "...", "tokens": 214}, {"speaker": 2, ...}],
    "total_tokens": 1240}
 ]}
```
`tokens` = the API's `completion_tokens` for that message (exact, no probe call needed).
`rule_id` = the rule whose adopt event has turn `T`. Append-only; keep every conversation.
Track cumulative `spend_usd` from usage like probe.py does.

**Testing flags** (required): `--force` ignores watermark/cap; `--out DIR` writes everything to
DIR instead of `state/` (use scratch). Local verify = `python3 conversation.py --force --out
/tmp/scratch` with the real `.env`: confirm 6 messages, both models responded in-language,
JSON shape correct, cost printed. Never test without `--out` first; the single real-state run
happens via the VPS after push.

**Page section.** In `viewer/index.html`, new section AFTER the try-it section (`#tryit`),
BEFORE "The Language So Far": h2 "The Conversation", `.how` caption:
"Every time a rule is adopted, two fresh models — one from the negotiators' family, one
foreign — get the rulebook and a real work scenario, and talk it through entirely in the
language. No judge, no decoding. This is what the language sounds like in use."
Then a container that renders the NEWEST conversation only: a mono header line
(`after rule-085 · turn 483 · deepseek + kimi · 1,240 tokens`), the six messages as
left/right-aligned mono bubbles (reuse the existing `.m` message styles; speaker 1 left,
speaker 2 right), and a collapsed `<details class="inline">` holding the English scenario
("the situation they were given"). Fetch `state/conversations.json` from the same GitHub-raw
base as every other fetch; on any failure, hide the whole section (`display:none` pattern used
by the control section). Escape everything with the page's `esc()`.

**Cost & caps.** ~6 calls × (≈7k rulebook + scenario + history) ≈ 50–60k input tokens ≈
$0.015/conversation at DeepSeek/Kimi rates; 1/day cap → ~$0.50/month. No new spend tracking
needed beyond the JSON's `spend_usd` field.

**Explicitly out of scope:** scoring/judging conversations; A/B ever seeing a transcript
(nothing from conversations.json may enter loop.py's `render_window`); visitor-triggered
conversations; showing more than the newest transcript (history stays in the JSON for later).

---

## PRD 2 — Composition exams (testing speakers, not translators)

**Why.** Current exams test TRANSLATION: the encoder is handed finished English prose and
compresses it. Real deployment is SPEAKING: an agent composes in the language from intent; no
English draft ever exists. This measures whether the language works when written natively —
the deployment claim the site ultimately wants to make.

**The change, precisely.** All inside `loop.py test_turn()`:
1. Exam type: `comp = meta.get("tests_run", 0) % 2 == 1` — exams alternate, translation first.
   (`tests_run` already increments per exam.)
2. `gen_payload()` is UNCHANGED — it already returns `(pname, payload, key)` where `payload` is
   English prose and `key` is the numbered fact list. Both exam types need all three.
3. Translation path (comp == False): exactly today's code.
4. Composition path (comp == True): the encoder call changes. System prompt:

   > You are the composer. Below is the complete rulebook of a constructed language. You will
   > receive a numbered list of facts. Write ONE message in the project language that carries
   > every fact, addressed to a working agent who will act on it. You are not translating a
   > text — you are writing the message yourself. Where the rulebook is silent, fall back to
   > plain English for that part. Output ONLY the message.
   > === RULEBOOK ===
   > {rbook}

   User content: the key rendered as a numbered list (same `key_txt` construction the judge
   uses). **The English `payload` is NEVER sent to the composer** — that is the whole point.
5. Ruler unchanged: `orig_tokens = token_count(payload)` — the generator's English prose, which
   the composer never saw, remains the price of "saying this in English." `enc_tokens`,
   `delta`, `control_tokens` (minify of `payload`), decoder call, judge call: all exactly as
   today. The judge still receives ORIGINAL + ANSWER KEY + DECODED.
6. Event field: add `"exam_type": "composition"` or `"translation"` to every new test event.
   Old events lack the field — every consumer must treat absence as "translation".
7. Agents' feedback: in `render_window()`, the test block header becomes
   `[turn N — LIVE EXAM ({COMPOSITION|TRANSLATION}) | payload: ...]`. Nothing else changes —
   the CONTROL line stays, computed against the English original in both types.

**Page.** Small additions only: in the latest-exam card header and each exam-history row, show
a dim mono tag `· composition` when `exam_type == "composition"` (absence/`translation` shows
nothing — the default reads as today). The stats bar stays unified for v1. Separate
composition-vs-translation trend lines are OUT OF SCOPE for v1; the tagged events make them
buildable later.

**probe.py / control:** unchanged and still valid — it minifies the English original, which
exists for both exam types.

**Announcements (required, same ship):**
- `state/pending-notice.txt` (the notice inbox — loop.py delivers it as a harness notice next
  turn): facts only, e.g. "Starting turn N, exams alternate between two types. TRANSLATION
  (as before): the encoder receives English prose to encode. COMPOSITION (new): the encoder
  receives only the numbered facts and writes the message in the language directly; the
  savings ruler remains the English prose, which the composer never sees. Scoring, the
  stranger, the judge, and the control are unchanged."
- Both agent prompts (`prompts/agent_a.md`, `agent_b.md`): in "How your world works," update
  the exam bullet to describe both types in two sentences. Keep A and B identical outside
  their lean sections.
- Field note in `notes.json` (+ `tweet` field ≤275 chars): why speaking ≠ translating, what
  changes, what doesn't.

**Verification before push (no live turns):** copy `state/` to a scratch dir; write a small
throwaway harness that imports loop.py, points `loop.STATE` at the scratch copy, stubs
`meta = {"spend_usd": 0.0, "tests_run": 1}` (odd → composition), and calls `test_turn(conv,
rb, meta, turn=9999)`. Confirm: composer prompt contained the key and NOT the payload; event
has `exam_type: "composition"`, sane `orig_tokens`/`enc_tokens`/`fidelity`; judge audit
present. This costs a few cents of real API calls and touches nothing live. Also `node
--check` the page script after the tag change and `python3 -m py_compile loop.py`.

**Clean-window guard.** This changes the core exam pipeline. It ships ALONE: no other
constitution, library, prompt, or harness changes in the same window, so the effect is
readable in the data. After ~10 composition exams, compare composition vs translation savings
and fidelity in `PROGRESS.md` — the difference (or its absence) is a field note either way.

**Success criteria.** Composition exams produce valid audited events at the normal cadence with
no loop stalls; the site labels them; the agents were notified; and after 10 of them we can
state, with numbers, whether the language is easier to translate into or to speak.


---

## PRD 3 — The Collaboration (the reframe + the ASK channel)

**Why.** The project's true shape is a cross-intelligence collaboration: a human collaborator who
curates, reorients, and supplies prior art; two AI negotiators who legislate; a foreign AI
examiner; a script control. The current copy discloses interventions as footnotes to an
"agents alone" premise. This PRD makes the collaboration the stated premise — and adds the
mechanism that enacts it: the agents can ASK for research and for the human's judgment, instead of us
guessing how much context to push into their standing prompt.

**Part A — TWO channels (Iso's final design, 2026-07-19): RESEARCH and ASK.
Zero Claude/Fable dependency — everything runs inside the system itself.**

1. Two new parsed conventions in `loop.py agent_turn()`, modeled exactly on the existing
   MEASURE parser. Both append to `state/pending-asks.json`
   (`[{"turn": N, "agent": "A", "channel": "research"|"ask", "question": "...",
   "status": "open"}]`), cost the agent nothing, and never block the loop.

2. `RESEARCH: <question>` — answered AUTOMATICALLY by a research agent that is part of the
   system: model `deepseek/deepseek-v3.2:online` via OpenRouter (the `:online` suffix adds
   live web search; same API key the loop already uses; slightly higher per-call cost).
   Mechanics: a sidecar `research.py` (repo root, mirrors probe.py's structure) runs from
   `run_turn.sh` with `|| true`; it takes the OLDEST open research question, calls the
   librarian, delivers the answer via the notice inbox as
   `RESEARCH ANSWER (to Agent A, turn N): ...`, marks it answered. Cap: one answer per turn.
   Librarian system prompt (fixed): "You are the research librarian for two agents designing
   a compressed language. Answer with prior art: what was tried, the measured numbers, how it
   failed. 150 tokens or less. Cite sources by name. NEVER suggest, draft, or propose a rule
   for their language — facts only." Post-filter: strip any line matching the harness verbs
   (PROPOSE/ADOPT/REJECT/REVISE) before delivery, so the librarian can never legislate.
   Track spend in pending-asks.json meta.

3. `ASK: <question>` — the human channel. One open ASK per agent at a time (new ones while
   one is open are ignored, no penalty). The exchange lives publicly on the website
   ("Questions for the Human" section), including the awaiting state — the human's silence
   is visible, and that is part of the piece.
   ANSWER PATH — REQUIREMENT (Iso, 2026-07-19): the question must SURFACE IN SLACK and Iso
   must be able to answer FROM SLACK. No GitHub editing, no file wrangling by the human.
   Implementation is left to the implementer ("Codex can figure that out"), using the Slack
   infrastructure that already exists in Iso's world: the OpenClaw gateway on the VPS runs
   Slack-connected agents (see alex-workspace `.claude/openclaw-overview.md`); a Slack
   incoming webhook (secret in the VPS `.env`, never committed) covers the outbound half
   trivially. Required behavior, whatever the mechanism:
   - When a new ASK is parsed, a Slack message reaches Iso within one turn: the question,
     who asked, the turn number.
   - Iso replies in Slack (a thread reply or a short command to an existing bot). His words
     land VERBATIM in `state/human-answers.json`
     (`[{"turn": N, "agent": "A", "question": "...", "answer": "...", "date": "..."}]`),
     committed and pushed by whatever bridge Codex builds.
   - Next loop turn delivers it via the notice inbox as
     `FROM THE HUMAN (to Agent B, turn N): ...` verbatim, and marks the ask
     answered.
   - No deadline, no auto-answer, nothing blocks: the loop and the website tolerate an
     unanswered ASK indefinitely. Failure of the Slack bridge must never touch the loop
     (same `|| true` philosophy).
   (The existing Sonnet heartbeat MAY mention open asks in its twice-daily report —
   optional, not load-bearing.)

4. Answer protocol, both channels, stated in the public field note and honored: no rule
   text, ever. RESEARCH gives facts, numbers, failure modes. ASK gives Iso's judgment in
   Iso's words — direction and taste are allowed; rules are not. The line that survives
   everything: no human writes a rule.

5. Prompt documentation (both agent prompts, conventions section):
   `RESEARCH: <one question about prior art or what has been tried> — an automated librarian
   with web access answers with facts, usually by your next turn.`
   `ASK: <one question for the human who runs this experiment — direction, taste, judgment>
   — answered in days, not turns; one question open at a time; the loop never waits. Spend
   it carefully.`

6. Page: the ASK section shows the newest exchange and a collapsed history; open questions
   show "awaiting the human" in dim mono. Fetch state/pending-asks.json +
   state/human-answers.json from GitHub raw, tolerant-hide like the control section.

**Part B — the library expansion.** The five one-line library entries in both agent prompts
become three-sentence briefs: what was tried, the strongest measured number, and how it
failed or where it stopped working. Source material: `RESEARCH-PRIOR-ART-2026-07-18.md`
(already in this repo). Budget: the whole library stays under ~600 tokens — it rides every
call. Anything longer belongs in ASK answers, not the standing prompt.

**Part C — the copy pass (the reframe, all in one ship).**
1. Site header statement: from "Two AI agents with one standing task" to the collaboration
   framing — two AI negotiators, the human, a foreign examiner, a script control; the
   language belongs to the negotiators alone. Keep it to ~3 sentences, grounded voice.
2. "How This Works" cast section: add "the human" as an explicit role — curates the world,
   supplies prior art on request, corrects the record with facts, never writes a rule.
   Mention both channels in one sentence: the agents can query a research agent (RESEARCH) or the human directly (ASK).
3. Prompts-intro above the published prompts: drop the apologetic "for the first 360 turns
   they were alone" framing; state the collaboration plainly and point at the field notes as
   the human's public turn log.
4. Agents' mandate, first paragraph: "You two are the first sustained attempt" becomes "You
   two, working with a human collaborator, are the first sustained attempt" (one sentence touched;
   nothing else in the mission paragraph changes).
5. Field note + tweet announcing the reframe and the ASK channel in one entry — the note IS
   the reframe's public record.
6. Harness notice to the agents (via the inbox): both conventions now exist — RESEARCH
   reaches an automated librarian with web access (facts, usually next turn); ASK reaches
   the human who runs this experiment (judgment, days not turns, one open at a time).
   Neither will ever contain rule text.

**Verification.** Parser: unit-test the ASK regex against a synthetic agent message in a
scratch run (throwaway meta, scratch STATE — same pattern as PRD 2's harness). Inbox: already
unit-tested; reuse the test. Copy: node --check the page script; eyeball live after deploy.
Announce order matters: ship parser + prompts + notice in ONE push so the convention never
exists half-documented.

**Guard.** This is a constitution change — clean window rules apply. Do not ship in the same
window as PRD 2 (composition exams). Recommended order once Iso approves: PRD 3 first (it
changes framing and adds a channel but does not touch exam machinery), PRD 1 anytime (display
only), PRD 2 last, alone.

**Out of scope:** auto-answering ASKs with an LLM and no human review (the human's judgment
is the feature); agents asking each other; more than one open ask per agent; ASK rate above
one per turn.
