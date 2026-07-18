# Raw research ledger — agent-to-agent language compression

**Date:** 2026-07-18 WITA  
**Companion synthesis:** `RESEARCH-PRIOR-ART-2026-07-18.md`  
**Purpose:** Preserve the evidence trail so Claude can audit or reinterpret the synthesis.  
**Source rule:** Technical claims below come from papers, official specifications, or the authors' official repositories. Search-result snippets and secondary coverage were used only for discovery.

## Run provenance

Claude Code started dynamic workflow `wf_0a91d67c-f60` under session `886e37ba-1c22-4edf-86d9-02cb11c9e846`. The scope agent completed, then all five search agents failed with `You've hit your session limit · resets 2:20pm (Asia/Makassar)`. The workflow's terminal result was:

```json
{
  "summary": "No claims extracted. 0 sources fetched, all empty/failed. 0 URL dupes, 0 budget-dropped.",
  "stats": {"angles": 5, "sources": 0, "claims": 0, "dupes": 0}
}
```

The five scoped angles were:

1. Academic emergent communication.
2. Compression systems and benchmarks.
3. Agent protocols and production traffic.
4. Direct prior art on LLM-invented languages.
5. Information-theory baselines.

Codex resumed the run manually, adding the project's requested sixth vein, machine-oriented shorthands/DSLs, and kept conclusions separate from this ledger.

## Research question carried forward

Survey compression of LLM agent-to-agent communication and extract lessons for `alanguagealltheirown.com`: two LLM agents negotiate a token-efficient language; every third turn a blind generator writes a fresh mixed-domain message and answer key; an encoder uses only the rulebook; a foreign stranger model decodes from only the rulebook and encoded message; a judge audits fact survival. Compare academic emergent communication, prompt and latent compression, production protocols, machine-oriented formats, information theory, and direct attempts at LLM-negotiated interlinguas. End with five untried ideas classified as harness upgrades or prior-art “library” material, and state the premise cost of disclosing any library material.

## Search coverage

Representative queries run, with wording retained so another agent can reproduce or broaden the sweep:

```text
emergent communication anti-efficient encoding Zipf neural agents language compositionality
natural language does not emerge naturally multi-agent dialog Kottur
LLM agents invent own language compressed communication protocol emergent language
Agora LLM agents communication protocol negotiate efficient formats
LLMLingua prompt compression 20x minimal performance loss paper
LLMLingua-2 data distillation efficient task-agnostic prompt compression
gist tokens learning to compress prompts 26x
DroidSpeak KV cache sharing cross LLM communication multi agent
MCP JSON-RPC transport messages official
A2A specification JSON-RPC messages Agent Card tasks official
AutoGen agent-to-agent message types official
multi-agent LLM communication compression tokens messages
LLM agents negotiate own language shorthand compressed interlingua experiment
GibberLink official ggwave repository
token-efficient structured data format JSON LLM shorthand DSL
Shannon source coding and rate-distortion fidelity criterion
tokenizer compression correlation model performance
```

## Live project snapshot used for calculations

After fetching `origin/main`, the newest remote state was turn 350; the newest exam was turn 348. No checkout, state mutation, loop execution, or API exam was performed.

```text
turn: 350
exams: 110
latest exam: t348, gen-task-logistics, 412 -> 364 tokens, fidelity 100, 20/20 facts
rulebook: v0.137, 2,444 tokens
rules: 11 adopted, 6 proposed, 24 rejected, 7 reverted
all-time body savings: language 7.54%, minifier 16.10%
last-10 passing body savings: language 14.54%, minifier 15.56%
last-10 passing totals: original 4,878 tokens, encoded 4,166 tokens
average body tokens saved per message: 71.2
```

Derived protocol-overhead calculations:

```text
cached-once break-even = 2,444 rulebook tokens / 71.2 saved per message = 34.33 messages
10-message cached-once overhead = (4,166 + 2,444 - 4,878) / 4,878 = +35.51%
10-message repeated-rulebook overhead = (4,166 + 10*2,444 - 4,878) / 4,878 = +486.43%
```

Interpretation boundary: these are differential protocol costs, not complete API-call costs. The comparison isolates the encoded body and rulebook. Common encoder/decoder instruction scaffolding, payload generation, grading, and negotiation costs are not included.

## Source notes: emergent communication

### Kottur et al. — Natural Language Does Not Emerge “Naturally” in Multi-Agent Dialog

