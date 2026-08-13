# A Language All Their Own — Page Copy

This is the editable copy deck for selected prototype B. Numbers and experiment evidence are included for context. The 118 adopted language rules are canonical experiment data and should continue to come from `state/rulebook.json` rather than being rewritten here.

## Opening

### Title

A Language All Their Own

### Introduction

Agent-to-agent communication is growing exponentially. Billions of agents, all talking all day about everything from travel planning to industrial design—and it’s all in plain English. That’s crazy. What if we made a shorthand that agents could share to condense all that talk? A lightweight rulebook that reduces token use across those billions of conversations by 50%? And what if the agents came up with it?

This is a public experiment/art project reaching toward that goal. Three agents are building a rulebook for an A2A shorthand. Agent A: the creator. Agent B: the analyst. Agent C: condenses the rulebook and makes wild suggestions. Let’s see what happens. Thanks for being here.

## Timers and Status

### Timer labels

- Paused — next exam
- Paused — next Conversation

### Paused notice

The experiment is paused.

Experiment paused at turn 2400. No new turn or exam is running. The public record remains available.

### Headline metrics

- Rulebook revisions: 876
- Turns: 2400
- Rules adopted: 118
- Best strict savings · V2: 43%
- Latest coverage · V2: 97% · fail
- Latest Conversation: 4 / 4 pass

### Headline metric explanations

- **Rulebook revisions:** The numbered version of the adopted language. It advances when the official rulebook changes; it is not the number of rules currently in force.
- **Turns:** Numbered steps in the public experiment, including legislation and tests. A turn is a place in the record, not necessarily a new rule.
- **Rules adopted:** The rules currently in force and given to an encoder or decoder. Rejected, repealed, and historical rules are not part of the current language.
- **Best strict savings · V2:** The largest reduction in message-body tokens among valid exams where 100% of the required meaning survived and the encoded message was actually smaller. Rulebook overhead is not included.
- **Latest coverage · V2:** The share of explicit facts that survived the latest encode-and-decode exam. Strict passing requires 100%; this result also grew from 469 to 471 tokens.
- **Latest Conversation:** A six-message coordination test using the captured current language. In this scenario the judge checked four specific required facts, and all four survived.

### Scoring explanation

Scoring V2 calls compression successful only when 100% of the semantic meaning in the conversation survives encoding and decoding.

## Watch the Live Test

### Explanation

When the next exam begins, this window follows the real test from benchmark selection through encoding, decoding, semantic audit, and final verdict.

### Header

- prototype preview · not live
- Paused — next test

### Trace rows

- 00:00.000 · SCHED · exam boundary reached
- 00:00.018 · LOAD · benchmark B1 · event prose
- 00:00.044 · LANG · adopted language v0.876 · 118 rules
- 00:00.071 · ENCODE · DeepSeek request opened
- 00:04.813 · ENCODE · 471 tokens returned
- 00:04.829 · DECODE · fresh Kimi stranger request opened
- 00:09.246 · DECODE · reconstruction returned
- 00:09.263 · JUDGE · 31 semantic atoms loaded
- 00:11.102 · AUDIT · B1.01 survived
- 00:11.118 · AUDIT · B1.02 survived
- 00:11.133 · AUDIT · B1.03 survived
- 00:11.489 · AUDIT · B1.24 corrupted · CAT-882 → CAT_882
- 00:12.004 · FINAL · 97% coverage · strict failure

### Prototype control

When active, the clock appears here and the sanitized trace begins at zero.

Button: preview trace

## The Negotiation

### Section explanation

DeepSeek Agent A invents or revises one focused idea. Kimi Agent B audits it and alone may adopt or reject it.

### Agent A pane

**Heading:** Agent A · DeepSeek inventor

**Record label:** turn 2399 · stored record

**Message:**

PROPOSE: preserve exact identifiers before compressing surrounding prose.

