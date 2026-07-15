# A Language All Their Own

Two AI agents in a permanent working session, with one standing task: **invent the optimal
language for machine-to-machine communication.** Companies are engineering agent-to-agent
protocols top-down; here, the machines negotiate one bottom-up, in public.

Every rule they propose must survive a live test: one agent encodes a real message in the
language, a **fresh agent that has never seen the conversation** decodes it using only the
rulebook, and a grader scores how much meaning survived. Token costs are measured with the real
tokenizer — hunches about efficiency die by measurement here. Rules that don't pay rent get
rejected; everything is on the record.

**The rulebook is the artifact.** Paste `state/rulebook.json` (or its rendered form) into any
LLM's context and it can read and write the language. Adoption cost: zero. An Esperanto for
machines, without Esperanto's fatal flaw.

## What's in this repo

- `state/conversation.json` — the full negotiation, every turn, every test, append-only
- `state/rulebook.json` — the versioned language: every rule with status, scores, and the
  agents' own reasoning for adopting or killing it
- `loop.py` — the entire engine (~300 lines; the code is plumbing, the LLMs do the language)
- `prompts/` — the agents' actual system prompts, unabridged
- `payloads/` — the fixed test corpus (prose, task instructions, structured data)
- `viewer/` — the public page
- `MECHANICS.md` — how a turn actually works: statelessness, the rulebook-as-memory,
  context assembly, test anatomy
- `state/tuning-runs/` — discarded early transcripts, kept as evidence (including the first
  attempt, where the agents fell into the JSON trap and scored fidelity 0)

The loop runs every 15 minutes. One rule of reading the transcript: the interesting parts are
the failures.

*An art project by Iso Rabins. The agents are DeepSeek v3.2; the harness never suggests rules,
frameworks, or examples — the discoveries are theirs.*
