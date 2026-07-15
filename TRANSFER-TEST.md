# TRANSFER TEST — the v1.0 finale (design, not yet run)

*Brief §3.6: did they invent a **language** or an **in-joke**? Hand the rulebook to two fresh
agents of entirely different lineage — a Claude and a GPT — with zero conversation history, and
measure whether the language transfers. Pass = language. Fail = dialect collapse. Either result
is a finding; either is the finale's content.*

## Readiness trigger (proposed)

Run when BOTH hold:
- **10+ adopted rules** in the kernel, and
- **rolling fidelity ≥ 90** across the last 5 live tests (the DeepSeek pair's own baseline is
  stable enough to compare against).

Manually triggered by Iso's go — never by the loop.

## Protocol

1. **Pairings, run across all payloads** (19 after set v3): for each payload, four encode/decode
   crossings — DeepSeek→DeepSeek (baseline, from live-test history), Claude→GPT, GPT→Claude,
   and Claude→Claude (controls for "is GPT the weak link or the language").
2. Encoder gets rulebook + payload, decoder gets rulebook + encoded text only — identical
   prompts to the live loop's, identical grader (DeepSeek, temp 0), identical token probes.
3. Models via the same OpenRouter key: `anthropic/claude-sonnet-5`, `openai/gpt-5-mini` (pin
   exact IDs at run time; log them in the output). Est. cost for the full battery: **under $2**.
4. Output: `state/transfer-test-<date>.json` + a side-by-side table (payload × pairing ×
   fidelity/compression). Deltas vs. baseline are the story.

## Publication

- PROGRESS entry with the honest verdict, boring-is-boring.
- A page section ("Can strangers speak it?") rendering the table.
- One premise-mode tweet with the headline number.

## Skeleton

`transfer_test.py` (this repo, manual-run only) — loads the live rulebook, iterates payloads ×
pairings, reuses the live encoder/decoder/grader prompts verbatim. Written and syntax-checked,
NOT wired to the loop; running it costs money and is Iso-gated.
