# Internal Learning on Private Data for a Self-Hosted, Hard-Partitioned Brain (late 2026)

Evidence-strength tags used below: **[Strong]** = peer-reviewed and/or replicated across several papers, or official regulator text; **[Moderate]** = one peer-reviewed paper or several consistent preprints/engineering reports with numbers; **[Weak]** = a single preprint, vendor blog, or a claim without stated method. Nothing here is legal advice; the legal sections report what official sources and law-firm commentary say. Note: the shared web-search budget ran out near the end of this round, so a few items listed under Gaps could not be checked further.

## 1. Gains: which internal-learning methods measurably improve retrieval/extraction on a private corpus, and by how much

### Takeaway
Fine-tuning an embedder on synthetic queries generated from the corpus reliably helps, but the gain depends on how far the corpus is from the base model's training data. It ranges from about +26 R@10 points on a far-off domain (SEC filings) to +1–2 points on enterprise email/Slack, and to zero where the base model is already strong. The levers with the biggest and most consistent payoff are cheap ones: false-negative-aware hard-negative mining (about +4.5 nDCG) and distilling LLM relevance labels into a small cross-encoder, which matches the 7B teacher at roughly 1% of the latency. For small or low-data partitions, full fine-tuning can match or fall below the base model. Lightweight adapters are safer there.

