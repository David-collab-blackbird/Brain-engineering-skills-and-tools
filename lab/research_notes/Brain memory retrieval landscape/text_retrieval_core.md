# Text Retrieval Core for High-Accuracy RAG / Memory (state as of Oct 2026)

Scope: chunking, contextual retrieval, hybrid lexical+dense, late interaction, rerankers, text embedding models, embedding limits, exact vs ANN at 10k–100k items. Target system: self-hosted brain, >=90% Context Recall@~10 after reranking, in every query class, at 10k–100k items, with frequently changing content and multi-item reasoning queries.

Convention: [VENDOR] = claim by the model/tool maker; [INDEP] = third-party or academic result; [OLD] = pre-2024 result.

---

## 1. Chunking: fixed vs semantic vs structure-aware vs late chunking vs proposition-level

### Takeaway
No chunking method dominates. Well-tuned fixed/recursive or paragraph chunks (~200–400 tokens, little or no overlap) are within 1–3% of fancier methods for corpus-wide retrieval. Semantic chunking rarely justifies its cost on real documents. Proposition chunking is task-dependent: it helped weak or unsupervised retrievers on Wikipedia QA (2023) but a 2026 study found it 15–27% worse in-corpus. LLM-guided chunking gives the best recall but runs at about 1 doc/s. Contextualising chunks, whether by late chunking or by LLM context, helps corpus-wide retrieval.