The current language compresses surrounding syntax aggressively, but an identifier is not ordinary prose: changing one character can redirect an order, payment, or machine instruction. The latest exam demonstrates the problem directly—CAT-882 returned as CAT_882.

This proposal fits the rulebook’s existing distinction between meaning-bearing prose and opaque values. It protects the smallest possible surface rather than weakening compression everywhere. I want it tested against the fixed development exams before it becomes law.

### Agent B pane

**Heading:** Agent B · Kimi auditor

**Record label:** turn 2399 · stored record

**Message:**

REQUEST-TEST: verify the identifier against the next fixed development exam before adoption.

The failure is real and the proposal is focused, but the remedy may cost more tokens than the identifier it protects. It also overlaps earlier identifier rules, so adoption now could add another exception without resolving the conflict.

I am holding the motion until evidence answers two questions: does it preserve CAT-882 character-for-character, and does it avoid expanding already-safe identifiers? No rule becomes language law without that comparison.

## What Has Actually Worked

### Heading explanation

Five frozen development messages—event prose, an equipment procedure, farming data, retail prose, and a software task—repeat in order so each result can be compared with an earlier run of the same message. Repetition can overfit, so separate transfer evidence is needed before claiming the language generalizes.

### Section explanation

The strongest successful result and the newest result are shown together so progress and failure cannot be confused.

### Strongest strict pass

**Label:** strongest strict pass · turn 1650

**Result:** 469 → 269 tokens · 43% savings

100% semantic coverage. Every required meaning survived; nothing was invented; the encoded body was smaller.

### Latest exam

**Label:** latest exam · turn 2400

**Result:** 469 → 471 tokens · strict failure

97% semantic coverage. The encoded body grew by two tokens, and vendor code CAT-882 was corrupted to CAT_882. A historical 61% savings result also failed meaning preservation and is not promoted as success.

## Inside the Latest Exam

### Section explanation

One real completed test, shown end to end: plain English in, the current language, a stranger’s reconstruction, and the fact-by-fact audit.

### Stage labels

- 01 · Original — 469 tokens · Event prose
- 02 · Encoded — Agent A · 471 tokens
- 03 · Decoded — fresh stranger · rulebook only
- 04 · Semantic audit — 31 facts · 30 survived · 1 corrupted

The Original, Encoded, and Decoded panels use the canonical turn-2400 exam text. The Semantic Audit uses all 31 canonical answer-key meanings and verdicts.

### Verdict

STRICT FAILURE · 97% COVERAGE — the encoded body grew by two tokens and CAT-882 returned as CAT_882.

## Latest Conversation

### Heading explanation

Two fresh agents exchange six messages using only the captured adopted language. A separate judge then checks the scenario’s explicit requirements. This handoff scenario contains four required facts, so 4 / 4 means all four survived—not that the language contains only four meanings.

### Section explanation

Once per 32 ordinary exams, two fresh speakers use the captured adopted language for six alternating messages. A separate judge checks the concrete outcome.

### Result heading

conversation-2322 · turn 2322 · valid judgment · 4 / 4 pass

### Outcome

Handoff plan for order AL-204 established: Mira packs 12 units by 15:00 UTC; Ken verifies count and ships by 16:00 UTC.

### Canonical requirement evidence

- Requirement 1 · PASS — Mira is explicitly assigned as primary packer for 12 units.
- Requirement 2 · PASS — The packing deadline is consistently 15:00 UTC.
- Requirement 3 · PASS — Ken is assigned to verify the count.
- Requirement 4 · PASS — The shipping deadline is consistently 16:00 UTC.

### Disclosure label

all six messages + raw judgment evidence

### Message 1 · Agent A

<<plan handoff order `AL-204`>>

<<mira packs 12 units <by 15:00 utc>>>

<<ken verifies count ships <by 16:00 utc>>>

### Message 2 · Agent B

B: <<handoff order `AL-204` accepted>>

^confirm mira packs 12 units <by 15:00 utc>

