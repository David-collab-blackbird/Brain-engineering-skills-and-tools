# Retrieval Engineering Practices of the Largest Search, E-commerce, Visual-Search and Code-Search Operators (as of Oct 2026), and What Transfers to a Private Multimodal Memory

Scope note: all sources fetched 2026-10-23. "Disclosed" = stated by the operator in a paper, blog, docs, or sworn testimony/court document. "Reported" = secondary coverage of primary material I did not read directly. "Vendor claim" = unverified self-benchmark. Numbers carry their conditions. Pre-2023 sources are flagged [OLDER].

---

## 1. Web search (Google, Bing): query understanding, KG, learning-to-rank, freshness, raters, side-by-side, interleaving, leak and DOJ disclosures

### Takeaway
Google's disclosed recipe is layered: retrieve with text/neural matching (and passage-level scoring), then re-rank using a small number of very strong signals, mainly aggregated user interaction (Navboost/Glue) and models trained on clicks plus human rater scores (RankEmbed/RankEmbedBERT). After that, hand-written "twiddlers" and diversity/dedup/freshness systems adjust results. Everything is gated by a large evaluation machine of raters, side-by-sides and live experiments. A private memory can copy the layering, the passage-level scoring, freshness-by-query-class, dedup/diversity and the evaluation discipline, using LLM judges where Google uses human raters. It cannot copy the click-signal pillar.

