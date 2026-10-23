# Frontier AI Memory and Retrieval Research Directions (2025–2026)

Scope note: this covers work beyond mainstream RAG (hybrid search, rerankers, contextual retrieval, ColPali, GraphRAG, Mem0/Zep/Letta, LongMemEval). Research date: 2026-10-23. Maturity labels: **IDEA** (blog/position only), **PAPER** (preprint/peer-reviewed, no usable code), **OPEN CODE** (paper plus runnable repo/model), **PRODUCTION** (shipped in a product or mainstream library). Evidence labels: **Strong** (multiple benchmarks, independent replication), **Moderate** (one paper, several benchmarks, reasonable baselines), **Weak** (single setting, self-reported vendor numbers, synthetic tasks, or contradicted). Every number is reported with its conditions. "Test in brain" items are my inferences, not sourced claims.

## Q0. Catalogue overview: which frontier directions matter for a >=90%-recall, multi-tenant, fast-changing brain?

### Takeaway
The directions with the most usable evidence for our standard are: (1) reasoning-aware retrieval (query expansion plus reasoning rerankers), (2) agentic and file-based memory controllers (coding agents over files, grep plus vector tools), (3) offline "sleep-time" consolidation of memory, and (4) corpus-specific evaluation and embedder adaptation. Parametric memory (memory in weights, test-time training, per-user LoRA, knowledge editing) is the boldest direction but stays research-grade. On factual updates, retrieval beats editing weights. Embedding inversion is now practical enough that stored vectors should be treated as equivalent to plaintext.