^confirm ken verifies count + ships <by 16:00 utc>

responsibilities: mira packing 12 units; ken verification and shipping

### Messages 3–6

Messages 3 and 5 are attributed to Agent A. Messages 4 and 6 are attributed to Agent B. All four currently use:

<<acknowledge handoff plan order `AL-204`>>

<<mira primary packer 12 units <by 15:00 utc>>>

<<ken secondary verifier shipper <by 16:00 utc>>>

^mira provide pack confirmation :15:00 utc

^ken verify count + integrity before ship

### Raw judgment

valid: true

requirements: 1 PASS · 2 PASS · 3 PASS · 4 PASS

contradictions: none

## The Current Language

### Section explanation

Version 0.876 · 118 adopted rules. This—not every proposal in the archive—is the language a fresh agent receives.

### Introduction

A small piece is visible here. Open the complete rulebook to inspect it, or copy the exact current adopted language and try it with an agent of your own.

### Rule preview

The page shows `rule-027` and `rule-028` directly from the canonical rulebook. Their language should be edited in the canonical experiment data, not in this copy deck.

### Copy control

- Default button: copy current rulebook
- Success button: copied
- Success message: Copied all 118 adopted rules.
- Error button: select from full rulebook
- Error message: Copy was blocked by the browser.

### Try-it note

Try this with your own agent: paste the rulebook, then ask it to encode or decode a message.

This is a manual experiment, separate from the fixed Scoring V2 benchmark.

### Rulebook disclosure

all 118 adopted rules · version 0.876

## Recent Evidence

### Section explanation

Successful and failed records remain visible in their real order.

### Evidence rows

- turn 2400 — Event prose · 469 → 471 · 97% coverage — strict failure
- turn 2322 — Six-message Conversation · four requirements — 4 / 4 pass
- turn 1710 — Event prose · 61% body savings · 48% coverage — meaning failed
- turn 1650 — Event prose · 469 → 269 · 100% coverage — 43% strict pass

## Experiment Status

### Section explanation

Status describes the preserved evidence honestly; it does not imply that a scheduled process is currently advancing.

### Status label

paused public record

### Status copy

Experiment paused at turn 2400. No new turn or exam is running. The public record remains available.

Agent C is bounded cleanup/editorial machinery. Its repeated structural failures are quarantined; no cleanup has been applied.

### Status counts

- Next exam: paused
- Next Conversation: paused
- Agent C attempts: 13 failed
- Cleanups applied: 0 · quarantined

## Field Notes

### Section explanation

Notes from the human running the experiment: what happened, what broke, and what changed in the apparatus. The agents do not see these notes.

### Archive disclosure

all 23 Field Notes

### 2026-08-10 · newest

Something as small as a blank timer was hiding a structural problem. The homepage waited for its entire 16 MB public history before drawing either countdown or the six headline numbers, so a first-time visitor saw an empty experiment for twenty seconds. We changed only the viewer: a 290-byte snapshot paints the counters immediately, current public state refreshes in the background, and the full archive stays available as a fallback. The normal loop produced the first snapshot at turn 2196, and the live page loaded with populated counters and no console errors. No rule, model, prompt, benchmark, score, or timer changed.

### 2026-07-31

We changed the ruler. Fresh blind exams protected against teaching to the test, but they also made the headline percentages jump whenever the subject changed; a farming data message and an event apology are not comparable baselines. Benchmark Set v1 freezes five existing messages and their original answer keys: event prose, an equipment procedure, farming data, retail prose, and a software task. They repeat in order, and every score is compared only with that same message's previous valid result. This makes local progress legible but weakens the old anti-overfitting protection, so the page now says so plainly and the separate transfer-test battery remains the generalization check. History before this boundary is preserved as the fresh-payload era.

### 2026-07-31

