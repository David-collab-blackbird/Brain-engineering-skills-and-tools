# Query Understanding for Retrieval (A) and Evaluation Methodology for Retrieval/Memory Systems (B)

Scope note: research done 2026-10-23. Numbers are reported with benchmark and conditions. Vendor or self-published claims are flagged. Pages that could not be fetched: deepeval.com contextual-recall docs, trulens.org RAG-triad docs, and the Brown/Cai/DasGupta 2001 paper on projecteuclid.org (bot-blocked). Some fetched arXiv pages had internal inconsistencies between text and tables; those are noted where they occur.

---

## A1. Query rewriting and expansion (HyDE, query2doc, multi-query/RAG-Fusion, step-back)

### Takeaway
LLM query expansion reliably helps weak or zero-shot retrievers (BM25, unsupervised dense) and long or unusual query formats. It often hurts strong retrievers and rerankers, ambiguous queries, and domains the LLM doesn't know. Multi-query/RRF increases candidate diversity but did not significantly improve top-k accuracy in the one controlled enterprise study found. These are conditional tools that should be gated per workload class and validated on the gold set, not default-on.

### Cited Findings
- **HyDE (Gao et al., 2022):** zero-shot Contriever on TREC DL19 nDCG@10 went from 44.5 to 61.3 and Recall@1k from 74.6 to 88.0. On DL20, nDCG@10 went from 42.1 to 57.9 and Recall@1k from 75.4 to 84.4. That is close to fine-tuned ContrieverFT (62.1 / 63.2 nDCG@10). On BEIR low-resource sets it improved over Contriever on every set (e.g., FiQA Recall@100 56.2 to 62.1; TREC-NEWS 42.3 to 50.9) but trailed fine-tuned ContrieverFT on FiQA and DBPedia, and trailed BM25 on TREC-COVID Recall@100 (41.4 vs 49.8) — [HyDE paper, arXiv 2212.10496](https://arxiv.org/pdf/2212.10496)
- **query2doc (Wang et al., 2023):** abstract claims a 3%–15% BM25 improvement on MS MARCO and TREC DL without fine-tuning. It also reports gains for dense retrievers in-domain and out-of-domain, with no numbers in the abstract — [query2doc, arXiv 2303.07678](https://arxiv.org/abs/2303.07678)
- **Main failure-mode study (Weller et al., EACL Findings 2024):** 11 expansion methods, 12 datasets, 24 retrievers. "Gains from expansion are negatively correlated with base retrieval performance": expansions help weaker models and generally hurt stronger ones. The exception is long-query shift (ArguAna, TREC Clinical Trials, Tip-of-the-Tongue), where expansion helps. In an error analysis of 30 failures, nearly all were expansions adding irrelevant or misleading terms that dilute the relevance signal. Recommendation: use expansion for weak models or format-shifted data, and avoid it for strong rerankers — [When do Generative Query and Document Expansions Fail?](https://ar5iv.labs.arxiv.org/html/2309.08541)
- **"LLM-based Query Expansion Fails for Unfamiliar and Ambiguous Queries" (arXiv 2505.12694, 2025):**
  - With BM25 on MS MARCO and Llama-8B, Q2D changes nDCG@10 by −1.13 when the LLM lacks knowledge versus +4.00 when it has it.
  - Ambiguity hurts badly. On TREC Web with BM25, Recall@100 falls by −13.90 (Q2D) and −17.39 (Q2E) for highly ambiguous queries. On AmbigDocs with dense retrievers, Q2D Recall@100 falls by −25.52 (Contriever) and −31.35 (E5-base-v2).
  - Dense retrievers on BioASQ lose up to ~11 nDCG@10 points.
  - Stronger baselines degrade more. On MS MARCO, Q2D lowers Contriever nDCG@10 by 8.24 while raising BM25 by 4.00 — [arXiv 2505.12694](https://arxiv.org/html/2505.12694v1)
- **Multi-query + RRF in an enterprise setting (Dell, arXiv 2603.02153, March 2026):** original query plus one LLM rewrite, fused with RRF, over hybrid BM25+dense with a FlashRank reranker, on N=115 RAGAS-synthetic support queries.
  - Top-3 gains ranged from +0.87 to +4.35 pp, and none was significant (McNemar exact test, BH-adjusted p ≥ 0.125). Hit@10 fell from 0.51 to 0.44–0.48.
  - Q1 and Q2 top-10 lists overlapped little (Jaccard 0.09–0.28), so the rewrite surfaced new candidates, but they were near-duplicates or conflicting.
  - Named failure modes: reranker saturation (extra candidates crowd out good ones), redundancy, and rewrite-anchored reranking dropping strong original matches (Top-1 fell to 7.8–15.7%). Latency rose (65.98 s vs 54.60 s average retrieval; the absolute baseline time is unexplained).
  - Small, synthetic, single-domain study — [arXiv 2603.02153](https://arxiv.org/pdf/2603.02153v1)
- **Step-back prompting (Zheng et al., DeepMind, 2023):** on TimeQA with PaLM-2L, RAG went from 57.4% to 68.7% with step-back + RAG (+11.3 pts), and Hard went from 46.8% to 62.3% (+15.5). The introduction reports +7% on MuSiQue, but the excerpt does not say whether that was with RAG — [Step-Back paper, arXiv 2310.06117](https://arxiv.org/html/2310.06117v2)
- **Reasoning-intensive queries (BRIGHT, ICLR 2025):** querying with LLM-generated reasoning (GPT-4, Llama-3-70B) improves average nDCG@10 by up to 12.2 points. BM25 benefits most. Baselines are low: BM25 14.5 and the best embedding model ~22.5 average nDCG@10.
  - An MS MARCO-trained MiniLM cross-encoder *hurt* (BM25 14.3 to 13.1 at k=10, to 8.3 at k=100).
  - GPT-4 LLM reranking helped (BM25 to 17.4; Google embedder 19.5 to 22.6 at k=100) — [BRIGHT, arXiv 2407.12883](https://arxiv.org/pdf/2407.12883)
- **Time-aware query expansion in memory retrieval (LongMemEval, ICLR 2025):** improves temporal-reasoning recall by about 6.8%, and by about 11.3% when a strong LLM does the expansion — [LongMemEval, arXiv 2410.10813](https://arxiv.org/html/2410.10813v2)

### Inferences
- For a brain whose requests are reasoning tasks ("equity is up, plan the next purchase"), the literal query is vocabulary-poor relative to the needed items (holdings, cash, targets, rules). BRIGHT-style reasoning expansion and step-back (asking "what information would one need?") are the best-evidenced rewrites for this shape. HyDE-style "fake answer" expansion is riskier when the LLM doesn't know the user's private facts: a personal corpus is by definition "unfamiliar" to the LLM, which is exactly the failure condition in 2505.12694.
- Safe pattern: always retrieve with the original query too, and fuse (RRF) rather than replace. Gate expansion per workload class using gold-set measurements. Watch reranker saturation when adding candidates.
- An MS MARCO-trained cross-encoder can actively harm reasoning queries (BRIGHT), so the reranker must be evaluated on the brain's own gold set, not assumed.

### Gaps
- No 2025–26 head-to-head study was found comparing HyDE vs query2doc vs multi-query vs step-back on one benchmark with set-level "all required items" recall.
- The original RAG-Fusion claims are blog-level; no rigorous benchmark numbers were found beyond the Dell study.

---

## A2. Query decomposition and multi-hop / iterative retrieval (IRCoT, Self-Ask, agentic loops)

### Takeaway
For multi-item and multi-hop needs, decomposition and iterative retrieval give the largest measured recall gains of any query-side technique (+9 to +21 points). They cost about 3–9× latency for iterative methods, and up to ~600× for an LLM decomposition call versus a pure vector lookup. Adaptive routing by query complexity recovers most of the gain at roughly half the cost, but complexity classifiers are inaccurate.

### Cited Findings
- **IRCoT (Trivedi et al., ACL 2023):** interleaving retrieval with chain-of-thought improves retrieval by up to 21 points and downstream QA by up to 15 points over one-step retrieve-and-read (GPT-3; HotpotQA, 2WikiMultihopQA, MuSiQue, IIRC). Gains also hold out of distribution and with Flan-T5-large — [IRCoT, arXiv 2212.10509](https://arxiv.org/abs/2212.10509v1)
- **Question decomposition + rerank (ACL SRW 2025, arXiv 2507.00355), MultiHop-RAG:** Hits@4 from 0.611 to 0.763, Hits@10 from 0.781 to 0.872, MRR@10 from 0.464 to 0.635.
  - Latency was 0.03 s/query for naive retrieval versus 18.9 s/query for QD+rerank (16.7 s is the LLM decomposition call).
  - Failure modes: the LLM produced the maximum 5 sub-queries 93–99% of the time regardless of how many evidence items were needed (near-zero correlation). QD adds noise on already-precise queries. Decomposition alone gives only marginal gains on HotpotQA, and supporting-fact F1 was slightly lower. Gains depend on a strong cross-encoder. Sub-queries are generated once and never adapted to evidence — [arXiv 2507.00355](https://arxiv.org/html/2507.00355v1)
- **Adaptive-RAG (NAACL 2024):** routes each query to no-retrieval, single-step, or multi-step (IRCoT) using a T5 complexity classifier.
  - With GPT-3.5: single-step F1 46.99 (time 1.00×), multi-step 50.87 (3.33×), Adaptive 50.91 (1.46×).
  - With FLAN-T5-XL: multi-step 48.85 F1 at 8.81× vs Adaptive 46.94 at 3.60×.
  - Absolute latency per route: 0.35 s / 3.08 s / 27.18 s.
  - Classifier accuracy was only 54.5% overall (66% for single and multi-step, 31% for no-retrieval) — [Adaptive-RAG, arXiv 2403.14403](https://arxiv.org/html/2403.14403v2)
- **Anthropic multi-agent research system (engineering blog, June 2025; vendor, internal eval):** Opus 4 lead with Sonnet 4 subagents beat single-agent Opus 4 by 90.2% on Anthropic's internal research eval. On BrowseComp, token usage explained 80% of performance variance, and tool calls plus model choice brought it to 95%. Multi-agent runs use about 15× the tokens of chat (agents about 4×). Lesson: agents start with overly long, specific queries, and the fix is short, broad queries first, then narrowing — [Anthropic Engineering](https://www.anthropic.com/engineering/multi-agent-research-system)

### Inferences
- The "plan next purchase" class is inherently multi-item, so set-level recall will likely need decomposition (a sub-query per required facet) or iterative retrieval. Single-shot retrieval will struggle to put *all* required items in top-k.
- Two cost controls are evidenced: (a) route by complexity, and (b) cap and adapt the number of sub-queries. Uncapped LLM decomposition over-generates. Because the complexity classifier is ~55% accurate, routing errors must be measured as their own metric in the eval harness.
- Anthropic's "token usage explains variance" finding implies that for reasoning-heavy classes, more retrieval budget buys recall. The eval harness should report a recall-vs-budget curve, not a single point.

### Gaps
- Exact numbers for Search-R1 / R1-Searcher (RL-trained search agents) versus IRCoT were not retrieved in this session.
- No source measured *set-level* "all items in top-k" recall for decomposition. All reported figures are Hits@k, MRR, or answer F1.

---

## A3. Routing and metadata filtering (self-query, intent classification, scoped retrieval)

### Takeaway
Explicit metadata filtering yields large retrieval gains on multi-source queries (~+15 pp Hits@10). LLM-inferred filters are about 80–92% accurate and fail in specific ways: hallucinated values outside the allow-list, and filters invented for queries that shouldn't have one. A front-end–declared scope is therefore strictly better than inferred scope when available. Inferred filters need allow-list validation and a fallback to unfiltered search.

### Cited Findings
- **Multi-Meta-RAG (arXiv 2406.13213), MultiHop-RAG, LLM-extracted source/date filters:**
  - bge-large Hits@10 0.749 → 0.891, Hits@4 0.666 → 0.767, MAP@10 0.269 → 0.329.
  - voyage-02 Hits@10 0.742 → 0.904, Hits@4 0.663 → 0.792.
  - Generation accuracy: GPT-4 0.56 → 0.606, PaLM 0.47 → 0.608.
  - The paper's text percentages don't match its own tables; the table values are used here — [Multi-Meta-RAG](https://arxiv.org/html/2406.13213v2)
- **Filter-inference accuracy ("Probe, Don't Prompt", arXiv 2607.03929, 2026), MultiHop-RAG, 2,556 queries:**
  - GPT-3.5 set-exact filter accuracy was 80.9% overall, versus 88.0% for a model-free substring baseline and 90.9% for a hidden-state probe.
  - On null queries (no filter should apply) accuracy was 0.0% (0/301): the LLM always extracted something.
  - Non-null queries scored 91.7%, comparison queries 98.2%.
  - Allow-list drift: 128 distinct source strings were produced, 79 of them not in the 49-source allow-list — [arXiv 2607.03929](https://arxiv.org/pdf/2607.03929)
- **Adaptive-RAG's complexity router** (a form of intent routing) was 54.5% accurate. Routing decisions are error-prone even when end metrics look good — [Adaptive-RAG](https://arxiv.org/html/2403.14403v2)
- **Tenant/ACL filtering as a hard pre-filter:** a vector store with a tenant prefilter showed 0.0 cross-tenant leakage. Leakage appeared only when graph expansion bypassed the filter (see B4) — [arXiv 2602.08668](https://arxiv.org/pdf/2602.08668v2)

### Inferences
- A declared context scope (e.g., finance/investments) should be applied as a hard or boosting filter. Inferred scope should be (1) constrained to an enumerated allow-list (structured output / enum), (2) allowed to return "none", and (3) used as a soft boost, or run alongside unfiltered retrieval and fused, so that a wrong filter cannot zero out recall.
- Cross-domain reasoning tasks (e.g., an investment purchase that depends on cash-flow facts from the "business" scope) argue for scope as a *prior* rather than an exclusive filter. Whether to filter or boost should be measured per class.
- Eval harness must score filter inference separately, including null-filter cases and out-of-allow-list values.

### Gaps
- No study was found that measures declared (UI-supplied) scope versus LLM-inferred scope on the same corpus.
- No 2025–26 accuracy numbers were found for LangChain/LlamaIndex self-query retrievers with modern models (GPT-4o/Claude-class). Only the GPT-3.5 data above.

---

## A4. Agentic retrieval vs single-shot pipelines

### Takeaway
Evidence from coding agents and 2026 memory work shows that a persistent tool-using agent with simple lexical tools (grep/find) can match or beat embedding RAG on structured, keyword-rich corpora. Results depend heavily on the harness. Practitioners report that semantic search still matters for large, unstructured, or non-text corpora. The recommended pattern is "retrievers as tools inside an agent loop," not either/or.

### Cited Findings
- **"Is Grep All You Need? How Agent Harnesses Reshape Agentic Search" (arXiv 2605.15184, May 2026):** on a 116-question LongMemEval sample, grep "generally yields higher accuracy than vector retrieval" across a custom harness and provider CLIs. Scores depend heavily on harness and tool-calling style even with identical data. A second experiment adds distractor history, but its results were not available in the excerpt; no exact numbers were obtained — [arXiv 2605.15184](https://arxiv.org/abs/2605.15184)
- **Augment Code SWE-bench agent (practitioner talk, jxnl.co, Sept 2025):** "grep and find were sufficient" to top SWE-bench Verified. Agent persistence compensated for simple tools, and better embeddings did not necessarily improve end-to-end results.
  - Stated limits of grep: large codebases, unstructured natural language (Slack, docs), third-party code, and non-text media.
  - Recommendation: expose embeddings as tools within the agent loop.
  - SWE-bench repos are small and keyword-distinctive, which favours grep. No head-to-head numbers were given — [jxnl.co](https://jxnl.co/writing/2025/09/11/why-grep-beat-embeddings-in-our-swe-bench-agent-lessons-from-augment/)
- **Anthropic multi-agent research (vendor):** +90.2% over single-agent on an internal eval, at roughly 15× chat tokens — [Anthropic Engineering](https://www.anthropic.com/engineering/multi-agent-research-system)
- **Embedding-only metrics are weak proxies for agent outcomes** (Augment, as above) — [jxnl.co](https://jxnl.co/writing/2025/09/11/why-grep-beat-embeddings-in-our-swe-bench-agent-lessons-from-augment/)

### Inferences
- A personal/enterprise brain mixes structured, keyword-rich data (tickers, account names, dates) with unstructured notes, images, and video. That points to hybrid: give the agent lexical search, semantic search, metadata or structured query, and temporal tools. Evaluate the agent loop end-to-end (did required items enter context?), not just the retriever's top-k.
- Because the harness strongly affects outcomes, the harness itself (tool descriptions, result formatting, truncation) is a tunable variable and must be versioned in the eval.

### Gaps
- No controlled study was found on a heterogeneous personal corpus (text + images + video at 10k+ items) comparing agentic versus single-shot retrieval with set-level recall.
- No exact accuracy deltas for grep versus vector in 2605.15184.

---

## A5. Personalised and contextual retrieval (user state, session context)

### Takeaway
Rewriting queries with conversation history and user profile, followed by fusion and reranking, gives large gains in personalised conversational search (TREC iKAT: +0.12–0.15 nDCG@10). The 2026 LOCOMO-CONV benchmark shows that memory retrieval fails mainly on *implicit* and *composed* needs, where the user doesn't explicitly ask. That is the reasoning-task shape this brain targets.

### Cited Findings
- **TREC iKAT (CFDA & CLIP, arXiv 2509.15588):** on iKAT-2024, SPLADE without rewrite scored nDCG@10 0.297. History-aware rewrites (CHIQ-AD, LLM4CS) reached ~0.322. Rewrite + RRF + rerank reached 0.4425 (+0.145), with MRR 0.488 → 0.663.
  - RRF-before-rerank (0.4425) beat rerank-before-RRF (0.4275).
  - A fine-tuned rewriter with a 512-token limit collapsed to 0.129 because it truncated history.
  - On iKAT-2023, gains were small (+0.03–0.04), and CHIQ-AD alone was below baseline — [arXiv 2509.15588](https://arxiv.org/html/2509.15588v1)
- **"When Users Don't Ask" (LOCOMO-CONV, arXiv 2609.03467, Sept 2026):** four query styles (dialog, implicit, counterfactual, composed), five memory systems.
  - Retrieval gaps concentrate on implicit and composed queries, which QA-style benchmarks miss.
  - Multi-facet query rewriting narrows the gap for raw-turn memory but not for abstractive or summarised memory.
  - "Silent grounding": memory can improve responses without surfacing the gold fact, so gold-fact scoring misses it. No recall numbers were available in the fetched summary — [arXiv 2609.03467](https://academy.dair.ai/papers/when-users-dont-ask-benchmarking-context-driven-memory-retrieval-in-conversation-2609.03467)
- **Anthropic Contextual Retrieval (Sept 2024, vendor, multi-domain internal eval):** prepending LLM-generated chunk context before embedding and indexing reduced top-20 retrieval failure (1 − recall@20) from 5.7% to 3.7% (−35%). Adding contextual BM25 brought it to 2.9% (−49%), and reranking to 1.9% (−67%). Domains: codebases, fiction, ArXiv, science papers; Gemini Text 004 embeddings — [Anthropic](https://anthropic.com/news/contextual-retrieval)
- **LongMemEval:** fact-augmented key expansion (index-side) improves recall@k by about 9.4% and QA by about 5.4%. Round-level storage beats session-level storage. Fact-level compression hurts overall but helps multi-session reasoning — [LongMemEval](https://arxiv.org/html/2410.10813v2)

### Inferences
- Session and user state (current holdings, active goals, recent turns) should be injected into the rewrite step. The LOCOMO-CONV finding suggests the brain should store raw items alongside abstractions, since rewriting doesn't rescue retrieval over abstractive-only memory.
- Index-side enrichment (contextual chunk headers, fact-augmented keys) complements query-side rewriting and has some of the cleanest measured gains.

### Gaps
- Official TREC iKAT 2025 overview results were not retrieved.
- No quantitative recall figures for LOCOMO-CONV.

---

## B1. Metrics for multi-item retrieval tasks

### Takeaway
Standard metrics (recall@k, nDCG, MRR, Hits@k) are per-item or first-hit. Multi-item reasoning tasks need a set-level, per-query binary metric: all required items in top-k ("complete recall" or "Context Recall@k = 1"). Report it alongside mean recall@k (partial credit) and nDCG for ranking quality. RAGAS's default context recall is claim-based against a reference *answer*, not item-based, so it is not the right primary metric for this standard.

### Cited Findings
- **RAGAS LLM-based context recall** = supported reference-answer claims ÷ total claims. It uses the reference answer as a proxy for reference contexts. **NonLLMContextRecall** = retrieved reference contexts ÷ total reference contexts, matched by string similarity — [RAGAS docs](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)
- **Anthropic's contextual-retrieval eval** used 1 − recall@20 ("failed retrieval rate") as its headline — [Anthropic](https://anthropic.com/news/contextual-retrieval)
- **Common ranking metrics:** MultiHop-RAG work reports Hits@4/Hits@10/MRR@10/MAP@10 — [Multi-Meta-RAG](https://arxiv.org/html/2406.13213v2); [QD paper](https://arxiv.org/html/2507.00355v1)
- **Leakage metrics designed as set-level per-query indicators:** RPR (share of queries with ≥1 unauthorized item) and Leakage@k. This is a model for "at least one / all" style metrics — [arXiv 2602.08668](https://arxiv.org/pdf/2602.08668v2)
- **Gold-fact metrics miss "silent grounding"** on implicit queries — [arXiv 2609.03467](https://academy.dair.ai/papers/when-users-dont-ask-benchmarking-context-driven-memory-retrieval-in-conversation-2609.03467)

### Inferences
- **Recommended primary metric:** CR@k_all(q) = 1 if every required item ∈ top-k (or ∈ final context for agentic loops), else 0. Average it per workload class. Its per-query binary nature makes binomial confidence intervals (B2) directly applicable.
- **Secondary metrics:** mean item recall@k (diagnoses near-misses), nDCG@k with graded relevance (required vs helpful), precision or context-noise@k (to detect saturation), and filter/route accuracy.
- Support "alternative sufficient sets" in gold labels (e.g., either of two statements proves the balance), or the metric will under-count.
- RAGAS NonLLMContextRecall or the ranx Recall metric compute mean item recall. CR@k_all is trivial to compute from qrels, either custom or by thresholding ranx per-query recall at 1.0.

### Gaps
- No published standard name or benchmark for the "all required items in top-k" metric was found. MultiHop-RAG Hits@k is per-item, not all-items.

---

## B2. Building gold sets: synthetic queries, human annotation, LLM-as-judge, sample size

### Takeaway
LLM judges agree well with humans on *system ranking* in aggregate (Kendall τ ≈ 0.89–0.94). Per-topic agreement is weaker (τ ≈ 0.55 for nDCG@20), and LLM judges are lenient, favour LLM-based rankers, and are gameable. Synthetic queries overestimate absolute effectiveness. Absolute ">=90%" claims therefore need human-verified gold labels on real or realistic queries. To show ≥90% with 95% confidence you need roughly 140–400 queries *per class*, depending on how far above 90% the true rate is.

### Cited Findings
- **TREC 2024 RAG Track (Upadhyay et al., arXiv 2411.08275):** UMBRELA (GPT-4o) versus fully manual judgments, 77 runs, 27 topics.
  - Run-level τ: nDCG@20 0.890, nDCG@100 0.944, Recall@100 0.929.
  - Per-topic τ: 0.553, 0.767, 0.829.
  - Human assessors were stricter. LLM-assisted human workflows did not raise correlation.
  - With one-third of the topics, τ fell to 0.768 ± 0.08 — [arXiv 2411.08275](https://arxiv.org/html/2411.08275v1)
- **Counter-evidence (Clarke & Dietz, arXiv 2412.17156):**
  - Circularity: when UMBRELA is also used as a reranker, τ falls to 0.63 for the top 60 systems and −0.40 for the top 5. Twelve systems scored >0.95 nDCG under UMBRELA but 0.68–0.72 under humans.
  - Manipulation: run uwc1, built to exploit the judge, ranked 5th by LLM versus 28th by humans.
  - Weak top-end discrimination: τ 0.51 for the top 20.
  - LLM judges show a "clear and substantial bias in favor of LLM-based rankers" (citing Balog et al. 2025) — [arXiv 2412.17156](https://arxiv.org/html/2412.17156v2)
- **Synthetic-data bias (arXiv 2506.10301, TREC DL 2023, 82 queries):**
  - LLM judgments average +0.28 higher than humans (Bland-Altman limits −2.1 to 1.62).
  - GPT-4 judging inflates NDCG by +0.207 and MAP by +0.069 (p<0.001).
  - Synthetic collections "may be easier and thus overestimate system effectiveness." Bias affects absolute scores more than relative system comparisons.
  - GPT-based systems get a significant MAP boost from GPT judges (+0.032, p=0.006) — [arXiv 2506.10301](https://arxiv.org/html/2506.10301v2)
- **ARES (NAACL 2024):** synthetic queries filtered so that each query retrieves its own source passage, DeBERTa judges, and prediction-powered inference (PPI) over a human-labelled set.
  - About 150 human labels is the minimum (unreliable below ~100–150); 150–300 is typical.
  - Context-relevance τ was 0.91 on real systems, 0.16 above RAGAS.
  - Replacing humans with GPT-4 labels lowered τ by 0.05–0.30.
  - Judges failed under large domain shift (τ 0.28–0.38) — [ARES, arXiv 2311.09476](https://arxiv.org/html/2311.09476v2)
- **Synthetic query style differs from real:** real queries are shorter and differ in question-word distribution — [arXiv 2506.10301](https://arxiv.org/html/2506.10301v2). ARES's filter (keep only queries whose source passage is top-1) biases the set toward *easy, lexically aligned* queries — [ARES](https://arxiv.org/html/2311.09476v2)
- **Small-sample start (Anthropic, vendor practice):** begin with about 20 real-usage queries, since early effect sizes are large. A single-call LLM judge with a 0–1 rubric score plus pass/fail was most consistent with human judgment — [Anthropic Engineering](https://www.anthropic.com/engineering/multi-agent-research-system)
- **Interval choice (Agresti & Coull, with Casella's comment, on Brown-Cai-DasGupta 2001):** the Wald interval is "seriously deficient" at any n. Wilson (score) performs "surprisingly well even for small n" and is preferred in practice. Clopper-Pearson is too conservative. Near 0 or 1, boundary-modified Wilson or Jeffreys intervals are recommended — [Agresti & Coull commentary](https://users.stat.ufl.edu/~aa/articles/agresti_coull_2001.pdf)
- **Wilson 95% intervals for a per-query binary metric** (my own calculation with the standard Wilson formula, z=1.96):
  - Observed 90%: n=100 → [82.6, 94.5]; n=200 → [85.1, 93.4]; n=400 → [86.7, 92.6]; n=1000 → [88.0, 91.7].
  - Observed 93%: n=200 → [88.6, 95.8]; n=400 → [90.1, 95.1].
  - Observed 95%: n=100 → [88.8, 97.9]; n=200 → [91.0, 97.3].
  - Minimum n per class for the Wilson lower bound to clear 90%: about 384 at observed 93%, about 139 at observed 95%, about 71 at observed 97% (computed; the formula is standard per the source above).

### Inferences
- **Gold-set protocol suggestion:**
  1. Seed each workload class with real or user-written queries.
  2. Generate synthetic variants with an LLM, but stratify by difficulty: paraphrase, implicit need, multi-item, temporal, and adversarial. Avoid ARES-style "must retrieve top-1" filtering, which removes hard cases.
  3. Have an LLM propose required-item sets, then have a human verify every required set (required items determine pass/fail, so they must be human-trusted).
  4. Use an LLM judge only for secondary graded relevance, calibrated against about 150+ human labels using PPI-style correction.
  5. Never use the same LLM as both reranker and judge (circularity).
- A ">=90% at 95% confidence" claim on n=100 per class requires observed ≥ about 96%. A realistic target is 200–400 queries per class, or report "observed X% [Wilson CI]" and treat 90% as the point-estimate standard with the CI shown.
- Paired comparisons between pipeline variants on the same queries should use McNemar's exact test (as Dell did), or ranx's paired t-test or Fisher randomization test, with multiple-comparison correction.

### Gaps
- No source quantified LLM-judge reliability specifically for "is this item *required* to answer this reasoning task" labels (as opposed to graded relevance).
- The Brown/Cai/DasGupta original could not be fetched (bot-blocked). Recommendations are taken from the Agresti & Coull commentary.

---

## B3. Tools and frameworks for a custom retrieval eval

### Takeaway
For a custom retrieval harness with human-verified qrels, the core should be IR-standard tooling: ranx (or trec_eval / pytrec_eval) for metrics, significance tests, and fusion. A thin custom layer adds the set-level CR@k_all metric and per-class Wilson CIs. RAGAS, DeepEval, and TruLens are useful for generation-side and LLM-judged metrics but rely on LLM judges or reference answers. ARES adds statistically grounded CIs via PPI. Tracing tools (Phoenix, Arize) are for observability, not ground truth.

### Cited Findings
- **ranx:** Hits, Hit Rate, Precision, Recall, F1, R-Precision, Bpref, RBP, MRR, MAP, DCG, NDCG. Statistical tests: paired t-test (default), Fisher randomization, Tukey HSD. About 25 fusion methods (RRF, CombSUM, CombMNZ, BordaFuse, and others) with normalization and fusion optimization. Numba-accelerated. Metrics "tested against TREC Eval for correctness." Speed claims have no benchmarks on the page — [ranx GitHub](https://github.com/AmenRa/ranx)
- **RAGAS** context recall: LLM claim-based (needs a reference answer) or non-LLM string-match against reference contexts — [RAGAS docs](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)
- **ARES:** fine-tuned DeBERTa judges plus PPI confidence intervals. Needs about 150+ human labels and a ~32 GB GPU for hours of fine-tuning. English only. Fails under large domain shift. Outperforms RAGAS on system-ranking τ — [ARES](https://arxiv.org/html/2311.09476v2)
- **Dell study** used RAGAS to *generate* its synthetic eval set and McNemar plus Benjamini-Hochberg for significance. An example of a lightweight, statistically disciplined harness — [arXiv 2603.02153](https://arxiv.org/pdf/2603.02153v1)
- **Leakage study harness:** 95% bootstrap CIs (10,000 resamples, fixed seed). A template for reproducible CIs on non-binomial metrics — [arXiv 2602.08668](https://arxiv.org/pdf/2602.08668v2)

### Inferences
- **Suggested stack for the builder:**
  - qrels and runs in TREC format (JSONL with query_id, class, required_item_ids[], alt_sets, helpful_item_ids[]).
  - ranx for standard metrics, comparison, and fusion experiments.
  - A ~50-line custom module for CR@k_all, per-class Wilson CIs, and McNemar.
  - Optionally RAGAS or DeepEval for answer faithfulness, and Phoenix for traces in agentic loops.
  - Version every run with config hash, model versions, and harness version.
- BEIR and MTEB harnesses are useful only for sanity-checking embedding models on public data. They don't measure the private corpus.

### Gaps
- DeepEval and TruLens docs were blocked during this session, so their exact metric definitions are not cited here. Both are known to provide LLM-judged contextual recall/precision/relevance (unverified in this session).
- No comparative study of RAGAS vs DeepEval vs TruLens judge reliability in 2025–26 was found.

---

## B4. Adversarial and security evaluation (tenant leakage, prompt injection via retrieved content)

### Takeaway
Leakage and injection are measurable with set-level per-query metrics. Pure vector retrieval with a tenant pre-filter leaked nothing in a 2026 study, but graph or hybrid expansion that bypasses the filter leaked on up to 95% of queries until per-hop authorization was added. Knowledge-poisoning attacks reach about 90% success with only 5 injected texts. Indirect prompt-injection success ranges from about 5% to 31% across LLMs, with more capable models more susceptible. These must be standing test classes in the harness.

### Cited Findings
- **Retrieval Pivot Attacks (arXiv 2602.08668, Feb 2026):**
  - Vector-only with tenant prefilter: RPR = 0.0.
  - Undefended hybrid vector→graph pipeline: RPR 0.95 (synthetic), 0.695 (Enron), 0.085 (SEC EDGAR). Mean 16–19 leaked items per query on synthetic data.
  - All leakage occurred at exactly 2 hops through shared entities, and arose organically without injected documents.
  - Per-hop authorization gave RPR 0.0 across all corpora and 7 attack types. It was robust to 5% metadata mislabeling and 10% forgery, with <1 ms median latency cost — [arXiv 2602.08668](https://arxiv.org/pdf/2602.08668v2)
- **PoisonedRAG (USENIX Security 2025):** about 90% attack success with 5 malicious texts per target question in a knowledge base of millions of texts. Existing defenses were found insufficient — [PoisonedRAG](https://arxiv.org/abs/2402.07867v2); [USENIX](https://www.usenix.org/conference/usenixsecurity25/presentation/zou)
- **BIPIA indirect prompt injection (Microsoft, arXiv 2312.14197):** 5 tasks, 250 attacker goals, 25 LLMs.
  - Attack success rate: GPT-4 0.310, GPT-3.5 0.262, average 0.118. More capable models were more vulnerable. End-of-content injections were most effective.
  - Black-box defenses (boundary markers plus explicit reminder) reduced GPT-4 ASR to 0.21–0.24.
  - White-box fine-tuning reduced ASR to about 0.005. Boundary awareness was the more important component — [BIPIA](https://arxiv.org/html/2312.14197v4)
- **LLM judges can be fooled** by prompt attacks embedded in content into judging irrelevant text relevant (Alaofi et al. 2024, as cited by Clarke & Dietz). Injected memory items could therefore corrupt LLM-judged evals too — [arXiv 2412.17156](https://arxiv.org/html/2412.17156v2)

### Inferences
- **Security test classes for the harness:**
  - (a) Cross-scope and cross-tenant leakage: RPR and Leakage@k must be 0, with a CI upper bound reported (with 0/n failures, the 95% upper bound is about 3/n by the rule of three; standard statistics).
  - (b) Poisoned-memory items: plant adversarial items and measure retrieval rank and answer flip rate.
  - (c) Injection-in-retrieved-content: measure ASR with the brain's real prompt template.
  - (d) Graph or link expansion hops must re-check ACLs at every hop.
- For a personal brain the "tenants" may be family members, business entities, or partners, so scope filters double as access controls and must be enforced in retrieval, not only in prompts.

### Gaps
- No 2025–26 benchmark numbers were found for injection ASR on frontier models (Claude 4.x / GPT-5 class). BIPIA figures are from older models.
- Embedding-inversion leakage risk for self-hosted vector stores was not researched in depth.

---

## B5. Memory-specific evaluation (stale facts, temporal reasoning, knowledge updates)

### Takeaway
LongMemEval (ICLR 2025) is the reference design. It has 500 human-curated questions across five abilities (information extraction, multi-session reasoning, temporal reasoning, knowledge updates, abstention), and commercial assistants and long-context LLMs lose about 30–60% accuracy on it. Vendor leaderboards report near-saturation on some categories, but their metrics are inconsistent and self-reported. A custom harness should copy LongMemEval's category structure and add stale-fact and supersession tests on the brain's own data.

### Cited Findings
- **LongMemEval (arXiv 2410.10813, ICLR 2025):** 500 curated questions, five abilities. Settings: S (~115k tokens per question) and M (500 sessions, ~1.5M tokens).
  - ChatGPT (GPT-4o) fell from 0.918 (offline reading) to 0.577. Coze fell to 0.330. GPT-4o long-context on S fell from 0.870 to 0.606.
  - Optimizations: round-level storage, fact-augmented key expansion (+9.4% recall@k, +5.4% QA), time-aware query expansion (+6.8% temporal recall, +11.3% with a strong LLM), and Chain-of-Note reading (up to +10 points) — [LongMemEval](https://arxiv.org/html/2410.10813v2)
- **Supermemory LongMemEval-S claims (vendor, self-reported):** gpt-4o answerer, knowledge update 100%, temporal 95%, multi-session 96%, versus Zep 83.3/62.4/57.9 and full-context gpt-4o 78.2/45.1/44.3.
  - With gpt-5 or gemini-3-pro as the answerer, the same system scores 87–90 (knowledge update) and 75–82 (other categories).
  - The "Recall@20" and "LLM-judge" tables contain identical numbers, an unexplained inconsistency. Baseline configurations are not described — [Supermemory research](https://supermemory.ai/research/longmembench.md)
- **Grep vs vector on LongMemEval:** grep generally beat vector retrieval on a 116-question sample, with strong harness dependence — [arXiv 2605.15184](https://arxiv.org/abs/2605.15184)
- **LOCOMO-CONV (2026)** extends memory evaluation to implicit, counterfactual, and composed in-dialog needs, and finds QA-style benchmarks miss these gaps — [arXiv 2609.03467](https://academy.dair.ai/papers/when-users-dont-ask-benchmarking-context-driven-memory-retrieval-in-conversation-2609.03467)

### Inferences
- **Memory-specific test classes to add to the gold set:**
  - (1) Knowledge update: the gold set includes the *latest* value, and the stale value counts as a "must-not-be-preferred" item (track a stale-above-current rate).
  - (2) Temporal: queries with relative time ("since last quarter"), scored on retrieving the correct time-sliced items.
  - (3) Abstention: the required set is empty, and the system should signal no evidence.
  - (4) Multi-session aggregation: the required set spans many items, which tests k sufficiency.
  - (5) Implicit or composed needs (LOCOMO-CONV style).
- Vendor LongMemEval numbers are not comparable across vendors (answer model, judge, and metric differ). The brain should report retrieval-level CR@k_all on LongMemEval-S as an external sanity check, plus its own private gold set.

### Gaps
- No quantitative knowledge-update-specific retrieval figures from the LongMemEval paper itself were obtained in the fetched content.
- No independent (non-vendor) 2026 LongMemEval leaderboard was found.
