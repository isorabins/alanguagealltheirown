# BUILD TONIGHT — A Language All Their Own (overnight v1)

**For:** Fable nightly worker, night of 2026-07-14 (or first run after this lands)
**Contract:** This doc + `BRIEF.md` (same folder) are the full spec. Iso approved this direct build in the 2026-07-14 cowork session. **Spec Kit: waived by Iso for this item** — this document is the spec/plan/tasks contract. Do not run the speckit chain. Do not build beyond this doc.

**Prime directive:** v1 of this project died in 2025 because the builder made a cathedral (see `alex-brain/moltbook-language-project.md` — 1,178 lines of Docker diagrams and SQL schemas before a single conversation ran). Read BRIEF.md §7. The code is plumbing; the LLMs do the language. If you catch yourself adding a library, a server, a database, or a framework tonight — stop, you are re-dying the same death.

---

## What Iso wakes up to (definition of done)

1. `projects/a-language-all-their-own/` containing:
   - `loop.py` — the whole engine, one file, target ~200–300 lines
   - `prompts/agent_a.md`, `prompts/agent_b.md`, `prompts/grader.md` — hot-editable, read fresh each turn
   - `payloads/` — 10–15 test payloads (see below)
   - `state/conversation.json`, `state/rulebook.json` — exact shapes from BRIEF.md §5
   - `viewer/index.html` + `viewer/state.js` — the UI
2. A **40+ turn final run** that went through **at least 2 prompt-tuning iterations first** (see Tuning Protocol)
3. Viewer copied to `ForAlex/a-language-all-their-own/` (Syncthing → Iso's Desktop) so he double-clicks `index.html` over `file://` and it just works
4. `MORNING-READOUT.md` in the project folder AND copied next to the viewer in ForAlex — see required contents below
5. `PROGRESS.md` updated, episodic memory entry written, queue item annotated

## Hard boundaries tonight (do not cross)

- **NO:** FastAPI, schedulers, systemd, databases, npm/node builds, frameworks, Vercel, domain checks or purchases, tweets/upload-post, new accounts, NLP/linguistics libraries of any kind. Python stdlib + `requests`. That's it — OpenRouter is a plain HTTPS POST, no provider SDK.
- **Nothing external leaves the system** (fleet rule 4). Everything tonight is local files.
- **Budget cap: ~$5 API spend.** Use `OPENROUTER_API_KEY` from Bitwarden (Alex Fleet Secrets, per TOOLS.md; verified live 2026-07-14 evening). At DeepSeek prices the whole night should land under $1, so the cap is a tripwire, not a target — track spend from the `usage` fields as you go and stop the run if you're going to blow past it.
- **CONTAMINATION RULE:** Do NOT read Babel v1's seed vocabulary or academic frameworks (`alex-brain/moltbook-language-project.md` §"Initial Seed Vocabulary" / §"Emergent Language Research") into the agent prompts, and do not paraphrase them in. BRIEF.md §6 is explicit: no linguistic frameworks, no suggested rule types, no examples of "good" rules. The discoveries belong to the agents. Babel v1 is useful to you only as the anti-pattern.

## Decisions already made (don't relitigate tonight)

- **Model pairing (changed 2026-07-14 evening by Iso — cost):** same model both sides for v1 — `deepseek/deepseek-v3.2` via OpenRouter (`POST https://openrouter.ai/api/v1/chat/completions`, OpenAI-shaped) for Agent A, Agent B, the fresh decoder, and the grader. Live pricing $0.21/M in / $0.32/M out — the eventual 15-min cadence runs ~$0.50/day. Put each role's model id in a config constant at the top of loop.py so any role swaps to any OpenRouter model without touching code. (Different-models is a later episode, not tonight's noise.)
- **Token counting:** from the `usage` field on every OpenRouter response — the encode call's `completion_tokens` is the encoded message's exact size; the decode call's gives the decoded-English size. To size standalone text (rulebook/kernel per version), send it as the sole user message of a `max_tokens: 1` probe call and read `prompt_tokens`, subtracting the empty-prompt overhead measured once at startup. Log token counts on every message. No count_tokens endpoint, no tokenizer library.
- **Test cadence:** every 5th turn is a test turn, exactly per BRIEF.md §5 Scoring: harness picks a payload → Agent A encodes per current rulebook → a **fresh, history-free** call decodes back to English → grader scores fidelity 0–100 → result appended to conversation and rulebook.
- **Payloads:** curated set, written by you tonight, saved in `payloads/` as plain files. Mix: ~5 prose paragraphs (varied register — news, instructions, casual), ~5 task instructions ("summarize X and flag risks"), ~3 small structured-data snippets. No wiki scraping, no audience submissions.
- **Turn mechanics:** agents alternate. Each agent call gets: its system prompt + the current rulebook + the last ~10 turns of conversation. Non-test turns are free discussion: propose rules, argue, revise. The harness (your code) parses a lightweight convention for rule proposals — keep it dumb, e.g. agents mark proposals with a `PROPOSE:` / `ADOPT:` / `REJECT:` line the harness regexes out. If parsing gets fancy, you've gone cathedral.

