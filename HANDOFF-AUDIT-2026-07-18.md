# AUDIT BRIEF — adversarial review of all work, project start (2026-07-14) → 2026-07-20

**UPDATED 2026-07-20: Part Two added below — the constitution era. Audit BOTH parts.**

**Your role:** you are a skeptical auditor. The builder (a prior Claude session) claims the work below
was done, verified, and shipped. Assume nothing. Trust no claim in this file until you have checked it
against primary evidence: the git history, the live site, the live data files, the code, and the X
timeline. Your product is a findings report, not fixes.

**Rules of engagement**
- Verify against PRIMARY evidence only: `git log` in this repo, https://alanguagealltheirown.com,
  raw state files on GitHub (`state/*.json`), the code itself, x.com/@alanguageall.
- For every claim: mark CONFIRMED (you saw the evidence), BROKEN (evidence contradicts), or
  UNVERIFIABLE (say what access you lacked). Quote the evidence.
- Do NOT fix anything. Do NOT push. Do NOT deploy. Do NOT run `python3 loop.py` (it consumes a real
  turn of the live artwork; the VPS owns turns). Read-only, plus local scratch files.
- Write your findings to `AUDIT-FINDINGS-<date>.md` in this directory (it will be gitignored by the
  `HANDOFF-*.md`… note: it will NOT match that pattern — do not `git add` it).
- End with a prioritized fix list: what is actually broken, worst first.

**Shell gotchas that will waste your time if ignored**
- An rtk shell hook mangles piped output. NEVER pipe curl/JSON into a parser or grep — write to a
  file, then read the file. Symptom: bizarre "N in NF:" formatted output.
- Working directory can reset between shell calls. Use absolute paths or `cd` per command.
- `.env` holds a live API key. Never print, echo, or commit it.

---

## 1. What this project is (orientation, 60 seconds)

Two DeepSeek agents (A and B) negotiate a constructed AI-to-AI compression language in public, one
turn per 15 minutes, on a Hetzner VPS (`language-loop.timer` → `run_turn.sh` → commits pushed to this
public repo). Every 3rd turn is an exam: a blind generator writes a 400–600-word message plus an
answer key of its facts; an encoder compresses it using only the rulebook; a FOREIGN model
(kimi-k2.6; everything else deepseek-v3.2) decodes it from the rulebook alone; a judge grades each
key fact SURVIVED/CORRUPTED/MISSING plus INVENTED; fidelity = 100×survived÷(total+invented).
Public page: alanguagealltheirown.com (Vercel; deploy is separate from git push).
THE ONE INVARIANT: the decoder sees ONLY the rulebook and the encoded message. Never the original.

Key docs: `MECHANICS.md` (system), `PROGRESS.md` (append-only log, newest first),
`RESEARCH-PRIOR-ART-2026-07-18.md` (prior-art memo by Codex), `notes.json` (public field notes),
`PROMOTION.md` (X strategy + anti-goals). `HANDOFF-2026-07-17-redesign.md` = builder's own handoff
(read skeptically; it is a claims document, same as this one).

## 2. What Iso asked for, chronologically (audit each has a real shipped artifact)

1. Add the X/Twitter follow-through task to the handoff after the bot went live (2026-07-17).
2. Build the approved site redesign (spec in `HANDOFF-2026-07-17-redesign.md`).
3. MID-BUILD REVERSAL: keep the two agent panes side-by-side (he rejected the merged feed after
   seeing it). The live page must have side-by-side panes.
4. Unify page vocabulary: the every-3rd-turn event is an "exam" everywhere; "test" only where it
   means rules being tested.
5. Push the changes live ("go ahead and push those changes").
6. A "third-party testing probe… totally separate" → became THE CONTROL: `probe.py`, a no-AI
   minifier baseline counted with the loop's own tokenizer, page section, field note #13.
7. A try-it-yourself section: visitors paste a paragraph, watch encode → stranger decode → judge
   audit, intentionally staged/slow. Built overnight local-first, then FLIPPED LIVE on his
   "push all the changes live" (2026-07-18).
8. Savings ladder on the page: cumulative savings at 1/10/100 messages given the rulebook entry fee,
   with the caching assumption stated.
9. Field-notes X stream: every note tweeted, backlog dripped 2/day, new notes join automatically.
10. Deep research on prior art (Claude's fan-out died on session limits; Codex delivered the memo —
    verify the memo exists and its numbers were re-verified by the builder).
11. Library-not-fork decision: Iso explicitly overruled the "purity" objection — prior-art library
    goes to the LIVE agents, disclosed publicly.