- Primary source: [ACL Anthology, EMNLP 2017](https://aclanthology.org/D17-1321/)
- Setup: cooperative Task & Talk reference game with end-to-end learned communication.
- Reported result: protocols can achieve near-perfect task reward while remaining uninterpretable and non-compositional.
- Positive intervention: stronger restrictions on the communication channel make protocols more human-like and compositional.
- Limitation for this project: narrow game and trained neural agents, not open-domain black-box LLMs.
- Raw relevance: successful decoding alone cannot establish that a reusable language mechanism emerged.

### Chaabouni et al. — Anti-efficient Encoding in Emergent Communication

- Primary source: [arXiv 1905.12561](https://arxiv.org/abs/1905.12561)
- Setup: speaker/listener signaling game; tests whether emergent messages follow Zipf's law of abbreviation.
- Reported result: frequent inputs were associated with the longest messages and outputs clustered near the maximum allowed length.
- Intervention: adding a length penalty shifted messages toward the expected frequency/length relationship.
- Proposed explanation: long messages were easier for the listener to discriminate; the speaker lacked a least-effort pressure.
- Raw relevance: efficiency must be directly priced. A general instruction to “compress” is weaker than a measured marginal cost.

### Lee, Cho, and Kiela — Countering Language Drift via Visual Grounding

- Primary source: [ACL Anthology, EMNLP-IJCNLP 2019](https://aclanthology.org/D19-1447/)
- Reported result: pretrained agents optimized on non-linguistic task reward can drift radically away from natural language.
- Best tested constraint: combined syntactic language-model likelihood and semantic visual grounding preserved English syntax while retaining communication performance.
- Limitation: preserving human language was the goal; this project intentionally allows divergence.
- Raw relevance: a reward can improve task success while corrupting the communication property one thinks is being optimized.

### Kouwenhoven, Peeperkorn, and Verhoef — Searching for Structure with LLMs

- Primary source: [ACL Anthology, COLING 2025](https://aclanthology.org/2025.coling-main.667/)
- Setup: LLMs learn and use artificial languages in classical referential games over repeated generational transmission.
- Reported result: initially holistic languages acquire structural properties and become learnable enough for successful communication.
- Failure mode: transmission can also produce non-humanlike degenerate vocabularies.
- Limitation: constrained referential meanings, not arbitrary prose/tasks/data or compression against English.
- Raw relevance: this is the closest published LLM-language-emergence result found, but it does not reproduce the project's open-domain or efficiency design.

### Boldt and Mortensen — Induced Morphological Phrasebooks

- Primary source: [ACL Anthology, ACL 2026](https://aclanthology.org/2026.acl-long.1389/)
- Setup: induce form/meaning mappings from an emergent language, then make rule-based agents speak with the original neural agents.
- Reported result: phrasebook agents communicated effectively; ablation showed that repetition and morpheme order carried meaning.
- Measurement result: normalized pointwise mutual information between forms and meanings tracked speak/hear ability better than common topographic-similarity measures.
- Raw relevance: directly supports rule ablation and testing an explicit form/meaning lexicon rather than inferring structure from aggregate fidelity.

## Source notes: prompt, latent, and cache compression

### Jiang et al. — LLMLingua

- Primary source: [ACL Anthology, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.825/)
- Method: budget controller plus coarse-to-fine and token-level prompt compression using a smaller language model.
- Reported result: up to 20× compression with little downstream performance loss on GSM8K, BBH, ShareGPT, and an arXiv corpus.
- Non-equivalence: receiver performs the downstream task from a compressed prompt; it is not required to reconstruct every keyed fact for a stranger.
- Raw relevance: learned extractive deletion is an important ceiling and possible offline baseline, but the headline ratio is not directly comparable.

### Pan et al. — LLMLingua-2

- Primary source: [ACL Anthology, Findings ACL 2024](https://aclanthology.org/2024.findings-acl.57/)
- Method: data-distilled bidirectional token classification with smaller encoder models.
- Reported result: 2–5× prompt compression, 3–6× faster compression than prior methods, and 1.6–2.9× end-to-end latency improvement in the tested settings.
- Evaluated across in-domain and out-of-domain datasets and multiple target LLMs.
- Non-equivalence: trained compressor, extractive objective, and downstream quality metrics rather than loss-audited reconstruction.
- Raw relevance: strongest practical text-compression comparator found.

### Mu, Li, and Goodman — Gist Tokens

- Primary source: [arXiv 2304.08467](https://arxiv.org/abs/2304.08467)
- Method: modify attention masks during instruction tuning so a model must compress a prompt into one or more reusable continuous gist-token activations.
- Reported result: up to 26× prompt compression, up to 40% FLOP reduction, and 4.2% wall-time improvement with limited quality loss.
- Failure/limit noted by authors: out-of-distribution performance falls; compression loses some nuance; large token-count reduction does not translate proportionally to latency.
- Non-equivalence: requires training and passes hidden activations, not portable text to an unrelated black-box model.
- Raw relevance: useful upper bound and reminder to measure wall time/cost separately from tokens.

### Ge et al. — In-context Autoencoder

- Primary source: [arXiv 2307.06945](https://arxiv.org/abs/2307.06945)
- Method: train a lightweight context autoencoder that converts long context into compact memory slots consumed directly by the LLM.
- Reported result: 4× context compression with about 1% additional parameters and reduced inference latency/GPU memory.
- Non-equivalence: model modification, learned continuous memory, no human-readable interlingua.
- Raw relevance: another ceiling, not a fair body-text baseline.

### Liu et al. — DroidSpeak

- Primary source: [arXiv 2411.02820](https://arxiv.org/abs/2411.02820)
- Method: share selected KV-cache layers and recompute critical layers between fine-tuned variants derived from the same foundational model.
- Reported result: up to 3× throughput and 2.6× faster prefill with negligible accuracy loss relative to full recomputation.
- Hard applicability boundary: same-base-model variants. The project's DeepSeek encoder and Kimi decoder do not share this latent space.
- Raw relevance: addresses redundant context computation, not a transferable machine language.

### Du et al. — Interlat

- Primary source: [ACL Anthology, ACL 2026](https://aclanthology.org/2026.acl-long.1248/)
- Method: agents communicate through last hidden states; a learned process further compresses the latent messages.
- Reported result: outperformed the paper's fine-tuned chain-of-thought and single-agent baselines; further compression accelerated inference by up to 24× while retaining competitive performance.
- Stated scope: feasibility study, including heterogeneous-model experiments.
- Non-equivalence: requires model-internal state and learned alignment; no public text, rulebook, or black-box API portability.
- Raw relevance: supports keeping a separate “latent communication” category rather than treating it as a competitor to text.

## Source notes: production protocols and communication topology

### Model Context Protocol

- Primary source: [official transport specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
- Normative wire form: UTF-8 JSON-RPC messages.
- Standard transports: stdio and Streamable HTTP; HTTP can use JSON responses or Server-Sent Events.
- Search within the normative transport page found no semantic compression layer.
- Raw relevance: MCP prioritizes interoperability and tool/context exchange, not compact agent prose.

### Agent2Agent Protocol 1.0

- Primary source: [official specification](https://a2a-protocol.org/latest/specification/)
- Data model: Agent Cards, Messages, Parts, Tasks, Artifacts, and Extensions.
- Bindings: JSON-RPC, gRPC, and HTTP/JSON; supports sync, streaming, polling, and push notifications.
- Design goal: opaque independent agents can exchange text, files, and structured data without sharing internal state.
- Search within the normative specification found no semantic compression layer.
- Raw relevance: production protocol value comes from stable types, lifecycle, discovery, and transport behavior.

### Microsoft AutoGen AgentChat

- Primary source: [official message reference](https://microsoft.github.io/autogen/stable/reference/python/autogen_agentchat.messages.html)
- Message design: typed `BaseChatMessage`/event subclasses, Pydantic structured messages, JSON-serializable dictionaries.
- Agent state guidance: pass only new messages to stateful agents instead of replaying the entire history each turn.
- Search within the message reference found no semantic compression mechanism.
- Raw relevance: reducing repeated history and using structured message types are the normal engineering controls.

### Marro et al. — Agora

- Primary source: [arXiv 2410.11905](https://arxiv.org/abs/2410.11905)
- Method: a meta-protocol that chooses standardized routines for frequent interactions, natural language for rare interactions, and LLM-written routines for intermediate cases.
- Reported result: large networks formed self-organizing automated protocols and completed complex tasks with decentralized coordination.
- Missing comparison for this project: the abstract does not report an open-domain text compression/fidelity ratio or stranger reconstruction test.
- Raw relevance: closest production architecture to a multi-mode agent language; strong “library” material, but disclosure would contaminate independent invention.

### Zhang et al. — AgentPrune

- Primary source: [arXiv 2410.02506](https://arxiv.org/abs/2410.02506)
- Method: one-shot pruning of redundant spatial-temporal edges in multi-agent message-passing graphs.
- Reported results across six benchmarks: 28.1–72.8% token reduction; comparable performance at $5.6 reported cost vs $43.7 for compared topologies; improved resistance to two tested agent attacks.
- Non-equivalence: saves tokens by suppressing transmissions, not compressing an individual message.
- Raw relevance: demonstrates that topology is often a larger efficiency lever than language.

### Wang et al. — AgentDropout

- Primary source: [ACL Anthology, ACL 2025](https://aclanthology.org/2025.acl-long.1170/)
- Method: dynamically eliminate redundant agents and communications across rounds.
- Reported result: 21.6% average prompt-token reduction, 18.4% completion-token reduction, and a reported 1.14 task-performance improvement over compared methods.
- Non-equivalence: network/round selection, not a portable code.
- Raw relevance: another reason not to benchmark invented syntax against whole-system pruning claims.

## Source notes: machine-oriented formats

### Token-Oriented Object Notation (TOON)

- Primary source: [authors' official repository and benchmark](https://github.com/toon-format/toon)
- Design: JSON data model represented with indentation, explicit array lengths/field headers, and table-like rows for uniform objects.
- Self-reported mixed-structure benchmark: 76.4% retrieval accuracy using 2,759 tokens vs pretty JSON's 75.0% using 4,587 tokens, a 39.9% token reduction across four models.
- Authors' caveat: deeply nested or irregular data may be less efficient; compact JSON can beat TOON on some structures; CSV remains stronger for simple flat tables.
- Evidence-quality caveat: maintained project benchmark, not an independent peer-reviewed evaluation.
- Raw relevance: directly testable on `gen-data-*` exams as a specialized deterministic baseline, not a universal prose baseline.

### GibberLink

- Primary source: [authors' official repository](https://github.com/PennyroyalTea/gibberlink)
- Mechanism: two prompted ElevenLabs agents switch to Georgi Gerganov's existing `ggwave` data-over-sound protocol after confirming both sides are AIs.
- What it does not do: agents do not negotiate semantics, invent grammar, make a token-efficient text code, or discover the transport unprompted.
- Raw relevance: exclude from “invented language” precedent; include only as a transport-mode-switch demonstration.

## Source notes: information theory and tokenization

### Shannon — A Mathematical Theory of Communication

- Primary source: [IEEE primary-source reproduction of the 1948 Bell Labs paper](https://reach.ieee.org/primary-sources/a-mathematical-theory-of-communication/)
- Core frame used here: exact or approximate reproduction of a selected message; savings arise from source statistical structure.
- Raw relevance: separates lossless source redundancy from semantic/lossy compression and makes the channel/code assumptions explicit.

### Shannon — Coding Theorems for a Discrete Source With a Fidelity Criterion

- Primary source: [1959 paper](https://gwern.net/doc/cs/algorithm/information/1959-shannon.pdf)
- Core frame used here: rate-distortion theory asks the minimum communication rate possible under a defined distortion/fidelity constraint.
- Raw relevance: the project's key-item audit is a distortion function. A curve at fidelity 90/95/98/100 is more informative than a single mean.

### Goldman et al. — Unpacking Tokenization

- Primary source: [arXiv 2403.06265](https://arxiv.org/abs/2403.06265)
- Method: vary training data used for BPE tokenizers, train models using those tokenizers, and evaluate downstream behavior.
- Reported result: tokenizer compression correlates with downstream performance, especially for generation and smaller models; replicated in English and Turkish.
- Raw relevance: the tokenizer is part of the communication channel and codebook. New human-short symbols may be model-expensive.

### Schmidt et al. — Tokenization Is More Than Compression

- Primary source: [arXiv 2402.18376](https://arxiv.org/abs/2402.18376)
- Method: PathPiece finds minimum-token segmentations for a fixed vocabulary; authors train 64 models across tokenizer design choices.
- Reported result: fewer tokens alone did not guarantee better downstream model performance; pre-tokenization and vocabulary construction mattered.
- Raw relevance: measure semantic performance and tokenizer cost separately; neither can stand in for the other.

## Direct-prior-art disposition

### Closest inclusions

- `Searching for Structure`: LLMs iteratively shape artificial languages, but only in referential games and without English compression baselines.
- `Agora`: LLM networks form mixed routine/natural-language protocols, but not a public, textual, stranger-decoded language.
- `Morphological Phrasebooks`: interpretable form/meaning mappings and ablation, but induced from neural emergent languages rather than negotiated by general LLMs.
- `LLMLingua` family: practical discrete prompt compression, but trained compressors and downstream-task evaluation.

### Exclusions or category errors

- GibberLink: prewritten sound modem, not language invention.
- Latent/KV methods: not portable text and usually require weights, training, cache access, or model alignment.
- MCP/A2A/AutoGen: interoperability formats; no semantic compression claim.
- Media reports and product blogs: excluded from factual claims when a paper/spec/repository was available.
- Secondary surveys: used to discover papers, not cited as evidence for measured results.
- “First ever” claims: unsupported. The defensible wording is “no published primary-source match found in this sweep.”

## Raw five-idea extraction before synthesis

1. Add rulebook-inclusive and cache-aware accounting.
2. Publish a rate-distortion frontier against multiple frozen baselines.
3. Remove adopted rules one at a time to measure causal marginal value.
4. Test multiple stranger families/tokenizers and exact-string adversarial cases.
5. Preserve the untouched lineage; if prior art is disclosed, use a labeled informed fork and identical frozen exams.

No idea above was implemented during this research run.