### Cited Findings
- **Chroma chunking study [INDEP, 2024]** (text-embedding-3-large, 5 chunks retrieved, 5 corpora, 328k tokens, 472 LLM-generated queries). Token-level recall by method:
  - Recursive 200 tok/no overlap: 88.1
  - Recursive 400: 89.5
  - Recursive 800/400 overlap: 85.4
  - TokenText 800/400 (the OpenAI file-search default): 87.9, with the lowest efficiency
  - Kamradt semantic (default): 83.6
  - ClusterSemantic 400: 91.3
  - LLM chunker (GPT-4o): 91.9, the best
  - Recall spread across methods: up to ~9 points
  - With all-MiniLM-L6-v2, overlap helped recall: TokenText 250/125 scored 82.4, and dropping the overlap cut it to 77.1.
  - Limitation: small, synthetic dataset — [Chroma Research](https://www.trychroma.com/research/evaluating-chunking)
- **"Is Semantic Chunking Worth the Computational Cost?" (Vectara, Oct 2024) [INDEP]:**
  - Semantic chunkers won only on synthetic "stitched" documents, e.g. Miracl F1@5 81.89 vs 69.45 fixed.
  - On the 4 real-document datasets fixed-size won every time, e.g. HotpotQA 90.59 fixed vs 87.37 breakpoint vs 84.79 clustering.
  - Evidence-retrieval differences were tiny (ExpertQA 47.11 / 47.08 / 46.87).
  - Conclusion: fixed-size is the efficient default, and the embedding model matters more than the chunker — [arXiv 2410.13070](https://arxiv.org/html/2410.13070v1)
- **"Beyond Chunk-Then-Embed" (U. Queensland/CSIRO/Google, Feb 2026) [INDEP]** (6 BEIR datasets + GutenQA, 4 embedders):
  - Paragraph, fixed-size and sentence chunking differ by only 1–3% in-corpus.
  - Proposition-based chunking is 15–27% worse than paragraph chunking in-corpus.
  - LumberChunker (LLM-guided) is 10–30% better for in-document retrieval, but processes ~1.11 docs/s vs ~1,854 docs/s for paragraph chunking.
  - Contextualised (late) chunking improves in-corpus retrieval but degrades in-document retrieval, by -3.83% (E5-large) to -53.17% (Nomic).
  - Rankings reverse between in-corpus and in-document tasks — [arXiv 2602.16974](https://alphaxiv.org/abs/2602.16974)
- **Dense X Retrieval (propositions; EMNLP 2024; data from Dec 2023) [INDEP]** (average over NQ/TQA/WebQ/SQuAD/EQ, passage-recall@20):
  - SimCSE: 49.1 (passage) → 61.7 (proposition)
  - Contriever: 62.8 → 70.5
  - DPR: 69.5 → 72.2
  - GTR: 76.6 → 79.2
  - Gains are large for unsupervised retrievers (+10.1 average) and small for supervised ones (+2.7), and largest on out-of-domain sets (GTR SQuAD R@5 54.4 → 63.3).
  - The propositioniser is a fine-tuned Flan-T5-Large — [arXiv 2312.06648](https://arxiv.org/html/2312.06648v3)
- **Late chunking (Jina, Sept 2024) [VENDOR paper]** (jina-embeddings-v2-small, 256-token chunks, BEIR nDCG@10, naive → late):
  - SciFact: 64.20 → 66.10
  - TREC-COVID: 63.36 → 64.70
  - FiQA: 33.25 → 33.84
  - NFCorpus: 23.46 → 29.98
  - Quora: no change, because documents fit in one chunk
  - Gains grow with document length. No training is needed, but a long-context embedder is required (8k) — [arXiv 2409.04701](https://arxiv.org/html/2409.04701v1); code at [github.com/jina-ai/late-chunking](https://github.com/jina-ai/late-chunking)
- **Late chunking is model-dependent [INDEP, Apr 2025]:**
  - BGE-M3 on NFCorpus: early nDCG@5 0.246 vs late 0.070.
  - Stella-V5 on MS MARCO: early 0.630 vs late 0.503.
  - Late chunking only works well with models built for it (Jina-v3) — [arXiv 2504.19754](https://arxiv.org/html/2504.19754v1)

### Inferences
- Default for the brain: structure-aware splitting (headings/paragraphs) with a recursive fallback at ~200–400 tokens and little overlap. Then fix context loss with contextual retrieval (section 2), not with semantic chunkers.
- Do not use proposition-only indexing as the main index. It may be worth a second, additive index for atomic facts or memories, since it helps on out-of-domain short-fact queries.
- Late chunking is cheap (no LLM) but only safe with an embedder that has been validated for it. Qwen3-Embedding / BGE-M3 have no evidence of benefiting, and BGE-M3 was badly hurt.
- In-document vs in-corpus reversal: chunk size and contextualisation should be tuned per query class with your own eval, not globally.

### Gaps
- No found benchmark of chunking on personal/enterprise mixed corpora (notes, email, tickets) at 10k–100k items.
- No head-to-head of structure-aware (Markdown/HTML heading) chunking against recursive chunking with modern 2025–26 embedders, beyond the paragraph-based results above.

---

## 2. Contextual retrieval (Anthropic, Sept 2024)

### Takeaway
Prepending a 50–100-token LLM-written context to each chunk before embedding and BM25 indexing cut top-20 retrieval failures by 35% (embeddings only), 49% (+ contextual BM25) and 67% (+ reranking) in Anthropic's own tests. Independent replications are small and mixed. They agree that it helps, but that gains depend on the model and LLM, and that reranking is needed for fusion gains to show consistently.

### Cited Findings
- **Anthropic's results [VENDOR]** (1 − recall@20, averaged across codebases, fiction, ArXiv and science papers; Gemini text-004 embeddings):
  - Baseline: 5.7% failures
  - Contextual embeddings: 3.7% (-35%)
  - + contextual BM25: 2.9% (-49%)
  - + Cohere rerank: 1.9% (-67%)
  - Retrieval set-up: retrieve top-150, rerank to top-20; top-20 beat top-10 and top-5.
  - Context written by Claude 3 Haiku.
  - Contextualising improved "every embedding-source combination" tested, and Voyage and Gemini embeddings were best.
  - One-time cost: $1.02 per million document tokens with prompt caching (assuming 800-token chunks and 8k-token docs). Caching cuts cost by up to 90% and latency by more than 2x — [Anthropic](https://anthropic.com/news/contextual-retrieval)
- **Independent small replication [INDEP, Apr 2025]** (NFCorpus subset, ~50 queries, Jina-V3, fixed window): contextual nDCG@10 0.308 vs late chunking 0.294.
  - Context was generated with Phi-3.5-mini (4-bit). It used up to ~20 GB VRAM on long documents, and smaller LLMs did worse.
  - Dense + BM25 fusion (weights 1 / 0.25) needed a Jina-reranker-v2 step to give consistent gains.
  - Verdict: neither technique is definitive — [arXiv 2504.19754](https://arxiv.org/html/2504.19754v1)
- **Feb 2026 taxonomy paper [INDEP]:** contextualised chunking improves in-corpus retrieval (+22–27% relative for proposition chunks, from low baselines) but can hurt in-document retrieval — [arXiv 2602.16974](https://alphaxiv.org/abs/2602.16974)

### Inferences
- Anthropic's baseline was already ~94% recall@20, so the gains are measured near the ceiling. For the >=90%-at-k=10 target this is one of the few techniques with evidence of moving the last few points. Apply it to both the dense and the BM25 index.
- With frequently changing content, context should be regenerated only for chunks whose parent document changed. Prompt caching on the parent document makes per-document refresh cheap (about $1/M doc tokens at Haiku-class pricing).
- Use a capable small LLM (Haiku-class) for context. The replication suggests weak local LLMs degrade the benefit.

### Gaps
- No large independent replication of the 35/49/67% numbers found. Anthropic's per-model numbers exist only in its charts and appendix.
- No published measurement of contextual retrieval specifically on multi-item reasoning queries.

---

## 3. Hybrid search: BM25/SPLADE + dense and fusion methods

### Takeaway
Hybrid lexical + dense retrieval reliably beats either alone, on BEIR, in Anthropic's tests, and on adversarial combinatorial queries (LIMIT, where BM25 crushes dense models). Convex/weighted score fusion beats RRF when tuned with even a few labelled examples. RRF is a robust zero-label default but is sensitive to its k.

### Cited Findings
- **BEIR reproducible baselines [INDEP, 2023, OLD]** (average nDCG@10):
  - BM25 flat: 0.424
  - BM25 multifield: 0.429
  - SPLADE (distil CoCondenser): 0.474
  - Contriever: 0.448
  - Contriever + SPLADE hybrid: 0.493
  - The hybrid is +0.019 over the best single model — [arXiv 2306.07471](https://arxiv.org/pdf/2306.07471)
- **Fusion functions (Bruch, Gai & Ingber; ACM TOIS 2023) [INDEP, OLD]:**
  - Convex combination of lexical and semantic scores beats RRF both in-domain and out-of-domain.
  - RRF is "sensitive to its parameters", which contradicts earlier claims.
  - The convex combination is largely agnostic to normalisation and needs only a small labelled set to tune alpha — [Pinecone research mirror](https://www.pinecone.io/research/an-analysis-of-fusion-functions-for-hybrid-retrieval/md/); [arXiv 2210.11934](https://arxiv.org/pdf/2210.11934)
- **Anthropic [VENDOR]:** embeddings + BM25 beat embeddings alone, and contextual BM25 took failures from 3.7% to 2.9% — [Anthropic](https://anthropic.com/news/contextual-retrieval)
- **LIMIT (DeepMind, 2025) [INDEP]:** on combinatorial "who likes X" queries, BM25 scores R@100 93.6 vs ≤18.9 for every single-vector model, including Qwen3-Embed at 4.8 — [arXiv 2508.21038](https://arxiv.org/pdf/2508.21038v2)

### Inferences
- BM25 (or SPLADE) must be a first-class retriever in the brain, not a fallback. It covers exact names, IDs, rare terms and attribute-conjunction queries where dense models fail structurally.
- Fusion: start with RRF (k≈60) with no labels. Once there is a labelled eval set of ~50–100 queries per class, switch to a tuned convex combination with min-max normalisation. Either way, a cross-encoder reranker over the union (top ~100–150) shrinks the importance of the fusion choice.
- BGE-M3 gives dense + sparse + multi-vector output from one model (MIT licence). Qdrant, Vespa and Elasticsearch support hybrid search natively, and Postgres can combine pgvector with tsvector/ParadeDB BM25.

### Gaps
- No found 2025–26 independent BEIR-scale numbers for hybrid with modern LLM-based embedders (Qwen3-Embedding + BM25). The gain may be smaller on BEIR averages, but LIMIT shows it is large on combinatorial queries.
- Learned sparse (SPLADE-v3, opensearch neural sparse) 2025–26 numbers were not retrieved in this pass.

---

## 4. Late interaction (ColBERT family) vs single-vector

### Takeaway
Multi-vector late interaction is markedly more robust than single-vector on combinatorial queries (LIMIT R@100 54.8 vs ≤18.9) and competitive on BEIR even at tiny sizes (answerai-colbert-small, 33M params, BEIR 53.79). The cost is storage: one vector per token, compressed to ~20–36 bytes each.

### Cited Findings
- **answerai-colbert-small-v1 (33M params, Apache-2.0) [VENDOR model card]:** BEIR average nDCG@10 53.79 vs bge-small-en 51.68 vs ColBERTv2 50.02.
  - Usable via RAGatouille, colbert-ai, Sentence-Transformers, and the `rerankers` library — [Hugging Face](https://huggingface.co/answerdotai/answerai-colbert-small-v1)
- **ColBERTv2 [INDEP, OLD 2021–22]:**
  - Residual compression stores 20 bytes/vector (1-bit) or 36 bytes/vector (2-bit), vs 256 bytes for ColBERTv1.
  - MS MARCO index: 154 GiB (v1) → 16–25 GiB, a 6–10x reduction.
  - Highest MRR@10 of any standalone retriever at the time (39.7).
  - Beats single-vector baselines on most BEIR tasks, e.g. NQ 56.2 vs 50.5 for RocketQAv2 — [arXiv 2112.01488](https://arxiv.org/pdf/2112.01488)
- **PLAID** is the efficient search engine for ColBERTv2 — [arXiv 2205.09707](https://arxiv.org/pdf/2205.09707)
- **LIMIT [INDEP]** (full LIMIT, R@2/R@10/R@100):
  - GTE-ModernColBERT: 23.1 / 34.6 / 54.8
  - Best single-vector model (Promptriever): 3.0 / 6.8 / 18.9
  - LIMIT-small (46 docs), R@10: ColBERT 97.6 vs Qwen3-Embed 52.3 — [arXiv 2508.21038](https://arxiv.org/pdf/2508.21038v2)
- **Jina-ColBERT-v2** (multilingual late interaction; 2024) — [arXiv 2408.16672](https://arxiv.org/pdf/2408.16672)

### Inferences
- At 100k chunks × ~300 tokens = 30M token vectors × ~36 bytes, a 2-bit ColBERT index is about 1 GB, which is feasible on one machine. A cheaper pattern is to use ColBERT as a reranker over the hybrid top-200, storing no extra index. answerai-colbert-small is fast enough to rerank on CPU.
- Libraries to evaluate: PyLate (training/indexing, GTE-ModernColBERT), RAGatouille, Vespa and Qdrant multivector.

### Gaps
- The 2025–26 Jina-ColBERT-v2 and GTE-ModernColBERT BEIR numbers and a modern latency/cost table were not fetched in this pass. MUVERA (fixed-dimensional encodings for multi-vector search) was not verified.

---

## 5. Rerankers

### Takeaway
A cross-encoder or listwise reranker over the top 100–150 candidates is the single largest recall lever after hybrid retrieval. Anthropic's tests saw failures go from 2.9% to 1.9%. Qwen3-Reranker raised the Qwen3-Embedding-0.6B first stage from 61.8 to 69.8 nDCG on MTEB-R.

Best open-weight options as of late 2026:
- Qwen3-Reranker-4B/8B (Apache-2.0)
- jina-reranker-v3 (0.6B, listwise)
- mxbai-rerank-large-v2 (1.5B, Apache-2.0)

These have overtaken bge-reranker-v2-m3. The hosted options (Cohere Rerank 4, Voyage rerank-2.5) give mostly vendor-only numbers.

### Cited Findings
- **Qwen3-Reranker (June 2025, Apache-2.0, 32k context, instruction-aware) [VENDOR paper]** (reranking the top-100 from Qwen3-Embedding-0.6B):

  | Model | MTEB-R | MMTEB-R | MLDR | MTEB-Code | FollowIR |
  |---|---|---|---|---|---|
  | First stage (Qwen3-Embedding-0.6B) | 61.82 | 64.64 | 50.26 | 75.41 | — |
  | Qwen3-Reranker-0.6B | 65.80 | 66.36 | — | — | — |
  | Qwen3-Reranker-4B | 69.76 | 72.74 | 69.97 | 81.20 | 14.84 |
  | Qwen3-Reranker-8B | 69.02 | 72.94 | 70.19 | — | — |
  | bge-reranker-v2-m3 | 57.03 | — | — | 41.38 | — |
  | jina-multilingual-reranker-v2 | 58.22 | — | — | — | — |

  - bge-reranker-v2-m3 and jina-multilingual-reranker-v2 score below the first stage on MTEB-R — [arXiv 2506.05176](https://arxiv.org/html/2506.05176v1)
- **jina-reranker-v3 (0.6B, Qwen3 backbone, listwise, 131k context; Sept 2025) [VENDOR paper]** (top-100 from jina-embeddings-v3, BEIR nDCG@10):

  | Model | BEIR |
  |---|---|
  | jina-reranker-v3 | 61.85 |
  | mxbai-rerank-large-v2 | 61.44 |
  | Qwen3-Reranker-4B | 61.16 |
  | jina-reranker-m0 | 58.95 |
  | mxbai-rerank-base-v2 | 58.40 |
  | jina-reranker-v2 | 57.06 |
  | bge-reranker-v2-m3 | 56.51 |
  | Qwen3-Reranker-0.6B | 56.28 |

  - CoIR (code): Qwen3-Reranker-4B is best at 73.91.
  - Licence is not stated in the paper — [arXiv 2509.25085](https://arxiv.org/html/2509.25085v4)
- **mxbai-rerank-v2 (base 0.5B / large 1.5B, Apache-2.0, 8k context; 2025) [VENDOR]** (BEIR average with a BM25 first stage):

  | Model | BEIR |
  |---|---|
  | mxbai-rerank-large-v2 | 57.49 |
  | mxbai-rerank-base-v2 | 55.57 |
  | Cohere rerank-3.5 | 55.39 |
  | bge-reranker-v2-gemma | 55.38 |
  | Voyage rerank-2 | 54.54 |
  | jina-reranker-v2 | 54.35 |

  - Latency per query on A100 (NFCorpus): base 0.67 s, large 0.89 s, bge-reranker-v2-m3 3.05 s, bge-reranker-v2-gemma 7.20 s.
  - Install with `pip install mxbai-rerank`; `MxbaiRerankV2(...).rank(query, docs)` — [Mixedbread](https://www.mixedbread.com/blog/mxbai-rerank-v2)
- **Cohere Rerank 4 (Dec 2025; Fast and Pro; 32k context, 4x Rerank 3.5; 100+ languages; "self-learning" tuning) [VENDOR, via press]:** claims parity or better vs Qwen3-Reranker-8B, Jina Rerank v3 and Voyage rerank-2.5 on finance, healthcare and manufacturing, but no numeric scores were published in the article. API only — [VentureBeat](https://venturebeat.com/ai/coheres-rerank-4-quadruples-the-context-window-to-cut-agent-errors-and-boost)
- **LLM-as-reranker:** on LIMIT-small, Gemini-2.5-Pro given all 46 docs in context solved 100% of 1,000 queries, while single-vector models were at R@10 52–90 [INDEP] — [arXiv 2508.21038](https://arxiv.org/pdf/2508.21038v2)
- **Independent small check [INDEP, but by a seller of Qwen3 APIs]:** Qwen3-Reranker-4B reached 96.84% nDCG@10 only with the full ChatML template, and 77.98% without it — [Regolo](https://regolo.ai/embeddinggemma-2-vs-qwen3-embedding-benchmarks.md)

### Inferences
- Recommended self-hosted stack: Qwen3-Reranker-4B (best all-round quality, instruction-aware, so per-query-class instructions are possible) or jina-reranker-v3 (0.6B, listwise, cheaper). The 0.6B Qwen reranker is a much weaker reranker and is not recommended as primary.
- Critical build detail: use the exact official prompt template for Qwen3-Reranker (yes/no logit scoring in ChatML). Template mistakes cost about 19 points in the one independent test.
- Rerank depth: 100–150 candidates → top 10–20, following Anthropic. For multi-item reasoning queries, a final LLM listwise pass over the top ~30–50 (long-context model) is the strongest evidence-backed option for combinatorial needs (LIMIT).
- Serving: Qwen3-Reranker runs under vLLM / sentence-transformers CrossEncoder / Infinity / TEI. A 4B model on one GPU should handle 100 candidates in well under a second, but this is inferred, not measured.

### Gaps
- No verified numeric scores for Voyage rerank-2.5 or Cohere Rerank 4. Independent latency comparisons of Qwen3-Reranker-4B/8B vs jina-v3 were not found.
- bge-reranker-v2.5-gemma2-lightweight was not covered by fetched sources.
- RankZephyr / RankGPT listwise numbers were not fetched.

---

## 6. Text embedding models (MTEB/MMTEB leaders, retrieval-specific)

### Takeaway
Best open-weight retrieval embedder: Qwen3-Embedding (0.6B/4B/8B, Apache-2.0, 32k context, MRL, instruction-aware). MMTEB retrieval is 70.88 for 8B and 69.60 for 4B; MTEB-Eng-v2 retrieval is 69.44 for 8B and 68.46 for 4B, beating Gemini Embedding 001 (67.71 / 64.35). Hosted leaders in 2026 are Voyage-4 (Jan 2026, shared embedding space, open voyage-4-nano) and Gemini Embedding 2 (Mar 2026, multimodal, preview). OpenAI text-embedding-3-large is clearly behind on retrieval.

### Cited Findings
- **Qwen3-Embedding (June 2025, Apache-2.0) [VENDOR paper; MTEB-submitted]:**

  | Model | MMTEB retrieval | MTEB-Eng-v2 retrieval | CMTEB retrieval | MTEB-Code |
  |---|---|---|---|---|
  | Qwen3-Embedding-8B | 70.88 | 69.44 | 78.21 | 80.68 |
  | Qwen3-Embedding-4B | 69.60 | 68.46 | — | 80.06 |
  | Qwen3-Embedding-0.6B | 64.64 | 61.83 | — | 75.41 |
  | Gemini Embedding (001) | 67.71 | 64.35 | — | 74.66 |
  | NV-Embed-v2 | 56.72 | 62.84 | — | — |
  | gte-Qwen2-7B | 60.08 | 58.09 | — | — |
  | text-embedding-3-large | 59.27 | — | — | 58.95 |
  | Cohere multilingual v3 | 59.16 | — | — | — |
  | multilingual-e5-large-instruct | 57.12 | 53.47 | — | — |
  | BGE-M3 | 54.60 | — | — | — |

  - Dimensions: 1024 / 2560 / 4096 (0.6B / 4B / 8B), all MRL. Context 32k. Instruction-aware: a task instruction is prepended to queries — [arXiv 2506.05176](https://arxiv.org/html/2506.05176v1)
- **Voyage-4 family (15 Jan 2026) [VENDOR]:**
  - Models: voyage-4-large (MoE, ~40% lower serving cost claimed), voyage-4, voyage-4-lite, and voyage-4-nano (open weights, Apache-2.0).
  - All share one embedding space, so you can embed documents with -large and queries with a smaller model.
  - MRL at 2048/1024/512/256; float, int8, uint8 and binary output.
  - On 29 RTEB datasets (nDCG@10), voyage-4-large beats Gemini Embedding 001 by 3.87%, Cohere Embed v4 by 8.20% and OpenAI v3-large by 14.05%. Qwen3 was not compared — [Voyage blog](https://blog.voyageai.com/2026/01/15/voyage-4/)
- **Gemini Embedding 2 (10 Mar 2026, public preview `gemini-embedding-2-preview`, API only) [VENDOR via press]:**
  - First natively multimodal Gemini embedder: text, image, video, audio and PDF in one space.
  - 3072 dims with MRL to 1536/768. Truncation barely matters (68.16 at 2048 → 67.99 at 768). 8k text context. $0.25/M tokens.
  - `task_type` RETRIEVAL_QUERY / RETRIEVAL_DOCUMENT.
  - The article's "MTEB English 68.32 lead" conflicts with Qwen3-8B's higher reported numbers, so treat it as unclear — [NYU Shanghai RITS](https://rits.shanghai.nyu.edu/ai/google-launches-gemini-embedding-2-its-first-multimodal-embedding-model/)
- **EmbeddingGemma (4 Sept 2025, 308M params) [VENDOR]:**
  - Described by its makers as the top multilingual text embedder under 500M on MTEB, but the numbers are shown in charts only.
  - 768 dims with MRL to 512/256/128; 2k context; 100+ languages.
  - Required prefixes: query `"task: search result | query: "`, document `"title: none | text: "` — [Hugging Face blog](https://huggingface.co/blog/embeddinggemma)
- **"EmbeddingGemma 2" (reported Oct 2026; unverified) [3rd-party]:**
  - Reported as 270M text-only to 740M full multimodal, 8k context, MRL.
  - Reported MMTEB mean 61.36 vs Qwen3-0.6B 64.33, and MTEB-Code 78.68.
  - No official model card or weights link was found, so treat it as unverified — [Regolo](https://regolo.ai/embeddinggemma-2-vs-qwen3-embedding-benchmarks.md)
- **Aggregator figures (early 2026) [secondary; versions often unstated]:**
  - Licences: NV-Embed-v2 is CC-BY-NC-4.0 (non-commercial); jina-embeddings-v3 is CC-BY-NC (commercial use via API); BGE-M3 is MIT; nomic-embed-text-v1.5 is Apache-2.0 with MRL down to 64.
  - Cohere embed-v4 is API/VPC with "MTEB 65.2"; text-embedding-3-large "64.6" at $0.13/M; voyage-3-large $0.06/M.
  - The source has internal inconsistencies — [PremAI](https://www.premai.io/blog/best-embedding-models-for-rag-2026-ranked-by-mteb-score-cost-and-self-hosting/)

### Inferences
- Primary self-hosted choice: Qwen3-Embedding-4B, or 8B if GPU budget allows. Truncate with MRL to 1024–2048 dims for storage. Always use a task instruction on queries and none on documents.
- 0.6B is a reasonable CPU/edge option but scores ~6–8 retrieval points lower.
- A hosted alternative or second opinion is voyage-4-large for documents with voyage-4-nano locally for queries, thanks to the shared space. This is an unusual property worth testing for the brain.
- Avoid NV-Embed-v2 (non-commercial licence) and jina-v3 weights (NC) for enterprise self-hosting.
- MTEB averages are not the target metric. Build an in-domain eval with Context Recall@10 per query class before choosing; the leaderboard spread at the top (~1–3 points) is smaller than domain effects.

### Gaps
- The live MTEB leaderboard (Oct 2026) was not fetched. Newer entries may now lead (e.g., NVIDIA llama-embed-nemotron, jina-embeddings-v4/v5, Snowflake Arctic Embed 2, Stella, Nomic v2).
- No verified retrieval-only scores for Cohere embed v4, voyage-4 on MTEB, or Gemini Embedding 2.

---

## 7. Known limits of embeddings (LIMIT, DeepMind, 2025 → ICLR 2026)

### Takeaway
Single-vector embeddings provably cannot represent every top-k combination of documents at a given dimension. On a deliberately simple combinatorial dataset, every SOTA embedder scores under 20 recall@100, while BM25 scores 93.6 and ColBERT 54.8. Multi-item / conjunctive queries are exactly where a single dense retriever breaks.

### Cited Findings
- **Theory:** the number of top-k subsets an embedding can realise is bounded by the sign-rank of the qrel matrix, so for any fixed d some relevance patterns are unrepresentable.
  - Free-embedding optimisation (the best case, optimising directly on test data) gives a "critical n" fit of y = −10.53 + 4.03d + 0.052d² + 0.0037d³.
  - Extrapolated limits for k=2: ~500k docs at d=512, ~1.7M at 768, ~4M at 1024, ~107M at 3072, ~250M at 4096 — [arXiv 2508.21038](https://arxiv.org/pdf/2508.21038v2); [ICLR 2026](https://iclr.cc/virtual/2026/poster/10007818)
- **LIMIT full results (R@2 / R@10 / R@100):**

  | Model | R@2 | R@10 | R@100 |
  |---|---|---|---|
  | Qwen3-Embed (4096) | 0.8 | 1.8 | 4.8 |
  | Gemini Embed (3072) | 1.6 | 3.5 | 10.0 |
  | E5-Mistral | 1.3 | 2.2 | 8.3 |
  | GritLM | 2.4 | 4.1 | 12.9 |
  | Promptriever | 3.0 | 6.8 | 18.9 |
  | Snowflake Arctic L | 0.4 | 0.8 | 3.3 |
  | GTE-ModernColBERT | 23.1 | 34.6 | 54.8 |
  | BM25 | 85.7 | 90.4 | 93.6 |

  - On LIMIT-small (46 docs), Qwen3-Embed scores R@10 52.3, and Gemini-2.5-Pro as a long-context reranker solves 100% of queries.
  - Fine-tuning on the LIMIT train split barely helps (R@100 11.2). Only training on the test split solves it, i.e. by overfitting — [arXiv 2508.21038](https://arxiv.org/pdf/2508.21038v2)

### Inferences
- Practical free-embedding limits are far above 100k at d≥1024. Real models, however, are far below their theoretical ceiling, which is why they fail at n=46 for some query types. The issue is the query type (conjunctions/combinations of attributes, "all items that satisfy X and Y"), not corpus size.
- Design implication: route multi-item / attribute-combination queries through BM25 + structured metadata filters + query decomposition (one sub-query per needed item, union the results), then cross-encoder or LLM reranking. Do not rely on one dense vector per query.
- This is the strongest evidence for a "retrieve per sub-need, then rerank the union" design for the reasoning-heavy query classes.

### Gaps
- No measurements of how often real enterprise queries fall into LIMIT-like combinatorial patterns.

---

## 8. Exact vs ANN search at 10k–100k items

### Takeaway
At 10k–100k vectors, exact (flat) search is cheap and removes ANN recall loss entirely. HNSW at typical settings loses a few percent of recall@10 (~96% in one large-scale measurement), which matters directly against a 90% end-to-end target.

### Cited Findings
- **One independent FAISS benchmark** (~20 GB of 384-dim vectors, 200 queries, recall@10 vs flat):

  | Index | Recall@10 | Time for 200 queries |
  |---|---|---|
  | Flat | 1.000 | 12.4 s |
  | HNSW (M=32, efC=40, efS=64) | 0.962 | 0.95 s |
  | HNSW+PQ | 0.902 | — |

  - Dataset sizes between 10k and 1M were not tested — [Datashot](https://datashot.substack.com/p/scaling-vector-search-flat-vs-hnsw)

### Inferences
- **Arithmetic** (not a cited benchmark): 100k × 1024-dim float32 = ~400 MB. A brute-force dot product is ~100M multiply-adds per query, typically single-digit to tens of milliseconds on CPU with BLAS and sub-millisecond on GPU. 100k × 4096 dims is ~1.6 GB, still feasible.
- Recommendation: use exact search (FAISS IndexFlatIP, pgvector with no index or `SET enable_indexscan=off`, Qdrant `exact=true`, or numpy/torch matmul) up to ~1M vectors. If HNSW is used, set ef_search ≥ 200 and measure recall against flat on your own data.
- Exact search also removes HNSW's weak handling of filtered queries and of deletes/updates, which matters for frequently changing content.

### Gaps
- No found 2025–26 controlled benchmark of HNSW recall at exactly 10k–100k with modern 1024–4096-dim embeddings. pgvector/Qdrant benchmark pages were found but not fetched.
- The impact of filtered HNSW queries on recall was not measured in fetched sources.
