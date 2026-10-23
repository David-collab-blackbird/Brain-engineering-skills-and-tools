# AI Memory Systems, Temporal Knowledge Graphs and Graph/Entity-Centric Retrieval (state of the art, late 2026)

Researcher notes, compiled 2026-10-23. Every number is tagged **[VENDOR]** (published by the system's own maker), **[THIRD-PARTY]** (a competitor or another party re-ran it; may still be biased), or **[ACADEMIC]** (peer-reviewed or arXiv benchmark paper, not by the vendor). Where a secondary write-up reports a number, the note says so.

---

## 1. Systems: data model, write path, retrieval path, temporal handling, licence, self-hostability

### Takeaway
The field has split into two camps:
- **Structured/temporal stores.** Zep/Graphiti is a bi-temporal KG; Mem0g, EverMemOS and MemOS use versioned cells. They keep superseded facts but mark them invalid.
- **Compressed-log or agent-edited memory.** Mastra Observational Memory, Letta memory blocks and sleep-time agents. These rewrite a compact context and drop superseded items.

Notably, Mem0's April 2026 algorithm moved *away* from UPDATE/DELETE to ADD-only extraction plus multi-signal retrieval. Currency (returning the latest fact) is therefore increasingly handled at retrieval and read time rather than write time. For a ≤2% stale-fact target, Graphiti's explicit `t_valid` / `t_invalid` / `t'_created` / `t'_expired` edge model is the most concrete, open-source (Apache-2.0) and self-hostable reference design.

### Cited Findings

**Zep / Graphiti (bi-temporal KG)**
- Data model has three tiers:
  - an **episode subgraph**: raw messages, text or JSON kept as a "non-lossy data store", linked to the entities they mention;
  - a **semantic entity subgraph**: resolved entity nodes, with facts stored as edges;
  - a **community subgraph**: clusters built with label propagation rather than Leiden.

  — [Zep paper arXiv:2501.13956](https://arxiv.org/html/2501.13956)
- The bi-temporal model has two timelines. Timeline T (event time) uses `t_valid` / `t_invalid`. Timeline T′ (ingestion/transaction time) uses `t'_created` / `t'_expired`, for auditing. — [Zep paper](https://arxiv.org/html/2501.13956)
- Invalidation: an LLM compares a new edge with semantically related existing edges. If they contradict and overlap in time, the old edge's `t_invalid` is set to the new edge's `t_valid`, so new information wins. Facts are deduplicated only against edges between the same entity pair. — [Zep paper](https://arxiv.org/html/2501.13956)
- Entity resolution:
  - entity names are embedded (1024-dim) and searched alongside full-text search over names and summaries;
  - an LLM decides whether candidates are duplicates and writes a merged name and summary.

  — [Zep paper](https://arxiv.org/html/2501.13956)
- Retrieval has two stages:
  - **search**: cosine similarity over facts, entity names and community names, plus BM25 and n-hop breadth-first search;
  - **rerank**: RRF, MMR, episode-mention frequency, node distance from a centroid, or a cross-encoder (the most expensive option).

  Models in the paper: BGE-m3 for embedding and reranking; gpt-4o-mini for graph construction. — [Zep paper](https://arxiv.org/html/2501.13956)
- Graphiti repo facts:
  - Apache-2.0, about 32k stars;
  - backends: Neo4j 5.26, FalkorDB 1.1.2 and Amazon Neptune; Kuzu is deprecated and "will be removed";
  - custom entity and edge types can be defined as Pydantic models;
  - includes an MCP server;
  - "works best with LLM services that support Structured Output"; smaller models may produce schema and ingestion failures;
  - `SEMAPHORE_LIMIT` defaults to 10.

  — [getzep/graphiti](https://github.com/getzep/graphiti)
- Zep Community Edition was deprecated in 2025, and Zep itself is now cloud-only. Graphiti remains self-hostable. — [Vectorize/Hindsight blog (vendor-authored roundup)](https://hindsight.vectorize.io/blog/2026/08/11/open-source-agent-memory-systems)

**Mem0 / Mem0g**
- Original (2025) write path:
  1. An LLM extracts candidate facts from three inputs: a conversation summary, the last m=10 messages, and the new message pair.
  2. For each candidate, it retrieves the top s=10 similar memories.
  3. An LLM tool call chooses **ADD / UPDATE / DELETE / NOOP**. DELETE removes contradicted memories.

  — [Mem0 paper arXiv:2504.19413](https://arxiv.org/html/2504.19413)
- Mem0g graph variant:
  - Neo4j directed labelled graph; entity nodes carry a type, an embedding and a timestamp;
  - pipeline steps: entity extractor, relationship generator, conflict detector, update resolver;
  - obsolete relations are **marked invalid, not deleted**, to support temporal reasoning;
  - retrieval is entity-centric subgraph expansion plus semantic triplet matching;
  - gpt-4o-mini handles extraction and updates.

  — [Mem0 paper](https://arxiv.org/html/2504.19413)
- **April 2026 algorithm change [VENDOR]**:
  - single-pass, **ADD-only** extraction: no UPDATE or DELETE, so "memories accumulate rather than being overwritten";
  - agent-generated facts are stored with the same weight as user facts;
  - entity linking;
  - multi-signal retrieval that fuses semantic, BM25 and entity-match scores.

  The post does not mention a graph variant; entity linking is the closest feature. — [Mem0 blog, AI memory benchmarks](https://mem0.ai/blog/ai-memory-benchmarks)
- Licence and hosting: Apache-2.0 open-source core with an embedded store by default; production commonly uses an external vector DB; a hosted tier also exists. About 63k stars. — [Vectorize/Hindsight roundup (vendor)](https://hindsight.vectorize.io/blog/2026/08/11/open-source-agent-memory-systems)

**Letta (MemGPT)**
- Memory structure: editable in-context **core memory blocks**, plus archival and recall memory. Apache-2.0 and self-hostable as a server. — [Vectorize/Hindsight roundup](https://hindsight.vectorize.io/blog/2026/08/11/open-source-agent-memory-systems)
- Sleep-time agents, introduced in v0.7.0:
  - each sleep-time-enabled agent is a pair, a primary agent and a sleep-time agent;
  - the primary converses and searches recall and archival memory, but **cannot edit its own core memory**;
  - the sleep-time agent owns the memory-editing tools and asynchronously rewrites and consolidates the shared blocks at a configurable frequency;
  - Letta suggests a fast model for the primary and a slower model (gpt-4.1 or Sonnet 3.7) for the sleep-time agent.

  — [Letta blog, sleep-time compute](https://www.letta.com/blog/sleep-time-compute)

**Mastra Observational Memory (2026 entrant)**
- Mechanism:
  - an **Observer** agent turns raw messages into dated, dense observations once a token threshold is hit, and the raw messages are dropped;
  - a **Reflector** agent condenses observations past a second threshold, "removing superseded ones";
  - each observation carries up to three dates: observed, referenced and relative.

  — [Mastra research](https://mastra.ai/research/observational-memory)
- There is "no per-turn dynamic retrieval based on the user prompt". Memory is a stable context prefix. Mastra calls it open source, in the mastra-ai/mastra repo; the article names no licence. — [Mastra research](https://mastra.ai/research/observational-memory)

**EverMemOS (2026, arXiv:2601.02163)**
- The **MemCell** is the core unit. It holds:
  - an episode narrative;
  - atomic facts;
  - "foresight" (plans or temporary states with a validity window);
  - metadata (timestamps, source pointers).

  — [EverMemOS paper](https://arxiv.org/pdf/2601.02163)
- Write and read pipeline:
  - **Consolidation**: cells join MemScenes by centroid similarity, with a maximum time gap (7 days on LoCoMo, 30 days on LongMemEval). Scene summaries update a user profile with recency-aware updates, and conflicting evidence is tracked.
  - **Retrieval**: dense and BM25 search over atomic facts, fused with RRF, then scene selection and episode reranking. Expired foresight is dropped. An LLM sufficiency verifier can trigger a query rewrite.

  — [EverMemOS paper](https://arxiv.org/pdf/2601.02163)

**MemOS (arXiv:2507.03724)**
- A **MemCube** wraps three kinds of payload (plaintext, activation/KV-cache, parameter/LoRA) with metadata:
  - provenance and origin signature;
  - TTL;
  - access control;
  - a **version chain**, plus a "Time Machine" for snapshots and rollback.

  The lifecycle states are Generated, Activated, Merged, Archived and Expired, though the paper's state lists are internally inconsistent. — [MemOS paper](https://arxiv.org/pdf/2507.03724v4)

**Cognee**
- Apache-2.0, about 31k stars. Text becomes entities, relationships and chunks, with custom data models and ontologies. Stores: a graph store (Kuzu), PGVector and relational metadata. Using Postgres as the graph store is a "demo feature"; the production version is a licensed product. Includes an `improve` operation and session distillation. The README says nothing about temporal features. — [topoteretes/cognee](https://github.com/topoteretes/cognee)

**A-MEM**
- Zettelkasten-style notes carrying contextual descriptions, keywords and tags. An LLM generates links between similar notes. "Memory evolution" lets new memories update the attributes of older notes. Repos: WujiangXu/A-mem and A-mem-sys. — [A-MEM arXiv:2502.12110](https://arxiv.org/abs/2502.12110)

**HippoRAG 2**
- Builds on Personalized PageRank over a phrase and passage graph. It was designed to fix the drop on simple factual QA seen in earlier KG-RAG, and claims +7% on associative memory tasks over a state-of-the-art embedding model. — [HippoRAG 2 arXiv:2502.14802](https://arxiv.org/abs/2502.14802)

**Others**
- Memobase is described as user-profile memory. Hindsight (MIT licence, embedded PostgreSQL) runs semantic, BM25, graph and temporal retrieval in parallel with cross-encoder reranking, and per its own vendor blog "lacks native fact-validity modeling". Memary has been dormant since 2024. — [Vectorize/Hindsight roundup](https://hindsight.vectorize.io/blog/2026/08/11/open-source-agent-memory-systems)

### Inferences
- **Graphiti is the closest off-the-shelf match** to the "current fact plus what changed in March" requirement. Only it exposes both valid time and transaction time on every fact edge in a self-hostable Apache-2.0 package. Mem0g marks relations invalid but stores only node timestamps, not explicit validity intervals.
- **Mem0 moving to ADD-only is a warning sign** for stale-fact error. With nothing overwritten, currency depends entirely on retrieval and the reader LLM picking the newest fact. That only works if timestamps are carried into context and ranking. Do not adopt ADD-only without a recency or validity filter.
- **A converging pattern** across EverMemOS, MemOS, Mastra and Zep:
  - keep raw episodes for provenance;
  - derive atomic facts with time metadata;
  - consolidate into scenes, communities or profiles;
  - retrieve with hybrid dense and BM25 search fused by RRF, then rerank.

  This is a defensible default architecture.

### Gaps
- No primary details were obtained for LangMem (licence, data model) or Memobase internals.
- Supermemory's architecture page (versioning, `isLatest`, relation types) could not be read.
- The Letta sleep-time docs page was blocked, so `docs.letta.com/guides/agents/architectures/sleeptime` could not be fetched.
- The MemOS licence was not confirmed.

---

## 2. Benchmarks: scores per system, disputes, critiques, full-context baselines

### Takeaway
Headline memory-benchmark scores are **not comparable across vendors**. The same product (Zep) has been reported anywhere from **58 to 95 on LoCoMo**, depending on who ran it, the answer and judge model, and the grading prompt.

LoCoMo is badly compromised:
- it is short (16–26k tokens);
- 22% of its questions (category 5) are dropped by everyone;
- about 6–7% of its answer key is wrong;
- the standard Mem0-derived judge accepts many wrong answers.

**Full-context baselines often match or beat memory systems on LoCoMo.** On LongMemEval-S (about 115k tokens), good memory systems do beat full context with gpt-4o, though the gap shrinks with modern long-context models. Selective forgetting and multi-hop conflict resolution (MemoryAgentBench) remain essentially unsolved by every system.

### Cited Findings

**Benchmark definitions**
- **LongMemEval**:
  - 500 questions testing five abilities: information extraction, multi-session reasoning, knowledge updates, temporal reasoning and abstention;
  - LongMemEval_S is about 115k tokens per question; LongMemEval_M is about 1.5M tokens (500 sessions);
  - the GPT-4o evaluator agrees with human experts more than 97% of the time.

  — [LongMemEval arXiv:2410.10813](https://arxiv.org/html/2410.10813)
- LongMemEval's data file was replaced by `longmemeval_s_cleaned` in September 2025, which changed the haystack for 454 of 500 questions. Pre- and post-September scores are therefore not strictly comparable. — [braindetox.kr summary of CoreDotToday audit](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html)
- **LoCoMo**:
  - the paper describes 50 conversations and 7,512 questions, but only 10 conversations and 1,986 questions are public;
  - 444 of the 446 category-5 adversarial questions have no answer field;
  - Mem0, Zep and EverMemOS all grade only 1,540 questions;
  - the original metric was token F1; the LLM-judge "J" score came from the Mem0 paper (April 2025) and its prompt was copied by Zep, Memobase and EverMemOS.

  — [braindetox.kr / CoreDotToday](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html)
- **BEAM** (ICLR 2026):
  - 100 automatically generated conversations of up to **10M tokens**, with 2,000 validated questions;
  - the paper's LIGHT framework (episodic memory + working memory + scratchpad) improves results by 3.5–12.69% over the strongest baselines, depending on the backbone;
  - even 1M-context models struggle as dialogues get longer.

  — [BEAM arXiv:2510.27246](https://arxiv.org/abs/2510.27246)
- **MemoryAgentBench** (ICLR 2026) tests four competencies: Accurate Retrieval, Test-Time Learning, Long-Range Understanding and **Selective Forgetting**. It introduced the FactConsolidation-SH/MH datasets. RAG and memory agents use a gpt-4o-mini backbone by default. — [MemoryAgentBench arXiv:2507.05257](https://arxiv.org/html/2507.05257v2)

**MemoryAgentBench Selective Forgetting (FactConsolidation) [ACADEMIC], accuracy %, single-hop / multi-hop**

| Agent | Single-hop | Multi-hop |
|---|---|---|
| GPT-4o long-context | 60.0 | 5.0 |
| HippoRAG-v2 | 54.0 | 5.0 |
| BM25 | 48.0 | 3.0 |
| Cognee | 28.0 | 3.0 |
| MemGPT | 28.0 | 3.0 |
| Text-Embed-3-Large | 28.0 | 4.0 |
| Mem0 | 18.0 | 2.0 |
| GraphRAG | 14.0 | 2.0 |
| RAPTOR | 14.0 | 1.0 |
| Zep | 7.0 | 3.0 |

- All methods score at most 7% on multi-hop. o4-mini reaches 80.0 on multi-hop at 6K context but falls to 14.0 at 32K. — [MemoryAgentBench](https://arxiv.org/html/2507.05257v2)

**LongMemEval-S scores (judge GPT-4o unless noted)**
- **Zep paper [VENDOR]**:
  - gpt-4o: Zep **71.2%** vs full context 60.2%;
  - gpt-4o-mini: Zep 63.8% vs full context 55.4%;
  - Zep's average context is 1.6k tokens vs 115k for full context, with latency of 2.58s vs 28.9s;
  - knowledge-update with gpt-4o: 83.3% vs 78.2% (with gpt-4o-mini, Zep is *lower*: 74.4% vs 76.9%);
  - temporal reasoning with gpt-4o: 62.4% vs 45.1%.

  — [Zep paper](https://arxiv.org/html/2501.13956)
- **Mastra OM [VENDOR]**:
  - overall: 94.87% (gpt-5-mini), 93.27% (gemini-3-pro), 84.23% (gpt-4o);
  - gpt-5-mini per type: knowledge-update 96.2%, temporal 95.5%;
  - Observer and Reflector ran on gemini-2.5-flash.

  — [Mastra](https://mastra.ai/research/observational-memory)

  Correction from an independent audit: 94.87 is a simple average of six type scores; weighting all 500 questions equally gives 93.6%. — [braindetox.kr / CoreDotToday](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html)
- **Mem0 2026 [VENDOR]**: LongMemEval 94.4% (about 6.8k tokens per retrieval, p50 1.09s). The previous algorithm scored 67.8%. — [Mem0 blog](https://mem0.ai/blog/ai-memory-benchmarks)
- **MemOS paper [THIRD-PARTY to the others]**, gpt-4o-mini: MemOS 77.8, Memobase 72.4, Mem0 66.4, Zep 63.8, Supermemory 58.4, MIRIX 43.49, MemU 38.4. — [MemOS paper](https://arxiv.org/pdf/2507.03724v4)
- **EverMemOS [VENDOR]**: 83.00 (gpt-4.1-mini); knowledge-update 89.74 vs 74.26 for MemOS. Baselines were copied from the MemOS leaderboard. — [EverMemOS paper](https://arxiv.org/pdf/2601.02163)
- **Supermemory "97%" [VENDOR]** is a **Recall@20** retrieval metric, not answer accuracy, with a GPT-4o judge. Its earlier QA figure was 81.6%. The "97%" claim is not comparable to the accuracy numbers above. — [Supermemory research](https://supermemory.ai/research); [braindetox.kr](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html)
- **Redis re-measurement, September 2026 [THIRD-PARTY, Redis's own harness]**:
  - setup: LongMemEval-S, task-averaged, official GPT-4o judge, gpt-4o answerer;
  - Google Vertex Memory Bank: about 70 → **42.4** (−28);
  - Oracle Agent Memory: 93.8 → 86.0 (both gpt-5.5 xhigh), and 78.1 on gpt-4o;
  - Bedrock AgentCore: 73.6 → 77.0;
  - Emergence: 82.4 → 81.3;
  - Mastra OM: reproduced exactly at 84.2;
  - Zep, Mem0 and Supermemory were not reproduced;
  - the page's LangMem row appears to be a table error.

  — [Redis agent memory benchmark report](https://redis.io/resources/agent-memory-benchmark-report/)
- Hindsight claims 94.6% on LongMemEval-s and "#1 on BEAM 10M"; it gives no metric or LLM. **[VENDOR]** — [Hindsight blog](https://hindsight.vectorize.io/blog/2026/08/11/open-source-agent-memory-systems)
- Full context on LongMemEval_S with gemini-3.1-flash-lite: **81.6%** (59M tokens, $14.95, ±3.4). Per type:
  - single-session user 97.1%;
  - knowledge-update 75.6%;
  - temporal 80.5%;
  - multi-session 75.2%;
  - preference 63.3%.

  — [braindetox.kr / CoreDotToday](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html)

**LoCoMo scores and the Zep–Mem0 dispute**
- **Mem0 paper [VENDOR]**: J score per category (single-hop / multi-hop / open-domain / temporal), with gpt-4o-mini for the memory systems:

  | System | Single-hop | Multi-hop | Open-domain | Temporal |
  |---|---|---|---|---|
  | Mem0 | 67.13 | 51.15 | 72.93 | 55.51 |
  | Mem0g | 65.71 | 47.19 | 75.71 | 58.13 |
  | Zep | 61.70 | 41.35 | 76.60 | 49.31 |
  | LangMem | 62.23 | 47.92 | 71.12 | 23.43 |
  | OpenAI | 63.79 | 42.92 | 62.29 | 21.71 |
  | A-Mem* | 39.79 | 18.85 | 54.05 | 49.91 |

  — [Mem0 paper](https://arxiv.org/html/2504.19413)
- **Zep rebuttal (May 2025)**. Zep says Mem0 ran Zep incorrectly in three ways:
  - it assigned the user role to *both* speakers;
  - it put timestamps in the message text instead of the `created_at` field;
  - it ran searches sequentially.

  Zep's corrected score is **75.14% ± 0.17** vs Mem0g's 68.44%. Its first figure (about 84%) was a miscalculation; Mem0's CTO said category 5 had been removed from the denominator but kept in the numerator. Mem0's own **full-context baseline was about 72.9–73%, beating Mem0's best (about 68%)**. — [Zep blog](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/); [braindetox.kr](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html)
- **Letta [VENDOR]**: a filesystem-only agent (grep, search, open; gpt-4o-mini) scored **74.0%** on LoCoMo, beating Mem0g's 68.5%. Letta says Mem0's reported MemGPT numbers could not be reproduced because loading LoCoMo would need major refactoring, and Mem0 did not respond. Letta argues that "current memory benchmarks may not be very meaningful". — [Letta blog](https://www.letta.com/blog/benchmarking-ai-agent-memory)
- **2026 vendor LoCoMo claims**: Zep 94.7 (gpt-5.4 with reasoning answering *and* grading), Mem0 92.5, EverMemOS 92.3. Mem0's 92.5 setup:
  - managed platform, top-200 retrieval (about 7k tokens), single pass;
  - gpt-4o answerer and judge per the secondary source; gpt-5 per another excerpt (the sources conflict);
  - a new grading prompt.

  — [braindetox.kr](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html); [Mem0 blog](https://mem0.ai/blog/ai-memory-benchmarks)
- Zep's LoCoMo history ranges from 58.44 (Mem0 re-measurement) and 59.22 (MemOS paper) through 65.99 (Mem0 paper), 75.14 (Zep 2025), 79.09 (MIRIX), and 81.06/85.22 (EverMemOS with gpt-4o-mini/gpt-4.1-mini) to 94.7 (Zep 2026). — [braindetox.kr](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html); [EverMemOS](https://arxiv.org/pdf/2601.02163)
- **MemOS paper LoCoMo [THIRD-PARTY]**, gpt-4o-mini, J / F1:
  - MemOS 75.80 / 45.27
  - Memobase 72.01 / 50.18
  - Mem0 64.57 / 43.46
  - MIRIX 64.33
  - Zep 59.22 / 41.23
  - MemU 56.55
  - Supermemory 55.34

  — [MemOS paper](https://arxiv.org/pdf/2507.03724v4)

**LoCoMo critiques (independent or semi-independent)**
- **Penfield audit**:
  - 99 score-corrupting answer-key errors in 1,540 questions (**6.4%**);
  - the theoretical maximum score is about **93.6%**;
  - the judge accepted **up to 62.81% of intentionally wrong answers** (gpt-4o-mini judge).

  — [Penfield via DEV](https://dev.to/penfieldlabs/we-audited-locomo-64-of-the-answer-key-is-wrong-and-the-judge-accepts-up-to-63-of-intentionally-33lg) (as summarised in [braindetox.kr](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html))
- **CoreDotToday audit** (Claude-as-judge, 24 verdicts checked by humans): 7.0% of answers wrong or ambiguous, rising to 30.2% in open-domain. — [braindetox.kr](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html)
- **Grading-prompt sensitivity**: the *same* 1,540 gpt-4o-mini answers score:

  | Grading | Score |
  |---|---|
  | LongMemEval-style prompt | 55.8% |
  | Mem0-2025 prompt | 70.3% |
  | Strict prompt | 56.4% |
  | Mem0-2026 prompt | 81.4% |
  | Token F1 | 40.4 |

  The Mem0-2026 rule counts dates within 14 days and durations within 50% as correct. Under it, all "hedged" and "near-date" wrong answers passed. Swapping only the judge (gpt-4o-mini, Gemini, Haiku) spreads scores by 12 points. — [braindetox.kr / CoreDotToday](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html)
- **The Mem0 harness discourages abstaining**:
  - it evaluates only categories 1–4;
  - its answer prompt says "NEVER say 'not specified' … COMMIT AND ANSWER";
  - the judge accepts a match against any one item of a gold list.

  — [DEV: benchmark forbids "I don't know"](https://dev.to/gde03/the-ai-memory-benchmark-everyone-quotes-forbids-saying-i-dont-know-o1n)
- **Statistical noise**:
  - LoCoMo 95% CI is ±3.1 points when clustered by conversation;
  - the minimum detectable difference is about 4.5 points on LoCoMo and about 4–6 on LongMemEval's 500 questions;
  - Mem0g vs Mem0 (+1.56) and Letta filesystem vs full context (+1.1) are both inside the noise.

  — [braindetox.kr / CoreDotToday](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html)
- **Full context on LoCoMo (1,540 questions)**:

  | Model | Mem0-2025 grading | Mem0-2026 grading | Strict grading |
  |---|---|---|---|
  | gpt-4o-mini | 70.3% | 81.4% | 56.4% |
  | gemini-3.1-flash-lite | 80.7% | 88.1% | 60.5% |

  Full context with gemini-3.1-flash-lite cost $2.51 in total. — [braindetox.kr / CoreDotToday](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html)

### Inferences
- **Treat any LoCoMo number as near-useless for selection.** The answer-key ceiling is about 93.6, the judge is lenient, conversations fit in context, and there are no knowledge-update questions.
- **For a "current fact" requirement, the relevant public slices are**:
  - the LongMemEval *knowledge-update* and *temporal-reasoning* categories;
  - MemoryAgentBench *FactConsolidation*;
  - BEAM's update and contradiction categories, which come from secondary descriptions and were not confirmed from the paper page.
- **MemoryAgentBench is the most sobering evidence.** Every commercial memory system, Zep included at 7.0 on single-hop, scored *below* BM25 and long-context on selective forgetting. Bi-temporal design alone does not guarantee correct supersession; it depends on the extraction LLM detecting the conflict.
- **Build an in-house eval** with a strict judge, abstention questions and a pinned answer/judge model, reported with CIs. Vendor deltas under about 5 points are noise.

### Gaps
- The BEAM per-system leaderboard and its exact ten ability categories could not be confirmed from the paper page.
- Mem0's BEAM figures (64.1 on 1M, 48.6 on 10M) are vendor-only, with no stated LLM. — [Mem0 blog](https://mem0.ai/blog/ai-memory-benchmarks)
- No independent reproduction of Zep's 94.7 or Mem0's 92.5/94.4 was found.

---

## 3. Temporal knowledge modelling: bi-temporal, invalidation, event sourcing, effect on stale answers

### Takeaway
Bi-temporal edges (valid time + transaction time) with invalidate-not-delete are the dominant design: Graphiti, Mem0g's "mark invalid", MemOS version chains, EverMemOS foresight validity windows. Evidence that they reduce stale answers is **indirect and mixed**:
- they help temporal-reasoning questions substantially (Zep: +17 points over full context with gpt-4o);
- they give only small or inconsistent gains on knowledge-update questions;
- they fail MemoryAgentBench's selective-forgetting test.

The strongest single signal is cheap: keeping dated history beats discarding it by about 47 points in one small study.

### Cited Findings
- **Zep vs full context on LongMemEval [VENDOR]**:

  | Category | Model | Full context | Zep |
  |---|---|---|---|
  | Temporal reasoning | gpt-4o | 45.1% | 62.4% |
  | Temporal reasoning | gpt-4o-mini | 36.5% | 54.1% |
  | Knowledge update | gpt-4o | 78.2% | 83.3% |
  | Knowledge update | gpt-4o-mini | 76.9% | 74.4% (worse) |

  — [Zep paper](https://arxiv.org/html/2501.13956)
- **EverMemOS [VENDOR]**: knowledge-update 89.74 vs MemOS 74.26. It uses validity intervals on "foresight" and recency-aware profile updates. — [EverMemOS](https://arxiv.org/pdf/2601.02163)
- **Mastra OM [VENDOR]**: knowledge-update 96.2% and temporal 95.5% (gpt-5-mini). It has no graph: just dated observations plus a Reflector that removes superseded items. — [Mastra](https://mastra.ai/research/observational-memory)
- **LongMemEval time-aware query expansion**:
  - the LLM extracts a time range from the query and filters on it;
  - this improved temporal-reasoning recall by an average of **+11.3%** (round-level keys) and **+6.8%** (session-level keys) with GPT-4o as the extractor;
  - Llama 3.1 8B performed poorly at this step.

  — [LongMemEval paper](https://arxiv.org/html/2410.10813)
- **LongMemEval fact-augmented keys** (index each item with its extracted facts as an extra key) gave **+9.4% recall@k and +5.4% accuracy** on average. On LongMemEval_M, Recall@5 rose from 0.582 to 0.644. — [LongMemEval paper](https://arxiv.org/html/2410.10813)
- **Dated history vs discarded history**: 95.2% vs 47.6% on a small (210-question) customer study by CoreDotToday. Small sample; secondary report. — [braindetox.kr](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html)
- **Graphiti** invalidates outdated facts rather than deleting them, "so historical queries remain possible". — [getzep/graphiti](https://github.com/getzep/graphiti)
- **MemOS** offers a version chain and a "Time Machine" with snapshot and rollback, plus a provenance ID that persists through the memory's lifecycle. — [MemOS paper](https://arxiv.org/pdf/2507.03724v4)
- **Selective forgetting remains unsolved**. On FactConsolidation multi-hop, every system scores ≤7%. On single-hop, Zep scores 7.0 and Mem0 18.0, against BM25's 48.0. — [MemoryAgentBench](https://arxiv.org/html/2507.05257v2)

### Inferences
- **Recommended data model** for the brain: an append-only event log (episodes, the source of truth) plus derived fact edges carrying `valid_from`, `valid_to`, `recorded_at`, `superseded_at`, `superseded_by`, `source_episode_id` and `confidence`.
  - "Current" queries filter on `valid_to IS NULL AND superseded_at IS NULL`.
  - "What changed in March" queries scan facts whose `recorded_at` or `valid_from` falls in March.

  This combines Graphiti's bi-temporal edges with event-sourcing provenance.
- **Write-time contradiction detection by an LLM is the weak link.** MemoryAgentBench shows it, and so does Zep's gpt-4o-mini knowledge-update regression. For structured, high-churn facts (portfolio values, metrics, training plans), use **deterministic keyed upserts**: one entity, one attribute, one current value, with history. Do not rely on LLM conflict detection. Reserve LLM invalidation for unstructured facts.
- **Add query-time temporal parsing** (LongMemEval's time-aware expansion) and a recency prior in reranking. Both are cheap and measured.

### Gaps
- No public benchmark directly measures a "stale-fact error rate" (returning a superseded value as current). The ≤2% target will need a custom eval.
- No head-to-head study was found that isolates bi-temporal modelling from other system differences.

---

## 4. GraphRAG, LightRAG, LazyGraphRAG, HippoRAG: when graphs beat vector/hybrid retrieval, and at what cost

### Takeaway
Graphs win on **multi-hop reasoning and global or summarisation questions**, and lose or tie on **simple fact retrieval**, where vanilla RAG with a reranker is as good or better (GraphRAG-Bench, ICLR 2026). Among graph methods:
- **HippoRAG 2** is the most balanced: near-vanilla fact retrieval, a best-in-class multi-hop gain, and about 1k prompt tokens per query.
- **MS-GraphRAG global** is very costly (about 331k prompt tokens per query) and weak on fact retrieval.
- **LazyGraphRAG** cuts indexing cost to about 0.1% of GraphRAG, matching vector RAG.

### Cited Findings
- **GraphRAG-Bench (arXiv:2506.05690, ICLR 2026)**, gpt-4o-mini. Generation accuracy on the novel dataset (fact retrieval / complex reasoning / contextual summarisation):

  | System | Fact retrieval | Complex reasoning | Contextual summarisation |
  |---|---|---|---|
  | RAG with rerank | 60.92 | 42.93 | 51.30 |
  | HippoRAG2 | 60.14 | 53.38 | 64.10 |
  | MS-GraphRAG | 49.29 | 50.93 | 64.40 |
  | LightRAG | 58.62 | 49.07 | 48.85 |
  | RAPTOR | 49.25 | 38.59 | 47.10 |

  — [GraphRAG-Bench](https://arxiv.org/html/2506.05690v3)
- **GraphRAG-Bench retrieval recall** on fact retrieval, novel / medical:

  | System | Novel | Medical |
  |---|---|---|
  | RAG with rerank | 83.21 | 87.83 |
  | HippoRAG2 | 70.29 | 78.70 |
  | MS-GraphRAG | 61.04 | 38.06 |

  On complex reasoning (novel), LightRAG reaches 85.52 recall and HippoRAG2 69.77, against RAG's 64.47. — [GraphRAG-Bench](https://arxiv.org/html/2506.05690v3)
- **Average prompt tokens per query** (novel dataset):

  | System | Tokens |
  |---|---|
  | Vanilla RAG | 879 |
  | HippoRAG2 | 1,008 |
  | RAPTOR | 3,441 |
  | HippoRAG | 7,208 |
  | MS-GraphRAG local | 38,707 |
  | LightRAG | 100,832 |
  | MS-GraphRAG global | 331,375 |

  — [GraphRAG-Bench](https://arxiv.org/html/2506.05690v3) (the paper's text and its tables disagree on the global figure: about 4×10⁴ vs 331k)
- **Graph density** per 10k tokens: HippoRAG2 averages 2,310 edges and 523 nodes on novels, with average degree 8.75 (vs LightRAG 2.10 and MS-GraphRAG 1.48). — [GraphRAG-Bench](https://arxiv.org/html/2506.05690v3)
- **LazyGraphRAG (Microsoft)**:
  - indexing costs about **0.1% of full GraphRAG** and the same as vector RAG, because it uses NLP noun-phrase extraction with no LLM;
  - quality is comparable to GraphRAG global search at **700× or more lower query cost**;
  - at the Z500 budget it beats all conditions, including global search, on both local and global queries;
  - test set: 5,590 AP news articles and 100 synthetic queries;
  - no numeric win rates appear in the text.

  — [Microsoft Research blog](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/)
- **HippoRAG 2**: earlier KG-RAG methods "performed noticeably worse than standard RAG on basic factual tasks", and HippoRAG 2 fixes that while gaining +7% on associative memory. — [HippoRAG 2](https://arxiv.org/abs/2502.14802)
- **MemoryAgentBench**: structure-augmented RAG (GraphRAG, RAPTOR) scored *lowest* on selective forgetting (14.0 single-hop), while HippoRAG-v2 was the best RAG method (54.0). — [MemoryAgentBench](https://arxiv.org/html/2507.05257v2)

### Inferences
- **Default to hybrid dense + BM25 with a cross-encoder reranker** for fact lookups, the bulk of a personal brain's queries.
- **Add an entity/PPR layer (HippoRAG2-style)** for multi-hop questions. It costs about the same per query as vanilla RAG, though its LLM OpenIE indexing cost was not quantified here.
- **Avoid MS-GraphRAG-style community summaries** for a constantly changing corpus. Indexing is expensive, and summaries go stale the moment a fact changes. Use LazyGraphRAG-style deferred summarisation for "global" questions instead.
- **A per-query-class router** (fact / multi-hop / global / temporal) is supported by the evidence that no single retriever wins every class.

### Gaps
- GraphRAG-Bench's indexing cost and time figures (Appendix G.3) were not extracted.
- No absolute dollar cost was found for Graphiti or Mem0g ingestion per 10k items.
- nano-graphrag was not researched separately.

---

## 5. Consolidation, sleep-time compute, reflection, summarisation hierarchies (RAPTOR)

### Takeaway
Background consolidation shows real, measured gains in systems that use it as their core mechanism:
- Mastra's Observer/Reflector reaches 84–95% on LongMemEval-S, independently reproduced at 84.2 with gpt-4o;
- EverMemOS's ablations show scene consolidation adds about 4 points.

Letta's sleep-time compute evidence is on math reasoning, not memory QA. RAPTOR-style hierarchies underperform on fact and complex-reasoning retrieval in GraphRAG-Bench.

### Cited Findings
- **Sleep-time compute paper**, measured on math reasoning, not memory QA:
  - about **5× lower test-time compute** for the same accuracy on Stateful GSM-Symbolic and Stateful AIME;
  - up to +13% and +18% accuracy respectively when scaling sleep-time compute;
  - **2.5× lower cost per query** on Multi-Query GSM-Symbolic;
  - effectiveness is strongly correlated with how predictable the user's query is.

  — [arXiv:2504.13171](https://arxiv.org/abs/2504.13171)
- **Letta's rationale**: asynchronous memory rewriting avoids the "messy, disorganized memories" that incremental formation produces in the original MemGPT. No memory-benchmark numbers are given. — [Letta blog](https://www.letta.com/blog/sleep-time-compute)
- **Mastra OM**:
  - text compresses about 3–6×;
  - the gpt-4o score (84.23%) is above the gpt-4o Oracle (82.40%), but the author says the gap may be within variance;
  - Redis reproduced 84.2% exactly.

  — [Mastra](https://mastra.ai/research/observational-memory); [Redis](https://redis.io/resources/agent-memory-benchmark-report/)
- **EverMemOS ablation**: removing MemScenes (consolidation) drops LoCoMo from 93.05 to 89.16; removing MemCells drops it to 81.82. — [EverMemOS](https://arxiv.org/pdf/2601.02163)
- **RAPTOR** in GraphRAG-Bench (novel dataset):
  - fact retrieval 49.25 and complex reasoning 38.59, both below RAG with rerank;
  - highest faithfulness on creative generation (70.85).

  — [GraphRAG-Bench](https://arxiv.org/html/2506.05690v3)
- **MemOS MemScheduler** promotes frequently used memory to activation (KV) memory and distils stable templates into parameter memory. No isolated measurement of this is given. — [MemOS](https://arxiv.org/pdf/2507.03724v4)

### Inferences
- **Run consolidation as an asynchronous job** that produces *derived* artefacts (profiles, scene summaries, current-state tables) linked back to raw episodes. Never let it destroy raw episodes, or provenance and "what changed" queries break.
- **Summaries must be invalidated or regenerated when underlying facts change.** Otherwise consolidation becomes a stale-fact source.

### Gaps
- No memory-QA benchmark result isolating Letta's sleep-time agents was found.
- No measured effect of "reflection" (Generative-Agents style) on LongMemEval or BEAM was found.

---

## 6. Memory typing: episodic vs semantic vs procedural, preferences, provenance

### Takeaway
Leading systems converge on three layers:
- episodic raw events (Zep episodes, EverMemOS episodes, Letta recall);
- semantic facts and entities (Graphiti edges, atomic facts, Mem0 facts);
- profile/preference summaries (EverMemOS profile, Memobase, Letta core blocks).

Procedural memory is weakly represented (MemOS parameter memory). Preference questions remain a weak spot even for full context.

### Cited Findings
- **Zep**: episodes are the "non-lossy" episodic store, linked by episodic edges to semantic entities, which supports provenance from fact to source. — [Zep paper](https://arxiv.org/html/2501.13956)
- **EverMemOS** splits each MemCell into an episode (episodic), atomic facts (semantic), foresight (prospective, time-bounded) and metadata with source pointers. A user profile holds explicit facts and implicit traits. — [EverMemOS](https://arxiv.org/pdf/2601.02163)
- **MemOS** distinguishes plaintext, activation and parameter memory. Its metadata includes origin signature, semantic type and a provenance ID. — [MemOS](https://arxiv.org/pdf/2507.03724v4)
- **BEAM's LIGHT** splits memory into long-term episodic, short-term working memory and a key-fact scratchpad, and its ablation shows each component contributes. — [BEAM](https://arxiv.org/abs/2510.27246)
- **Preference questions are hard**:
  - full context (gemini-3.1-flash-lite) scores 63.3% on LongMemEval single-session-preference;
  - per Supermemory's table, Zep scores 56.7% and full context with gpt-4o 20%;
  - the category has only 30 questions, so one answer moves the score by 3.3 points.

  — [braindetox.kr](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html); [Supermemory](https://supermemory.ai/research); [Mastra](https://mastra.ai/research/observational-memory)
- **Mem0 2026 stores agent-generated facts with the same weight as user facts.** This is a provenance-relevant design choice. — [Mem0 blog](https://mem0.ai/blog/ai-memory-benchmarks)

### Inferences
- **Type every memory record** (`episodic | semantic_fact | preference | procedure | profile_summary`) and record its source (user-stated, agent-inferred, document-ingested). Treating agent-inferred facts like user-stated ones, as Mem0 now does, risks polluting "current fact" answers.
- **Evaluate preferences separately.** Public benchmarks have too few preference questions to reach ±2% precision.

### Gaps
- No benchmark evidence was found specifically for procedural memory (skills or workflows) in personal or enterprise assistants.
- No study was found quantifying provenance's effect on answer correctness.