### Cited Findings
**Officially documented ranking systems (Google Search Central)**
- Google publicly lists named ranking systems: BERT (understands intent from word combinations), neural matching (matches concept representations in queries and pages), RankBrain (relates words to concepts so pages rank without exact terms), and passage ranking (scores individual sections of a page to judge relevance). Also: "query deserves freshness" systems that show newer content when the query calls for it, deduplication (shows only the most relevant of near-identical pages; a featured-snippet page is not repeated), and site diversity (generally no more than two results per site in the top results). MUM is "not currently used for general ranking". — [Google Search Central: Ranking systems guide](https://developers.google.com/search/docs/appearance/ranking-systems-guide)

**Evaluation scale (Google, disclosed)**
- In 2023 Google ran 719,326 search quality tests, 124,942 side-by-side experiments and 16,871 live traffic experiments, leading to 4,781 launches. Rater ratings "don't directly affect ranking" but are used to benchmark quality. — [Google: Rigorous testing](https://google.com/search/howsearchworks/how-search-works/rigorous-testing/)
- Implied ratio: roughly 26 side-by-sides and 3.5 live experiments per launch (my arithmetic from the figures above).

**DOJ v. Google trial exhibits (primary exhibits, reproduced by Search Engine Land)**
- Q4 Search All Hands slide (Dec 8, 2016): "We do not understand documents. We fake it." — [Search Engine Land: 7 must-see Google ranking documents](https://searchengineland.com/google-search-ranking-documents-434141)
- "Google is magical" presentation notes (Oct 30, 2017): "The source of Google's magic is this two-way dialogue with users." — [Search Engine Land](https://searchengineland.com/google-search-ranking-documents-434141)
- The "3 Pillars of Ranking" slide lists Body (what the document says about itself), Anchors (what the web says about the document) and User-interactions (what users say about the document). — [Search Engine Land](https://searchengineland.com/google-search-ranking-documents-434141)
- Lehman testified (Sept 2023) that Google uses clicks in rankings. Google says it uses click data for training, evaluation, controlled experiments and personalization, and that individual clicks are noisy. — [Search Engine Land](https://searchengineland.com/google-search-ranking-documents-434141)
- [OLDER exhibits, 2014–2020; trial 2023]

**Navboost / Glue / twiddlers (testimony, as reported by secondary sources)**
- Pandu Nayak described Navboost as "one of the important signals". It runs only after retrieval ("you get Navboost only after they're retrieved in the first place"), narrowing tens of thousands of candidates to a few hundred. It can only affect documents that have accumulated click data. — [Hobo Web: Navboost](https://www.hobo-web.co.uk/navboost-how-google-uses-large-scale-user-interaction-data-to-rank-websites/) (secondary; no exhibit numbers given)
- Glue was described as "another name for Navboost that includes all of the other features on the page", i.e. interaction logging for non-organic SERP features. Trial documents reportedly call it a "super query log". — [Hobo Web](https://www.hobo-web.co.uk/navboost-how-google-uses-large-scale-user-interaction-data-to-rank-websites/)
- "Twiddlers" are re-ranking functions applied after core ranking to correct outputs. — [Hobo Web](https://www.hobo-web.co.uk/navboost-how-google-uses-large-scale-user-interaction-data-to-rank-websites/)
- CAVEAT: the widely repeated "13 months of click data" window appears in that article as the author's own analysis, not as an attributed quote. I did not verify it against a transcript, so treat it as reported, not confirmed.

**RankEmbed / RankEmbedBERT (2025 remedies opinion, as quoted by secondary source)**
- The court described RankEmbed and RankEmbedBERT as "ranking models that rely on two main sources of data": a share of 70 days of search logs, plus scores generated by human raters, i.e. "a combination of click-and-query data and scoring of web pages by human raters". — [Hobo Web: human quality raters in DOJ v Google](https://www.hobo-web.co.uk/how-human-quality-raters-are-used-new-evidence-from-doj-v-google-antitrust-trial/)
- Nayak testimony quoted there: "RankEmbedBERT was again one of those very strong impact things, and it particularly helped with long-tail queries." — [Hobo Web](https://www.hobo-web.co.uk/how-human-quality-raters-are-used-new-evidence-from-doj-v-google-antitrust-trial/)
- Takeaway: rater judgments do not set individual rankings directly, but they are training labels for an embedding-based ranker. That makes them an indirect but large influence. (The interpretation is the blog author's; the quotes are attributed to the court.)

**2024 Content Warehouse API leak**
- Committed to a public Google GitHub repo around March 13, 2024; public in May 2024. It covers 2,596 modules and 14,014 attributes. Google confirmed authenticity on May 29, 2024, while warning against "inaccurate assumptions". — [Wikipedia: 2024 Google Search documentation leak](https://en.wikipedia.org/wiki/2024_Google_Search_documentation_leak)
- Disclosed attribute names include goodClicks, badClicks and lastLongestClicks (Navboost click metrics), Chrome-derived click fields, a siteAuthority score, siteFocusScore/siteRadius/site2vecEmbeddingEncoded (site topical focus via embeddings), hostAge, and authors treated as entities. — [Wikipedia](https://en.wikipedia.org/wiki/2024_Google_Search_documentation_leak)
- Limitations: no code, no weights, and no indication of which attributes are live or deprecated. Analysis was done mainly by Rand Fishkin and Michael King (iPullRank). — [Wikipedia](https://en.wikipedia.org/wiki/2024_Google_Search_documentation_leak)

**Query fan-out (Google AI Mode / Deep Search, 2025–2026)**
- Robby Stein (VP Product, Search): Deep Search "can issue dozens or even hundreds of background queries". AI Mode uses structured backends such as the Shopping Graph (50B products, "updated I think 2 billion times every hour"), Finance, flights and movies as tools. — [Search Engine Journal, Jul 30 2025](https://www.searchenginejournal.com/query-fan-out-technique-in-ai-mode-new-details-from-google/552532/)
- Multimodal fan-out: Gemini identifies each distinct object in an image, generates several related searches, runs them in parallel against the Lens visual backend, and merges the results. Text and image are interpreted together to choose tools. — [Google Blog, Mar 5 2026](https://blog.google/company-news/inside-google/googlers/how-google-ai-visual-search-works/)

**Bing: LLM relevance labelling replacing crowd raters**
- Microsoft (Thomas, Spielman, Craswell, Mitra; SIGIR 2024): an LLM and prompt chosen to agree with first-party searcher feedback labels "as accurate as human labellers". It beat every human labeller population they studied, with crowd workers worst. Bing uses this to label at scale. — [arXiv 2309.10621](https://arxiv.org/html/2309.10621v3)
- Prompt findings: asking for aspect ratings (topicality, trust) before the overall label was the strongest variant. "Minor paraphrases can make a material difference", which "reinforces the need for high-quality 'gold' labels". Experiments used TREC-Robust 2004 with GPT-4 at temperature 0, not live Bing traffic. — [arXiv 2309.10621](https://arxiv.org/html/2309.10621v3)

**Interleaving (closest public evidence; Airbnb at KDD 2025)**
- Interleaving raised sensitivity "by a factor of up to 100" versus A/B, with about 50X less traffic for equal power in production. It agreed directionally with A/B 82% of the time (29 pairs; correlation 0.6). Counterfactual offline evaluation took about 1–2 hours versus weeks for A/B. — [Airbnb, KDD '25, arXiv 2508.00751](https://arxiv.org/html/2508.00751)

### Inferences
- The Google stack is a funnel: lexical/neural retrieval with passage scoring produces tens of thousands of candidates. Interaction and learned rankers cut that to hundreds. Twiddlers, dedup, diversity and freshness give the final page. Disclosed testimony places the click system after retrieval, so it cannot rescue a document the retriever missed. That applies directly here: recall@k is decided at candidate generation, and no reranker fixes a candidate-set miss.
- "We do not understand documents. We fake it" (2016) explains why Google leaned on user interaction. A private memory with few users has no interaction substitute, so it must invest more in document understanding (enrichment at ingest) and in LLM-based relevance judgment. LLMs make this feasible in 2024–2026 where it was not in 2016.
- Rater-labelled data used as training labels for an embedding ranker (RankEmbedBERT) maps onto: use LLM-judged relevance labels (Bing-style, calibrated against a small human gold set) to fine-tune or calibrate the reranker and embedding model on your own corpus.
- The side-by-side and live-experiment cadence implies that for a small system, the equivalent is a frozen golden query set per query class plus pairwise (side-by-side) LLM judging of old versus new pipeline before every change.
- Interleaving needs live users, so it is low value at 1–20 users. Counterfactual or offline replay on logged queries is the transferable form.

### Gaps
- I did not read primary DOJ transcripts or the remedies opinion PDF directly. Navboost's 13-month window and RankEmbed's 70-day figure are via secondary quoting.
- Google has not publicly disclosed how its Knowledge Graph lookup is fused with organic ranking. I found no primary source detailing entity-lookup/ranking fusion.
- No recent public Bing learning-to-rank architecture details beyond LLM labelling.
- Google's Search Quality Rater Guidelines content (Needs Met / Page Quality scales) was not fetched in this pass.

---

## 2. E-commerce search (Amazon, Shopify, Etsy, Instacart, Walmart): attribute extraction, query classification, hybrid, two-tower, rerankers, published gains

### Takeaway
Every large e-commerce operator runs lexical plus embedding retrieval in parallel (hybrid), never embeddings alone. They classify queries into categories/attributes before retrieval and use those as filters or boosts, and they increasingly use LLMs offline to enrich items and queries, then distill into small fast models. Embedding-retrieval gains are largest when training data is cleaned for relevance and hard negatives are mined. The biggest published single offline lifts come from adding non-text signals: a query graph, LLM-derived structured attributes, and relevance-filtered labels.

### Cited Findings
**Instacart**
- Hybrid recall: Postgres full-text (GIN index, ts_rank) top-Kt plus FAISS ANN over MiniLM-L3-v2 bi-encoder embeddings top-Ke, queried in parallel and unioned into one recall set. — [Instacart Tech: hybrid retrieval](https://tech.instacart.com/optimizing-search-relevance-at-instacart-using-hybrid-retrieval-88cb579b959c) (dated Sept 2024 on page; metadata says May 2025)
- Adaptive recall size per query uses query entropy (the conversion distribution spread): size = min(M, max(L, M·entropy/Q)) with L=500, M=1000, Q=10. Result: +1.7% mean converting position and −1.5% latency. RRF and convex combination fusion were "work in progress", with weights adjustable "based on the query and retailer context" (proposed, not shipped). The plan was to move ANN to pgvector to consolidate into one store. — [Instacart Tech](https://tech.instacart.com/optimizing-search-relevance-at-instacart-using-hybrid-retrieval-88cb579b959c)
- LLM query understanding ("Intent Engine", Nov 2025):
  - Category classification: retrieve top-K converted categories as candidates, have an LLM re-rank with injected Instacart context, then apply an embedding-similarity guardrail. This replaced a FastText flat classifier.
  - Query rewrites (substitute/broader/synonym prompts with CoT and few-shot): coverage went from about 50% to over 95% of traffic, with over 90% precision.
  - Semantic role labelling/attribute tagging (product, brand, attributes).
  - Head/tail split: an offline RAG "teacher" caches head queries; a LoRA fine-tuned Llama-3-8B "student" serves cache misses in real time (about 300 ms on H100). The student scored P 96.4%/R 95% versus the larger teacher's P 95.4%/R 96.2%. FP8 cut latency 10% but hurt recall, so it was not shipped.
  - A/B: scroll depth −6% and tail-query complaints −50%.
  — [Instacart Tech: Intent Engine](https://tech.instacart.com/building-the-intent-engine-how-instacart-is-revamping-query-understanding-with-llms-3ac8051ae7ac)

**Walmart (CIKM 2024)**
- DistilBERT Siamese two-tower EBR complements the lexical inverted index (hybrid). Products are encoded as title plus attribute values, each attribute with its own marker token. — [arXiv 2408.04884](https://arxiv.org/html/2408.04884v2)
- A cross-encoder Relevance Reward Model trained on human 3-class labels (exact/substitute/irrelevant) revises noisy engagement labels: about 30% of pairs were downgraded to 0.01 weight and about 3% to 0.1. Hard negatives are in-batch plus ANCE-style offline mined, with a product-type classifier guardrail to remove false negatives. The multi-objective loss is 0.5·engagement + 0.5·relevance; ablation shows either alone is insufficient. — [arXiv 2408.04884](https://arxiv.org/html/2408.04884v2)
- Results: exact-match Recall@20 +16.49% and Precision@20 +14.65% (all components, offline). The new labelling alone gave order Recall@20 +50.73%. Online: NDCG@10 up to +0.98% (p≈0); revenue +0.43% (p=0.06, not significant). — [arXiv 2408.04884](https://arxiv.org/html/2408.04884v2)

**Etsy (2023)**
- Unified Embedding Personalized Retrieval: a two-tower model whose product tower fuses (a) token embeddings of n-grams, categories and attribute key/values, (b) T5-small pretrained docT5query-style to generate purchased queries from product text, and (c) a bipartite query-product graph encoder averaging a year of neighbouring queries. Off-the-shelf DistilBERT/T5 fine-tuning gave no offline gain. — [arXiv 2306.04833](https://arxiv.org/html/2306.04833v2)
- Offline Recall@100/@1000:
  | Method | Recall@100 | Recall@1000 |
  |---|---|---|
  | BM25 | 0.55 | 0.62 |
  | Base two-tower | 0.33 | 0.61 |
  | UEPPR | 0.674 | 0.82 |
  | UEPPR + quality boost | 0.708 | 0.85 |

  Note that a naive two-tower model lost to BM25 at @100. — [arXiv 2306.04833](https://arxiv.org/html/2306.04833v2)
- Dynamic hard negatives gave the largest ablation gain. Quality features were appended to the product vector with a constant query-side weight vector, so a single ANN inner product includes a quality prior; weights were tuned by Bayesian optimisation. Faiss 4-bit fastscan plus re-ranking 5×K kept recall loss under 4% at P99 under 20 ms. — [arXiv 2306.04833](https://arxiv.org/html/2306.04833v2)
- Online A/B: site-wide conversion +2.63% and organic search purchase rate +5.58%. — [arXiv 2306.04833](https://arxiv.org/html/2306.04833v2)

**Amazon**
- [OLDER, KDD 2019] Semantic Product Search: a behaviour-trained model with a 3-part thresholded loss (random negatives, impressed-not-purchased, purchased), n-gram average pooling and OOV hashing. It reported Recall@100 at least +4.7% and MAP +14.5% versus prior semantic baselines, motivated by lexical failures on synonyms, hypernyms, antonyms, morphology and misspellings. — [Amazon Science: Semantic product search](https://www.amazon.science/publications/semantic-product-search)
- COSMO (SIGMOD 2024): LLMs mine query→purchase and co-purchase pairs into commonsense relations (used_for_function, used_for_event, used_for_audience…). These are refined through human plausibility/typicality annotation, a classifier filter and instruction-tuning, then stored as KG triples. On the KDD Cup 2022 Shopping Queries relevance task, a COSMO-enhanced cross-encoder improved macro F1 by 60% (frozen encoders) and 22–28% (fine-tuned) over the best baseline. These are offline results only; no A/B numbers were disclosed. — [Amazon Science blog, May 2024](https://www.amazon.science/blog/building-commonsense-knowledge-graphs-to-aid-product-recommendation)
- SIGIR 2026 (Zhu, Vedula, Malmasi): an LLM extracts structured attributes offline into a category-aware attribute graph; online, candidates are ranked by an LLM reasoning over the structured representation instead of raw text. Results: 57% fewer tokens per product and over 5% average precision gain, zero-shot. — [Amazon Science: LLM-guided attribute graphs](https://www.amazon.science/publications/from-unstructured-to-structured-llm-guided-attribute-graphs-for-entity-search-and-ranking)

**Shopify (Oct 2024)**
- Streaming text and image embedding pipelines run on Dataflow, triggered by merchant create/update events: about 2,500 embeddings/s (about 216M/day), written both to the warehouse and to a topic for real-time ingest into Storefront Search. Near-real-time was chosen over batch because merchant edits must appear quickly. No relevance metrics were disclosed. — [Shopify Engineering](https://shopify.engineering/how-shopify-improved-consumer-search-intent-with-real-time-ml)

**Airbnb (adjacent marketplace, 2025)**
- EBR is a candidate generator ahead of heavy rankers. Training positives were booked listings; negatives were listings seen or wishlisted but not booked, because random negatives made the task "too easy and hurt performance". IVF was chosen over HNSW despite HNSW's slightly better recall, because most queries are filtered (geo) and HNSW with filters had poor latency; clusters act as a standard filter. Offline metric: recall. A/B: a statistically significant bookings lift "on par with" the largest ranking wins in two years. — [Airbnb Tech: EBR](https://airbnb.tech/ai-ml/embedding-based-retrieval-for-airbnb-search/)

### Inferences
- Consistent pattern: lexical plus dense in parallel, union, then rerank. No operator above relies on dense alone. Etsy's table shows an untuned two-tower model losing to BM25 at Recall@100, which supports always keeping BM25 as a recall channel.
- Enrichment at ingest (attributes, categories, LLM-generated "queries this item answers", à la docT5query, and relations à la COSMO) is the most transferable family. It needs no clicks: an LLM can produce it per item at 10k–100k scale cheaply.
- Query→category/attribute classification followed by filtering or boosting is essential for faceted questions (date ranges, people, document types, modality). Instacart's "retrieve candidate categories → LLM re-rank → embedding guardrail" pattern needs no conversion data if candidates come from the corpus taxonomy.
- Instacart's head/tail split maps to caching LLM query understanding for recurring queries and running a small model or a direct LLM call for novel ones.
- Walmart's lesson that "engagement labels are noisy, so relevance-filter them with a cross-encoder" maps to: if you ever fine-tune on your own usage logs, filter with an LLM judge first.
- Airbnb's filtered-ANN finding matters: metadata filters (time, owner, type) are common in memory queries. Choose an index that does filtered search well (IVF/partitioned, or a DB with native pre-filtering). Note that vector stores often struggle with filtered HNSW.

### Gaps
- No recent public Amazon numbers for hybrid lexical+semantic fusion in production search.
- Shopify disclosed infrastructure but no relevance metrics.
- Instacart's hybrid fusion results (RRF versus convex) were not published.

---

## 3. Visual search (Pinterest, Google Lens): unified embeddings, multi-stage retrieval, measurement

### Takeaway
Pinterest's trajectory is from many specialised embeddings to one multi-task unified embedding (2019), then a unified query/pin/product embedding enriched with LLM/VLM captions and board text (2024), then a graph + content + sequence universal representation (2025). Each step was justified by both offline metrics and A/B. Google Lens/AI Mode now decomposes an image into objects and fans out multiple parallel searches. For a private multimodal memory, the transferable lessons are: (a) one shared embedding space across modalities and tasks, (b) enrich images with generated captions and surrounding text before embedding, and (c) decompose multi-object images into per-region queries.

### Cited Findings
- [OLDER, 2019] Pinterest replaced per-product visual embeddings with one multi-task metric-learning embedding trained on engagement plus human-labelled data across domains (camera photos, web images, catalogue images). It "outperforms all specialized embeddings previously deployed for each product", can be binarised "without compromising precision and recall", and was validated by offline metrics, user studies and A/B tests (numbers not in the abstract). — [arXiv 1908.01707](https://arxiv.org/abs/1908.01707v1)
- OmniSearchSage (2024; ACM DOI 10.1145/3589335.3648309): a single query embedding learned jointly with pin and product embeddings. Entity text is enriched with generative-LLM image captions, historical engagement and user-curated board titles. In production: relevance +8% or more, engagement +7% or more, ads CTR +5% or more, at 300k requests/s across retrieval and ranking. Code is open in pinterest/atg-research. — [arXiv 2404.16260](https://arxiv.org/abs/2404.16260v1)
- Pinterest search relevance (2024): a Llama-3-8B cross-encoder teacher scored 5-level accuracy 0.602 versus 0.535 for mBERT and 0.503 for the SearchSAGE baseline. Enrichment ablation (mDeBERTa):
  | Input added (cumulative) | Accuracy |
  |---|---|
  | BLIP caption only | 0.457 |
  | + title/description | 0.561 |
  | + link text | 0.565 |
  | + board titles | 0.577 |
  | + high-engagement query tokens | 0.580 |

  The teacher labelled billions of pairs (over 100× human labels). A student trained on 6M distilled labels (0.535) beat one trained on 0.3M human labels (0.484). Online: search fulfillment +0.7% (US) and +2.0% (non-US); nDCG@20 +2.18%. — [arXiv 2410.17152](https://arxiv.org/html/2410.17152v1)
- OmniSage (2025): unifies graph neural networks, content (text+visual) models and user-sequence models with multiple contrastive tasks, on graphs with billions of nodes. It serves five applications with about +2.5% sitewide saves. — [arXiv 2504.17811](https://arxiv.org/abs/2504.17811)
- Google Lens/AI Mode (Mar 2026): Gemini identifies each distinct object in an image, runs several related searches simultaneously against the Lens visual backend, and merges the results. A selected result image can seed a new fan-out. The image and the text question are interpreted together to choose tools. The object-detection method and per-object query counts were not disclosed. — [Google Blog](https://blog.google/company-news/inside-google/googlers/how-google-ai-visual-search-works/)

### Inferences
- Pinterest's ablation is direct evidence for multimodal memory: captions alone are weak (0.457), and adding the human/contextual text around an image (titles, descriptions, collections) gives the largest jump. For a personal brain: store VLM caption + OCR + filename/folder/album + surrounding message/email text + EXIF/date/location with each image, and index all of it lexically and densely.
- One shared embedding space (Pinterest unified, OmniSearchSage) supports cross-modal queries such as text→image and image→doc. Off-the-shelf multimodal embedders approximate this. Keep a text-surrogate channel (captions/OCR in BM25) as a recall backstop, because cross-modal embeddings are weaker on exact names and numbers.
- LLM teacher → cheap student distillation shows LLM relevance labels can substitute for missing human/click labels. At 10k–100k items you can skip distillation and run the LLM/cross-encoder reranker directly on the top-k.
- Lens-style object decomposition maps to: for image queries (or image items with multiple subjects), produce per-region crops/captions and index or query them separately.

### Gaps
- No public numeric Recall@k for Google Lens.
- I did not find a 2025–2026 Pinterest Engineering post giving a full visual-search multi-stage funnel with stage-wise recall numbers. The 2017–2019 "Visual Discovery" papers exist but are older and were not fetched.

---

## 4. Code search / coding agents (Sourcegraph, Cursor, Augment, GitHub Copilot, Claude Code): embeddings vs grep/agentic search, measurements, indexing

### Takeaway
The field converged on "both": agentic lexical search (grep/glob, iterated by the model) is the default because it is exact, always fresh and needs no index. Semantic retrieval adds measurable gains, mostly on large codebases. Cursor's controlled numbers are the best public evidence: +12.5% average offline accuracy, and +2.6% code retention on repos with 1,000+ files versus +0.3% overall. Index freshness and security drove Claude Code and Sourcegraph away from embeddings-only. Custom embeddings trained on agent traces or hard negatives beat off-the-shelf ones.

### Cited Findings
**Cursor (Nov 2025)**
- Semantic search raised average accuracy on Cursor Context Bench by 12.5% (range 6.5%–23.5% depending on model), improving every model tested. — [Cursor blog: semsearch](https://cursor.com/en-US/blog/semsearch)
- Online A/B: code retention +0.3% overall and +2.6% on codebases with 1,000+ files. Dissatisfied follow-up requests were 2.2% higher without semantic search. Smaller online effects are expected because not every request needs search. No sample size or dates given. — [Cursor blog](https://cursor.com/en-US/blog/semsearch)
- Custom embedding training: agent session traces record the searches and file opens made before finding the right code. An LLM ranks which content would have been most helpful at each step, and the embedding model is trained so its similarities match those LLM rankings. "Our agent makes heavy use of grep as well as semantic search, and the combination of these two leads to the best outcomes." — [Cursor blog](https://cursor.com/en-US/blog/semsearch); [ZenML summary](https://www.zenml.io/llmops-database/enhancing-ai-coding-agent-performance-with-custom-semantic-search)
- Indexing (Jan 2026):
  - A Merkle tree of file hashes is used for incremental sync. A 50k-file repo is about 3.2 MB of hashes, and only diverging branches are walked.
  - Syntactic chunking; embeddings are cached by chunk content hash, so unchanged chunks are never re-embedded.
  - Index reuse: org clones average 92% similarity, and simhash matching reuses a teammate's index.
  - Results for files the client cannot prove it holds are dropped.
  - Time-to-first-query: median 7.87 s → 525 ms; p99 4.03 h → 21 s.
  — [Cursor blog: secure codebase indexing](https://cursor.com/blog/secure-codebase-indexing)

**Claude Code (Boris Cherny, reported May 2025)**
- "Originally, very early versions of Claude actually used RAG. We indexed the code base, I think using Voyage, just off-the-shelf RAG, and that worked pretty well… Eventually, we landed on just agentic search… It outperformed everything else by a lot." Evidence was "mostly vibes" plus some internal benchmarks; no numbers. Reasons given: "the code drifts out of sync"; security ("this index has to live somewhere"); trade-off is "latency and tokens". — [OfficeChai](https://officechai.com/ai/claude-researcher-explains-how-agentic-search-performed-better-than-rag-for-code-generation/) (secondary report of a video interview)

**Sourcegraph Cody**
- Embeddings were removed from Cody Enterprise and "replaced… with Sourcegraph Search" (keyword/code search), for scalability across many large repos plus security and low maintenance. — [Sourcegraph Cody FAQ](https://sourcegraph.com/docs/cody/faq) (undated docs page; change dates to around Sourcegraph 5.3, early 2024)

**GitHub Copilot (Sept 2025)**
- A new code embedding model gave +37.6% relative retrieval quality (0.362 → 0.498 average on a multi-benchmark), about 2× throughput and an about 8× smaller index. Code acceptance ratio was +110.7% (C#) and +113.1% (Java) in VS Code. Training used contrastive InfoNCE plus Matryoshka representation learning. Hard negatives (code that looks right but is not, surfaced with LLMs) "drove the largest quality gains". — [GitHub Blog](https://github.blog/news-insights/product-news/copilot-new-embedding-model-vs-code/)

**Augment Code (Feb 2026, vendor claim)**
- The Context Engine (semantic codebase index) was exposed over MCP. Claimed quality gains when plugged into other agents: Claude Code + Opus 4.5 +80%, Cursor + Opus 4.5 +71%, Cursor + Composer-1 +30%. These are the company's own benchmarks, unverified, and the headline "over 70%" figure is inconsistent with the 30% case. — [SiliconANGLE](https://siliconangle.com/2026/02/06/augment-code-makes-semantic-coding-capability-available-ai-agent/)

### Inferences
- The defensible synthesis: agentic lexical search plus semantic retrieval, with the model choosing tools, beats either alone. Lexical wins on exact identifiers and freshness; semantic wins on conceptual queries and in large corpora (the Cursor 1,000+ file effect). For a memory "brain", expose BM25/grep-like exact search, metadata filters and dense search as separate tools to the agent (Claude Code) and let it iterate. Do not hide everything behind one fused endpoint.
- The staleness objection (Claude Code, Sourcegraph) is solved industrially by content-hash incremental indexing (Cursor Merkle tree plus per-chunk embedding cache; Shopify event-driven re-embedding). Copy that: hash every item/chunk, re-embed only on change, and keep a lexical index updated synchronously.
- Training embeddings on traces ranked by an LLM (Cursor) is a recipe that needs no human labels and works with few users. Once the memory has agent traces, an LLM can label "which item would have helped" and you can fine-tune or adapt embeddings.
- Hard negatives are repeatedly the largest single lever (GitHub, Walmart, Etsy, Airbnb). If fine-tuning, mine near-miss items from your own corpus.

### Gaps
- No independent third-party benchmark comparing grep-only versus embeddings versus hybrid agentic retrieval across vendors with matched models.
- Cursor did not disclose baseline accuracy, sample sizes or Context Bench composition.
- No published Anthropic numbers for Claude Code agentic versus RAG.

---

## 5. Answer engines (Perplexity, You.com)

### Takeaway
Very little is disclosed. Perplexity publicly chose a hybrid lexical+vector engine with strong boolean filtering (Vespa) because pure vector databases "could not reliably support even simple boolean filters", and later moved its web index to a purpose-built internal system. Google's AI Mode discloses query fan-out (dozens to hundreds of sub-queries for Deep Search).

### Cited Findings
- Perplexity (Vespa case study): 780M+ queries/month. It needed keyword plus semantic in one engine, having found that "vector databases could not reliably support even simple boolean filters" while traditional backends offered only primitive semantic ranking. Its goal is passage-level relevance. It has since moved the web index to a purpose-built internal search system while keeping Vespa for other uses. Multi-phase ranking and passage ranking are described as Vespa capabilities, not confirmed Perplexity internals. — [Vespa: Perplexity case study](https://vespa.ai/case-studies/perplexity/) (vendor case study)
- Google AI Mode / Deep Search query fan-out: see section 1. — [Search Engine Journal](https://www.searchenginejournal.com/query-fan-out-technique-in-ai-mode-new-details-from-google/552532/)

### Inferences
- The consistent message from Perplexity and from e-commerce is: hybrid plus reliable structured filtering in the same engine. For a memory system this argues for a store that does BM25, vector and metadata filters natively in one query (e.g., Postgres with pgvector plus full-text, or Vespa/OpenSearch-class engines), rather than a vector-only store.
- Query fan-out (decomposing a question into sub-queries and unioning results) is the answer-engine analogue of recall expansion. It is the most direct lever for multi-hop or broad questions in a memory brain.

### Gaps
- No primary disclosure of You.com's retrieval stack was found in this pass.
- Perplexity's internal ranking stages, rerankers and freshness mechanics are undisclosed beyond the vendor case study.

---

## 6. Cross-cutting: retrieval funnel, ingest-time enrichment, query classification, feedback loops — what transfers to a single-organisation memory with little click data

### Takeaway
The industrial funnel transfers almost entirely at small scale, and the small scale makes the expensive stages affordable everywhere. The steps are: query understanding/classification → multi-channel candidate generation (lexical + dense + metadata/entity lookup + fan-out) → filtering → learned/LLM reranking → dedup/diversity/freshness adjustments → evaluation gate. What does not transfer is click-trained ranking (Navboost, engagement-trained two-towers). The proven substitutes are LLM relevance judgments (Bing, Pinterest teacher), LLM enrichment at ingest (Pinterest captions, Amazon COSMO and attribute graphs, Etsy docT5query), and LLM-labelled agent traces (Cursor).

### Cited Findings
- Click/interaction systems act only after retrieval and only on documents with accumulated interactions (Nayak testimony, reported). — [Hobo Web](https://www.hobo-web.co.uk/navboost-how-google-uses-large-scale-user-interaction-data-to-rank-websites/)
- Rater judgments become training data for rankers (RankEmbedBERT) and helped long-tail queries most. — [Hobo Web quoting the remedies opinion](https://www.hobo-web.co.uk/how-human-quality-raters-are-used-new-evidence-from-doj-v-google-antitrust-trial/)
- LLM labellers match or exceed human labellers when selected and calibrated against gold labels, but are prompt-sensitive. — [Microsoft, SIGIR 2024](https://arxiv.org/html/2309.10621v3)
- LLM-distilled labels (6M) beat human labels (0.3M) for training a relevance student. — [Pinterest, arXiv 2410.17152](https://arxiv.org/html/2410.17152v1)
- Enrichment text around images is worth more than captions alone (0.457 → 0.580 accuracy). — [Pinterest, arXiv 2410.17152](https://arxiv.org/html/2410.17152v1)
- LLM-extracted structured attributes improve ranking precision by over 5% zero-shot and cut tokens 57%. — [Amazon, SIGIR 2026](https://www.amazon.science/publications/from-unstructured-to-structured-llm-guided-attribute-graphs-for-entity-search-and-ranking)
- LLM query rewrites gave over 95% coverage at over 90% precision, versus about 50% coverage from session-mined rewrites. The LLM category classifier uses corpus-derived candidates plus an embedding guardrail. — [Instacart](https://tech.instacart.com/building-the-intent-engine-how-instacart-is-revamping-query-understanding-with-llms-3ac8051ae7ac)
- Adaptive candidate-set size by query breadth: +1.7% converting position and −1.5% latency. — [Instacart](https://tech.instacart.com/optimizing-search-relevance-at-instacart-using-hybrid-retrieval-88cb579b959c)
- Quality priors folded into ANN scoring: Recall@100 0.674 → 0.708. — [Etsy, arXiv 2306.04833](https://arxiv.org/html/2306.04833v2)
- Freshness as a query-conditional system ("query deserves freshness"), and dedup/diversity as explicit final-stage systems. — [Google Search Central](https://developers.google.com/search/docs/appearance/ranking-systems-guide)
- Evaluation discipline: about 26 side-by-sides per launch at Google (2023). — [Google](https://google.com/search/howsearchworks/how-search-works/rigorous-testing/)
- Offline counterfactual evaluation correlates about 0.65 with A/B outcomes and runs in hours. — [Airbnb, KDD '25](https://arxiv.org/html/2508.00751)

### Transfer matrix (inference, built from the findings above)
| Industrial practice | Transfers to 10k–100k private memory? | Substitute or adaptation |
|---|---|---|
| Hybrid lexical + dense candidate generation (all operators) | Yes, directly | BM25 + dense in parallel, union; at this scale retrieve generously (top 100–300 per channel) |
| Query classification → filters/boosts (Instacart, Amazon) | Yes | LLM classifies query class, modality, time range, entities; categories come from the corpus taxonomy, not conversions |
| Query rewriting / fan-out (Instacart, Google AI Mode) | Yes | LLM generates synonym/broader/sub-queries; union results |
| Ingest-time enrichment: attributes, captions, generated questions, relations (Amazon, Pinterest, Etsy) | Yes, highest leverage | Per-item LLM/VLM pass producing caption, OCR, entities, dates, typed attributes, "questions this answers"; index in both lexical and dense channels |
| Entity / knowledge-graph lookup as a parallel channel (Google KG, Amazon COSMO) | Yes | Entity table/graph built at ingest; exact entity hits added to candidates |
| Passage-level scoring (Google passage ranking) | Yes | Chunk-level retrieval with parent-document return |
| Cross-encoder / LLM reranker (Walmart RRM, Pinterest teacher) | Yes, and affordable at small k | Rerank top 50–200 with a cross-encoder or LLM judge |
| Freshness, dedup, diversity final stage (Google) | Yes | Recency boost only for time-sensitive query classes; near-duplicate collapse |
| Click-trained ranking (Navboost/Glue, engagement two-towers) | No (little data) | LLM relevance labels; optionally light usage signals (item opened or cited) as weak priors |
| Interleaving / live A/B | Weak (few users) | Golden set + pairwise LLM side-by-side; offline replay of logged queries |
| Human raters plus guidelines (Google SQRG, Bing) | Partly | Small human gold set per query class to calibrate an LLM judge (Bing method) |
| Custom embedding fine-tuning with hard negatives (GitHub, Cursor, Walmart, Etsy) | Optional, later | Once traces exist: LLM-label traces (Cursor) and mine corpus hard negatives |
| Incremental content-hash indexing (Cursor, Shopify) | Yes | Hash per item/chunk; re-embed only on change; synchronous lexical update |
| Filter-friendly ANN (Airbnb IVF over HNSW) | Yes | Use a store with native filtered vector search; at 100k vectors exact/flat search is also viable |

### Inferences
- At 10k–100k items, brute-force exact vector search and LLM reranking of large candidate sets are computationally cheap. The latency and cost constraints that forced industrial distillation and approximation largely disappear, so recall@k is bounded mainly by candidate-generation coverage and enrichment quality. This is an inference from the scale difference, not a published measurement.
- The 90% recall standard per query class mirrors how operators measure by segment: Instacart for tail queries, Cursor for repos with 1,000+ files, Etsy for head versus tail. Build per-class golden sets and report recall per class, not a blended number.
- The most likely failure modes, given the evidence: exact identifiers/names missed by dense-only retrieval (fixed by the BM25 channel), images with poor surrounding text (fixed by VLM caption + OCR + context enrichment), time-scoped queries (fixed by query classification → date filter), and multi-hop questions (fixed by fan-out and an entity graph).

### Gaps
- No public operator reports a Recall@k number on a private-corpus-scale (10k–100k) multimodal setting, so all transfer claims are inferences.
- No published head-to-head of RRF versus learned fusion from the operators reviewed (Instacart listed both as work in progress).
- Weak usage signals (opens, citations) at very low user counts have no published evidence of value.