## Tuning protocol (this is the real work — budget most of the night here)

BRIEF.md §6: the steer/wander dial is the art. Procedure:

1. Write first-draft prompts. Each agent gets: role, the standing goal (invent + iteratively test the optimal AI-to-AI language, rules must survive encode/decode testing, rulebook size costs context tokens), how scoring works, the proposal convention. Nothing else.
2. Run 10 turns. **Read the transcript yourself, honestly.**
3. Diagnose against the two failure modes:
   - *Too loose:* pleasantries, mutual admiration, consciousness talk, mysticism drift → tighten the goal pressure.
   - *Too tight / boring:* they instantly emit JSON schemas or act like they're filling in your worksheet → loosen; remove any accidental steering.
4. Wipe state, adjust prompts, rerun. **Minimum 2 full iterations before the final run.** Keep each discarded transcript in `state/tuning-runs/` with one line on why it was rejected — that's tomorrow's evidence.
5. When a 10-turn read is genuinely interesting (they disagree at least once, propose something non-obvious, or react to a test failure), start the final 40+ turn run.
6. **Before a KILL verdict only:** flip the agent model constants to a stronger model (an `anthropic/claude-sonnet-*` id works through the same OpenRouter key, ~$0.50 for 10 turns) and rerun once. The readout must say which model produced the final transcript — the gate judges the idea, and a cheap model's flat transcript must not kill it unexamined.

## The viewer (keep it dumb, make it pretty)

- **One** `index.html`: inline CSS + JS, zero dependencies, zero build step, must work over `file://`.
- After **every** turn, `loop.py` regenerates `viewer/state.js` containing `window.STATE = {conversation: [...], rulebook: {...}};` — the page reads that. (This avoids `fetch()` being blocked on `file://`.)
- Layout per BRIEF.md §5: short project explanation up top (pull the artist statement from BRIEF §1) → two chat panes side by side (Agent A left, Agent B right, test-turn events styled distinctly) → rulebook table underneath (rule, status, token delta %, fidelity %, proposed turn, history). Metrics strip: current version, kernel/rulebook token size, last-test fidelity, turn count.
- Make it look like an art piece, not a dashboard: dark, typographic, monospace conversation. An hour of polish max.
- **Design direction (Iso, 2026-07-14 night):** Nous Research's visual language as the reference point, not a copy — near-black ground, warm cream ink, classical serif for headings/statement, monospace for the conversation and data, thin hairline rules, generous margins, no cards/shadows/dashboard chrome. The page should read like a research lab's internal artifact that happens to be public.

## MORNING-READOUT.md (required contents)

1. **Gate verdict, first line:** `CONTINUE` / `TUNE MORE` / `KILL`, with 2–3 sentences of honest reasoning. This is Iso's step-2 kill gate from the brief — do not soften it. A boring transcript reported as boring is a successful night.
2. 3–5 verbatim transcript excerpts — the best and the worst moments.
3. Metrics: turns run, rules proposed/adopted/rejected, fidelity scores over time, token-delta trend, total API spend.
4. What you tuned between iterations and why (one line per iteration).
5. Next-session list (should match PROGRESS.md): VPS scheduler, Vercel deploy + domain, tweets — all **explicitly not built tonight**.

## Deferred to Iso — surface as ops-dashboard cards, do not build

- `lang-project-twitter`: Iso creates the dedicated account himself with isogenoar@gmail.com (account creation/phone-verify is a human-only action — agents can't do signups), then grants standing approval for the fixed dry-changelog format. Agent wires it into upload-post after both exist. (Fleet rule 4 makes per-tweet approval a death sentence — see analysis/graveyard.md, Twitter automation.)
- `lang-project-domain`: purchase alanguagealltheirown.com — via Vercel domains, not Hover (auto-wires DNS to the future viewer; $11.25/yr, confirmed available 2026-07-14). Purchase = live-change approval.
- `lang-project-deploy`: go/no-go on VPS 15-min scheduler + public Vercel page, **only if** morning verdict is CONTINUE.

## Logging (per queue rules)

One `[vps]` entry in this folder's PROGRESS.md + episodic memory. Annotate the queue item with status and where outputs live.
