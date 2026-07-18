# Prior art and next experiments — research handoff

**Date:** 2026-07-18 WITA  
**For:** Claude Code, continuing session `886e37ba-1c22-4edf-86d9-02cb11c9e846`  
**Scope:** Research only. No prompt, harness, state, deploy, timer, or live-agent change was made.  
**Spec Kit:** N/A — this is a non-implementation research memo.

## Executive verdict

The project still has a credible original core. I did not find a published primary-source match for an open-domain, human-readable language negotiated by two general LLMs, written into a public rulebook, then tested by a foreign stranger model against generator-authored answer keys. The closest work either uses narrow referential games, trained/latent compressors, prewritten protocols, or communication-topology pruning.

The strongest research finding is uncomfortable but useful: **the live result currently measures message-body compression, not total communication cost.** The language briefly crossed above the dumb minifier in an earlier 10-exam window, but by fetched turn 350 it trailed the control again by about one point. More importantly, the 2,444-token rulebook transmitted to the decoder is excluded from the savings number. That is the first thing to fix before giving the agents prior art or claiming they have built a more efficient communication system.

## Current evidence from the repo

Computed from `origin/main` versions of `state/probe.json`, `state/conversation.json`, and `state/rulebook.json` after fetching turn 350 (latest exam: turn 348):

- 110 exams total.
- All-time average body savings: language **7.54%** vs dumb minifier **16.10%**.
- Last 10 passing exams: language **14.54%** vs dumb minifier **15.56%**.
- Latest exam: **412 → 364 tokens**, fidelity **100/100**; minifier produced **351 tokens**.
- Rulebook: **2,444 tokens**, 11 adopted rules, 6 proposed, 24 rejected, 7 reverted.
- Last 10 passing exams save **71.2 body tokens per message** on average. If the rulebook were transmitted once and then cached perfectly, it would take about **34 messages** to earn back its teaching cost. Across only those 10 messages, a once-cached rulebook still makes the protocol about **35.5% larger** than plain English. If the full rulebook is sent on every stateless API call, as the current harness does, there is no one-time cost to amortize; at current message sizes the transmitted rulebook plus encoded bodies is about **486% larger** than the original bodies.

This does not make the page's body-savings number false. It means the honest label is “payload compression,” with a second differential-cost measure showing rulebook overhead and the cache assumption. Encoder/decoder instructions common to both treatments can be reported separately from that protocol-specific overhead.

## What the research says

### 1. Emergent communication does not become efficient or compositional by itself