12. The package: (a) fix the accounting publicly (entry fee / break-even), (b) per-exam control
    line in the agents' feedback, (c) mandate rewrite with floor + 50% frontier, (d) the library.
13. No stale numbers in prompts: hardcoded figures replaced by a live ECONOMICS line computed each
    turn.
14. Iso's aliasing idea added to the library (define a long string once, reference it cheaply).
15. Mission paragraph: inspiring, mission-driven, access-for-billions framing, "languages outlive
    their makers" — but no promised outcomes, no manifesto bait.
16. Page reframed to "evolving experiment" honesty (not "agents did it all alone").
17. All progress docs updated; check-in defined for 2026-07-19.

## 3. Claim ledger — verify each

### A. The redesign (viewer/index.html)
- CLAIM: live page has side-by-side panes (#paneA/#paneB), judgment renderer with full answer key
  and CORRUPTED/MISSING marks, 15-row expandable exam history, Language/Rejected collapsed behind
  live-count summaries, six-cell stats bar, "exam" vocabulary unified.
  VERIFY: fetch the live page to a file; check each element; open in a browser; expand a fid<80
  history row (t225 = fidelity 40 if still in window; any low row otherwise).
- CLAIM: render(S) tolerates the empty fallback state without throwing.
  VERIFY: in browser console on the live page, call
  `render({conversation:[],rulebook:{rules:[],version:"0.0",kernel_tokens:0},meta:{}})`, then reload.
- KNOWN WEAKNESS (builder admits): an explicit mobile-viewport (≤760px) visual pass was started but
  never completed. Check stacking at 375px width.

### B. The Control (probe.py + page section + field note #13)
- CLAIM: `probe.py` minifier is fair-and-dumb (lowercase, strip edge punctuation, drop
  the/a/an/please, any word containing a digit kept VERBATIM) and uses the same provider-pinned
  tokenizer probe as `loop.py` (`prompt_tokens` minus calibrated overhead, deepseek pinned).
  VERIFY: read both files side by side; confirm method identity; confirm probe.json numbers are
  internally consistent (spot-recompute 3 exams' percentages).
- CLAIM: wired into `run_turn.sh` with `|| true`; incremental (never re-bills counted exams);
  backfilled 77 exams for ~$0.004; self-updating since (t339+ entries exist with later `updated`).
  VERIFY: read run_turn.sh; check probe.json `updated` is recent and exam count grows with turns.
- CLAIM: page control section computes last-10 PASSING (fid≥90) for both script and language, shows
  the gap, hides gracefully if data missing.
  VERIFY: read the IIFE in index.html; recompute from probe.json; compare displayed numbers.
- HONESTY ITEM (builder flags): field note #13 (dated 07-17) says the agents "crossed the only line
  that matters" (beat the script last-10). By t350–357 the gap had REVERSED (script ahead again).
  The note is a dated historical record and the page self-corrects live — but judge whether a
  follow-up correction note is owed. Note #14 partially addresses this ("after stalling at
  dumb-script level"). Your call: is the public record honest end-to-end?

### C. Try-it-yourself (viewer/api/ + page section)
- CLAIM: THE INVARIANT HOLDS — `viewer/api/decode.js` receives only {encoded}; the original text
  never reaches the decoder endpoint.
  VERIFY: read all three endpoint files. This is the single most important code check in the audit.
- CLAIM: judge endpoint ports loop.py's fidelity arithmetic exactly (survived/(total+invented),
  RESPONDED capped at 15, clamped, −1 unparseable).
  VERIFY: line-by-line against loop.py's test_turn.
- CLAIM: verified end-to-end locally AND on production (prod run: 104→94 tok, 12/12 facts, fid 100).
  VERIFY: run one live exam on the production page yourself (costs Iso ~a cent; acceptable).
- KNOWN WEAKNESSES (builder admits): rate limiting is in-memory per serverless instance (resets on
  cold start; per-IP 6/hr + global 150/day are soft). OpenRouter key-level spend cap in the
  dashboard was RECOMMENDED to Iso but is manual — check whether it exists is UNVERIFIABLE for you;
  flag it as an open risk regardless. Also confirm no health-check gating: if endpoints die, the
  section shows inline errors (by design) — confirm that's acceptable UX or flag.
- SECURITY: the OpenRouter key was added to Vercel env via a first attempt PIPED THROUGH the rtk
  shell (mangled), then fixed via file redirect. VERIFY no key material ever landed in: git history
  (`git log -p -S "sk-or" --all` and search for OPENROUTER in committed files), any committed .log,
  PROGRESS.md, or the handoffs. `.env` must be untracked (check .gitignore + `git ls-files`).

### D. X/Twitter (tweet.py + notes stream)
- CLAIM: rule-change tweets (adopted/rejected/reverted only, never raw proposals), ≤275 chars,
  premise restated every 5th tweet, mass-change flood guard (>3 changes → one summary).
  VERIFY: read tweet.py; then read the ACTUAL @alanguageall timeline and compare format claims
  against real tweets.
- CLAIM: notes leg — every entry in notes.json has a hand-written `tweet` field ≤275 chars; drip is
  oldest-first, 2 per UTC day, watermark `notes_posted` in state/tweet-state.json; new notes join
  the queue tail; 2 posted on 2026-07-18.
  VERIFY: check all 14 notes have `tweet` ≤275 with the site link; check tweet-state.json counters;
  check the live timeline shows the first two history tweets.
- COMPLIANCE: PROMOTION.md anti-goals (no follow automation, no mention spam, cadence beyond the
  bot = never). Verify nothing in the code can violate them.
- STILL OPEN (not a failure — queued): pinned premise tweet and the curated follow list (TASK 2 in
  the builder's handoff) were never executed. Confirm still pending, not silently dropped.

### E. Constitution changes (prompts/agent_a.md, agent_b.md, loop.py)
- CLAIM: both prompts carry — floor (mindless script ≈16%), frontier (50% at full fidelity,
  unclaimed), library with FIVE entries (routine/prose split, declare-once tables, positional
  grammar, local aliasing, two cautions), mission paragraph (access wall, growth curve as labeled
  projection, gigawatts at scale, "languages outlive their makers", closing craft-valve), and NO
  hardcoded entry-fee/break-even numbers (those moved to a live ECONOMICS line).
  VERIFY: read both prompt files fully. Check A and B are identical except the lean sections.
- CRITICAL VERIFY (builder's own context was compacted around this change — treat as unproven):
  the live ECONOMICS line. CLAIM: loop.py computes, every turn, from state/probe.json +
  rulebook: entry fee, avg saved/msg, break-even count, you-vs-script last 10 — and renders it into
  the agents' context (near the rulebook). Read loop.py and CONFIRM THIS CODE EXISTS AND IS
  CORRECT. If it does not exist, the prompts reference an ECONOMICS line that never appears —
  a broken promise inside the agents' own constitution. This is the audit's #1 code check.
- SEMI-STALE NUMBER (builder flags): the mandate hardcodes "about 16%" for the script's average and
  the frontier "50%". 16% drifts with data. Judge severity; a fix would derive it or soften the
  phrasing.
- CLAIM: per-exam CONTROL line in agents' exam feedback (render_window shows control_tokens with
  free-vs-language framing) and `control_tokens` stored on test events from t360.
  VERIFY: read loop.py render_window + test_turn; check a t360+ test event in conversation.json.
- CLAIM: notice inbox mechanism (state/pending-notice.txt consumed at turn start → notice event,
  race-safe vs VPS commits); notice #5 delivered at t360 with the day's true numbers.
  VERIFY: read consume_notice() in loop.py; find the t360 notice event in conversation.json; confirm
  pending-notice.txt no longer exists; check the notice's numbers against probe.json history.

### F. Page honesty (the piece's credibility)
- Entry-fee ladder: math correct from live data (kernel, avg saved/msg over last-10 passing,
  break-even, 1/10/100 nets); "paid once (then cached)" assumption stated; negative-savings case
  handled honestly.
- Prompts-intro reframe: page no longer claims the agents got everything alone; states the
  evolving-experiment framing + the never-crossed line (no human writes a rule). Verify the field
  notes actually disclose each intervention claimed.
- Stats bar definitions: "passing = fidelity ≥ 90"; avg fidelity excludes the −1 unparseable
  sentinel. Verify legend says so and code does so.
- Try-it section copy: "you are watching the real pipeline run on your words" — verify true (no
  canned responses, no caching of results).

### G. Process claims
- PROGRESS.md entries vs git reality: every "shipped" entry should map to commits/deploys. Spot-check
  five.
- Ground rules at top of PROGRESS.md: kill-gate decision was due 2026-07-17 — no explicit
  CONTINUE/KILL entry exists (builder flags: approval was implicit via the redesign go-ahead).
  Flag for Iso to record a one-line formal gate decision.
- Budget rule says "1h/day tinkering" — 07-17/18 massively exceeded it. Not a code bug; an honest
  process flag for Iso.
- Heartbeat: scheduled task `language-loop-heartbeat` (twice daily). UNVERIFIABLE from repo alone —
  check `state/` commit cadence instead: gaps >30 min in `git log` timestamps = loop stalls; note any.

## 4. Report format

1. Executive verdict: 5 sentences max. Is the public artifact honest? Is the live system what the
   logs claim? What is actually broken?
2. Claim table: every lettered claim above → CONFIRMED / BROKEN / UNVERIFIABLE + one-line evidence.
3. Findings, worst first: anything BROKEN, then risks, then polish. For each: what, where, evidence,
   suggested fix (do not apply it).
4. The three things the builder should be most embarrassed by. Be specific. If you found nothing
   real, say so — but look hard first: a clean audit that found nothing is usually a lazy audit.


---

# PART TWO — the constitution era (2026-07-18 evening → 2026-07-20 morning)

Everything below happened after Part One was written. Same rules: primary evidence only,
CONFIRMED / BROKEN / UNVERIFIABLE per claim, fix list at the end, touch nothing.

## H. The constitution package (mandate, library, control line, economics)
- CLAIM: both agent prompts carry — floor (script ≈16%) / frontier (50%) paragraph, a live
  ECONOMICS reference, a mission paragraph (access wall, growth projection, gigawatts,
  "languages outlive their makers"), and a six-entry library (routine/prose split,
  declare-once tables, positional grammar, local aliasing, token-aware substitution, two
  cautions). A and B identical outside their lean sections.
  VERIFY: read both files; diff them; check each library entry against
  RESEARCH-PRIOR-ART-2026-07-18.md for factual honesty (e.g. TOON "~40%" — is that what the
  source benchmark says?).
- CRITICAL CODE CHECK: the ECONOMICS line. CLAIM: loop.py computes it each turn from
  probe.json + rulebook (entry fee, avg saved/msg over last-10 passing, break-even count,
  you-vs-script) and renders it into the agents' context near the rulebook. The builder's
  own session context was compacted around this change — VERIFY THE CODE EXISTS, IS CALLED,
  AND ITS ARITHMETIC IS RIGHT. If the numbers it shows disagree with probe.json recomputes,
  the agents are being steered by wrong data.
- CLAIM: every exam event since t360 carries `control_tokens` and the agents' exam feedback
  includes the CONTROL line. VERIFY in conversation.json + render_window code.
- BUILDER-ADMITTED WEAKNESSES: the "about 16%" floor and "~2,400 token" fee in the mandate
  prose are semi-stale hardcodes (fee now ~8,000); the mission paragraph's growth curve is a
  projection stated as trajectory — judge whether the labeling is honest enough; the 50%
  frontier claim ("no known portable text protocol...") rests on one research memo — assess.

## I. Notices and the inbox mechanism
- CLAIM: state/pending-notice.txt is consumed at turn start by consume_notice() and delivered
  as a harness notice; notices #5 (constitution, t360), #6 does not exist (numbering skipped —
  verify what the actual count is), #7 (parliament repair facts, staged 2026-07-20) delivered
  or pending. VERIFY: count type=="notice" events; read their content; confirm #7's facts
  against your own recomputation (drift, the 14 phantom adoptions, rule-099's identity).
- HONESTY CHECK: notice #7 tells the agents "Agent A, turn 520" votes never registered.
  Verify that claim from the transcript yourself before trusting it.

## J. The invention-era claims (the numbers the builder reported to Iso)
- CLAIMS made at various points: gap −2.1 (t357) → +12.9 (t483) → +11.7 (t521); "12 exams
  overnight, zero failures"; best single exam −55% at fid 90 (t510) and −46% at fid 100
  (t402); aliasing adopted with thresholds; positional slots adopted; symbol substitution
  proposed by the agents unprompted (rule-104-era); pruning proposed but jammed.
  VERIFY: recompute every one of these from state/probe.json and state/conversation.json.
  The builder computed last-10-passing as fid≥90 over probe.json entries — check the page's
  control section uses the SAME definition (a mismatch would make the site contradict the
  reports).
- ATTRIBUTION CAVEAT the builder flags: the constitution package (floor + library + mission +
  economics) shipped as ONE intervention, so nothing isolates WHICH ingredient caused the
  gap flip. The clean-window doctrine was the builder's own rule and was traded away for
  speed with Iso's approval. Judge whether public claims ("the library did it") overreach.

## K. The parliament jam and the 2026-07-20 repair
- CLAIM (the diagnosis): three interacting defects — (1) numbering drift: agents self-number
  proposals; their "rule-084 = prune" is officially rule-099; 14 consecutive ADOPT votes
  landed on official rule-084 (already adopted) as no-ops; (2) apply_conventions stamped
  history + bumped version + re-probed kernel on NO-OP votes (rule-084 reached 47 history
  events; version counter inflated to ~233); (3) format miss: votes without the colon or
  wrapped in ** (Agent A t520) never parsed at all.
  VERIFY: re-derive all three from state + the pre-repair loop.py in git history
  (commit before "parliament repair"). This is the audit's centerpiece — the builder
  diagnosed and repaired the system's own bug; check both the diagnosis and the fix.
- CLAIM (the repair): PROPOSE/REVISE now strip leading self-assigned "rule-NNN -" prefixes;
  votes that change nothing neither stamp history nor set changed. Five unit-test cases
  passed. VERIFY: read the new apply_conventions; rerun the five cases; hunt for regressions
  the builder missed (e.g. does the strip regex ever eat a LEGITIMATE text that starts
  "rule-NNN ..."? does the no-op skip break REVISE-to-identical-text edge cases? does
  blocking no-op REJECT change tombstone "died at" lookups?).
- BUILDER-ADMITTED JUDGMENT CALLS to audit: (a) chose NOT to clean the spammed history in
  state (47 phantom events remain; page rule-cards and version stat inflated by them) —
  right call or should state be repaired on the record like the July-15 precedent? (b) the
  page's "rulebook revisions" stat (v0.233) now overstates real legislative activity —
  is the site honest while that number stands? (c) library entry #6 (token-aware
  substitution) shipped the SAME morning as the repair — a second clean-window violation;
  attribution of any coming improvement is muddied. Assess.

## L. The X notes stream (running since 07-19)
- CLAIM: 2/day drip, oldest-first; 4 of 14 posted as of 07-20 morning; rule-change tweets
  continue independently. VERIFY: tweet-state.json counters AND the live @alanguageall
  timeline — do the posted tweets match the notes' `tweet` fields verbatim? Any tweet exceed
  275 chars or misrender?

## M. The keeper→human rename (2026-07-19 night)
- CLAIM: "keeper" eliminated from both prompts, site copy, and the PRD file; pushed and
  deployed; zero live mentions remain. VERIFY: grep the live page, the raw prompt files, and
  the repo. Historical mentions in PROGRESS/notes are exempt (append-only records).

## N. The PRD file itself (PRD-conversation-and-composition.md — committed to the repo)
Audit the specs as engineering documents:
- Internal consistency: does PRD 1's conversation trigger fight the daily cap correctly?
  Does PRD 2's alternation parity (tests_run % 2) survive the fallback-payload path? Does
  PRD 3's RESEARCH sidecar (deepseek/deepseek-v3.2:online) exist as a real OpenRouter model
  suffix — verify :online works with a provider-pinned request or flag the conflict
  (provider pinning + web plugin may be incompatible — the builder never tested this).
- House-rule compliance: do the specs anywhere let A/B see demo/conversation artifacts?
  Does PRD 3's ASK flow keep "no human writes a rule" enforceable in mechanism, not just
  protocol?
- The Slack requirement in PRD 3 is deliberately under-specified ("Codex can figure that
  out") — flag anything that makes it dangerous to improvise (secrets handling, who can
  post answers, spoofing a "FROM THE HUMAN" message into the inbox: what authenticates that
  an answer actually came from Iso? THIS IS A REAL GAP the builder noticed while writing
  this audit line — assess severity).

## O. Open items the builder says are open (verify none were silently dropped)
- Page collapse-everything pass (Iso asked twice; promised "this morning" 2026-07-20).
- X TASK 2: pinned premise tweet + curated follow list — still unexecuted since 07-17.
- Field note #13's "crossed the line" claim — still no correction note; gap since re-flipped
  positive, which weakens but does not erase the issue.
- A/B homogenization (same-model echo) — flagged to Iso, no intervention; candidate fix
  (foreign model as Agent B) undecided.
- OpenRouter key-level spend cap (try-it backstop) — recommended to Iso, never confirmed set.
- Kill-gate formal decision — still not recorded in PROGRESS.

## Report format (Part Two)
Same as Part One, plus: name the single highest-risk unaudited assumption in the whole
system today, and the three things the builder should be most embarrassed by across BOTH
parts. If the ECONOMICS line or the repair diagnosis fails verification, lead with that.