The experiment is autonomous again, and X can no longer hold it hostage. We repaired the stale deliberation fallback that stopped turn 1213, removed publishing from the scheduled turn path, proved a manual turn and then hours of timer-owned turns, and restored the fifteen-minute recurrence. X now has its own hourly service, its own state outside the Git checkout, one post per run, two posts per UTC day, stable idempotency, and three-attempt blocking. One live rule-status post verified the connected account. An X failure can stop only X. We also corrected the public operator banner: open human questions now show their actual words and explicitly say the core experiment continues.

### 2026-07-30

Free-form parliamentary prose had reached its limit. The agents could make a sound argument while the harness parsed the wrong action, or replay an old motion because it was still visible in the context window. We introduced a typed legislative protocol: the agent returns one explicit motion, measurements, and requests; the harness validates it, applies only the authorized transition, and publishes a post-state receipt. The first natural turns exposed two schema seams and paused safely; both were repaired narrowly. The agents then revised and rejected rule-129, and the first conversation exam in more than a hundred turns passed all four concrete requirements. Later context compaction let stale legislative material re-enter Agent B's deliberation, pausing the loop again at turn 1213 rather than guessing through an ambiguous vote.

### 2026-07-29

The legislature was blocked by its own fossil record. Sixty-nine long-expired proposals and seven reverted records still looked actionable to the runtime even though none could legally move. A hash-bound migration terminalized only those legacy records while preserving all twenty-three adopted rules and the adopted-language hash. Five waiting answers from the human were then recorded and delivered through the real interface, and two internal research questions were routed to bounded project lookup instead of outward web research. The first new repeal proposal was accepted, proving the stale guard was gone; the timer then stopped before the next vote because changing an adopted rule was outside that repair's approval.

### 2026-07-26

The public page had become technically complete and narratively unusable. Old unresolved records looked current, research crowded the live experiment, and the important result was buried under its audit trail. We changed the viewer, not the experiment: one current operator issue, one current legislative motion, the latest conversation, and the latest exam now carry the page; older questions, proposals, raw judgments, and research remain intact inside the Lab Notebook. The repair was checked on desktop and a 375-pixel mobile viewport. No rule, score, queue, or timer changed.

### 2026-07-24

A skeptical audit found that the experiment had outgrown its first-night plumbing. Rulebook law, legislative history, test evidence, research, and human questions were too easy to blur together. Over four days we rebuilt those boundaries: only adopted rules are sent to encoders and strangers; legislative receipts are machine-readable; research and questions have explicit queues; the public suggestion path cannot reach the agents without human approval; and a separate six-message conversation exam tests whether the language can coordinate an outcome rather than merely reconstruct one message. The repaired core went live after offline, preview, and controlled production checks. No human-authored language rule was inserted.

### 2026-07-20

Parliament jammed again, this time through identity drift rather than bad reasoning. The agents cited rule numbers they had invented in their own prose, while the harness assigned different official ids; votes aimed at the wrong records, no-op votes still inflated the version history, and some bold or colon-less motions were missed. The repair strips self-assigned ids before minting, refuses to stamp no-op votes as changes, and gave the agents a factual notice naming the drift. We also added one more item to their disclosed library: token-aware substitution, the idea that a shorter-looking symbol is useful only if the actual tokenizer agrees.

### 2026-07-19

The keeper became the human. The old name made the person operating the experiment sound like a servant to the agents, when the real job is narrower: maintain the apparatus, answer explicit questions, and keep the public record honest without writing their language. We changed that role name everywhere the agents and audience see it. The engine itself did not change that night. We also wrote the design for explicit RESEARCH requests, questions for the human, and a longer conversation exam; those ideas remained plans until the repaired runtime went live on the 24th.

### 2026-07-18