Kottur et al. found that agent-invented codes could achieve near-perfect task reward while remaining non-compositional and uninterpretable; increasingly restrictive communication conditions were needed to make the code more language-like ([EMNLP 2017](https://aclanthology.org/D17-1321/)). Chaabouni et al. found an even sharper failure: neural agents preferred maximum-length, anti-efficient messages until message length was explicitly penalized; only then did the code begin to follow Zipf's law of abbreviation ([arXiv 1905.12561](https://arxiv.org/abs/1905.12561)).

The LLM-era result is similar. Kouwenhoven et al. showed that iterated transmission between LLMs can turn initially holistic artificial languages into more structured, learnable systems, but it can also create non-humanlike degenerate vocabularies ([COLING 2025](https://aclanthology.org/2025.coling-main.667/)). Boldt and Mortensen's induced “morphological phrasebooks” show why ablation matters: repetition and morpheme order carried meaning, and an information-theoretic form/meaning measure tracked actual speak/hear ability better than common surface metrics ([ACL 2026](https://aclanthology.org/2026.acl-long.1389/)).

**Transferable lesson:** a high score does not prove a useful language mechanism. The harness must price length explicitly, test transfer, and causally ablate rules. The current agents' minification plateau is consistent with the literature, not surprising evidence that they have exhausted language design.

### 2. The spectacular compression numbers come from a different game

LLMLingua reports up to 20× prompt compression with little downstream performance loss, using a learned coarse-to-fine token-removal system ([EMNLP 2023](https://aclanthology.org/2023.emnlp-main.825/)). LLMLingua-2 reports 2–5× compression, 3–6× faster compression, and 1.6–2.9× end-to-end latency improvements across its tested tasks ([ACL Findings 2024](https://aclanthology.org/2024.findings-acl.57/)). Gist Tokens compress reusable prompts up to 26×, but they require training the model to communicate through continuous activations; the paper reports up to 40% FLOP reduction but only 4.2% wall-time improvement and acknowledges nuance loss ([arXiv 2304.08467](https://arxiv.org/abs/2304.08467)). ICAE similarly reports 4× context compression after training a context autoencoder ([arXiv 2307.06945](https://arxiv.org/abs/2307.06945)).

Latent and KV-cache systems are further away from this project's premise. DroidSpeak gets up to 3× throughput and 2.6× faster prefill by sharing selected KV-cache layers between fine-tuned models derived from the same base model ([arXiv 2411.02820](https://arxiv.org/abs/2411.02820)). That cannot be sent as portable text to a closed, unrelated Kimi decoder. These systems are useful ceilings, not fair competitors.

**Transferable lesson:** compare the project to discrete, portable, cross-model text baselines. Do not let trained soft-token or shared-cache numbers make a 15–25% text result look weak; they solve a materially easier compatibility problem.

### 3. Production agent protocols optimize interoperability, not semantic compression

MCP encodes UTF-8 JSON-RPC messages over stdio or Streamable HTTP ([MCP transport specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)). A2A defines Messages, Parts, Tasks, Artifacts, Agent Cards, and JSON-RPC/gRPC/HTTP bindings; it deliberately supports opaque agents and multiple modalities ([A2A 1.0 specification](https://a2a-protocol.org/latest/specification/)). AutoGen likewise uses inspectable, JSON-serializable typed chat messages between agents ([AutoGen message reference](https://microsoft.github.io/autogen/stable/reference/python/autogen_agentchat.messages.html)). None of those normative surfaces defines a semantic text-compression layer.

Agora is the closest systems result to a practical “agent language.” It uses standardized routines for frequent interactions, natural language for rare interactions, and LLM-written routines in the middle ([arXiv 2410.11905](https://arxiv.org/abs/2410.11905)). Separate multi-agent efficiency work usually removes messages or agents instead of inventing a denser language: AgentPrune reports 28.1–72.8% token reduction by pruning a spatial-temporal communication graph ([arXiv 2410.02506](https://arxiv.org/abs/2410.02506)); AgentDropout reports 21.6% fewer prompt tokens and 18.4% fewer completion tokens by dynamically eliminating redundant communication ([ACL 2025](https://aclanthology.org/2025.acl-long.1170/)).

**Transferable lesson:** the boring production answer is typed schemas, cached routines, and fewer transmissions. A universal invented language is the art/research question, not the standard engineering path.

### 4. Machine-oriented shorthands work best on narrow structure

TOON is a recent schema-aware JSON representation that declares repeated fields once and uses tabular rows. Its own four-model benchmark reports 39.9% fewer tokens than pretty JSON with 76.4% vs 75.0% retrieval accuracy, while warning that deeply nested or irregular data can erase the gain ([official repository and benchmark](https://github.com/toon-format/toon)). This is strong evidence for removing repeated keys on the project's structured-data exams, but not evidence for a universal prose language.

GibberLink is not prior art for invented language. Its authors prompted two voice agents to switch to the preexisting `ggwave` data-over-sound protocol after identifying each other as AIs ([official repository](https://github.com/PennyroyalTea/gibberlink)). It is a transport-mode switch, not negotiated semantics, grammar, or token compression.

**Transferable lesson:** route by payload type. Tabular data wants a table/schema; exact commands want verbatim protection; prose wants selective deletion or abstraction. One syntax for everything is likely to underperform specialized modes.

### 5. Information theory gives the right measurement frame

Shannon separates exact reconstruction from approximate reconstruction and bounds compression by source redundancy ([1948 paper](https://reach.ieee.org/primary-sources/a-mathematical-theory-of-communication/)). His rate-distortion formulation asks the more relevant question here: what minimum rate is possible at a specified fidelity or distortion level ([1959 paper](https://gwern.net/doc/cs/algorithm/information/1959-shannon.pdf)). The project's answer-key audit is already a domain-specific distortion function: missing, corrupted, and invented facts are distortion.

The missing piece is a **curve**, not one average. Report the best savings achievable at fidelity 90, 95, 98, and 100, plus exact-string survival. Also report bytes and tokenizer-specific tokens separately. Tokenizers are themselves learned compression codebooks, and tokenizer compression correlates with model behavior ([Goldman et al. 2024](https://arxiv.org/abs/2403.06265)), although minimizing token count alone does not guarantee better downstream performance ([Schmidt et al. 2024](https://arxiv.org/abs/2402.18376)). A novel spelling or symbol can therefore look short to humans while costing more model tokens.

**Transferable lesson:** compressed English may be the rational optimum for black-box pretrained models with fixed tokenizers. If the agents do not invent a vocabulary, that may be a property of the channel, not a lack of imagination.

### 6. Closest prior art, and what remains distinct

The closest published work found in this sweep is:

- LLMs iteratively learning artificial languages in narrow referential games, with structure and degeneration both emerging ([Kouwenhoven et al.](https://aclanthology.org/2025.coling-main.667/)).
- Agora's self-organizing mixture of standard routines, generated routines, and natural language in networks of LLM agents ([Marro et al.](https://arxiv.org/abs/2410.11905)).
- Learned morphological phrasebooks that let rule-based agents interoperate with a neural emergent language, validated through ablation ([Boldt and Mortensen](https://aclanthology.org/2026.acl-long.1389/)).
- Prompt compressors, latent channels, and communication-pruning systems that achieve larger efficiency gains but give up portability, inspectability, open-domain reconstruction, or the “invented from scratch” premise.

I found no primary-source paper that combines this project's full design: two general LLM negotiators, an accumulating human-readable rulebook, open-domain mixed payloads, a foreign black-box stranger decoder, precommitted answer keys, public longitudinal state, and a deterministic no-language control. Phrase the novelty as “we have not found a published match,” not “first ever.”

## Five strongest ideas the project has not tried

1. **(a) Harness/measurement — show total cost and amortization.** Keep body savings, but add `rulebook + encoded body`, a cached-rulebook break-even count, and a clear cache assumption. On the fetched turn-350 last-10 passing average, the 2,444-token rulebook takes about 34 messages to amortize even if taught only once. This is the priority.

2. **(a) Harness/measurement — build a rate-distortion baseline ladder.** For each frozen exam, score plain English, dumb minifier, a lossless structured format on data payloads, a simple extractive compressor, and the agent language at identical fidelity thresholds. Publish the frontier at 90/95/98/100 rather than one average. Do not install or train a heavy compressor before the cheap baselines prove the need.

3. **(a) Harness/measurement — causally price every adopted rule.** Replay a frozen exam battery with one adopted rule removed at a time. Record change in fidelity, body tokens, and rulebook tokens. A rule stays only when its marginal benefit exceeds its teaching cost. This turns “rules must pay rent” from a prompt slogan into evidence.

4. **(a) Harness/measurement — run a transfer and fragility matrix.** Rotate at least three stranger model families and count every message under each receiver's tokenizer. Split results by prose/task/data and add a fixed adversarial battery for CLI strings, identifiers, decimals, negation, units, scope, and conditionals. This distinguishes a portable language from one model's tolerance for damaged English.

5. **(b) Library material — test an explicitly informed fork, never contaminate the main lineage.** Fork the current rulebook into a labeled side experiment and disclose only three prior-art patterns: Agora's routine/natural-language split, TOON-style declare-fields-once tables, and morphological phrasebooks with explicit ordering. Run the same frozen exams against the untouched “invented from scratch” lineage. Cost to the premise: the fork can no longer claim independent invention; benefit: it reveals whether the plateau is lack of ideas or a genuine channel limit.

## Recommendation to Claude

Do not feed the literature to the live agents yet. First propose one measurement-only change to Iso: add total-cost/amortization reporting and offline per-rule ablations without changing prompts, cadence, decoder visibility, or live state. That preserves the artwork while making the claim scientifically honest.

**Plain-English direction:** fix the accounting before steering the language. The current agents may be winning on message bodies, but the project has not yet shown that the communication system beats English after teaching the receiver how to read it.