### Cited Findings
**Synthetic-query embedder fine-tuning (GPL / InPars / Promptagator / CustomIR family)**
- **[Moderate] CustomIR (Oct 2025).** Method: GPT-4o synthetic queries using several personas, BM25 hard negatives cleaned by an LLM false-negative filter, and InfoNCE at temperature 0.07. Gains over the base model:
  - Enron, 10,077 docs: BGE-M3 +1.6 R@10 / +2.1 nDCG@10; Qwen3-Embed-Small +1.6 / +1.2.
  - Internal Slack, 1,678 docs: BGE-M3 +1.1 / +1.4; Qwen3-Embed-Small +2.1 / +2.7.
  - Qwen3-Embed-Small plus CustomIR comes within 1–2 points of the Large model.
  - The LLM judged 31.69% of BM25 "negatives" on Enron to be false negatives.
  - Using synthetic negatives alone gave mixed results; on Enron, R@100 fell below baseline (0.7764 vs 0.7950).
  - Evaluation used synthetic queries, not human-written ones.
  — [CustomIR, arXiv 2510.21729](https://arxiv.org/html/2510.21729v1)
- **[Moderate] Databricks (Feb 2025).** Recall@10 before → after fine-tuning:
  - gte-large (0.4B): FinanceBench 0.293 → 0.552 (+0.259); ManufactQA 0.821 → 0.873 (+0.052); Databricks DocsQA 0.849 → 0.884 (+0.035).
  - e5-mistral-7B: FinanceBench +0.191; ManufactQA +0.077; DocsQA **0 gain**.
  - Training data: 6k–14k synthetic queries from Llama-3-405B, filtered by a GPT-4o judge, with in-batch negatives only. Hard negatives were not tried.
  - On DocsQA, fine-tuning brought no end-to-end RAG gain, because retrieval was not the bottleneck there.
  — [Databricks blog](https://www.databricks.com/en/blog/improving-retrieval-and-rag-embedding-model-finetuning)
- **[Strong] GPL (NAACL 2022).**
  - Average across 6 BEIR datasets: +6.3 nDCG@10 over a zero-shot MS MARCO model (51.5 vs 45.2), and +2.7 over QGen. TSDAE+GPL reached 52.9.
  - **Corpus-size effect (Robust04):** 1K passages scored 37.6, *below* the zero-shot 39.0. 10K passages scored 41.4, 50K scored 42.5, and the full 528K scored 41.3. Gains level off beyond 50K passages.
  - Smaller corpora need more queries per passage: SciFact peaked near 50 queries per passage.
  - Training took about 9.6 hours on a V100 for 100K steps.
  - Caveat: these were 2021-era base models; modern embedders start much higher.
  — [GPL, arXiv 2112.07577](https://arxiv.org/pdf/2112.07577)
- **[Moderate] R-GPL (2025)** re-mines hard negatives with the model being adapted, every 30k steps. Average +1.3 nDCG@10 over GPL; better on 13 of 14 BEIR sets. Regressions on ArguAna (−1.9) and LoTTE Science (−0.5). Several gains of +0.3 or less were not significant. — [R-GPL, arXiv 2501.14434](https://arxiv.org/pdf/2501.14434)
- **[Strong] Promptagator (ICLR 2023).** Few-shot (8 examples) prompted query generation trains a 110M retriever to 47.8 average nDCG@10 on 11 BEIR sets, versus 45.5 zero-shot, ColBERTv2 46.2 and GTR-XXL (6B) 44.9.
  - Adding a 110M reranker raises this to 52.8.
  - Round-trip consistency filtering is worth +2.5, but it *hurt* the two smallest datasets (NFCorpus, SciFact), likely from overfitting.
  - On Climate-FEVER, few-shot fell below zero-shot (16.8 vs 21.4).
  — [Promptagator, arXiv 2209.11755](https://arxiv.org/pdf/2209.11755)
- **[Moderate] InPars-v2.** GPT-J generates queries (100k queries took about 30 h on an A100), monoT5-3B keeps the top 10k pairs, and monoT5-3B is then fine-tuned on them. BEIR average 0.545 vs 0.533 for monoT5-3B trained only on MS MARCO, i.e. **+0.012**. Adapting an already-strong reranker gives small gains. — [InPars-v2](https://ar5iv.labs.arxiv.org/html/2301.01820)

**Hard-negative mining**
- **[Moderate] NV-Retriever (2024).**
  - Naive top-k mined negatives contain 38.8% (NQ) to 47% (StackExchange) false negatives, as judged by Llama-3.1-70B, and the rate grows with corpus size.
  - "TopK-PercPos" (keep only negatives scoring below 95% of the positive's score) cuts false negatives by 50–57%. It raises average nDCG@10 from 0.5407 to 0.5856 on a QA subset, and from 51.44 to 60.55 across 15 MTEB retrieval sets (the two sets are not directly comparable).
  - Teacher choice matters: e5-mistral-7B gave 0.5810 vs 0.5002 for BM25.
  — [NV-Retriever, arXiv 2407.15831](https://arxiv.org/pdf/2407.15831)

**LLM-labelled relevance distilled into rerankers**
- **[Strong] Rank-DistiLLM (2024).**
  - monoELECTRA distilled from RankZephyr/RankGPT-4 listwise rankings is statistically indistinguishable from its teachers on TREC DL (two-stage: 0.720/0.711 vs RankZephyr 0.719/0.720 with a BM25 first stage).
  - Out of domain (TIREx), monoELECTRA-Large (330M) scores 0.434 vs RankZephyr-7B 0.437. Latency drops from about 25 s to about 300 ms per query.
  - About 10k training queries is enough, and gains peak at 50 passages per query.
  - **Hard negatives are essential:** distilling from BM25-sampled rankings gave only 0.644/0.622.
  - A pairwise loss (RankNet) works as well as listwise.
  — [Rank-DistiLLM, arXiv 2405.07920](https://arxiv.org/html/2405.07920v1)
- **[Moderate] Pinterest (2024).**
  - Llama-3-8B teacher reaches 0.602 accuracy on 5-level relevance, vs 0.503 for the baseline.
  - A student trained on 30M teacher-labelled pairs beats one trained on 0.3M human labels (0.548 vs 0.484 accuracy), and keeps improving as distilled data grows.
  - Online: +2.18% nDCG@20, and +0.7% (US) / +2.0% (non-US) search fulfilment.
  — [Pinterest, arXiv 2410.17152](https://arxiv.org/html/2410.17152v1)
- **[Moderate] Microsoft/Bing (Thomas et al.).** GPT-4 relevance labels agree with TREC assessors at κ = 0.60 with an "aspects" prompt, vs 0.38 without prompt features. Small prompt paraphrases change results materially, and simulating multiple judges *hurt* (κ = 0.22). The authors report LLMs beat every crowd-worker population they studied. — [Thomas et al., arXiv 2309.10621](https://arxiv.org/html/2309.10621v3)
- **[Weak] Dashworks (Nov 2023, vendor).** GPT-4-labelled about 85k (query, chunk) pairs for about $93. A cross-encoder trained on them raised MAP by 83% (no baseline given). Queries came from an internal question repository, not customer data. — [Dashworks blog](https://dashworks.ai/blog/how-we-improved-our-llm-ranker-accuracy-by-85-for-less-than-100)

**Lightweight adapters vs LoRA vs full fine-tuning**
- **[Moderate] Search-Adaptor (ACL 2024).** A small residual adapter on frozen embeddings:
  - Google embedding API: +0.0475 average nDCG@10 over 14 BEIR sets. OpenAI API: +0.0349.
  - GTE-Large: 0.5335 → 0.5604, while LoRA reached only 0.5232.
  - **Full fine-tuning of Sentence-T5 on small data scored the same as zero-shot (0.4151),** and on TREC-COVID fell from 0.599 to 0.418.
  — [Search-Adaptor, arXiv 2310.08750](https://arxiv.org/html/2310.08750v3); [ACL Anthology](https://aclanthology.org/2024.acl-long.661)
- **[Weak–Moderate] Chroma (May 2024).** A linear transform applied **only to query embeddings**, so document vectors are untouched and nothing is re-embedded. Trained on as few as about 1,500 labelled query-doc pairs with random negatives. Reports "up to 70%" nDCG gain on CQADupstack over all-MiniLM-L6-v2. It broke even at 20–35% of the training data. Synthetic positives gave no significant gain, and rerankers were unstable with little data. — [Chroma embedding adapters](https://www.trychroma.com/research/embedding-adapters)
- **[Moderate] Sentence-transformers PEFT.** A LoRA adapter on bert-base reached NanoBEIR nDCG@10 0.4705 vs 0.4728 for full fine-tuning. The adapter file is 9.44 MB (2.14% of the base model). API: `add_adapter` / `load_adapter` / `set_adapter` / `delete_adapter`. — [sentence-transformers PEFT README](https://raw.githubusercontent.com/UKPLab/sentence-transformers/master/examples/sentence_transformer/training/peft/README.md)
- **[Moderate] "LoRA Without Regret" (Thinking Machines, Sep 2025).** LoRA matches full fine-tuning for supervised fine-tuning on small-to-medium datasets. It falls behind only when the dataset exceeds adapter capacity. Apply it to all layers, including MLP; use a learning rate about 10× the full fine-tuning rate; it is less tolerant of large batches. — [Thinking Machines blog](https://www.thinkingmachines.ai/blog/lora/)

**Domain-adapted extractors (LLMs)**
- **[Moderate] LoRA Land (2024).** 310 LoRA fine-tunes of models up to 7B over 31 tasks:
  - 224 of 310 beat GPT-4. NER (CoNLL++) went 0.733 → 0.989 vs GPT-4 0.742.
  - GPT-4 still won on coding and MMLU.
  - Serving: 25 adapters on one A100 with p90 time-to-first-token of about 200 ms or less.
  — [LoRA Land, arXiv 2405.00732](https://arxiv.org/html/2405.00732v1)
- **[Weak–Moderate] EMRModel (2025).** A LoRA fine-tune of Qwen2.5-7B on 7,329 medical-dialogue records raised structured-record extraction F1 from 49.0% to 88.1%. It beat untuned DeepSeek-V3/R1 and Spark-medical-X1 (81.9%). — [EMRModel, arXiv 2504.16448](https://arxiv.org/pdf/2504.16448)

**Production precedent**
- **[Weak] Glean** builds a custom embedding model per customer:
  - Method: continued pre-training on company data, then training on title-body pairs, anchors, co-access, synthetic QA, and query-click pairs.
  - Claims about 20% search improvement after 6 months, with no baseline or method given.
  - Says lexical search plus recency handles 60–70% of enterprise queries.
  — [jxnl.co write-up of Glean talk](https://jxnl.co/writing/2025/09/11/why-glean-builds-custom-embedding-models-for-every-customer/)

### Inferences
- Expected gain for this brain: most partitions hold personal and small-business text, which modern embedders (BGE-M3, Qwen3-Embed) handle reasonably well. The realistic expectation is therefore **+1 to +3 R@10 from embedder fine-tuning** (CustomIR- and DocsQA-like), not FinanceBench-like jumps. Big gains are likely only for jargon-heavy or unusual partitions, such as construction specs or gym programming notation. This matches the prior round's finding that evaluation-first work is the bigger lever (frontier_research_directions.md, Q14).
- Partition size matters. GPL lost to zero-shot at 1K passages and Promptagator's filtering hurt the smallest sets. So partitions under about 5–10K items should default to **no training, or a query-side adapter**, not LoRA or full fine-tuning of the embedder.
- Highest expected value per GPU-hour:
  1. False-negative-filtered hard negatives (TopK-PercPos at 95%, or an LLM filter).
  2. An LLM-labelled cross-encoder reranker. This is also the component that can be trained on non-partition data; see Q8.
- Extraction is where fine-tuning gives the largest absolute jumps (+25–40 F1 points on narrow schemas). It is also a low-memorization task type; see Q4.
- Promotion gate: an adapter ships only if it beats the base model on that partition's *held-out, partly human-written* eval set by more than the noise margin. The CustomIR and Databricks numbers show gains of +1–2 points sit close to the noise floor.

### Gaps
- No 2025–26 study measures embedder fine-tuning gains on *personal or household* corpora (diaries, family admin, health logs). All corpora found are enterprise or public.
- No head-to-head, on the same private corpus, of query-side linear adapter vs LoRA vs full fine-tuning with modern (2025+) embedders.
- No measured results for multimodal (image/video) embedder fine-tuning on private data were found in this round.

## 2. Personal / per-user / per-tenant adaptation

### Takeaway
Per-user or per-tenant adapters are technically cheap to store and serve: adapters of about 10 MB, thousands per GPU with S-LoRA. Each adapter can be deleted on its own. The evidence that they *improve retrieval* comes from LLM personalization benchmarks (LaMP), not from retrieval over personal corpora. For retrieval, the best-evidenced per-partition technique is a query-side adapter on frozen document embeddings: about 1.5k pairs, no re-embedding, deleted by removing one file.

### Cited Findings
- **[Moderate] OPPU (One PEFT Per User, 2024).**
  - Each user gets a personal PEFT module on a shared base model. It is reported to significantly beat prompt-based personalization on all 7 LaMP tasks.
  - PEFT updates are typically under 1% of the base model's parameters.
  - Users "can own and use their LLMs individually" by plugging in their module.
  - Fine-tuning helps more than retrieval when the retrieved history is not highly relevant.
  — [OPPU, arXiv 2402.04401](https://arxiv.org/html/2402.04401v3)
- **[Moderate] Profile-to-PEFT (P2P, Oct 2025)**, from prior-round notes:
  - A hypernetwork turns a user profile into LoRA weights in 0.57 s per user, vs 20.44 s for OPPU.
  - Average accuracy: P2P 0.580, OPPU 0.568, full-history prompting 0.575, RAG 0.507.
  - The hypernetwork's training cost is amortized after about 1,450 users.
  — [P2P, arXiv 2510.16282](https://arxiv.org/pdf/2510.16282)
- **[Strong] S-LoRA (MLSys 2024)** serves thousands of LoRA adapters on one GPU, keeping them in host memory and paging them in per batch. Throughput is up to 4× vLLM's naive LoRA support and up to 30× HF PEFT. — [S-LoRA, arXiv 2311.03285](https://arxiv.org/html/2311.03285v3)
- **[Weak–Moderate] Query-side adaptation without re-embedding:** a linear query-only adapter trained from about 1,500 feedback pairs. Gains were smaller on held-out data, but it still beat the baseline. — [Chroma embedding adapters](https://www.trychroma.com/research/embedding-adapters). Search-Adaptor shows that adapters beat fine-tuning when labelled pairs are limited. — [Search-Adaptor](https://arxiv.org/html/2310.08750v3)
- **[Moderate] Risk specific to per-user models:** in user-inference attacks, users who contribute a large fraction of the fine-tuning data are the most exposed. Black-box attack AUROC reached 88% on Enron email. — [Kandpal et al., User Inference Attacks, arXiv 2310.09266](https://ar5iv.labs.arxiv.org/html/2310.09266)

### Inferences
- A per-user adapter holds 100% of that user's signal, so membership is trivially exposed to anyone who can query it. It is safe only if the adapter is loaded **exclusively** in that partition's request context, and stored as sensitive as the raw data (encrypted per partition).
- Most members will have tiny corpora (tens to hundreds of items). By the GPL and Promptagator small-corpus results, per-member *embedder* adapters will likely give negligible or negative gains. Per-member adaptation should be limited to (a) query-side linear adapters once real feedback exists, and (b) preference/format adapters for generation, not retrieval.
- Per-tenant adapters are the natural unit for the larger partitions: business (construction, cafe, gym ops), owner, household.

### Gaps
- No paper evaluates per-user *retrieval* adapters on personal corpora with recall metrics. LaMP measures generation and classification.
- No evidence on how many feedback pairs a *per-partition* query adapter needs when queries come from 1–10 people, rather than a public dataset.

## 3. Learning from usage (clicks, feedback, corrections) at small scale

### Takeaway
Learning-to-rank from clicks needs traffic this brain will not have: tens of thousands to millions of logged queries even in simulation. Explicit feedback in assistant/RAG settings is sparse, and even Glean calls it an open problem. The workable small-scale substitute is to log real queries and label them offline with an LLM judge. That turns a handful of users into thousands of training pairs, which can then train a query adapter or reranker.

### Cited Findings
- **[Moderate] Unifying online and counterfactual LTR (simulation, Oosterhuis & de Rijke).**
  - Even the best intervention-aware estimator took about 2·10⁴ queries to close the gap to online PDGD.
  - The policy-aware estimator had not converged after 10⁸ queries. COLTR never beat its starting policy.
  - With only 5 interventions, the intervention-aware estimator needed more than 20× the data needed with 50.
  — [arXiv 2012.04426](https://arxiv.org/pdf/2012.04426)
- **[Weak] Glean:** query-click pairs drive search learning. For the RAG assistant there are no direct document clicks; upvotes/downvotes are sparse and citation clicks are weak signals, described as "a pretty hard open question." — [jxnl.co write-up of Glean talk](https://jxnl.co/writing/2025/09/11/why-glean-builds-custom-embedding-models-for-every-customer/)
- **[Weak–Moderate]** About 1,500 query-doc pairs, which can come from application usage, are enough to train a useful query-side adapter. — [Chroma embedding adapters](https://www.trychroma.com/research/embedding-adapters)
- **[Moderate]** LLM judges are a credible label source: κ = 0.60 vs TREC assessors ([Thomas et al.](https://arxiv.org/html/2309.10621v3)). Teacher-labelled data beat human-only training at 100× scale ([Pinterest](https://arxiv.org/html/2410.17152v1)).
- **[Strong — regulator]** The OAIC checklist asks: "Can the model be updated if training data becomes inaccurate or out-of-date?" Corrections therefore have to propagate into trained artifacts (APP 10). — [OAIC generative-AI developer guidance](https://oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-developing-and-training-generative-ai-models)

### Inferences
- Treat user feedback (thumbs, "wrong item", corrections) as **seeds for an offline LLM-labelling loop**, not as online LTR signal:
  1. Log query → retrieved set → feedback.
  2. Nightly, a local LLM judge labels the top-50 for each logged query.
  3. Retrain the partition's query adapter or reranker, and gate it on the eval set.
- A correction ("this record is wrong / outdated") is a **data** event first. Fix the source item. Any artifact trained on the old version is then stale and must be retrained, which favours retrain-from-scratch schedules (Q5).
- Query logs are personal information, and in member partitions health information, so they stay within the partition.

### Gaps
- No empirical study was found on feedback learning for retrieval with fewer than about 20 users.
- No measured result was found for "learning from corrections" in RAG memory systems, beyond fixing the source item.

## 4. Risks: membership inference, training-data extraction, embedding inversion, cross-tenant leakage

### Takeaway
Fine-tuned models leak which data they were trained on:
- Membership-inference AUC of 0.78–0.98 is typical for fine-tuned LLMs, including LoRA fine-tunes. Publicly available base weights make the attack *easier*, because the base model serves as the attacker's reference.
- Generative tasks (summarization, dialogue) memorize about 20% of samples. Extractive and classification tasks memorize near 0%.
- Embedding vectors are invertible: 92% exact recovery of 32-token inputs, and 89% of names in clinical notes. Since 2025, attacks need little or no training data.

A model trained across partitions is therefore a cross-partition channel, the neural analogue of the IDF/LSA leak our experiments already found.

### Cited Findings
**Membership inference / extraction on fine-tuned LMs**
- **[Moderate] DP fine-tuning study (2025), GPT-2 / GPT-2-XL.** Without DP:
  - Membership-inference AUC exceeds 80% for both LoRA and full fine-tuning, with full fine-tuning reaching 97.8%.
  - Prefix-tuning and P-tuning sit around 60%.
  - Full fine-tuning and LoRA both reach maximum canary exposure.
  - The authors note this contradicts earlier claims that LoRA leaks least.
  — [Du et al., arXiv 2504.21036](https://arxiv.org/pdf/2504.21036)
- **[Moderate] LoRA-Leak (Jul 2025).** LoRA fine-tunes reach membership-inference AUC 0.775 "even under conservative fine-tuning settings." **Using the public pre-trained model as a reference increases leakage.** Of the four defences tested, only dropout and excluding certain layers from fine-tuning reduced risk while keeping utility. — [LoRA-Leak, arXiv 2507.18302](https://arxiv.org/abs/2507.18302v1)
- **[Moderate] LT-MIA (Apr 2026).** A learned attack (classifier under 500k parameters) reaches AUC 0.908 on held-out transformers, and TPR 0.375 at 1% FPR (vs 0.230 for the best baseline). It transfers to Mamba, RWKV and RecurrentGemma (AUC 0.94–0.97). The authors argue switching architecture won't help, and that DP protects but "substantially hurts utility." — [LT-MIA, arXiv 2604.03199](https://arxiv.org/html/2604.03199v1)
- **[Moderate] ICP-MIA (NDSS 2026):** a training-free black-box attack built on the "optimization gap." It beats prior black-box attacks, especially at low FPR. — [arXiv 2512.16292](https://arxiv.org/abs/2512.16292v2)
- **[Moderate] User inference (EMNLP 2024).** Attack AUROC for "was this *person's* data used" on GPT-Neo-125M: Enron 88%, CC News 66%, Reddit 56%. Outlier users and heavy contributors are the most exposed. Example-level DP, deduplication and contribution limits give only partial mitigation. — [arXiv 2310.09266](https://ar5iv.labs.arxiv.org/html/2310.09266); [EMNLP 2024](https://preview.aclanthology.org/setup/2024.emnlp-main.1014)
- **[Moderate] Memorization by task type:**
  - Summarization 20.7% and medical dialogue 19.6%; extractive QA 0.1%; translation and sentiment 0%.
  - Memorization rises with model size and epochs for generative tasks (summarization: 14% at 1 epoch, 22% at 10).
  - Greedy decoding memorizes the most.
  — [Exploring Memorization in Fine-tuned LMs, arXiv 2310.06714](https://arxiv.org/html/2310.06714v2)
- **[Weak] Repeated sensitive canaries (Aug 2025):**
  - Extraction rises from 0–5% before fine-tuning to 60–72% after fine-tuning with repeated sensitive data.
  - Mitigations: deduplication −70% leakage; DP −85% at 95.2% utility; content filtering −75%; combined to 0% on these canaries only.
  — [arXiv 2508.14062](https://arxiv.org/html/2508.14062v1)
- **[Moderate] PII leakage (Lukas et al., IEEE S&P 2023):** sentence-level DP still leaked about 3% of PII sequences, and scrubbing reduces but does not prevent leakage. Domains tested included health care and email. — [arXiv 2302.00539](https://arxiv.org/abs/2302.00539v1)
- **[Weak–Moderate]** A diffusion-LM membership attack (SAMA) reaches average AUC 0.81 and TPR 0.16 at 1% FPR, showing attacks keep pace with new architectures. — [arXiv 2601.20125](https://arxiv.org/html/2601.20125)

**Contrastive encoders (embedders)**
- **[Moderate] ASIA CCS 2025 (images only):** "An encoder model having a higher utility usually leads to higher privacy leakage risks." Membership-attack accuracy rose from 0.500 (MoCo-v1) to 0.747 (MoCo-v3) as k-NN utility rose. Text was not tested. — [arXiv 2506.05743](https://arxiv.org/html/2506.05743v1)

**Embedding inversion (applies to the vectors of any embedder, fine-tuned or not)**
- **[Strong] Vec2Text (EMNLP 2023):**
  - 92.0% exact recovery of 32-token inputs (GTR-base), and 60.9% from OpenAI ada-002.
  - On MIMIC-III clinical notes: 89.2% of full names recovered, 26% of notes recovered exactly.
  - Gaussian noise at λ = 0.01 cut reconstruction BLEU to about 13% of the original while costing about 2% nDCG. Coarse information such as clinical area may still leak.
  — [arXiv 2310.06816](https://arxiv.org/pdf/2310.06816)
- **[Moderate] ALGEN (Feb 2025):** a one-step linear alignment from about 1k leaked (embedding, text) pairs gives Rouge-L about 41–46 across T5, ada-2 and OpenAI 3-large. The authors conclude that none of the tested defences (noise, shuffling, WET, DP) is effective. — [arXiv 2502.11308](https://arxiv.org/html/2502.11308v2)
- **[Moderate] Zero2Text (Feb 2026):** needs **no training pairs**, only limited API queries. Reaches Rouge-L 26.08 on OpenAI 3-large and 22.55 on Qwen3-Embedding-0.6B, and works on PubMed medical text. Local-DP noise defences were insufficient. — [arXiv 2602.01757](https://arxiv.org/html/2602.01757)

**Membership inference on the retrieval store (relevant to any learned retrieval component)**
- **[Moderate]** Asking a RAG system whether a sample "appears in the context" gives black-box AUC about 0.80 and gray-box about 0.90, and 0.99 on HealthCareMagic with Flan. A prompt-instruction defence helped some models only. — [Anderson et al., arXiv 2405.20446](https://arxiv.org/html/2405.20446v3)
- **[Weak–Moderate]** Mirabel flags queries whose top similarity score is an outlier, with detection recall of 0.99–1.00. — [arXiv 2505.22061](https://arxiv.org/html/2505.22061v1)
- **[Weak]** LoRAcle shows LoRA fine-tuning trajectories can be used as a membership oracle (image models). — [arXiv 2601.11207](https://arxiv.org/html/2601.11207v1)

**Regulator view on memorization**
- **[Strong — regulator]** OAIC names the risk of "attacks designed to make a model regurgitate its training dataset." It says personal information "includes inferred, incorrect or artificially generated information produced by AI models." — [OAIC generative-AI developer guidance](https://oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-developing-and-training-generative-ai-models)

### Inferences
- **Cross-tenant leakage quantified by analogy.** If one model is fine-tuned on partitions A and B, a user of B can run reference-based membership attacks against A's items. The public base checkpoint is the ideal reference (LoRA-Leak), and per-user inference AUROC reached 88% on email (Enron). This is the same class of leak as the cross-partition IDF/LSA statistics our experiments found, and stronger, because neural models memorize content rather than just term frequencies. **Rule: no weights, adapters, statistics, or negative-mining indexes may be fitted on data from more than one partition, unless every user of the artifact is entitled to every partition in its training set.**
- Synthetic queries generated from a partition's documents are *derived personal information*: OAIC counts AI-generated information as personal information. Synthetic data is not a way out of partition rules unless it is properly de-identified.
- Adapters and fine-tuned weights must be treated as **plaintext-equivalent** to their training data. This extends the prior round's rule for vectors and indexes: encrypt per partition, and load only within that partition's request context.
- Task choice matters. A fine-tuned *extractor* (span/field extraction) is a low-memorization task type (extractive QA 0.1%, classification ~0%). A fine-tuned *generator* (summaries, chat) on member data is high-memorization (about 20%). Avoid fine-tuning generators on health data.
- LoRA does not protect privacy by itself (AUC above 80% without DP). Dropout and layer exclusion are cheap partial mitigations (LoRA-Leak).

### Gaps
- **No 2024–26 paper measuring membership inference or training-data extraction on *fine-tuned text dense retrievers or bi-encoders* specifically** was found. Evidence is from image contrastive encoders and generative LMs, and was carried over by analogy.
- No paper directly quantifies leakage across tenants in a *mixed-tenant fine-tuned retriever or reranker*.
- No evidence on whether fine-tuning an embedder makes its vectors easier or harder to invert, compared with the base model.

## 5. Deletion / unlearning for fine-tuned models and adapters

### Takeaway
Approximate unlearning of LLMs is not reliable deletion:
- Metrics show forgetting while adversarial prompts still recover 73–84% of the "forgotten" knowledge.
- Minimal fine-tuning restores it.
- The OAIC itself says unlearning "does not yet appear to be a robust solution."

Exact deletion is achievable by design: per-partition or per-source adapters that can be dropped and retrained, SISA-style sharding, or SIFT-Masks-style merging. Australian law (APP 11.2) requires destroying or de-identifying personal information once it is no longer needed, including all copies. The 2026 exposure draft's right to erasure would cover only large platforms.

### Cited Findings
**Approximate unlearning fails adversarial tests**
- **[Moderate] "Unlearning Isn't Deletion" (May 2025):** models "can appear to forget while their original behavior is easily restored through minimal fine-tuning." Irreversible, non-catastrophic forgetting is especially hard to achieve. — [arXiv 2505.16831](https://arxiv.org/abs/2505.16831v1)
- **[Moderate] "Can LLMs Truly Forget?" (Aug 2026, UMass/Microsoft):** NPO, SimNPO and AltPO reach Forget Quality 0.919–0.999 on the clean benchmark. Adversarial attack success is still 72.8–84.3%, vs 87.5% for the model that never unlearned. Prompt-based unlearning collapses as the forget set grows. — [arXiv 2608.21606](https://www.alphaxiv.org/abs/2608.21606.md)
- **[Strong — regulator]** OAIC: "model unlearning does not yet appear to be a robust solution," and de-identified information is increasingly re-identifiable. — [OAIC blog, Oct 2024 / Jan 2025](https://www.oaic.gov.au/news/blog/can-personal-information-be-used-to-develop-or-train-a-generative-ai-model)

**Approximate methods for adapters and rankers**
- **[Moderate] LLMEraser:** influence-function edits to a LoRA adapter, about 31× faster than retraining (1.4×10³ s vs 5.4×10⁴ s). Utility is close to retraining (AUC 0.6319 vs 0.6357). It is **approximate, with no exact guarantee**. — [arXiv 2412.00383](https://arxiv.org/pdf/2412.00383)
- **[Weak–Moderate] Neural Machine UnRanking (CoCoL):** removes queries or documents from ColBERT and BERT-dot rankers while keeping retain-set performance near a retrained model. Empirical only, no formal guarantees, and relearning takes only 1–2 epochs. — [arXiv 2408.05330](https://arxiv.org/html/2408.05330v2)

**Exact-by-design deletion**
- **[Strong] SISA (IEEE S&P 2021):** shard and isolate training so a deletion retrains only one shard. Unlearning is 4.63× faster than full retraining on Purchase, 2.45× on SVHN and 1.36× on ImageNet (small accuracy loss). — [Machine Unlearning, arXiv 1912.03817](https://arxiv.org/abs/1912.03817)
- **[Moderate] SIFT-Masks (2025):** fine-tune one task vector per data source with a shared sign constraint, then merge. Unlearning a source = deterministic retrain of that source and subtraction, about 20 steps, up to 250× less compute than retraining. Scaled to 500 sources on 0.7–1.5B models. Requires fully deterministic training and about 1/32 of a model's storage per mask, and it sometimes falls short of centrally trained accuracy. — [arXiv 2504.04626](https://arxiv.org/html/2504.04626v1)
- **[Moderate]** Sentence-transformers supports `delete_adapter`, and adapters are about 2% of base-model size. — [sentence-transformers PEFT README](https://raw.githubusercontent.com/UKPLab/sentence-transformers/master/examples/sentence_transformer/training/peft/README.md)

**Australian legal context (what official sources say)**
- **[Strong — regulator] APP 11.2:** take reasonable steps to destroy or de-identify personal information once it is no longer needed for any permitted purpose (para 11.29).
  - "Destroyed when it can no longer be retrieved" (11.49).
  - Covers "all copies," including backups (11.39).
  - "Beyond use" is allowed only in very limited cases, with four conditions (11.52–11.53).
  - The guidelines do not discuss derived data or trained models.
  — [OAIC APP Guidelines ch. 11](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-11-app-11-security-of-personal-information)
- **[Strong — regulator]** The OAIC AI guidance says APPs 12 and 13 (access and correction) "are also relevant… but are outside the scope of this guidance." It recommends designing systems to support access and correction records, and considering the consequences of withdrawn consent. — [OAIC generative-AI developer guidance](https://oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-developing-and-training-generative-ai-models)
- **[Moderate] Tranche 2 exposure draft, Privacy Amendment (Personal Data Protection) Bill 2026 (31 Aug 2026; submissions closed 18 Sep 2026; not law):**
  - A right to erasure for **large platforms only**: revenue above $500M or more than 2.5M monthly users.
  - A "fair and reasonable" test that would replace APPs 3, 4 and 6.
  - Stricter consent: voluntary, informed, current, specific and unambiguous.
  - De-identification is "context-dependent and not a permanent state."
  - Sources: [Lander & Rogers](https://landers.com.au/legal-insights-news/australias-next-wave-of-privacy-reform-key-changes-proposed-in-the-privacy-amendment-personal-data-protection-bill-2026); [Information Age](https://ia.acs.org.au/article/2026/australians-to-gain--right-to-erasure--under-privacy-reforms.html); [McCullough Robertson](https://mccullough.com.au/2026/08/31/privacy-act-reforms-tranche-2-proposals/)
- **[Moderate] Comparative, EU:** EDPB Opinion 28/2024 says a model trained on personal data is anonymous only if the likelihood of extraction "is insignificant." It lists unlearning as a mitigation. A regulator could order erasure of the dataset *or the model*. — [IAPP summary](https://iapp.org/news/a/edpb-weighs-in-on-key-questions-on-personal-data-in-ai-models)

### Inferences
- Deletion design for this brain:
  1. Every trained artifact (adapter, reranker head, query transform) gets a **training manifest** listing the item IDs and content hashes it was trained on.
  2. A deletion or correction event marks every artifact that contains the item as stale.
  3. Stale artifacts are **retrained from scratch on the current partition data** within a deletion SLA, e.g. 24–72 h. A small per-partition adapter retrains in minutes to hours on one GPU, based on the GPL and LoRA costs above.
  4. The old artifact file is then destroyed, along with any backup copies (APP 11.39).
- Approximate unlearning (LLMEraser, gradient-ascent methods) may be used as a stopgap between deletion and retrain, but **never as the deletion mechanism of record**, given the adversarial-recovery evidence and the OAIC's statement.
- Per-partition adapters are a natural SISA with one shard per partition. For large partitions, shard the adapter by time or source (SIFT-Masks style) so one deletion retrains one shard.
- The exposure-draft erasure right would likely not cover this brain's operator directly. APP 11.2 (destroy when no longer needed), APP 10/13 (quality and correction) and a member's withdrawal of consent still require models to be fixable. Designing for exact deletion is the defensible position, and is consistent with the EDPB view.

### Gaps
- There is no OAIC guidance or determination on whether a trained model or adapter "holds" personal information for APP 12 access, APP 13 correction, or APP 11.2 destruction.
- There are no exact-unlearning results for bi-encoder embedders specifically, beyond retraining.
- The exposure draft's exceptions to the right to erasure are not described in the sources fetched.

## 6. Purpose limitation: APP 6 and training models on members' health data

### Takeaway
According to the OAIC's October 2024 guidance and the APP Guidelines:
- Training a model on personal information collected for another purpose is a **secondary use**. It requires consent, or a reasonable expectation plus a related purpose. For health (sensitive) information, the purpose must be *directly related*.
- The OAIC's own example treats fine-tuning a chatbot on customer queries collected to answer those queries as a secondary use.
- A privacy-policy update alone is "generally not sufficient." There is no legitimate-interests or business-improvement exception. Even de-identifying data is itself a secondary use.
- A gym that collects health information is a health service provider and is covered regardless of turnover.

The most defensible path for member health data is therefore express opt-in consent, or excluding it from training. This is not legal advice.

### Cited Findings
- **[Strong — regulator] OAIC, *Guidance on privacy and developing and training generative AI models* (21 Oct 2024):**
  - Where training "was not a primary purpose of collection," developers "need to carefully consider their privacy obligations."
  - Without consent or an exception, developers should "seek consent for that use and/or offer individuals a meaningful and informed ability to opt-out," and "should not rely on a broad consent."
  - Updating a privacy policy or giving notice "by themselves will generally not be sufficient," and secondary AI use "will be difficult to establish" as within reasonable expectations.
  - For sensitive information, the secondary purpose must be "directly related," meaning "closely associated with the primary purpose, even if it is not strictly necessary."
  - If consent can't be obtained and no exception applies, sensitive information must be deleted from the training dataset.
  - "De-identifying personal information is a use of the personal information for a secondary purpose."
  - The Act applies to organisations "fine-tuning commercially available models for their purposes."
  - Bank example: the primary purpose was responding to customer queries, so fine-tuning a chatbot on those queries is a secondary use that needs consent or an exception.
  - Privacy notices should "explicitly refer to training artificial intelligence models."
  — [OAIC guidance](https://oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-developing-and-training-generative-ai-models)
- **[Strong — regulator]** "The Privacy Act does not have a legitimate interests basis for data processing or a business improvement exception." — [OAIC blog (S. Otorepec, Director Health and Government)](https://www.oaic.gov.au/news/blog/can-personal-information-be-used-to-develop-or-train-a-generative-ai-model)
- **[Strong — regulator] APP Guidelines ch. 6:**
  - The reasonable-expectation test is objective ("a reasonable person, who is properly informed").
  - "Related" needs "more than a tenuous link"; "directly related" means closely associated.
  - Use only the minimum personal information necessary.
  - The guidelines do not list "service improvement" as a permitted secondary purpose.
  — [OAIC APP Guidelines ch. 6](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-6-app-6-use-or-disclosure-of-personal-information)
- **[Strong — regulator]** The OAIC health privacy guide lists "quality assurance, incident monitoring or clinical audit activities" as directly related purposes, with a prompt to consider whether de-identified information can achieve them. It does not mention AI or model training. — [OAIC Guide to health privacy ch. 3](https://www.oaic.gov.au/privacy/guidance-and-advice/guide-to-health-privacy/chapter-3-using-or-disclosing-health-information/)
- **[Strong — regulator]** A gym or weight-loss clinic is "a health service provider in situations where they collect your health information," and such providers are covered by the Privacy Act "even if they're a small business." — [OAIC: What is a health service provider](https://www.oaic.gov.au/privacy/your-privacy-rights/health-information/what-is-a-health-service-provider)
- **[Strong — regulator] I-MED inquiry (report 31 Jul 2025).**
  - I-MED shared de-identified scans and reports with Annalise.ai for AI training without patient notice or consent.
  - The OAIC closed its inquiries because the data was sufficiently de-identified ("De-identified information is not 'personal information'"). It stated this is not an endorsement.
  - It called building AI on large amounts of personal information a high privacy-risk activity, and urged removing or de-identifying personal information from training sets.
  — [OAIC I-MED report](https://www.oaic.gov.au/privacy/privacy-assessments-and-decisions/privacy-decisions/Investigation-inquiry-reports/report-into-preliminary-inquiries-of-i-med)
- **[Moderate — commentary] MinterEllison (Jan 2025):** the reasonable-expectation threshold is especially hard to meet where a model is commercialised beyond the service that collected the data, rather than used to improve that service. Vague wording like "use for research purposes" is insufficient. In the hospital fine-tuning example, both hospital and vendor are developers. — [MinterEllison](https://www.minterellison.com/articles/oaic-privacy-guidance-for-ai-developers)
- **[Moderate] Proposed (not law):** the tranche 2 "fair and reasonable" test would replace APP 6, and consent would need to be "voluntary, informed, current, specific and unambiguous." — [Lander & Rogers](https://landers.com.au/legal-insights-news/australias-next-wave-of-privacy-reform-key-changes-proposed-in-the-privacy-amendment-personal-data-protection-bill-2026)

### Inferences
- Hosting locally removes APP 8 (cross-border disclosure) concerns, but **does nothing for APP 6**. Purpose limitation applies to use, wherever it happens.
- On a plain reading of the OAIC bank example, even "improve the same service for the same member" training counts as secondary use. For member health and training data (sensitive), the safe options are:
  1. **Express, specific, opt-in consent** naming model training, with a working opt-out that triggers artifact retraining.
  2. Exclude health partitions from any training. Instead, use public or synthetic health-domain data to adapt shared extractors.
  3. Robust de-identification. But that is itself a secondary use, and the OAIC's I-MED outcome depended on extensive controls.
- A partition-local adapter used only to serve that same member's own queries is arguably the closest fit to "directly related." Whether it qualifies is a question for legal advice; the official sources do not settle it.
- Staff and business-partner data (employment context) and household data are separate purpose contexts with their own APP and exemption questions (e.g. the employee records exemption). Not researched here.

### Gaps
- There is no OAIC statement, determination or case specifically on fine-tuning *retrieval* models (embedders, rerankers) rather than generative models.
- Whether an internal retrieval-quality model is "directly related" to providing a fitness or health service is not addressed in official sources.
- Whether the business that holds member training and health data qualifies as a health service provider depends on facts. The OAIC says a gym is one when it collects health information; personal trainers are not named.

## 7. Differential privacy for fine-tuning: utility cost at small data scale

### Takeaway
- DP-LoRA costs about 3 accuracy points on large classification sets (67k–392k examples) at ε ≈ 6.7.
- Applying DP-SGD directly to a contrastive retriever **collapses** quality (nDCG@10 0.25 → 0.05 at ε = 16), because the in-batch loss is not decomposable per example.
- The workable DP route for retrieval is DP-trained synthetic query generation (about 80% of non-private nDCG at ε = 16) or the new group-bounded DP contrastive learning.

DP lowers membership-inference AUC to about 0.58 even at ε = 50, but it never reaches zero (about 3% of PII still leaked). So DP is a mitigation, not a basis for claiming "zero leakage" across hard partitions. No good evidence exists for very small datasets of 1k–5k items.

### Cited Findings
- **[Strong] DP fine-tuning of LMs (Yu et al., ICLR 2022):**
  - RoBERTa-Large with DP-LoRA at ε = 6.7: GLUE average 90.3 vs 93.4 non-private (gap 3.1). By task: MNLI 87.8 vs 90.2, SST-2 95.3 vs 96.4, QQP 87.4 vs 92.2, QNLI 90.8 vs 94.7. Training sets were 67k–392k examples.
  - Full DP fine-tuning of RoBERTa-Base averaged only 68.5.
  - DP-LoRA used 6.1 GB of GPU memory vs 27.9 GB for full DP.
  — [Yu et al., ICLR 2022 (text mirror)](https://object.cloud.sdsc.edu/v1/AUTH_da4962d3368042ac8337e2dfdd3e7bf3/ml-papers-txt/ICLR/2022/differentially_private_finetuning_of_language_models__d185490f.txt)
- **[Moderate] DP vs attacks (2025):**
  - With DP, membership-inference AUC drops to about 58% for all methods. Lowering ε further adds little.
  - Canary exposure falls substantially even at ε = 50.
  - Full fine-tuning gives the best privacy-utility trade-off under DP; LoRA is recommended when utility matters.
  — [Du et al., arXiv 2504.21036](https://arxiv.org/pdf/2504.21036)
- **[Strong] DP synthetic queries for retrieval (Carranza et al., NAACL 2024).** MS MARCO nDCG@10:
  - Non-private: 0.2525.
  - Retriever trained on DP synthetic queries: 0.2027 at ε = 16, 0.1912 at ε = 8, 0.1830 at ε = 3.
  - Retriever trained directly with DP: 0.0523 at ε = 16 and 0.0234 at ε = 3.
  - The cause: the in-batch softmax loss is not decomposable per example, so sensitivity grows with batch size.
  — [arXiv 2305.05973](https://arxiv.org/html/2305.05973v3); [NAACL 2024](https://preview.aclanthology.org/setup/2024.naacl-long.217)
- **[Moderate] DP-GCL (CCS 2026):** bounding each sample's contribution to small groups of 16 fixes contrastive sensitivity. On PEDES image-to-text retrieval at ε = 10 it scores 65.9% vs 14.2% for DP-SGD. Utility rises steeply up to about ε = 5. Tested on image and image-text data, not text-only retrieval. — [arXiv 2604.26467](https://arxiv.org/pdf/2604.26467)
- **[Moderate]** Sentence-level DP still leaked about 3% of PII sequences. — [Lukas et al., arXiv 2302.00539](https://arxiv.org/abs/2302.00539v1)
- **[Moderate]** Example-level DP gives only partial protection against *user*-level inference. — [Kandpal et al.](https://ar5iv.labs.arxiv.org/html/2310.09266)
- **[Moderate]** LT-MIA authors: DP "substantially hurts utility at needed noise levels." — [arXiv 2604.03199](https://arxiv.org/html/2604.03199v1)

### Inferences
- At this brain's partition sizes (hundreds to about 10k items per partition), DP's noise-to-signal ratio will be worse than in the 67k–392k-example results above. Expect a large utility loss at meaningful ε. DP is a poor fit *within* a partition, and it isn't needed there anyway, because the partition's own users are entitled to its data.
- DP's only plausible role is a **shared, cross-partition component**, e.g. a reranker or query generator learned from many partitions. Even then, ε > 0 means bounded leakage, not zero, which contradicts the hard-boundary rule. Recommendation: no DP-based cross-partition sharing for member or health partitions. At most, consider it for low-sensitivity business partitions with explicit sign-off.
- If a shared retriever is ever needed, Carranza's pattern (DP query generator → synthetic pairs → non-private retriever training) is the evidenced route. Do not apply DP-SGD directly to InfoNCE.

### Gaps
- No DP fine-tuning results were found for datasets under about 10k examples, or for text bi-encoders with user-level (rather than example-level) DP.
- No evidence on DP-LoRA for rerankers on private corpora.

## 8. Recommended design pattern(s) for a hard-partitioned brain

### Takeaway
Recommended pattern: **"Shared weights learn only from public or synthetic-from-public data. Private learning lives only in per-partition, droppable artifacts, retrained from scratch on a schedule, gated by a per-partition eval set."** This gets most of the measurable gains: a distilled reranker, false-negative-aware hard negatives, per-partition query adapters or LoRA, and domain extractors. It also keeps partitions, deletion and purpose limits intact by construction rather than by approximate unlearning or DP.

### Cited Findings
- **[Moderate]** Cross-encoders distilled from LLM rankings match 7B teachers at about 300 ms/query, trained on about 10k queries with hard negatives. The training queries can be public or synthetic, so no partition data enters the shared reranker. — [Rank-DistiLLM](https://arxiv.org/html/2405.07920v1)
- **[Moderate]** Query-side linear adapters need about 1.5k pairs and no corpus re-embedding. — [Chroma](https://www.trychroma.com/research/embedding-adapters). Residual adapters beat full fine-tuning with limited data. — [Search-Adaptor](https://arxiv.org/html/2310.08750v3)
- **[Moderate]** Embedder LoRA adapters are about 2% of base size and score within 0.002 nDCG of full fine-tuning; `delete_adapter` exists. — [sentence-transformers PEFT](https://raw.githubusercontent.com/UKPLab/sentence-transformers/master/examples/sentence_transformer/training/peft/README.md)
- **[Strong]** Thousands of LoRA adapters can be served from one GPU ([S-LoRA](https://arxiv.org/html/2311.03285v3)); 25 adapters on one A100 kept time-to-first-token near base levels ([LoRA Land](https://arxiv.org/html/2405.00732v1)).
- **[Moderate]** Gains for synthetic-query fine-tuning are +1–2 R@10 on enterprise text ([CustomIR](https://arxiv.org/html/2510.21729v1)), sometimes zero ([Databricks](https://www.databricks.com/en/blog/improving-retrieval-and-rag-embedding-model-finetuning)), and negative at 1K passages ([GPL](https://arxiv.org/pdf/2112.07577)). Hence the eval gate and size threshold.
- **[Strong]/[Moderate]** Exact deletion via sharding or isolated retraining: [SISA](https://arxiv.org/abs/1912.03817), [SIFT-Masks](https://arxiv.org/html/2504.04626v1). Approximate unlearning is not robust: [OAIC blog](https://www.oaic.gov.au/news/blog/can-personal-information-be-used-to-develop-or-train-a-generative-ai-model), [arXiv 2608.21606](https://www.alphaxiv.org/abs/2608.21606.md).
- **[Strong — regulator]** Secondary-use and sensitive-information limits ([OAIC guidance](https://oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-developing-and-training-generative-ai-models)). APP 11.2 requires destroying all copies ([APP 11](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-11-app-11-security-of-personal-information)).
- **[Moderate]** Fine-tuned weights and adapters leak membership (LoRA AUC 0.775 or higher): [LoRA-Leak](https://arxiv.org/abs/2507.18302v1), [Du et al.](https://arxiv.org/pdf/2504.21036).

### Inferences
This build specification is synthesised from the evidence above; it is not itself a source.

**Tier 0 (always): measure first.**
- Each partition gets an eval set: synthetic queries from a local LLM, plus 50–200 human-written queries from that partition's own users, labelled by a local LLM judge with an "aspects" prompt (Thomas et al.).
- Nothing is promoted unless it beats the current model on that partition's held-out set by more than the noise margin (suggested: at least +2 R@10 and a non-overlapping bootstrap CI).

**Tier 1 (shared, safe): public and synthetic-from-public data only.**
- (a) Distil a cross-encoder reranker (monoELECTRA or a modern small reranker) from a local 7B+ LLM's listwise rankings on **public** or template-generated queries over public corpora, with ColBERT- or embedder-mined hard negatives.
- (b) Adapt shared extractors (entities, dates, amounts, exercise and set notation) on public or synthetic documents.
- (c) Apply hard-negative hygiene (TopK-PercPos at 95%) wherever training happens.
- No partition data, statistics, or query logs ever enter shared weights. This is the neural version of the "no cross-partition IDF/LSA" rule the experiments established.

**Tier 2 (per-partition, droppable): only where the partition is large enough and the purpose is cleared.**
- Partitions under about 5–10k items: a query-side linear adapter only, once about 1.5k labelled pairs exist from logged queries plus LLM-judge labels. No re-embedding needed.
- Partitions over about 10k items, or in unusual domains: an embedder LoRA trained on synthetic queries generated from that partition (CustomIR recipe with LLM false-negative filtering). The partition's vectors are then re-embedded into its own index. Optionally add a per-partition reranker LoRA.
- Adapters are encrypted with the partition key, loaded only in that partition's request context, and treated as plaintext-equivalent.

**Tier 3 (health / member partitions): default no training.**
- Use Tier 1 shared models only.
- Per-member adapters only with express opt-in consent that names model training. They must be partition-local, retrained or removed on opt-out, and never generators (high memorization). Prefer extractive tasks.

**Deletion and correction pipeline**
1. Keep a training manifest (item IDs and hashes) per artifact.
2. A delete, correct or opt-out event marks the affected artifacts stale.
3. Retrain from scratch from current data within the SLA. Run a scheduled full retrain (e.g. weekly) regardless, so un-flagged drift and corrections propagate.
4. Destroy old artifact versions and their backups (APP 11.39).
5. Never rely on approximate unlearning as the deletion mechanism of record.
6. For large partitions, shard adapters by source or time (SISA, or SIFT-Masks-style merging) so one deletion retrains one shard.

**Feedback learning**
- Log queries, results and feedback per partition.
- Nightly, a local LLM judge labels the top-50 results of each logged query. Retrain the query adapter or reranker, then gate.
- Do not attempt online click-based learning-to-rank at this traffic level.

**Hardening**
- LoRA dropout and excluding some layers from fine-tuning (LoRA-Leak).
- Deduplicate training data, and filter PII and health spans from synthetic training text where the task allows.
- Outlier-similarity query monitoring (Mirabel-style) and rate limits.
- Pre-filter by access-control list before retrieval, so out-of-partition items cannot influence outputs.

**Do NOT**
- Fine-tune one embedder or reranker on mixed partitions.
- Fit global statistics or negative-mining indexes across partitions.
- Use DP to justify cross-partition sharing of member or health data.
- Fine-tune generative models on health data.
- Treat synthetic data derived from partition content as non-personal.

### Gaps
- The whole pattern still needs a brain-specific benchmark run comparing base, Tier 1 reranker, Tier 2 query adapter and Tier 2 LoRA per partition size. No public study covers this configuration.
- The thresholds (5–10k items, +2 R@10, 1.5k pairs) are inferred from public-corpus studies and need validation on brain data.
- The legal fit of partition-local, consented adapters under APP 6, and how APP 12/13 apply to adapters, are not settled by official sources. They require legal advice.
- Because the search budget ran out, these items were not checked further: Glean's actual permission-enforcement mechanism for per-customer models; 2026 work on text-embedder membership inference; and exact-unlearning methods for bi-encoders.