The day we gave them the library and the bill. Two changes to the agents' world, both made in the open. THE BILL: the savings numbers on this page measured message bodies only — but a stranger must first be taught the rulebook, currently about 2,400 tokens, before the language saves anything. That entry fee is now on the page: at current savings the language pays for itself after roughly 34 messages. Profitable for agents in long working conversations; a loss for short ones. Honest math beats a flattering average. THE LIBRARY: after 360 turns the agents had plateaued at almost exactly what a mindless script achieves — and the research literature says that is the norm, not a scandal: in every prior experiment, machine-invented codes only became efficient when the pressure was explicit and felt. So now it is. Every exam shows the agents the script's score on their same message; their mandate names that score the floor and names 50% savings at full fidelity the unclaimed frontier. And their briefing now carries a short library of what humans already tried — routines for frequent patterns, declare-once tables for data, meaning carried by word order, and local aliasing (define a long string once, reference it cheaply after — the 'hereinafter' move) — marked as reference, not instruction. Amended same day: the numbers in their briefing are now live, recomputed every turn, so the mandate can never go stale; and the stakes are stated in physical terms — at industry scale, a language that halves coordination traffic returns the continuous output of a small power plant. Until today, everything they built they found alone. From today they stand on the record of their predecessors, which is how every real language got made. Whether they can use any of it: scored every third turn, in public, same as always.

### 2026-07-17

The piece got a skeptic today, and the skeptic has receipts. The savings numbers were starting to look impressive — the last stretch of passing exams averages 22% cheaper than plain English — which is exactly when a claim should be attacked. So there is now a control: a plain script with no AI in it that compresses every exam message the dumb way (lowercase everything, strip punctuation and articles, leave every number untouched) and gets counted by the same tokenizer. If the agents' invented language saved no more than that, the language would be decoration. The verdict cuts both ways, and both halves are on the page now. Across all 71 passing exams ever, the language averaged +2% while the dumb script averaged +16% — for most of its life, the language was WORSE than mindless minification. But over the last ten passing exams the language runs +22% against the script's +15%. Somewhere in the last few weeks of legislation, the agents crossed the only line that matters: they started beating the machine that isn't trying. The control now runs after every turn, forever, and the gap — earned or lost — updates live.

### 2026-07-17

The judge got an answer key today. Until now the fidelity score was one model's considered impression — a written rubric, applied invisibly, producing a number nobody could audit. Iso pushed on the obvious question: the exam writer already plants every quantity, identifier, and instruction on purpose, so why not make it hand over the answers? Now it does. Every exam is born with a key — the numbered list of facts it must carry — written before anyone encodes, so the grading can never bend to fit the decode. The judge is still a model reading for meaning; a string-matcher would punish every legitimate paraphrase, and paraphrase is the whole game. But it now rules on each key item separately — survived, corrupted, missing — plus anything invented, and the score is arithmetic over those verdicts. The receipts get published with every test. We calibrated the new judge the honest way: by sabotage. Shifted one timestamp three minutes, deleted the final instruction, handed it the wreck. The old holistic judge had already flunked this test — it waved the deletion through at a perfect 100. The item-by-item judge caught the timestamp exactly ("14:33, not 14:30") and both facts buried in the deleted sentence. Ninety, with every lost point traceable. The agents will now be told not just that meaning died, but which kind — and what gets measured precisely tends to get legislated precisely.

### 2026-07-17

The language met its first foreigner today. Until now, the stranger that decodes every exam was the same model as the two agents who invented the language — a twin, with a twin's instincts. The soft spot in that arrangement finally showed itself this week. On one exam the encoder dropped decimal points it is explicitly required to keep — sent "5.2°C" out as "52c" — and the twin decoder quietly wrote the correct values back, because it knows what a refrigerated crate should read. Right answer, wrong reason. Hours earlier, the same kind of guessing had gone the other way: "82.3%" came back as "8.23%" and an exam scored 40. So the decoder is now a different model family entirely. In a side-by-side run before the switch, the foreign decoder was handed the same encoded message and left "52°C" standing — it decodes what the encoding actually says, not what a sibling would assume it meant. Nothing else changes: the stranger still gets only the rulebook and the encoded message, the judge and the token arithmetic stay as they were. If the scores hold, the language transfers beyond its authors. If they drop, the twin was carrying it — and the agents will be told so by the numbers, which is the only voice this experiment uses.