### Cited Findings
- Retrieval or in-context editing beats every weight-editing method under realistic, autoregressive evaluation; most weight-editing methods collapse toward zero after many sequential edits — [Benchmarking and Rethinking Knowledge Editing, arXiv 2505.18690](https://arxiv.org/pdf/2505.18690)
- Coding agents working over file-based trajectory stores scored highest on LongMemEval-V2 (AgentRunbook-C 72.5% avg; off-the-shelf Codex ~69%) vs best RAG ~48.5%, but took ~108–186 s/query vs ~26 s — [LongMemEval-V2, arXiv 2605.12493](https://arxiv.org/pdf/2605.12493)
- Single-vector embedders have a provable ceiling on which top-k sets they can return; on the LIMIT dataset BM25 gets 93.6 recall@100 vs 4.8–18.9 for 4096-d SOTA dense models — [Weller et al., Google DeepMind, arXiv 2508.21038](https://arxiv.org/pdf/2508.21038)
- Zero-shot embedding inversion recovered information judged to leak from 82–92% of Enron emails, across four encoders — [ZSInvert, arXiv 2504.00147](https://arxiv.org/html/2504.00147v1)

### Inferences
Quick reference catalogue. Detail and sources are in Q1 onward.

| # | Direction | Maturity | Evidence | Priority for brain |
|---|---|---|---|---|
| 1 | Neural test-time memory (Titans, ATLAS, Nested Learning/Hope, TTT-E2E) | PAPER (no official code for Titans/Hope) | Weak–Moderate; poor NIAH for TTT-E2E | Watch only |
| 2 | Memory layers and sparse memory finetuning (Meta), Engram (DeepSeek) | PAPER / OPEN CODE (Engram) | Moderate (at small scale) | Watch; long-run option for org-wide static knowledge |
| 3 | Latent memory LLMs (MemoryLLM/M+), Memory Decoder | OPEN CODE | Moderate; M+ loses to base model on LongBench | Low |
| 4 | Parametric RAG and per-user LoRA (PRAG, DyPRAG, Poly-PRAG, DistilledPRAG, Doc-to-LoRA, P2P) | OPEN CODE (partly) | Weak–Moderate, small corpora (300 docs) | Experiment only; partitioning risk |
| 5 | Knowledge editing for updates | OPEN CODE | Strong *negative* evidence under realistic settings | Do not use for updates |
| 6 | Long context, CAG, Cartridges, KV compression (KVzip), context rot | OPEN CODE / PRODUCTION (1M windows) | Strong that long context degrades; CAG wins only below ~50–85k tokens | Use as a tier for small hot partitions; not for 10k+ items |
| 7 | Recursive Language Models (RLM) | OPEN CODE (DSPy integration reported) | Moderate (single group, GPT-5) | High: test for aggregation tasks |
| 8 | Reasoning retrievers/rerankers (ReasonIR, Rank1, ReasonRank, DIVER, BGE-Reasoner, FIRST) | OPEN CODE | Strong (BRIGHT, multiple groups, reproduced baselines) | High |
| 9 | RL-trained search agents (Search-R1, ZeroSearch, R1-Searcher, DeepResearcher) | OPEN CODE | Moderate (Wikipedia QA benchmarks) | Medium; training cost |
| 10 | RL-trained memory managers (Memory-R1, MEM1, MemAgent, Mem-alpha) | OPEN CODE (most) | Moderate; tiny training sets (Memory-R1 152 QA pairs) | Medium–High for the write path |
| 11 | Generative retrieval / DSI | PAPER / production at Alibaba (RecSys) | Weak for dynamic document corpora | Low |
| 12 | LLM-based learned sparse (CSPLADE), MUVERA | OPEN CODE / PRODUCTION (MUVERA in Weaviate 1.31) | Moderate–Strong | Medium |
| 13 | Neuro-inspired memory (HippoRAG 2, EM-LLM, LightMem sleep-time, "LMs need sleep") | OPEN CODE / PAPER | Moderate | High (sleep-time consolidation) |
| 14 | Structured/ontology-first memory (LLM wiki, AutoSchemaKG, Hindsight, MemOS) | OPEN CODE / IDEA (LLM wiki) | Weak–Moderate; vendor self-reports | High (entity cards plus wiki layer) |
| 15 | Self-improving retrieval (CustomIR, Chroma generative benchmarking, GEPA, ACE, ReasoningBank, autoresearch loops) | OPEN CODE | Moderate; small gains from embedder fine-tuning (+1–2 R@10) | High (eval-driven loop) |
| 16 | Privacy: embedding inversion and RAG membership inference | OPEN CODE (attacks) | Strong for attacks; defenses weak to moderate | Mandatory design input |
| 17 | New benchmarks (BEAM, MemoryAgentBench, LongMemEval-V2, LIMIT) | OPEN CODE | — | Adopt for eval |

### Gaps
- No source found that tests any frontier method at the exact target (10k+ mixed-modality items, per-task-class recall@k >= 90%, hard tenant partitions). All transfer claims below are inferences.

## Q1. Memory in weights: test-time training and neural memory (Titans, ATLAS, Nested Learning/Hope, TTT-E2E)

### Takeaway
Google's line of neural long-term memory (Titans, then ATLAS, then Hope/Nested Learning) and TTT-E2E compress context into weights at inference time. Reported gains are on perplexity and BABILong-style long-context tasks. An independent reimplementation could not reproduce the strong claims, and TTT-E2E scores 6% on 128K needle-in-a-haystack (NIAH) vs 99% for full attention. Not a retrieval replacement for exact-recall enterprise memory.

### Cited Findings
- Titans uses an MLP memory updated at test time by a "surprise" signal (the gradient of prediction error), with momentum and adaptive weight decay for forgetting. MIRAS frames sequence models as associative memories, defined by four design choices: memory architecture, attentional bias, retention gate and memory algorithm. Variants: YAAD (Huber loss), MONETA (generalized norms), MEMORA (probability-map constraint). Titans is reported to beat all baselines, including GPT-4, on BABILong and to scale beyond 2M tokens, but the blog gives no exact figures and no code link (Google blog dated 4 Dec 2025) — [Google Research: Titans + MIRAS](https://www.research.google/blog/titans-miras-helping-ai-have-long-term-memory/)
- Titans paper was accepted at NeurIPS 2025 — [NeurIPS 2025 poster](https://nips.cc/virtual/2025/poster/119639)
- ATLAS (Behrouz et al., May 2025) optimizes memory over a window of current and past tokens rather than only the latest token. Proposes "DeepTransformers". The abstract claims "+80% accuracy" on BABILong at 10M context, metric definition unclear — [arXiv 2505.23735](https://arxiv.org/abs/2505.23735v1)
- Independent "Titans Revisited" reimplementation: memory helps vs attention-only variants. However, Titans trails BERT4Rec on recommendation (HR@10 0.2177 vs 0.2603) and MLM accuracy is slightly below baseline. Test-time learning with a frozen backbone plateaued after 50 epochs, then declined. The authors conclude memory updates alone are insufficient — [arXiv 2510.09551](https://arxiv.org/html/2510.09551v1)
- Nested Learning (NeurIPS 2025, blog 7 Nov 2025) treats architecture and optimizer as nested optimization problems with different update frequencies. Hope is a self-modifying Titans variant with "continuum memory system" (CMS) blocks that update at multiple frequencies. The blog claims lower perplexity than Titans/Samba/Transformer and better long-context NIAH than Titans/TTT/Mamba2, with no numbers in text and no code — [Google Research: Nested Learning](https://research.google/blog/introducing-nested-learning-a-new-ml-paradigm-for-continual-learning)
- TTT-E2E (Astera, Nvidia, Stanford, UC Berkeley, UCSD; coverage April 2026). 3B model, 8K sliding window, updates last quarter of MLP layers on 1K-token chunks at inference. Loss is 0.015 lower than full attention across 8K–128K. Time-to-first-token is constant (~25 ms per 1K tokens) vs 12 to 70 ms per 1K tokens for full attention. **NIAH at 128K: 6% vs 99% for full attention** — [The Batch on TTT-E2E](https://www.deeplearning.ai/the-batch/test-time-training-end-to-end-ttt-e2e-retrains-model-weights-to-handle-long-inputs); paper [arXiv 2512.23675](https://arxiv.org/abs/2512.23675v1)

### Inferences
- Maturity: PAPER (Titans, ATLAS, Hope have no official code as far as found; TTT-E2E has a paper). Evidence: Weak to Moderate, with headline claims not independently reproduced.
- Compressing context into weights is lossy, which suits "gist" and style. It is poor for exact recall of a specific invoice line or member record. TTT-E2E's 6% NIAH score is direct evidence. This conflicts with a "every required context item in top-k" standard.
- Test in brain: none for now. If an open Titans/Hope checkpoint appears, run it as a *reader* over long session transcripts on BEAM-1M ([arXiv 2510.27246](https://arxiv.org/html/2510.27246v1)) and compare with retrieval. Do not use it as the store of record.
- Partitioning risk (inference): memory living in shared weights cannot be access-partitioned per user without separate model state per tenant.

### Gaps
- No exact BABILong accuracy figures from primary Titans/ATLAS sources were retrieved (blog has charts only).
- No evidence found of Titans/Hope deployed in any Google product.

## Q2. Memory layers, sparse memory finetuning, and conditional memory (Meta, DeepSeek Engram)

### Takeaway
Product-key memory layers let a model learn new facts with very little forgetting, because only a few memory slots are updated (Meta, Oct 2025). DeepSeek's Engram (Jan 2026) adds hashed N-gram lookup memory as a sparsity axis alongside MoE, with knowledge and long-context gains at 27B. These are the most credible "memory in weights" results, but they are tools for model builders, not drop-in brain components.

### Cited Findings
- Sparse memory finetuning (Lin, Zettlemoyer, Yih, Oğuz et al., FAIR, Oct 2025) uses a 1.3B model with one FFN layer replaced by a 1M-slot memory (k=32). Only the top-t slots, ranked by TF-IDF against pretraining batches, are updated. After learning 1K TriviaQA facts, NaturalQuestions F1 drops **89% with full finetuning, 71% with LoRA, 11% with sparse memory finetuning**. Caveats: sparse memory finetuning used SGD while baselines used AdamW; tests were factual QA only; small scale — [arXiv 2510.15103](https://arxiv.org/html/2510.15103v1)
- A follow-up, "Improving Sparse Memory Finetuning", appeared (April 2026) — [arXiv 2604.05248](https://arxiv.org/pdf/2604.05248) (not read in detail)
- Engram ("Conditional Memory via Scalable Lookup", DeepSeek, Jan 2026) modernizes N-gram embeddings for O(1) deterministic lookup, with a U-shaped scaling law for allocating parameters between MoE and Engram. At 27B, iso-parameter and iso-FLOPs vs a MoE baseline: MMLU +3.4, CMMLU +4.0, BBH +5.0, ARC-C +3.7, HumanEval +3.0, MATH +2.4. Multi-Query NIAH rises from 84.2 to 97.0. Lookup tables can be prefetched from host DRAM with "negligible overhead" (not quantified) — [arXiv 2601.07372](https://arxiv.org/abs/2601.07372); code [github.com/deepseek-ai/Engram](https://github.com/deepseek-ai/Engram); secondary [Introl summary](https://introl.com/blog/deepseek-engram-conditional-memory-architecture-january-2026)

### Inferences
- Maturity: sparse memory finetuning is PAPER; Engram is OPEN CODE, an architecture needing pretraining. Evidence: Moderate.
- These are the best evidence that weights *can* absorb new facts without catastrophic forgetting. But they need models pretrained with memory layers, and none of the self-hostable frontier-class open models found uses them.
- Test in brain (speculative, stage 3+): for slow-changing, org-wide, non-sensitive knowledge (SOPs, product catalogue), fine-tune a memory-layer model on that corpus. Measure closed-book recall vs RAG on a held-out question set. Never put tenant-private data in shared weights.

### Gaps
- No evidence of memory-layer models above ~8B being openly released for finetuning. No numbers for update speed (facts per hour) or for deleting facts (unlearning), which matter for privacy and erasure requests.

## Q3. Latent and plug-in memory modules (MemoryLLM/M+, Memory Decoder)

### Takeaway
M+ extends latent memory retention from under 20k to over 160k tokens, but underperforms its own base model on LongBench. Memory Decoder is a small pretrained decoder that imitates a retriever for domain adaptation (−6.17 perplexity on average). It needs retraining when data changes. Neither suits fast-changing facts.

### Cited Findings
- M+ (ICML 2025; base model Llama-3.1-8B) adds a 150k-token long-term memory pool with a co-trained retriever and extends retention from under 20k to over 160k tokens at similar GPU memory (~21.2 GB peak; 18.0 GB offloaded). LongBench average at 16k: **32.78 vs 35.81 for plain Llama-3.1-8B**, with the largest losses on HotpotQA and MuSiQue — [arXiv 2502.00592](https://arxiv.org/html/2502.00592v2); code [github.com/wanqyu-ustc/MemoryLLM](https://github.com/wanqyu-ustc/MemoryLLM)
- Memory Decoder (NeurIPS 2025) is a small transformer decoder trained to mimic a non-parametric retriever, which plugs into any model with the same tokenizer. Average perplexity falls 6.17 points across biomedicine, finance and law on Qwen and Llama models. Updating the underlying data requires retraining — [HF papers 2508.09874](https://huggingface.co/papers/2508.09874)

### Inferences
- Maturity: OPEN CODE. Evidence: Moderate on narrow metrics (perplexity, retention curves). There is no evidence on task-level recall@k.
- Test in brain: low priority. Memory Decoder could be a cheap domain-tone adapter for a vertical such as a fitness/health glossary, but it is not a fact store.

### Gaps
- No M+ or Memory Decoder results on memory benchmarks such as LongMemEval or LoCoMo were found.

## Q4. Parametric RAG and per-user/per-document LoRA (PRAG, DyPRAG, Poly-PRAG, DistilledPRAG, Doc-to-LoRA, Profile-to-PEFT)

### Takeaway
Turning documents or user profiles into LoRA adapters, increasingly via hypernetworks in one forward pass, can match or beat in-context RAG on small QA benchmarks. It fails on cross-document questions, and has only been tested on ~300-document corpora. Hypernetwork-generated per-user adapters (P2P) are 33x faster than training one adapter per user and roughly tie with full-history prompting.

### Cited Findings
- Poly-PRAG (Nov 2025) uses shared latent LoRA experts plus a router. Average F1 on LLaMA3-8B: Poly-PRAG 42.68 vs standard RAG 31.23, PRAG 41.59, DyPRAG 37.16. Storage for 300 documents: PRAG/DyPRAG need 96 GB at 8B; Poly-PRAG needs 872 MB. The evidence is limited to 300 documents per task — [arXiv 2511.17044](https://arxiv.org/html/2511.17044v1)
- DistilledPRAG generates one LoRA from the top-3 documents with a LongT5 generator, trained on 289k synthetic QA pairs. Average F1 on LLaMA-8B: 36.1 vs standard RAG 33.8. **But on cross-document questions: RAG 34.6, DistilledPRAG 30.9, PRAG 11.8, DyPRAG 5.0.** PRAG needs +100 s of offline training per new document at 8B. A reconstruction attack achieved ROUGE-2 recall below 9%, which the authors read as a privacy benefit — [arXiv 2509.01088](https://arxiv.org/pdf/2509.01088v2)
- DyPRAG (hypernetwork translating documents to parameters at test time) appears as a NeurIPS 2026 entry — [arXiv 2503.23895](https://arxiv.org/pdf/2503.23895); [NeurIPS 2026 listing](https://neurips.cc/virtual/2026/165648)
- Sakana AI Doc-to-LoRA / Text-to-LoRA: a hypernetwork generates a LoRA under 50 MB from a document in a sub-second forward pass. It is claimed to extend recall "tens of thousands of tokens" beyond native context. No accuracy figures vs in-context were found on the page — [project page](https://pub.sakana.ai/doc-to-lora) via [community post](https://piefed.nullspace.lol/c/technology/p/153988/instant-llm-updates-with-doc-to-lora-and-text-to-lora); code [github.com/SakanaAI/Doc-to-LoRA](https://github.com/SakanaAI/Doc-to-LoRA)
- Profile-to-PEFT (P2P, Oct 2025) uses a hypernetwork that maps a user profile to LoRA weights. It takes 0.57 s per user vs 20.44 s for one-PEFT-per-user (OPPU), and training is amortized after ~1,450 users. Average classification accuracy: P2P 0.580, OPPU 0.568, full history 0.575, RAG 0.507. Not uniform: OPPU wins on LaMP-2N (0.781 vs 0.716) — [arXiv 2510.16282](https://arxiv.org/pdf/2510.16282)

### Inferences
- Maturity: OPEN CODE for PRAG-family and Doc-to-LoRA. Evidence: Weak to Moderate (small corpora, F1 on Wikipedia multi-hop QA).
- The cross-document failure is fatal for "every required item" multi-hop tasks. Parametric injection should at most *augment* retrieved text, never replace it.
- Partition fit (inference): per-tenant adapters are a natural fit for hard access partitions, because an adapter can be loaded only for that tenant. Hypernetwork-shared weights, however, are trained across tenants and could leak information between them. Treat the hypernetwork's training data as cross-tenant.
- Test in brain: on one partition (e.g. owner's personal notes, ~300 docs), compare (a) RAG top-k, (b) RAG plus Doc-to-LoRA adapter of the partition, on per-task-class answer accuracy, especially cross-document questions. Also test P2P-style user-style adapters for *preferences/tone* only.

### Gaps
- No PRAG results beyond ~300 docs. No results with images or video. No data on adapter staleness when documents change.

## Q5. Knowledge editing for fact updates

### Takeaway
Under realistic evaluation, parameter-editing methods (ROME, MEMIT, MEND and others) collapse under sequential edits. AlphaEdit is stable but generalizes poorly. A simple retrieval-based editor (SCR) beats all of them. For a brain where facts change often, update the store, not the weights.

### Cited Findings
- With autoregressive decoding (no teacher-forcing leakage), most parameter-modifying methods drop to near zero on ZsRE as edits accumulate. AlphaEdit stays stable but scores only 8.38 Locality and 8.56 Portability (Llama-3.1-8B). The retrieval-based SCR beats all parameter methods (ZsRE average 52.53 on Llama-2). The authors recommend in-context/retrieval editing for limited updates and retraining for bulk updates — [arXiv 2505.18690](https://arxiv.org/pdf/2505.18690)
- EtCon (Edit-then-Consolidate, Dec 2025) proposes a consolidation step after editing — [arXiv 2512.04753](https://arxiv.org/pdf/2512.04753) (not read in detail)
- MemoryAgentBench: on multi-hop "selective forgetting" (FactConsolidation-MH, newer facts overriding older ones), **all methods, including long-context and RAG agents, score at most 7%** — [arXiv 2507.05257](https://arxiv.org/html/2507.05257v2)

### Inferences
- Maturity: OPEN CODE (EasyEdit-style). Evidence: Strong *against* weight editing for our use case.
- The bigger frontier problem is *store-level* conflict resolution: even retrieval systems fail multi-hop updates (at most 7%). The brain needs explicit validity intervals, supersession links and "current value" materialized views per entity, not raw chunks.
- Test in brain: build a FactConsolidation-style suite from our own domains, e.g. "member X changed plan, then the plan price changed: what does X pay?". Track it as its own task class with its own >=90% target.

### Gaps
- No method found that solves multi-hop selective forgetting above ~7% on MemoryAgentBench as of the paper version read.

## Q6. Long context vs RAG in 2026: 1M windows, CAG, Cartridges, KV compression, context rot

### Takeaway
Million-token windows exist, but reliability falls steeply with length. Chroma's Context Rot study found degradation in all 18 models. On LongMemEval, focused prompts of ~300 tokens beat full prompts of ~113k for every model family. On MRCR v2 8-needle at 1M, the best model (Claude Opus 4.6) scores 76%, while most others score 25–37%. "Put it all in context" (CAG) wins only up to roughly 50–85k tokens. Cartridges (KV caches trained offline per corpus) and KVzip (query-agnostic KV eviction) are the interesting middle ground.

### Cited Findings
- Chroma Context Rot (14 July 2025; Hong, Troynikov, Huber) tested 18 LLMs. Performance degraded with input length in every experiment. Lower needle-question similarity degrades faster, and a single distractor reduces accuracy. Shuffled haystacks beat coherent ones across all 18 models. LongMemEval focused (~300 tokens) beat full (~113k tokens) for every model family — [Chroma research](https://www.trychroma.com/research/context-rot)
- NoLiMa (ICML 2025): when needles require non-literal (semantic) matching, 10 of 12 models drop below 50% of their short-context baseline at 32K. GPT-4o falls from 99.3% to 69.7% — [HF papers 2502.05167](https://huggingface.co/papers/2502.05167)
- MRCR v2 8-needle (survey dated 15 March 2026; secondary aggregator, scores vary by evaluator). At 1M: Claude Opus 4.6 76.0%, Sonnet 4.6 65.8%, GPT-5.4 36.6%, Gemini 3 Flash 32.6%, Gemini 3 Pro ~24.5%. At 256K: Opus 4.6 93.0%, GPT-5.2 70.0%. Cites an estimate that effective context is ~60–70% of nominal — [yage.ai long-context benchmark survey](https://yage.ai/share/long-context-benchmark-en-20260315.html)
- LaRA (ICML 2025; 2,326 cases, 11 LLMs) finds no silver bullet. At 32K, long context beats RAG by 2.4 points on average; at 128K, RAG beats long context by 3.68. Long context wins comparison tasks (+15 points), while RAG wins hallucination detection (+22 points at 128K) and is immune to position effects — [arXiv 2502.09977](https://arxiv.org/html/2502.09977v1)
- CAG ("Don't Do RAG") preloads the KV cache with Llama 3.1 8B. It beats the best RAG on BERTScore in 5 of 6 settings, but **loses on HotpotQA-Large (85k tokens, 64 docs)**: 0.7407 vs 0.7535 for sparse top-5. Generation is up to ~41x faster than in-context learning without a cache. The authors say it is impractical for significantly larger knowledge bases — [arXiv 2412.15605](https://arxiv.org/html/2412.15605v2)
- Cartridges (Hazy Research, June 2025; ICLR 2026) train a small KV cache offline per corpus via "self-study" (synthetic conversations plus context distillation). They match ICL quality with 38.6x less memory and up to 26.4x throughput. On LongHealth, a 0.96 GB cartridge scored 55.1%, above full in-context. On MTOB, a Llama-3.1-8B cartridge trained on a 484k-token textbook scored 36.1 ChRF vs 36.3 for Llama 4 Scout with the full textbook. Cartridges are composable without retraining. The cost is offline training — [Hazy Research blog](https://hazyresearch.stanford.edu/blog/2025-06-08-cartridges); [ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/4681359a7b1e94571598ad1adda35e6e-Abstract-Conference.html); code [github.com/HazyResearch/cartridges](https://github.com/HazyResearch/cartridges)
- KVzip (NeurIPS 2025 oral) evicts KV pairs scored by how much they help the LLM reconstruct the context. One compressed cache is reused across queries, giving 3–4x cache reduction and ~2x decode latency reduction with negligible loss up to 170K tokens (LLaMA3.1, Qwen2.5, Gemma3) — [NeurIPS 2025](https://papers.nips.cc/paper_files/paper/2025/hash/f4eaa4b8f2d08edb3f0af990d56134ea-Abstract-Conference.html)
- BEAM (ICLR 2026) uses 100 conversations of 100K–10M tokens with 2,000 questions. 1M-context models degrade as conversations lengthen. At 10M, models score ~0.10–0.13 vs ~0.19–0.27 for the LIGHT memory framework (episodic index plus working memory plus scratchpad) — [arXiv 2510.27246](https://arxiv.org/html/2510.27246v1)
- MemoryAgentBench: long-context agents lead on test-time learning and long-range understanding (Claude-3.7-Sonnet overall 49.6), while RAG leads on accurate retrieval among the cheaper models — [arXiv 2507.05257](https://arxiv.org/html/2507.05257v2)

### Inferences
- Maturity: 1M windows are PRODUCTION. CAG, Cartridges and KVzip are OPEN CODE (KVzip code not confirmed). Evidence: Strong that context rot is real. Moderate for Cartridges.
- At 10k–100k items, the total corpus is far beyond any reliable window (10k items x ~500 tokens = 5M tokens). "Just put it all in context" is not viable. Long context belongs as the *reader* over a retrieved, focused set, sized to stay inside the reliability zone (~<=128K for most models; ~256K only for top models).
- Test in brain: (1) Per partition, measure answer accuracy vs context size: 4K, 16K, 64K, 128K of retrieved items, ordered relevant-first. Find each task class's knee. (2) For small hot partitions under ~50k tokens (a user's profile plus active projects), test CAG/prefix caching vs RAG. (3) Speculative: train a Cartridge per stable partition (e.g. company SOP manual) and compare accuracy and cost against RAG over the same partition.

### Gaps
- Exact Gemini 3.x / GPT-5.x long-context numbers come from an aggregator and vary by evaluator. No official long-context benchmark at 10k-item multimodal scale.

## Q7. Recursive Language Models and programmatic context access

### Takeaway
RLMs (Zhang, Kraska, Khattab; Dec 2025) put the corpus in a REPL variable and let the model write code to slice it and recursively call sub-models on the slices. On BrowseComp-Plus with 1,000 documents, RLM(GPT-5) scored 91.3 vs 51.0 for CodeAct with BM25. This is strong evidence for dense aggregation tasks that top-k retrieval handles badly.

### Cited Findings
- RLM(GPT-5, depth=1): BrowseComp-Plus (1,000 docs) 91.3 vs 70.5 for a compaction agent and 51.0 for CodeAct with BM25. OOLONG-Pairs (quadratic aggregation): ~0.1 F1 for base GPT-5 vs 58.0 for RLM. The median RLM run is cheaper than the base model, but outlier runs are costly. RLM-Qwen3-8B, fine-tuned on 1,000 trajectories, improved a median ~28% (secondary explainer of [arXiv 2512.24601](https://hyper.ai/fr/papers/2512.24601)) — [Buteau explainer](https://www.antoinebuteau.com/long-context-needs-recursion-not-bigger-windows/)
- An RLM implementation in DSPy is referenced in community posts — [newsblur "RLMs in DSPy"](https://bernhardbock.newsblur.com/story/rlms-in-dspy/0:29439c) (not verified in detail)

### Inferences
- Maturity: OPEN CODE (per references). Evidence: Moderate (single group, mostly GPT-5).
- This targets a task class our standard misses: queries like "total spend across all suppliers in Q3" or "which members attended both classes". These need *all* matching items, not top-k. Top-k recall@k cannot reach 90% here by construction.
- Test in brain: define an "aggregation" task class. Compare (a) hybrid top-k, (b) structured SQL over extracted facts, (c) RLM over a filtered partition dump. Measure exact-set recall and cost per query.

### Gaps
- The primary paper was not read directly. Numbers come from a secondary explainer, so verify against arXiv 2512.24601 before relying on them.

## Q8. Reasoning retrievers and rerankers (BRIGHT progress, test-time compute for retrieval)

### Takeaway
On BRIGHT, a benchmark of reasoning-intensive retrieval, the best pipelines rose from ~20 nDCG@10 in 2024 to ~46.8 by late 2025. The gains come from stacked components: LLM query expansion, reasoning-trained retrievers, and reasoning listwise rerankers. A strong reasoning reranker over a weak first stage adds +14–16 points. A weak reranker can *hurt* a strong first stage (Qwen3-8B cut LeetCode by 17.7 points). Test-time "think longer" (budget forcing) did not help Rank1.

### Cited Findings
- ReasonIR-8B (Meta, April 2025) is trained on synthetic reasoning queries with hard negatives. BRIGHT nDCG@10 is 29.9 without a reranker and 36.9 with one. As a RAG retriever it adds +6.4% on MMLU and +22.6% on GPQA vs closed-book. Code, model and data are open — [HF papers 2504.20595](https://huggingface.co/papers/2504.20595); [github.com/facebookresearch/reasonir](https://github.com/facebookresearch/reasonir)
- Rank1 (COLM 2025) is distilled from 635k DeepSeek-R1 reasoning traces on MS MARCO, with 386k kept after filtering. BRIGHT: 7B 27.5, 32B 29.4 vs RankLLaMA ~13.9. NevIR (negation): 70.1 for 32B vs 31.6 for RankLLaMA-7B. Int4 quantization takes 32B from 65.5 GB to 19.3 GB with negligible loss and fits on a 24 GB GPU. **Budget forcing (more test-time thinking) did not improve results** — [arXiv 2502.18418](https://arxiv.org/html/2502.18418v1); [github.com/orionw/rank1](https://github.com/orionw/rank1)
- ReasonRank (Aug 2025) uses cold-start SFT, then GRPO with a multi-view reward (NDCG@10 + Recall@10 + RBO). Training used ~13K synthesized examples. BRIGHT reranking ReasonIR top-100: 7B 35.74, 32B 38.03, and 40.6 on the leaderboard. It is 2–2.7x faster than pointwise Rank1, because it produces one reasoning chain per window — [arXiv 2508.07050](https://arxiv.org/html/2508.07050v1); [github.com/8421BCD/ReasonRank](https://github.com/8421BCD/ReasonRank)
- DIVER (Ant Group; v5 April 2026) pipeline: document cleaning and rechunking, two-round LLM query expansion, fine-tuned Qwen3-Embedding-4B blended 50/50 with BM25, and pointwise plus listwise reranking. BRIGHT leaderboard (avg nDCG@10): Rank-R1-14B 20.5; GPT4 + Rank1-32B 29.4; ReasonIR + QwenRerank 36.9; ReasonRank 40.8; BGE-Reasoner 45.2; DIVER v2 45.8; **DIVER v3 46.8**. Retriever-only on original queries: ReasonIR 24.4 vs DIVER-Retriever v2 31.9 — [arXiv 2508.07995](https://arxiv.org/html/2508.07995v5)
- Reproducible baselines (Waterloo, SIGIR 2026). Reason-Embed-4B scores 36.9 vs 13.8 for generic BGE. gpt-oss-120b reranking lifts SPLADE-v3 from 17.5 to 33.4, but adds only +3.4 on Reason-Embed-4B. Qwen3-8B reranking *lowers* Reason-Embed-4B by 1.2 on average (−17.7 on LeetCode). Up to 38% of documents in some BRIGHT tasks are duplicates — [arXiv 2509.02558](https://alphaxiv.org/abs/2509.02558v2); [SIGIR 2026 PDF](https://cs.uwaterloo.ca/%7Ejimmylin/publications/Sharifymoghaddam_etal_SIGIR2026.pdf)
- FIRST listwise reranking ranks candidates from the logits of the first generated identifier. It is ~50% faster than full-sequence decoding, with BEIR average 54.3 vs RankZephyr 53.7 (Contriever top-100) — [arXiv 2406.15657](https://arxiv.org/pdf/2406.15657); [github.com/gangiswag/llm-reranker](https://github.com/gangiswag/llm-reranker)

### Inferences
- Maturity: OPEN CODE (all of the above); self-hostable at 4B–32B. Evidence: Strong (multiple independent groups, plus reproducible baselines).
- Our corpus queries are mostly *not* BRIGHT-style (StackExchange/theorem reasoning). Expect a small lift on lookup queries and a large one on inferential queries, e.g. "which of our contracts are exposed to the new award rate?"
- Test in brain: tag eval queries as "lookup" or "inferential". For inferential queries, A/B (a) current reranker vs (b) ReasonRank-7B or Rank1-7B-int4 over the top-50/100, plus (c) LLM query expansion. Add a gate: only route queries classified as reasoning-heavy to the slow reranker, since weak rerankers can harm strong first stages.

### Gaps
- No BRIGHT-style results on multimodal, personal or enterprise corpora. Latency per query for 32B reasoning rerankers on consumer GPUs is not reported in the sources read.

## Q9. RL-trained search agents (Search-R1, ZeroSearch, R1-Searcher, DeepResearcher)

### Takeaway
Outcome-reward RL teaches 3–7B models to interleave reasoning with search calls. Search-R1 improves average exact match (EM) ~42% relative over RAG on 7B. ZeroSearch shows a fine-tuned 7–14B LLM can *simulate* the search engine during training at near-zero API cost, matching or beating real-search training. The evidence is on Wikipedia QA, not private corpora.

### Cited Findings
- Search-R1 (COLM 2025) uses `<search>` tags, masks retrieved tokens out of the loss (masking raised 7B average EM from 0.343 to 0.431), and an exact-match reward. 7B base: average EM 0.431 vs RAG 0.304 (~42% relative). E5 retriever over the 2018 Wikipedia dump, top-3 passages — [arXiv 2503.09516](https://arxiv.org/pdf/2503.09516); [github.com/PeterGriffinJin/Search-R1](https://github.com/PeterGriffinJin/Search-R1)
- ZeroSearch (May 2025), average EM over 7 QA sets with Qwen-2.5-7B base: 40.93 vs Search-R1 39.51. Real Google-search RL cost ~$586.7 in API fees for 64k queries vs ~$35 in GPU for a 7B simulator. A 14B simulator (34.47) outperformed Google Search (32.81) — [arXiv 2505.04588](https://arxiv.org/pdf/2505.04588)
- Related: R1-Searcher [arXiv 2503.05592](https://arxiv.org/pdf/2503.05592); DeepResearcher, RL in real web environments [arXiv 2504.03160](https://arxiv.org/pdf/2504.03160); "Rethinking the Design of RL-Based Deep Research Agents" [arXiv 2510.15862](https://arxiv.org/pdf/2510.15862); SearchGym simulated environments (Jan 2026) [arXiv 2601.14615](https://arxiv.org/pdf/2601.14615) (not read in detail)

### Inferences
- Maturity: OPEN CODE. Evidence: Moderate (consistent gains across groups, but all on public QA).
- ZeroSearch's simulator idea transfers neatly to a private brain: generate realistic noisy search results from the brain's own index to RL-train a small local "librarian" model, with no live index needed during training.
- Test in brain (stage 3): fine-tune a 7B search agent with Search-R1 recipes on synthetic multi-hop questions over one non-sensitive partition. The reward is exact match against generated answers. Compare evidence recall and number of search calls against a prompted frontier model.

### Gaps
- No evidence of RL search agents trained on private enterprise corpora, or on per-tenant access-filtered indexes.

## Q10. RL-trained memory managers (Memory-R1, MEM1, MemAgent, Mem-alpha)

### Takeaway
RL can teach small models *what to write, update and delete*. Memory-R1, trained on only 152 QA pairs, beats Mem0 by ~37% relative LLM-judge on LoCoMo (8B backbone). MemAgent, trained at 32K, reads 3.5M tokens with under 5% loss. This is the most practical frontier for the brain's *write path*.

### Cited Findings
- Memory-R1 trains a Memory Manager (ADD/UPDATE/DELETE/NOOP) and an Answer Agent (memory distillation over 60 retrieved memories) with PPO/GRPO and an exact-match reward, from 152 QA pairs. LoCoMo with LLaMA-3.1-8B (F1 / BLEU-1 / LLM-judge): Mem0 30.41 / 22.22 / 45.68; Zep 22.60 / 15.05 / 42.80; Memory-R1-GRPO 45.02 / 37.51 / 62.74 — [arXiv 2508.19828](https://arxiv.org/html/2508.19828v4)
- MEM1 uses a constant-size internal state, consolidated each turn via RL. MEM1-7B vs Qwen2.5-14B-Instruct on 16-objective multi-hop QA: ~3.5x performance, 3.7x lower memory — [arXiv 2506.15841](https://arxiv.org/abs/2506.15841)
- MemAgent reads in chunks with an overwrite memory, trained with Multi-Conv DAPO. Trained on 32K text in an 8K window, it extrapolates to 3.5M tokens with under 5% loss. RL-MemAgent-14B keeps over 75% accuracy at 3.5M tokens and over 95% on RULER at 512K — [alphaxiv 2507.02259](https://www.alphaxiv.org/abs/2507.02259v1); code [github.com/BytedTsinghua-SIA/MemAgent](https://github.com/BytedTsinghua-SIA/MemAgent)
- Mem-alpha uses RL over core, episodic and semantic memory tools. Trained on up to 30k tokens, it generalizes to over 400k tokens (13x) — [HF papers 2509.25911](https://huggingface.co/papers/2509.25911); code [github.com/wangyu-ustc/Mem-alpha](https://github.com/wangyu-ustc/Mem-alpha)
- M3-Agent (ByteDance Seed) is a multimodal (video plus audio) agent with entity-centric episodic and semantic memory, trained with RL. It beats a Gemini-1.5-pro / GPT-4o prompting agent by +6.7% on M3-Bench-robot, +7.7% on M3-Bench-web and +5.3% on VideoMME-long — [HF papers 2508.09736](https://huggingface.co/papers/2508.09736); code [github.com/bytedance-seed/m3-agent](https://github.com/bytedance-seed/m3-agent)

### Inferences
- Maturity: OPEN CODE (MEM1 code not confirmed). Evidence: Moderate. The LoCoMo baselines are self-run, and absolute numbers are low relative to vendor claims.
- M3-Agent is the most relevant result found for *video memory with entity identity*, e.g. recognising the same person across gym videos. It is a template for multimodal entity cards.
- Test in brain: log every memory write decision as (input, existing memories, action). Build ~200 QA pairs per domain from real usage, then GRPO-train a 7–8B local Memory Manager. Compare against the prompted frontier model on update correctness (the FactConsolidation-style suite in Q5) and on downstream recall@k.

### Gaps
- No RL memory manager evaluated with multi-user access control or adversarial (poisoned) inputs.

## Q11. Generative retrieval / differentiable search index, learned sparse retrieval, multi-vector compression

### Takeaway
Generative retrieval works at web scale in e-commerce recommendation (Alibaba, 300M items, online A/B gains). For dynamic document corpora, numeric-docid models collapse on new documents. LLM-based learned sparse retrieval (CSPLADE-8B) matches dense LLM retrievers on BEIR with a 20x smaller index. MUVERA makes multi-vector search practical and ships in Weaviate. The LIMIT paper shows that single dense vectors provably cannot represent all top-k combinations, which argues for sparse and multi-vector paths in our hybrid.

### Cited Findings
- Generative retrieval over dynamic corpora (SIGIR 2025 replication): numeric-docid DSI-SE falls from 0.718 to 0.205 Hit@10 on new documents (NQ). Text-docid methods (SEAL 0.732, LTRGR 0.799) generalize better than BM25 (0.586) on NQ but not on MS-MARCO. SEAL needs 2.2 GB memory and 619 ms vs DPR's 980 MB and 152 ms — [arXiv 2504.17519](https://arxiv.org/html/2504.17519v1)
- Alibaba CRID (July 2026) uses semantic cluster IDs plus a business-rank suffix that updates daily without codebook retraining. On a 300M-item Taobao corpus it gains +3.72 points Hitrate@20 over the best generative retrieval baseline and over 8% vs embedding-based retrieval out-of-search. Online: +0.54% orders, +1.06% GMV — [arXiv 2607.11392](https://www.alphaxiv.org/abs/2607.11392)
- CSPLADE (April 2025) is SPLADE on LLaMA-3 8B with bidirectional attention. BEIR-13 average 55.3 vs RepLLaMA-2-7B 55.1 vs SPLADE-v3 51.7. Index 6.7 GB vs 135 GB for a dense flat index. Calibration-based quantization (GPTQ, AWQ) collapses retrieval to under 10 MRR@10 — [arXiv 2504.10816](https://arxiv.org/pdf/2504.10816v1)
- MUVERA (Google, blog June 2025; NeurIPS 2024) uses fixed-dimensional encodings for multi-vector search. On BEIR it shows ~10% higher recall and ~90% lower latency vs PLAID, and PQ compresses memory 32x — [Google Research blog](https://research.google/blog/muvera-making-multi-vector-retrieval-as-fast-as-single-vector-search/); code [google/graph-mining](https://github.com/google/graph-mining/tree/main/sketching/point_cloud)
- Weaviate 1.31+ ships MUVERA. On LoTTE (~110k objects) memory fell from ~12 GB to under 1 GB and import time from 20+ min to 3–6 min. Recall needs HNSW ef of 512 or more to exceed 80%, and ef=2048 to exceed 90% — [Weaviate blog](https://weaviate.io/blog/muvera)
- LIMIT (Google DeepMind, ICLR 2026), 50k docs, recall@100: BM25 93.6, GTE-ModernColBERT 54.8, Promptriever-8B 18.9, Gemini Embedding 10.0, Qwen3-Embedding 4.8. Best-case critical corpus size (vectors optimized on the test qrels): 512-d ~500k docs, 1024-d ~4M, 4096-d ~250M — [arXiv 2508.21038](https://arxiv.org/pdf/2508.21038)

### Inferences
- Maturity: generative retrieval is PAPER for documents (PRODUCTION only in RecSys). CSPLADE is OPEN CODE. MUVERA is PRODUCTION. Evidence: Strong for LIMIT and MUVERA.
- LIMIT matters most for "instruction-like" or combinatorial queries such as "documents mentioning both X and Y". Keep a lexical/sparse leg and a multi-vector leg. Never rely on dense-only retrieval for the 90% target.
- Watch for a MUVERA trap: reaching 90% recall needs high ef, so if used, use it as candidate generation and rescore with full multi-vector MaxSim.
- Test in brain: build a LIMIT-style synthetic test from our own entity attributes (e.g. "members who like X and Y"). Measure dense vs BM25 vs SPLADE vs ColBERT recall@k. Skip generative retrieval for documents.

### Gaps
- No evidence on generative retrieval with per-tenant access filtering. No public SPLADE-v3 BRIGHT number beyond 17.5 (Waterloo).

## Q12. Neuroscience-inspired memory: HippoRAG 2, episodic segmentation, sleep-like consolidation

### Takeaway
The measured results come from engineering analogues, not biology. HippoRAG 2 (PPR over a passage-plus-phrase graph) beats NV-Embed-v2 on multi-hop retrieval (recall@5 78.2 vs 73.4). EM-LLM segments context by surprise into events and beats NV-Embed RAG by ~30% on LongBench. LightMem's "sleep-time" offline consolidation matches or beats baselines while cutting online tokens by over 100x. Weight-level "sleep" is early synthetic-task work.

### Cited Findings
- HippoRAG 2 (ICML 2025) uses query-to-triple linking, LLM "recognition memory" filtering, and PPR over phrase plus passage nodes. With a Llama-3.3-70B reader, F1 vs NV-Embed-v2: MuSiQue 48.6 vs 45.7, 2Wiki 71.0 vs 61.5, NQ 63.3 vs 61.9. Average passage recall@5 78.2 vs 73.4 — [arXiv 2502.14802](https://arxiv.org/html/2502.14802v1); code [github.com/OSU-NLP-Group/HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG)
- MemoryAgentBench: HippoRAG-v2 scores 65.1 average on accurate retrieval vs GPT-4o-mini long-context 49.2, and 54.0 on single-hop selective forgetting — [arXiv 2507.05257](https://arxiv.org/html/2507.05257v2)
- EM-LLM (ICLR 2025) marks event boundaries by surprise (token negative log-likelihood) with graph-modularity refinement, then retrieves by similarity plus temporal contiguity. With LLaMA-3.1-8B it is ~30.5% better than NV-Embed-v2 RAG on LongBench and 11.5% on ∞-Bench. It gets 100% passkey accuracy at ~10M tokens, and its boundaries correlate with human event boundaries — [arXiv 2407.09450](https://arxiv.org/html/2407.09450v3); code [github.com/em-llm/EM-LLM-model](https://github.com/em-llm/EM-LLM-model)
- LightMem (ICLR 2026) follows the Atkinson-Shiffrin model: sensory pre-compression (LLMLingua-2) and topic segmentation, then topic-aware short-term summaries, then a sleep-time offline long-term update. LongMemEval with GPT-4o-mini: 68.64 vs Mem0 53.61. Online-only tokens fall up to 105.9x and API calls up to 159x — [arXiv 2510.18866](https://arxiv.org/pdf/2510.18866v4); code [github.com/zjunlp/LightMem](https://github.com/zjunlp/LightMem)
- Sleep-time compute (Letta/Berkeley, April 2025) has the model precompute inferences about a context before queries arrive. It needs ~5x less test-time compute for the same accuracy and gives up to +13 points on Stateful GSM-Symbolic and +18 on Stateful AIME. Amortized across related queries, cost per query falls 2.5x. Gains depend on how predictable queries are — [arXiv 2504.13171](https://arxiv.org/abs/2504.13171v1)
- "Do Language Models Need Sleep?" (CMU/UMD, June 2026 preprint) runs offline recurrent passes to consolidate KV into SSM fast weights before eviction. Results are synthetic only: Rule 110 rises from ~10% to over 30% exact accuracy with 3–4 loops; GSM-Infinite subgroup from 0.419 to 0.615 — [alphaxiv 2605.26099](https://www.alphaxiv.org/abs/2605.26099v3)

### Inferences
- Maturity: HippoRAG 2, EM-LLM and LightMem are OPEN CODE; sleep-time compute is in PRODUCTION at Letta (per Letta's framing; the product was not verified here); weight-level sleep is PAPER. Evidence: Moderate.
- The strongest pattern for the brain is **write cheaply online, consolidate offline**. Ingest raw events immediately (soft inserts). A nightly "sleep" job then merges duplicates, resolves supersessions, rebuilds entity cards, precomputes likely-question answers (sleep-time compute), and re-embeds.
- Test in brain: implement the nightly consolidation job. Measure, before and after, (a) recall@k per task class, (b) the update-correctness suite, (c) online token cost. Also test EM-style surprise or topic segmentation vs fixed chunking for long transcripts and video transcripts.

### Gaps
- No measured results found for forgetting-curve (Ebbinghaus-style) decay in LLM memory that improved benchmark recall. These appear in vendor systems without published ablations.

## Q13. Structured / ontology-first memory: LLM wiki, entity cards, schema induction, semantic layers

### Takeaway
A strong 2026 trend is LLM-maintained, human-readable knowledge: Karpathy's "LLM wiki" (raw sources compiled into a markdown wiki navigated by indexes), Anthropic's file-based memory tool, and coding agents over files topping LongMemEval-V2. Hindsight (entity- and time-aware graph with four parallel retrievers, RRF, and a cross-encoder) reports 91.4% on LongMemEval. AutoSchemaKG induces schemas at web scale. Evidence for the wiki approach is anecdotal at ~100 articles.

### Cited Findings
- Karpathy's LLM wiki (covered 3 April 2026): raw sources go into `raw/`, and the LLM compiles a markdown wiki with summaries, concept articles and backlinks, navigated by index files with no vector search, plus periodic LLM "lint" health checks. Karpathy reports this is sufficient at ~100 articles / ~400k words. He calls it a "hacky collection of scripts", and no benchmarks exist — [VentureBeat](https://venturebeat.com/data/karpathy-shares-llm-knowledge-base-architecture-that-bypasses-rag-with-an)
- Anthropic memory tool plus context editing (29 Sept 2025). The memory tool is a client-side, file-based memory directory. In internal agentic search evals, memory plus context editing gave +39% over baseline and context editing alone +29%. On a 100-turn web search eval, token use fell 84% — [Claude blog](https://claude.com/resources/articles/context-management)
- "Is Grep All You Need?" (May 2026), on a 116-question LongMemEval sample across a custom harness and Claude Code, Codex and Gemini CLI: grep generally beat vector retrieval, and the harness and tool-output format changed scores as much as the retrieval method — [arXiv 2605.15184](https://arxiv.org/abs/2605.15184)
- LongMemEval-V2: coding agents over files reach 69.9–74.9% vs RAG 42.8–58.6%, but are 4–7x slower — [arXiv 2605.12493](https://arxiv.org/pdf/2605.12493)
- Hindsight (Dec 2025) has four memory networks: world facts, experiences, opinions with confidence, and entity observations. TEMPR retrieval runs semantic, BM25, graph and temporal search in parallel, then RRF, then a cross-encoder. LongMemEval: 39.0% full-context vs 83.6% Hindsight with a 20B backbone, and 91.4% with a larger backbone. LoCoMo 89.61% — [arXiv 2512.12818](https://arxiv.org/html/2512.12818v1)
- MemOS (July 2025+) treats memory as an OS resource. MemCubes (plaintext, KV/activation or parametric payloads, with metadata for lifecycle, ACL, TTL and provenance) can migrate between types. Self-reported with GPT-4o-mini: LoCoMo LLM-judge 75.80 vs Mem0 64.57; LongMemEval 77.8 vs Mem0 66.4 — [arXiv 2507.03724](https://arxiv.org/pdf/2507.03724v4); code [github.com/MemTensor/MemOS](https://github.com/MemTensor/MemOS)
- AutoSchemaKG (ACL 2026) induces schema dynamically from 50M+ documents, building 900M+ nodes and 5.9B edges. Schema alignment with human schemas is reported as 92–95% (BERTScore recall). Paired with HippoRAG2, multi-hop results are mixed vs HippoRAG2 alone (MuSiQue EM 31.8 vs 37.2; HotpotQA F1 78.3 vs 75.5) — [arXiv 2505.23628](https://arxiv.org/pdf/2505.23628); code [github.com/HKUST-KnowComp/AutoSchemaKG](https://github.com/HKUST-KnowComp/AutoSchemaKG)
- Vendor leaderboard claims for 2026 (LongMemEval: Mem0 94.4%, ByteRover 92.8%; LoCoMo: Zep 94.7%, Mem0 92.5%) are almost all self-reported and not comparable across judges or models — [Mem0 benchmark roundup](https://mem0.ai/library/agent-memory/ai-memory-benchmarks-in-2026)

### Inferences
- Maturity: LLM wiki is IDEA / hobby code. The Anthropic memory tool is PRODUCTION. Hindsight, MemOS and AutoSchemaKG are OPEN CODE. Evidence: Moderate for file and coding-agent memory on LongMemEval-V2. Weak for vendor LongMemEval numbers.
- Convergent design (inference): three layers. (1) Immutable raw store (source of truth, ACL-tagged). (2) LLM-compiled "wiki" of entity cards and topic pages with provenance links, per partition, linted nightly. (3) Retrieval indexes (BM25, dense, multi-vector, graph) over *both* raw and compiled layers. The agent gets both search tools and grep/file tools.
- Test in brain: on one partition, compare (a) RAG over raw only, (b) RAG over raw plus compiled entity cards, (c) a coding agent over the markdown wiki with grep, on the per-task-class recall and latency table. Expect (b)/(c) to win on synthesis and current-state questions, and (a) to win on latency.

### Gaps
- No controlled study found of LLM-wiki drift and hallucination accumulation over months of autonomous edits. Hindsight's code link was not confirmed from the page read.

## Q14. Self-improving retrieval: synthetic queries, embedder fine-tuning, DSPy/GEPA, eval-driven loops

### Takeaway
Synthetic-query fine-tuning of embedders on a private corpus gives *modest* gains: CustomIR reports +1.1 to +2.1 R@10, enough for a 0.6B model to match 4–8B models. The bigger lever is corpus-specific evaluation: Chroma showed public MTEB rankings can reverse on production data. Prompt- and context-evolution optimizers (GEPA, ACE, ReasoningBank) and autonomous experiment loops (Karpathy's autoresearch) make closed-loop tuning against our own eval feasible.

### Cited Findings
- CustomIR (Oct 2025) uses GPT-4o synthetic queries with personas, BM25 hard negatives filtered by an LLM (BM25 false-negative rate was 19.7% on Slack and 31.7% on Enron), and masked InfoNCE. R@10 gains: Enron +1.6 (Qwen3-Embed-0.6B, 0.5504 to 0.5664); Slack +2.1. The adapted 0.6B model nearly matches the 4B/8B models — [arXiv 2510.21729](https://arxiv.org/pdf/2510.21729)
- Chroma Generative Benchmarking: an LLM filters documents (judge alignment 46% to 75.2%) and generates queries steered by real user examples. On W&B production data, jina-v3 trails text-embedding-3-large, reversing its MTEB lead. Naive query generation inflates metrics — [Chroma research](https://trychroma.com/research/generative-benchmarking); code [github.com/chroma-core/generative-benchmarking](https://github.com/chroma-core/generative-benchmarking)
- GEPA (July 2025) uses reflective prompt mutation with Pareto selection. It beats GRPO by 6% on average and up to 20%, with up to 35x fewer rollouts, and beats MIPROv2 by over 10%. GRPO still won on AIME-2025 (38.00 vs 32.00) — [alphaxiv 2507.19457](https://www.alphaxiv.org/abs/2507.19457v2); code [github.com/gepa-ai/gepa](https://github.com/gepa-ai/gepa)
- ACE (Agentic Context Engineering, ICLR 2026) uses a generator, reflector and curator with incremental delta updates to a "playbook", avoiding brevity bias and "context collapse". It reports +10.6% on agent benchmarks and +8.6% on finance, and matches the top AppWorld production agent with a smaller open model, without labels — [HF papers 2510.04618](https://huggingface.co/papers/2510.04618); code [github.com/ace-agent/ace](https://github.com/ace-agent/ace)
- ReasoningBank (ICLR 2026) distills reusable strategies from both successes and failures into retrievable memory. Memory-aware test-time scaling (MaTTS) amplifies the gains; the abstract gives no numbers — [ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/980ea04d23d1f6908964eba2a74afe45-Abstract-Conference.html)
- Karpathy autoresearch (March 2026): an agent edits code, runs a fixed short training job, and keeps or reverts the change based on the metric. About 700 experiments in two days yielded 20 improvements and an 11% reduction in training time. Shopify's CEO reported a 19% gain overnight (secondary source) — [noqta.tn summary](https://noqta.tn/en/blog/karpathy-autoresearch-autonomous-ai-experiments-loop-2026)

### Inferences
- Maturity: all OPEN CODE. Evidence: Moderate. Embedder fine-tuning gains are real but small; evaluation-first is the high-value part.
- Test in brain (high priority): (1) Build a generative benchmark per partition and task class, seeded with real user queries. (2) Run an autoresearch-style loop whose single metric is the per-task-class "all required items in top-k" rate. Knobs: chunking, fusion weights, k, reranker choice, query-rewrite prompts (optimized with GEPA). Keep or revert each change, with a held-out set to prevent overfitting. (3) Then fine-tune the embedder per corpus (CustomIR recipe) and accept it only if it lifts the target metric by at least 1 point.

### Gaps
- No public study found of feedback-driven index optimization from click or usage signals in personal/enterprise memory. DSPy's integration of GEPA was not confirmed from the sources fetched.

## Q15. Privacy frontier: embedding inversion and membership inference against RAG

### Takeaway
Stored embeddings leak text. Vec2Text recovered 92% of 32-token inputs exactly (GTR-base) and 89% of full names in clinical notes. Zero-shot attacks (ZSInvert, Zero2Text) now need no training pairs and work against OpenAI text-embedding-3. Gaussian noise does not defend without destroying retrieval. Newer learned defenses (Eguard; SPARSE, concept-aware DP) show promise. RAG membership inference (Interrogation Attack) needs only ~30 natural-looking queries and evades detection.

### Cited Findings
- Vec2Text (EMNLP 2023): 92% exact recovery of 32-token inputs from GTR-base, BLEU 97.3. MIMIC clinical notes: 89% of full names recovered. Noise at λ=0.01 cut reconstruction BLEU to ~13% of the original with ~2% retrieval loss (in that setting) — [ar5iv 2310.06816](https://ar5iv.labs.arxiv.org/html/2310.06816)
- ZSInvert (April 2025) is universal and zero-shot (adversarial decoding plus a correction model). Enron emails: LLM-judged leakage of 82–92% across Contriever, GTE, GTE-Qwen and GTR. Takes ~30–90 s per document on one A40. Gaussian noise only works at σ=0.1, which destroys retrieval utility — [arXiv 2504.00147](https://arxiv.org/html/2504.00147v1)
- Zero2Text (Feb 2026) is training-free and needs no leaked pairs. Against OpenAI text-embedding-3-large on MS MARCO it reaches ROUGE-L 26.08 vs 14.79 for ALGEN, with cosine 0.66. Local DP (LapMech/PurMech) at ε/d=0.25 reduces but does not stop the attack. Evaluated on 200 samples — [arXiv 2602.01757](https://arxiv.org/html/2602.01757)
- Eguard (AAAI-26, March 2026) uses mutual-information optimization plus keyword-antonym contrastive learning. It claims over 95% of tokens are protected from inversion while keeping downstream utility (no utility numbers on the abstract page) — [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/40876)
- SPARSE (concept-aware privacy, NTU): elliptical (Mahalanobis) noise on concept-specific dimensions. STS12 at ε=10: leakage falls from 60.09% to 19.31% with 65.27% utility, vs LapMech 22.34% leakage and 60.72% utility. Cuts Vec2Text leakage 92.78% at ε=5 — [arXiv 2602.07090](https://arxiv.org/pdf/2602.07090)
- Interrogation Attack, RAG membership inference (2025): natural document-specific questions infer whether a document is in the datastore with ~30 queries. TPR@1%FPR is 2x prior attacks. Detection rate is as low as 5% vs over 90% for prior attacks. Costs under $0.02 per document — [arXiv 2502.00306](https://arxiv.org/html/2502.00306v2)
- Additional MIA work: DCMI differential calibration [arXiv 2509.06026](https://arxiv.org/pdf/2509.06026); ensemble privacy defense [arXiv 2512.03100](https://arxiv.org/html/2512.03100v1) (not read in detail)

### Inferences
- Maturity: attacks are OPEN CODE and cheap. Defenses are PAPER. Evidence: Strong for attacks.
- Design rule (inference): treat embedding vectors and every derived index (sparse vectors, ColBERT token vectors, KV caches, Cartridges, LoRA adapters) as **plaintext-equivalent**. Encrypt at rest per tenant. Never share an index across partitions with metadata-only filtering for highly sensitive data (member health). Keep sensitive partitions on local, Australian-hosted embedders, so text never goes to an external embedding API.
- Membership inference means the *answers* leak membership too. Enforce ACL filters *before* retrieval (pre-filtering), so out-of-partition documents can never influence answers. Rate-limit and log cross-partition-looking query patterns.
- Test in brain: run ZSInvert/Vec2Text against a sample of our own stored vectors as a red-team test. Measure leakage on synthetic PII. Evaluate SPARSE/Eguard-style protection on the recall@k target, and accept it only if the per-task-class recall loss is at most 1 point.

### Gaps
- No inversion results found for multimodal embeddings (image/video CLIP or ColPali vectors). This needs testing, since the brain stores images and video.

## Q16. Other surprising late-2025/2026 findings: benchmarks, agentic memory evaluation, context engineering

### Takeaway
Evaluation itself moved on in 2025–26. BEAM (up to 10M tokens), MemoryAgentBench (four competencies including selective forgetting), LongMemEval-V2 (agent experience, 25M–115M-token haystacks) and LIMIT (embedding ceilings) expose failures hidden by LoCoMo and LongMemEval-S. Saturated vendor scores (90%+) on those older benchmarks should not be trusted as evidence for our standard.

### Cited Findings
- LongMemEval-V2 (UCLA, May 2026): 451 questions; Small (~25M tokens) and Medium (~115M tokens) haystacks; five abilities (static state recall, dynamic state tracking, workflow knowledge, environment gotchas, premise awareness). No memory scores ~1%; RAG 38–51%; coding agents 68.7–74.9% — [arXiv 2605.12493](https://arxiv.org/pdf/2605.12493)
- BEAM tests ten abilities, including new ones (contradiction resolution, event ordering, instruction following), on 100K–10M token conversations — [arXiv 2510.27246](https://arxiv.org/html/2510.27246v1); data [HF BEAM-10M](https://huggingface.co/datasets/Mohammadta/BEAM-10M)
- MemoryAgentBench: smaller chunks help accurate retrieval but hurt long-range understanding. Agentic memory quality depends on backbone (MIRIX overall 26.2 with GPT-4o-mini vs 37.7 with GPT-4.1-mini), while RAG agents barely gain from a stronger backbone — [arXiv 2507.05257](https://arxiv.org/html/2507.05257v2)
- 2026 benchmarks also include STATE-Bench (Microsoft; GPT-5.1 without memory ~30% on travel tasks), DolphinBench (Mem0) and Locomo-Plus (secondary listing, no verified results) — [Mem0 roundup](https://mem0.ai/library/agent-memory/ai-memory-benchmarks-in-2026)
- Grep vs vector depends heavily on the harness: tool-output presentation changes scores as much as the retrieval method — [arXiv 2605.15184](https://arxiv.org/abs/2605.15184)

### Inferences
- Adopt BEAM-1M, the MemoryAgentBench FactConsolidation suite, the LongMemEval-V2 design pattern and LIMIT-style tests as external sanity checks, alongside our own generative benchmark. Report per task class, never as an average.
- Harness effects (inference): freeze the reader model and prompt format when comparing retrieval variants, or differences will be confounded.

### Gaps
- No benchmark found that combines multi-tenant access control, multimodal items and frequent updates. We will likely have to build it. LongMemEval-V2's Insert/Query API is a usable template.