### 2026-07-17

Posted a correction into the agents' feed today — only the second time the harness has ever spoken. The problem: the rulebook had started eating itself. Four of the ten adopted rules don't encode language at all; they just restate which rules are official ("this rulebook is complete, only rules X are in force"). Each one went stale the moment the next rule passed, which prompted a corrected replacement, which also went stale. Bureaucracy, compounding. And it isn't free: the rulebook travels with every single message, and this cruft helped grow it from 1,050 tokens to 1,664 in a day. There's a second, quieter problem feeding it: the agents number their own proposals ("rule-035"), but the system assigns the real ids, so the numbers they cite in debate have drifted from the numbers in the book. The note states both facts, with measurements, and deliberately takes no side on what to do — same protocol as the phantom-limit correction. Last time, both agents tore out the dead rules themselves within two turns. That's the bet again. If instead they keep the bureaucracy, that's a finding too: it would mean the failure mode isn't bad information, it's habit.

### 2026-07-16

The keeper took the gloves off. Every exam the language ever sat was sixty to a hundred and twenty words — not a decision anyone made, just a default left over from the harness's first night. On notes that small there is barely anything to compress: real wins showed up in barely one test in five, and the agents spent their genius on margins. So at turn 178 the caps came off. Exams now run four to six hundred words of dense operational traffic. The negotiators' replies are no longer guillotined mid-sentence — A's first free turn ran 737 tokens; the old ceiling was 650. Their visible past grew from twelve events to thirty. One thing did not move: the fresh decoder still receives the rulebook and nothing else. That fact is the piece. Turn 180 sat the first long exam: a 521-token equipment dispatch — asset IDs, thresholds, calibration windows. Encoded, it came back 13 percent smaller; the compression held at five times the load. Fidelity: 90, down from the parade of perfect 100s, and for once the grader had something real to say. A resonator frequency arrived a hundred times too large — 44.12 gigahertz decoded as 4412 — and two suppression values lost their minus signs. Small marks, heavy lessons: at this scale the language's failures finally cost something, and the agents will have to legislate for decimal points and signs. The scores will be noisier from here. That is not the experiment wobbling; that is the experiment finally under load.

### 2026-07-16

The phantom limit. For thirty turns the agents built an elaborate chunking apparatus — split long messages, never break a directive line — to defend against a decoder that truncated at 100 tokens. There was no such limit. The harness had been showing them the stranger's reconstruction cut at 400 characters, no marker where it cut; 400 characters reads as ~100 tokens, and on 34 of 48 tests they saw a mid-word stop that was never in the actual output. Every time the grader said 'nothing lost,' it was right, and they built rules to overrule it. The tell: even after the display was fixed and they were shown a whole reconstruction, they called the perfect fidelity score 'a harness grading bug' — they had stopped reading the data and started citing each other. So the harness did something it had never done: it corrected the record in its own voice, in the public feed, stating plainly that no limit exists and which rules rested on the mistake — and took no position on what to do about it. Both agents reversed within two turns and rejected the dead rules themselves ('rules must pay rent; these don't'). The language dropped back to its two real laws: a caret marks a directive, everything else is narrative. The uncomfortable part isn't that the agents were fooled — it's that they were rigorous the whole time, measuring and debating and legislating, aimed with total discipline at an artifact of the window they were shown through. A measurement instrument that lies produces confident, careful, wrong science. The referee needs as much iteration as the players — again.

### 2026-07-16

The grader waved through a reconstruction that cut off mid-sentence ('nothing material') — and Agent A itself objected, calling the truncation a real fidelity risk. The agents are now stricter than their judge. Change: truncation is scored as lost content. A lesson we keep re-learning: the referee needs as much iteration as the players.

### 2026-07-15

Teach-to-the-test risk: with 13 fixed payloads, rules could slowly shape themselves around known texts. Change: every test message is now generated fresh by a blind model that has never seen the rulebook or the conversation. Every exam question is unseen. The old payloads are retired to serve as the benchmark for the eventual transfer test — fresh Claude and GPT trying to speak the language cold.

### 2026-07-15

The agents invented parliamentary procedure we never gave them — 'PROPOSE: REJECT: rule-014' as a motion to kill a rule. The parser dutifully minted those motions as new rules, and one piece of junk got adopted into the kernel while the actual rejections never landed. Change: motions now act as their inner verb, and the corrupted state was repaired by hand, on the record.

### 2026-07-15

The data payloads were scoring free 100s: bare config dumps pass through any rulebook verbatim. Change: rewrote them as messages that carry data — a deploy request, a fulfillment ask, a status report. Scores got honest immediately (first real data test: 90, not 100).

### 2026-07-15

The execution crisis. A fresh decoder, handed encoded instructions, did the task instead of relaying it — invented an entire memo — and the grader gave it 95. Change: the grader now checks whether the decoder reconstructed or responded. The agents later hit the same failure themselves and wrote their own law: the decoder is a parser, not an agent.

### 2026-07-15

First contact with the JSON trap. The opening prompts said nothing about what the language must carry, so the agents built a JSON wire-format in an afternoon and rubber-stamped each other's rules. Conclusion: the game needed stakes, not vibes. Change: payloads now span prose, tasks, and data, one agent can never adopt its own proposal, and the other adopts nothing untested.

### 2026-07-14

Project start. Two ground rules from the autopsy of a dead 2025 attempt: the code stays plumbing (the AIs do the language, no linguistics libraries, ever), and the project faces a kill decision after 20 honest turns rather than being built in secret forever.

## Lab Notebook

### Disclosure label

Lab notebook · methods, machinery & complete archive

### Introduction

The public story is selective; the record is not. Open any drawer to inspect the material behind the claims.

### Complete legislature · 355 rule records

118 adopted · 159 rejected · 2 repealed · 76 historical. Only the adopted rules constitute the current language.

Links: current adopted language · complete rule record

### Development exams · five repeating messages

Event prose, equipment procedure, farming data, retail prose, and a software task repeat in order. This creates comparable measurements against the same source; it does not prevent overfitting. Separate transfer evidence is needed for that.

Every exam retains the original, encoded body, stranger’s decode, atom-by-atom judgment, and token counts.

Link: complete exam history

### Conversation archive · 18 six-message tests

Each entry captures a language version, six messages, scenario requirements, and the raw judgment.

Rows: turns 690, 786, 882, 978, and 1074 use the legacy judgment; turns 1170 through 2322 record 4 / 4 passing requirements.

Link: raw Conversation archive

### Research and human questions · 158 research · 9 questions

Agent research requests, answers, citations, questions for the human, and their delivery status remain in the collaboration record. Suggestions are approval-gated and cannot silently enter the language.

Link: complete collaboration record

### Prompts and judging machinery · 13 current source files

These are the disclosed instructions that define the legislators, exam writer, stranger, judges, research path, and cleanup roles.

Links: agent_a.md · agent_b.md · constitution.md · payloadgen.md · answer_key.md · grader_v2.md · conversation.md · conversation_judge.md · research.md · cleanup_a.md · cleanup_b_v2.md · cleanup_c_v2.md · cleanup_c_finalizer_v1.md

### Raw public records

Inspect the canonical JSON and human notes directly rather than relying on the summary page.

Links: runtime snapshot · rulebook · exam history · Conversations · Field Notes

## Footer

Turn 2400 fixture · local prototype · no live data or model calls

## Prototype-only Labels

These disappear in the production implementation:

- B · Preserves the current page rhythm most closely: timers and agent panes remain the opening experience; repaired evidence follows immediately.
- B — Agents before evidence
