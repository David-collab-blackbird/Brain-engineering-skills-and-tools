# How High-Stakes Retrieval Operators Build and Measure Retrieval (as of Oct 2026)

Scope note: covers legal research (Thomson Reuters/Westlaw/CoCounsel, LexisNexis/Protégé, Harvey), e-discovery/TAR (Relativity aiR, Everlaw, court validation law), enterprise search (Glean, Microsoft 365 Copilot, Google Gemini Enterprise/Agentspace, Atlassian Rovo), finance/data (Bloomberg, Palantir, AlphaSense), and healthcare (Abridge, Epic). Evidence labels: **[MEASURED-INDEP]** = independent or peer-reviewed measurement; **[MEASURED-VENDOR]** = vendor's own numbers; **[DOCS]** = official product documentation (describes mechanism, not accuracy); **[MARKETING]** = unquantified vendor claims.

---

## 1. Legal research: published architecture and independent accuracy evidence (Thomson Reuters, LexisNexis, Harvey)

### Takeaway
The legal incumbents rest generation on decades of **editorially enriched, structured corpora** (West Key Number taxonomy, headnotes, KeyCite/Shepard's citators, attorney-editor-curated practice content) plus citation verification, not on embeddings alone. Yet the only peer-reviewed independent test (Stanford RegLab/HAI, JELS 2025, data collected in spring 2024) found 17–33% hallucination rates and only 19–65% fully accurate answers, and found that a large share of failures came from **retrieval** (naive retrieval and inapplicable authority). Since then, measurement has moved to vendor-run, attorney-authored "ideal response" benchmarks (CoCoBench, BigLaw Bench) and the independent Vals reports. The two biggest incumbents opted out of the 2025 Vals legal research benchmark.

### Cited Findings

**Stanford RegLab/HAI study (Magesh, Surani, Dahl, Suzgun, Manning, Ho) [MEASURED-INDEP]**
- Peer-reviewed publication: *Journal of Empirical Legal Studies* 2025, vol. 22, pp. 216–242 (accepted 14 Mar 2025). The preprint was arXiv 2405.20362 (May 30, 2024). It was the first preregistered evaluation of AI legal research tools. — [Stanford NLP PDF](https://nlp.stanford.edu/~manning/papers/Magesh-Hallucination%E2%80%90Free-2025.pdf); [arXiv](https://arxiv.org/abs/2405.20362)
- Results per system (202 queries): Lexis+ AI was 65% accurate, 18% incomplete, ~17% hallucinated. Westlaw AI-Assisted Research was 41–42% accurate, 25% incomplete, ~33% hallucinated. Ask Practical Law AI was 19–20% accurate, 62% incomplete, ~17% hallucinated. GPT-4 hallucinated more than all three legal tools. — [arXiv HTML](https://arxiv.org/html/2405.20362); [JELS PDF](https://nlp.stanford.edu/~manning/papers/Magesh-Hallucination%E2%80%90Free-2025.pdf)
- Query mix: 80 general legal research, 70 jurisdiction- or time-specific, 22 false-premise, 30 factual recall. 20 queries came from LegalBench Rule QA and 20 from BARBRI; the other 162 were written by the authors. — [arXiv HTML](https://arxiv.org/html/2405.20362)
- Definitions: **hallucination = incorrect OR misgrounded**, where misgrounded means a cited source misstates the proposition or is inapplicable. Ungrounded (uncited) answers were coded as *incomplete*, not hallucinated. — [arXiv HTML](https://arxiv.org/html/2405.20362)
- Failure typology (Table 6, share of hallucinated responses; categories overlap):

  | Cause | Lexis+ AI | Westlaw | Practical Law |
  |---|---|---|---|
  | Naive retrieval | 47% | 20% | 34% |
  | Inapplicable authority | 38% | 23% | 34% |
  | Reasoning error | 28% | 61% | 49% |

  Retrieval is hard in law because relevance depends on jurisdiction, time and posture, not textual similarity, and textually similar but inapplicable documents distort answers. — [JELS PDF](https://nlp.stanford.edu/~manning/papers/Magesh-Hallucination%E2%80%90Free-2025.pdf); [arXiv HTML](https://arxiv.org/html/2405.20362)
- Conditions: Westlaw was queried May 23–27, 2024; the other tools Mar 22–Apr 22, 2024. Responses drifted over time, especially for Lexis+ AI. — [JELS PDF](https://nlp.stanford.edu/~manning/papers/Magesh-Hallucination%E2%80%90Free-2025.pdf)
- Caveats: Thomson Reuters said its internal testing showed lower hallucination rates. The study did not cover CoCounsel Legal (Aug 2025) or Protégé (Jan 2025). Lexis claimed its 2nd-gen tool's linked citations were "hallucination-free", and that version was not tested. In *U.S. v. Farris* (6th Cir. Apr. 3, 2026) a brief prepared with CoCounsel contained false quotations; the court held that citing real authorities did not excuse this. — [LLRX, Apr 2026](https://www.llrx.com/2026/04/hallucinations-by-west-lexis-ai/)

**Vals Legal AI Reports [MEASURED-INDEP, but opt-in]**
- Feb 2025 VLAIR covered 7 tasks against a lawyer baseline supplied by Cognia ALSP. Document Q&A: Harvey 94.8%, CoCounsel 89.6%, lawyers 70.1%. Chronology: Harvey 80.2%, matching lawyers. Redlining: lawyers (79.7%) beat every AI. EDGAR research: the best AI (Vecflow Oliver) scored 55.2% vs lawyers 70.1%. LexisNexis withdrew from the studied sections. Grading was blind auto-evaluation against model answers, with tasks set by firms such as Reed Smith and Fisher Phillips. — [Artificial Lawyer](https://www.artificiallawyer.com/2025/02/27/vals-publishes-results-of-first-legal-ai-benchmark-study/); [Report PDF (Berkeley mirror)](https://www.law.berkeley.edu/wp-content/uploads/archive/2025/12/VALs-AI-Legal-AI-report-February-2025-.pdf)
- Oct 2025 legal research VLAIR used 210 questions per tool. Accuracy: Counsel Stack 81%, Alexi 80%, ChatGPT 80%, Midpage 79%, lawyers 71%. Authoritativeness (citation quality): legal-AI average 76%, ChatGPT 70%. Multi-jurisdiction questions scored about 11 points lower. Thomson Reuters and LexisNexis declined to participate, and vLex withdrew before publication. — [LawSites](https://www.lawnext.com/2025/10/vals-ais-latest-benchmark-finds-legal-and-general-ai-now-outperform-lawyers-in-legal-research-accuracy.html)

**Thomson Reuters (Westlaw AI-Assisted Research, CoCounsel Legal)**
- Architecture [MARKETING/DOCS]: RAG over Westlaw "editor-enhanced primary law", using the West Key Number System, headnotes and KeyCite. Footnotes point to the passages used, and users are told to verify. — [TR blog](https://legal.thomsonreuters.com/blog/legal-research-meets-generative-ai/)
- CoCounsel Legal Deep Research (Aug 2025) is agentic: it builds a reviewable research plan and instructs agents to use Westlaw tools (Key Numbers, KeyCite, Precision Research markup, statute annotations). For firm DMS content it uses **federated search, not a central index**: an LLM rewrites the query, the query goes to each repository's native search, and AI reranks and summarizes the results. A hallucination checker flags possibly non-existent citations. — [LawSites, Aug 2025](https://www.lawnext.com/2025/08/thomson-reuters-launches-cocounsel-legal-with-agentic-ai-and-deep-research-capabilities-along-with-a-new-and-final-version-of-westlaw.html)
- Evaluation program [MEASURED-VENDOR, methods only]:
  - Attorney "Trust Team" tests use ideal-response grading: a test fails if it omits any detail the attorney marks "Critical".
  - More than 1,500 automated tests run nightly, and over 1M tests have run since launch.
  - An LLM judge is calibrated by attorneys, who review failures and spot-check passes. Tests are dropped when testers disagree. — [TR, Oct 2024](https://www.thomsonreuters.com/en-us/posts/innovation/legal-ai-benchmarking-cocounsel/)
- Attorney editors have run hundreds of evaluation sessions and graded thousands of responses. — [TR, Oct 2025](https://www.thomsonreuters.com/en-us/posts/innovation/the-brains-behind-the-bot-how-our-lawyers-shape-cocounsel/)
- CoCoBench (May 2026) [MEASURED-VENDOR]: hundreds of attorney-authored tasks with gold responses, built by 100+ legal SMEs over 15,000+ hours. It scores the citation record: what was cited, where it came from, and whether the source supports the claim. No accuracy numbers were published. — [TR CoCoBench](https://www.thomsonreuters.com/en-us/posts/innovation/why-legal-ai-needs-a-new-standard-inside-thomson-reuters-cocobench/)
- Aug 2026 result [MEASURED-VENDOR]: on 50 complex tasks (~6 lawyer-hours each), attorneys judged CoCounsel's output stronger than the expert reference on "nearly 40%" of tasks. Citation claims were sorted as supported, uncited, incorrect reasoning, fabricated, or misattributed. No overall accuracy or hallucination rate was reported. — [TR, Aug 2026](https://www.thomsonreuters.com/en-us/posts/innovation/when-legal-ai-is-evaluated-like-legal-work-the-results-change/)

**LexisNexis (Lexis+ AI / Protégé) [MARKETING]**
- Proprietary RAG over "authoritative legal content", processed through a multi-stage pipeline: semantic understanding, **recency filtering**, **authority ranking**, and citation validation. Citations link to sources, and unlinkable citations are flagged for manual check. Case law is "Shepard's-reviewed". No metrics are published. — [LexisNexis, May 2025](https://www.lexisnexis.com/community/insights/legal/b/thought-leadership/posts/legal-ai-citation-integrity)
- Protégé (2025) is a multi-agent system: an orchestrator that decomposes queries, a legal research agent, a **Reflection Agent** that reviews final answers, and a **Shepard's Citation Agent** that validates legal citations even in general-model (GPT-5) answers. No accuracy metrics. — [LawSites, Aug 2025](https://www.lawnext.com/2025/08/lexisnexis-launches-protege-general-ai-expanding-the-agentic-capabilities-of-its-ai-assistant-to-general-ai-models-such-as-gpt-5.html)

**Harvey**
- Retrieval infrastructure [DOCS/vendor blog]:
  - Corpus sizes: Assistant threads hold 1–50 docs, Vault projects 1k–10k docs, plus third-party legal data across 45 countries.
  - Vector store: LanceDB Enterprise in production (recall/latency tuning via IVF-PQ, VPC hosting, customer-owned buckets); pgvector for smaller or public projects. Benchmarks: 15M rows with metadata filtering at under 2 s P50 (LanceDB); 500K embeddings at under 2 s P50 (pgvector).
  - Embeddings are treated as being as sensitive as source documents. Enterprise deployments keep the vector DB in the customer's private cloud.
  - Harvey notes dense embeddings "struggle with rare terms like case identifiers and named entities".
  - No ground-truth datasets exist, so evaluation is built with domain experts. — [Harvey blog](https://www.harvey.ai/blog/enterprise-grade-rag-systems)
- Agentic search (Dec 2025): a ReAct loop of plan → per-source query formulation → retrieve → completeness check → loop → cited answer. Complex queries take 3–10 retrieval operations. **Tool-selection precision improved "from near zero to 0.8–0.9"**. Metrics tracked: hallucination, **tool recall, retrieval recall**, formatting, answer quality. Eval queries are written by ex-lawyer researchers, because no human may see customer queries. — [Harvey blog](https://www.harvey.ai/blog/how-agentic-search-unlocks-legal-research-intelligence)
- BigLaw Bench (Sep 2024) [MEASURED-VENDOR]: task-specific rubrics with positive points and negative points for hallucinations. A separate **Source Score** measures the share of required statements backed by an accurate reference to a specific document or passage. Harvey's models reached 74% of "lawyer-quality work product". Foundation models often fabricated sources when required to cite. — [Harvey BigLaw Bench](https://www.harvey.ai/blog/introducing-biglaw-bench)

### Inferences
- Legal leaders' moats are **structured enrichment + citator + authority/recency ranking**. The Stanford typology still shows that retrieving inapplicable or overruled authority is a dominant failure mode. For a "brain", "current-over-stale" needs an explicit citator-like layer (supersession/validity status per fact or document) applied at ranking time, not just embedding similarity.
- Even best-in-class legal RAG measured at 65% fully accurate (2024). No legal vendor publishes Recall@k for its retriever, and their evaluations are end-to-end answer grading. A ≥90% Context Recall@k standard is stricter and more retrieval-specific than anything these vendors publish.
- Harvey's choice of retrieval recall + tool recall + citation sets is the closest analogue to our metric design. Its "near zero → 0.8–0.9" tool-selection figure suggests that, in agentic setups, **routing recall** (did the agent query the right store?) must be measured separately from in-store retrieval recall.
- Thomson Reuters' federated-search approach (query the source system's own search, then rerank) is an alternative to central indexing that inherits source permissions automatically, at the cost of recall control.

### Gaps
- No published retriever-level recall figures (Recall@k, nDCG) from Thomson Reuters, LexisNexis or Harvey.
- No independent post-2024 replication of the Stanford study on CoCounsel Legal or Protégé was found. The incumbents declined the Oct 2025 Vals research benchmark.
- No public technical description of a Thomson Reuters or Lexis "knowledge graph" as used in RAG. Lexis docs do not mention one, and Thomson Reuters names Key Numbers/KeyCite only.
- No Vals 2026 legal research results were found.

---

## 2. E-discovery/compliance: TAR recall targets, validation protocols, and statistical certification of recall

### Takeaway
E-discovery is the only domain here with a **court-tested statistical recall-certification practice**. Courts accept "reasonable and proportional", not perfection. Agreed recall floors around 70–75% are common (Global Aerospace 75%, Insulin Pricing ≥70%), but no fixed legal threshold exists. The field has moved from elusion-only validation to **stratified sampling across all strata** (the *Broiler Chicken* protocol, now ordered in the Uber and Insulin Pricing MDLs), because elusion-only estimates can badly overstate recall. Leading researchers warn that recall above ~65–70% measured against an *independent* assessor approaches the ceiling of human agreement, so a 90% claim needs a carefully defined ground truth.

### Cited Findings

**Court thresholds and standards**
- *Global Aerospace* (Va. Cir. Ct., Loudoun County, 2012): the court set a **minimum 75% recall**. The producing party reported 81% recall and 80% precision. Training used 5,000 random docs from 1.3M, and ~173k docs were produced. — [Legal Technology](https://legaltechnology.com/ediscovery-us-judge-approves-predictive-coding-results/)
- Grossman & Cormack argue the Global Aerospace estimate ignored manual-review error: end-to-end recall was about **57% (81% × ~70%)**. They call 75% "an ill-specified acceptance criterion", not a validated standard, and warn that high average recall does not guarantee reliable recall. — [Grossman & Cormack chapter (IADC)](https://www.iadclaw.org/assets/1/7/10.2-_Grossman_and_Cormack_-_TAR_in_Electronic_Discovery.pdf)
- *In re Insulin Pricing Litig.* (D.N.J., MJ Singh, Apr 11, 2025): Express Scripts committed to **≥70% recall**, which the court found "sufficiently reasonable" (plaintiffs sought 70–80%+). The court **rejected an elusion set that excluded QC'd documents** and ordered validation "consistent with the validation process and recall calculation ordered in in re Broiler Chicken", including sampling the full TAR universe. — [eDiscovery Today](https://ediscoverytoday.com/2025/04/17/informal-discovery-dispute-as-to-tar-implementation-resolved-by-court-ediscovery-case-law/); [ACEDS](https://aceds.org/the-elusion-illusion-and-the-ai-revolution-aceds-blog/)
- *Uber MDL* (ECF 524, May 3, 2024) rejected elusion-only validation and required same-size samples from three populations. — [ACEDS](https://aceds.org/the-elusion-illusion-and-the-ai-revolution-aceds-blog/)
- *Rio Tinto v. Vale* (S.D.N.Y., MJ Peck, Mar 2, 2015): approved a protocol that reports estimated recall and precision "with their associated error margins", using a validation sample at ±2% margin of error and 95% confidence. It set no minimum recall and held it "inappropriate to hold TAR to a higher standard than keywords or manual review". — [Rio Tinto opinion PDF](https://www.steptoe.com/a/web/3oS1yD7SDvnQ7xm4REpsZf/3ZFuHj/20150303-rio-tinto-opinion-re-computer-assisted-review.pdf)
- Sedona TAR Case Law Primer (2d ed., 2023) quotes *Hyles v. NYC* ("the standard is not perfection, or using the 'best' tool"), *Da Silva Moore* ("the Federal Rules of Civil Procedure do not require perfection"), and *In re Diisocyanates* ("precision… is relatively less important than recall"). — [Sedona Primer PDF](https://thesedonaconference.org/sites/default/files/publications/Tar-Case-Law-Primer-2nd-Edition-2023.pdf)

**Validation protocols**
- *In re Broiler Chicken* (N.D. Ill., Jan 3, 2018; MJ Gilbert, Special Master Maura Grossman): the validation sample contains **500 docs coded responsive, 500 coded non-responsive, and 2,000 unreviewed (TAR-excluded) docs**. These are mixed into a blind set and reviewed by a subject-matter expert, and the coding table is disclosed to the opposing party. The Special Master warned against treating the recall percentage "as the sole indicator of an adequate review". — [ACEDS](https://aceds.org/tar-protocol-rules-the-roost-in-re-broiler-chicken/)
- Why elusion-only misleads. In a hypothetical 5M-doc example, elusion-only recall is 76% while stratified recall is 37%, because reviewer errors among reviewed docs are invisible to elusion sampling. In a 2024 Grossman et al. comparison, elusion-based recall exceeded stratified recall in all five cases (e.g., 94% vs 65%, 91% vs 55%). Multi-stage recall multiplies (search terms 50% × TAR 70% = 35%). — [ACEDS "Elusion Illusion"](https://aceds.org/the-elusion-illusion-and-the-ai-revolution-aceds-blog/)
- Sample sizing:
  - A fixed 95% confidence / ±5% margin gives 383 docs.
  - Sizing to a recall target is better. Example: for 75% minimum recall with 0.65% expected elusion, sample 1,078 docs; then, with 95% confidence, elusion is below 1.33% if no more than 7 of the 1,078 are responsive.
  - Use Wilson or Clopper-Pearson intervals. Report elusion-derived recall as a function of the elusion rate, not as a simple proportion confidence interval. — [ACEDS Part II](https://aceds.org/there-is-no-one-size-fits-all-sample-size-appropriate-for-tar-validation-part-ii/)
- Relativity aiR for Review validation [DOCS]:
  - Recall = TP/(TP+FN); precision = TP/(TP+FP); elusion = FN/(FN+TN); richness = (TP+FN)/N.
  - **95% Clopper-Pearson (exact, conservative) intervals**, which are asymmetric near 100%.
  - Human coding is treated as ground truth. Errored documents (score −1) are reported as an error rate.
  - The doc warns that the method does not detect human coding error. — [Relativity docs](https://help.relativity.com/RelativityOne/Content/Relativity/aiR_for_Review/aiR_for_Review_validation_statistics.htm)

**Measured GenAI review results**
- Redgrave study (Working Paper 2026-01, June 2026; not peer-reviewed) [MEASURED, interested authors]:
  - Corpus: 45,004 Mallinckrodt opioid docs. Ground truth: a blind expert coded a 1,000-doc sample, finding 73 responsive.
  - Recall: **aiR 88% (64/73)** vs managed Relativity Active Learning review **64% (47/73)**, even though RAL's own elusion test indicated 100% recall.
  - Effort: aiR prompts were iterated 43 times over ~18 hours, vs ~1,123 human review hours.
  - The 88% counts "Borderline" and error documents as positive. — [ComplexDiscovery](https://complexdiscovery.com/?p=68896); [ACEDS](https://aceds.org/the-elusion-illusion-and-the-ai-revolution-aceds-blog/)
- Cormack, Grossman & Pickens reanalysis (arXiv 2610.16925, Oct 12, 2026):
  - The two recall figures are "not comparable" because the arms measured different tasks.
  - "Filtered" task (first-level reviewers have the final say): RAL 64%, aiR 59.5%.
  - "Unfiltered" task: aiR 88%, RAL 97.2%.
  - A scalable continuous active learning (S-CAL) model trained on a 2,000-doc weighted sample matched aiR and reached an estimated 100% recall against the expert sample.
  - Expert-vs-reviewer agreement (Jaccard) was 0.27–0.42. Caveat: Cormack and Grossman hold a CAL patent. — [arXiv](https://arxiv.org/abs/2610.16925); [ComplexDiscovery](https://complexdiscovery.com/?p=68896)
- Everlaw Coding Suggestions [MEASURED-VENDOR, Sep 2024]: across 4 datasets (7,737 docs), precision 0.67 and **recall 0.89**. First-level human reviewers ranged 0.25–0.80 recall. On one dataset, GenAI recall was 0.82 vs human 0.60. — [Everlaw](https://www.everlaw.com/blog/ai-and-automation/genai-document-review-surpasses-human-performance-on-real-world-litigation)
- Historical baselines: the 2011 JOLT study found manual review averaged 59% recall / 32% precision vs TAR 77% / 85%. Voorhees found that two assessors share only ~67% of relevant docs, which puts a practical ceiling of ~65% recall at 65% precision when measured against an independent assessor. Exhaustive manual review is "at or near" 70% recall at best. — [Grossman & Cormack chapter](https://www.iadclaw.org/assets/1/7/10.2-_Grossman_and_Cormack_-_TAR_in_Electronic_Discovery.pdf)
- The Target Method achieved 70% recall with 95% reliability, at the cost of a large random sample. — [Grossman & Cormack chapter](https://www.iadclaw.org/assets/1/7/10.2-_Grossman_and_Cormack_-_TAR_in_Electronic_Discovery.pdf)

### Inferences
- **Directly transferable certification method for ">=90% Recall@k":**
  1. Define ground truth by blind expert labeling.
  2. Sample **stratified** across retrieved-in-top-k, retrieved-but-below-k, and never-retrieved items (Broiler Chicken style), not just the misses.
  3. Report a **lower one-sided 95% Clopper-Pearson or Wilson bound** per query class.
  4. Size samples to the target. Proving a lower bound ≥90% needs roughly 100+ positives per class with very few misses; for example, 0 misses in 29 queries gives a lower 95% bound of only ~90%.
  5. Multiply stage recalls for multi-stage pipelines (candidate generation × rerank × context packing).
- The courts' insistence on sampling the *full universe*, including QC'd and "known-good" sets, maps to our need to sample queries we believe are easy as well as hard ones.
- Inter-assessor agreement limits are real. Context Recall@k requires a crisp, item-level definition of "required items" (adjudicated by two raters plus a tie-break) or 90% is unmeasurable.
- Validation should also check the **end-to-end pipeline** (Redgrave/Cormack dispute): component recall can look perfect while workflow recall is 64%.

### Gaps
- I could not retrieve the Broiler Chicken order's exact recall formula text (secondary summaries only) or Sedona Primer Section V.B (recall figures across cases).
- No court has yet set a validation standard specific to GenAI review. The Redgrave and Cormack et al. work is the leading evidence and remains disputed.
- Reveal: no technical or validation evidence was gathered.

---

## 3. Enterprise search: permission enforcement, freshness, and published eval methods (Glean, Microsoft 365 Copilot, Google Gemini Enterprise, Atlassian Rovo)

### Takeaway
All four enforce permissions by **mirroring source-system ACLs and identities into the index and filtering at query time against the signed-in user**. None changes source permissions, so oversharing in the source becomes oversharing in AI answers, which is why Microsoft built Restricted Content Discovery. Freshness is connector-specific (webhooks plus hourly-to-daily incremental crawls, with full recrawls every 7–28 days), and permission-change latency is generally not guaranteed. Ranking is **hybrid lexical + semantic plus graph and activity signals**. Glean says lexical-with-recency handles 60–70% of queries and fine-tunes a per-customer embedding model. Published eval methods are online engagement metrics (Atlassian), LLM-judge RAG metrics calibrated to human agreement (Glean), and rarely any absolute recall numbers.

### Cited Findings

**Glean**
- Permissions [DOCS]:
  - Connectors ingest source ACLs, group memberships and roles during crawling. "At query time, Glean evaluates the signed-in user's identity against those mirrored permissions" before returning anything, and "Glean never grants broader access than the source system provides". Unreadable docs are never used as context or citations. — [Glean Security Principles](https://docs.glean.com/security/security-principles)
  - The Indexing SDK requires both per-document ACLs (`allowed_users`, `allowed_groups`, `allowed_group_intersections`) and identities via `get_identities()`. "An ACL naming a group Glean has never heard of matches nobody" (fail-closed). The SDK warns never to index sensitive content with an allow-all ACL temporarily, because fixing it later requires a full re-index. — [Glean Indexing SDK](https://developers.glean.com/libraries/indexing-sdk/permissions)
- Freshness defaults [DOCS]: values are defaults, not guarantees; "event notifications don't guarantee immediate search visibility"; no permission-change latency figure is given.

  | Connector | Incremental | Full crawl | Identity/groups |
  |---|---|---|---|
  | Google Drive | 3 h | 14-day discovery | 1 h |
  | Confluence | Webhook + 1 h | 7–30 days | — |
  | Jira | Webhook, 6 h | 28 days | 3 h |
  | SharePoint | Change notifications + 1 h | 28 days | — |

  — [Glean refresh rates](https://docs.glean.com/connectors/crawling-refresh-rates)
- Knowledge graph [DOCS]: content (with creator, timestamps, update history, folder), people (unified identities, teams, collaborators), and activity. Per-user activity data stays isolated; group aggregates are used only above privacy thresholds. — [Glean KG docs](https://docs.glean.com/security/knowledge-graph)
- Ranking [MARKETING]: hybrid search, with lexical for precision (IDs, titles) and semantic for recall. Signals include synonymy, intent and doc classification, term weighting, **freshness/staleness**, popularity and department. LLMs are given "caveats and deprecated results" context. — [Glean blog](https://www.glean.com/blog/hybrid-vs-rag-vector)
- Per-customer embeddings (talk by Glean's Manav, published Sep 2025) [vendor talk]:
  - Process: a BERT-based model gets continued pretraining on company data, is converted to an embedding model, and is retrained over time.
  - Training pairs: title–body, **anchor links**, **co-access** (docs opened together), Slack conversation windows, synthetic QA, plus query–click feedback.
  - "Unit tests" check specific behaviors (e.g., paraphrase invariance) against per-customer targets.
  - **Lexical + recency handles 60–70% of enterprise queries well**. Search quality improved ~20% after six months of feedback. — [jxnl.co writeup](https://jxnl.co/writing/2025/09/11/why-glean-builds-custom-embedding-models-for-every-customer/)
- Evaluation (Glean AI Evaluator) [MEASURED-VENDOR]:
  - Retrieval and generation are scored separately, loosely following RAGAS.
  - **Context relevance rate** = % of retrieved docs relevant. **Context recall rate** = % of queries where the canonical doc is retrieved.
  - Generation metrics: answer relevance, completeness (complete/incomplete/no-answer), and claim-level groundedness.
  - The LLM judge reached **74% agreement with humans vs 79% human–human agreement** (treated as the ceiling).
  - Recall sets are mined from sessions where unhappy users switched to search and refined their query, plus offline-mined QA pairs. Hard sets come from low-completeness queries.
  - Evaluator signals improved retention prediction by 18.8%. — [Glean blog](https://glean.com/blog/glean-ai-evaluator)

**Microsoft 365 Copilot**
- Semantic index [DOCS]: vector indices **complement** (not replace) the lexical Graph index.
  - The **tenant-level index** covers SharePoint text files and connector data.
  - The **user-level index** covers a user's working set: mailbox, docs that mention them, and docs they've shared or commented on.
  - Results are only those the user can access. Content shared via an "everyone in org" link is *not* added to the tenant index, only to the user index of people who opened it.
  - Freshness: user-created docs are indexed near real time; new docs on SharePoint sites with 2+ users are indexed **daily**; updates to already-indexed docs are indexed immediately. — [Microsoft Learn: Semantic indexing](https://learn.microsoft.com/en-us/microsoftsearch/semantic-index-for-copilot)
- Grounding flow: prompt → Graph + semantic index → modified prompt → LLM → Graph/index again for post-processing. — [Microsoft Learn](https://learn.microsoft.com/en-us/microsoftsearch/semantic-index-for-copilot)
- Permissions [DOCS]: "Copilot can only summarize or reference content that the user is authorized to access."
  - For encrypted or labeled content the user must hold **EXTRACT and VIEW** usage rights.
  - Outputs inherit the highest-priority sensitivity label of their sources.
  - User-defined label permissions block Copilot agents. — [Microsoft Learn: architecture & data protection](https://learn.microsoft.com/en-us/copilot/microsoft-365/microsoft-365-copilot-architecture-data-protection-auditing)
- Oversharing control [DOCS]: **Restricted Content Discovery** (`Set-SPOSite -RestrictContentOrgWideSearch $true`) hides a site from org-wide search and Copilot without changing permissions. It does not remove the site from the index. Sites with >500k items may take **over a week** to reflect the change. Microsoft frames it as a temporary governance control and warns it reduces answer completeness. — [Microsoft Learn: RCD](https://learn.microsoft.com/en-us/sharepoint/restricted-content-discovery)

**Google Gemini Enterprise (formerly Agentspace)** [DOCS]
- Custom data stores carry per-document `acl_info.readers.principals` (user_id/group_id) and must be created with `aclEnabled: true`. The searcher's identity comes from the IdP or workforce pool and is matched at query time. ACL import is supported only for Cloud Storage and BigQuery with the predefined schema. ACL refresh cadence is not stated. — [Google Cloud docs](https://docs.cloud.google.com/gemini/enterprise/docs/identity)

**Atlassian Rovo** [MEASURED-VENDOR, online only]
- Primary metric: a composite online engagement metric built on "long clicks" (dwell, or a post-click action such as comment or edit), discounted for lower positions. AI answers are judged on engagement, dwell and post-search actions.
- Results: ~10% improvement since Jan 2025; P90 latency down 300 ms. An A/B test claimed "60% more successful results" than the next enterprise search tool, with success undefined.
- Ranking uses collaborators' recent views, sharing and commenting from the Teamwork Graph. Google Drive recall improved by indexing viewed-and-accessible content. — [Atlassian blog](https://www.atlassian.com/blog/rovo/rovo-search-quality)

**Industry precedent for LLM relevance labels**
- Bing (Thomas, Spielman, Craswell, Mitra, SIGIR 2024) found LLM labels "as accurate as human labellers" when the prompt is validated against first-party gold labels. Cohen's κ vs TREC gold was 0.20–0.60 depending on prompt, and results vary unpredictably with paraphrase, which is why gold sets remain essential. — [arXiv 2309.10621](https://arxiv.org/html/2309.10621v3)

### Inferences
- The universal permission pattern is **index-time ACL capture + query-time identity filtering + fail-closed on unknown principals**. Glean's "unknown group matches nobody" and "never allow-all temporarily" are concrete rules we should copy. For zero cross-tenant leakage, add a **hard tenant partition** (separate index or namespace per tenant) beneath per-document ACLs. Harvey and Glean both keep per-customer storage and projects.
- Permission freshness is the weak spot everywhere: Glean's identity crawl runs every 1–3 h, Microsoft's RCD can take over a week, and Google states no cadence. A "brain" should treat **ACL revocation as an event that must propagate in bounded time**, and should test leakage with canary documents after permission changes.
- Glean's metric definitions match our target closely: "context recall rate = % of queries where the canonical doc is retrieved" is a single-item version of our all-required-items Context Recall@k. Its judge-calibration method (judge–human agreement benchmarked against human–human agreement, 74% vs 79%) is a template for validating any LLM judge we use.
- Freshness as a ranking feature (Glean) and "deprecated result" caveats in context are the enterprise analogue of a legal citator.
- Mining recall test sets from failure sessions (Glean) and from support tickets and feedback (Harvey) is how the leaders build golden sets without reading private queries.

### Gaps
- No published absolute retrieval recall or nDCG for Glean, Copilot, Gemini Enterprise or Rovo.
- Microsoft has not published Copilot retrieval eval methodology in the sources I found.
- No source states guaranteed permission-revocation propagation latency for any of the four.
- Google Gemini Enterprise ranking and freshness internals were not found.

---

## 4. Finance & data: Bloomberg, Palantir (Ontology), AlphaSense

### Takeaway
Palantir's Ontology is the most "brain-relevant" architecture found. It holds **typed objects, properties and links (nouns), actions (verbs), and functions**, with **row-level (object) and column-level (property) security policies computed at runtime**, markings that propagate through pipelines, and agent memory stored in the Ontology under the same policies. LLMs get Ontology-scoped tools (Ontology-Augmented Generation), not free-text RAG alone. Bloomberg and AlphaSense publish almost nothing about retrieval accuracy. Bloomberg's research shows a production orientation toward **learned sparse retrieval at BM25 latency**, and its agentic ASKB cites source and timestamp on every answer.

### Cited Findings

**Palantir**
- Ontology model [DOCS]: enterprise data is unified into "objects, properties, and links which evolve in real-time" (the semantic layer, "the nouns"). Actions are "the verbs (the kinetic, real-world execution)". Deterministic functions sit alongside LLM reasoning. Access policies are "marking-, purpose-, and role-based" and computed at runtime. Writeback and **decision lineage** record when a decision was made, which data version it used, and which application was involved. — [Palantir docs: Why Ontology](https://www.palantir.com/docs/foundry/ontology/why-ontology)
- Object security [DOCS]:
  - "The visibility of an object instance is governed by its object security policy, whereas the visibility of a property value is governed by its property security policy". Together this is **cell-level security**, managed independently of backing datasets.
  - Policy changes take effect almost immediately; restricted views need a pipeline rebuild.
  - Object/property policies are **read-time only** and "do not extend to downstream outputs or exports". Markings or classification-based access control (CBAC) are needed for downstream protection.
  - Caveat: if a property references a media set with different permissions, a user may be blocked from the property but still fetch the media directly. — [Palantir docs: Managing object security](https://www.palantir.com/docs/foundry/object-permissioning/managing-object-security/)
- Ontology resources (object, link and action types) are permissioned separately from the data (object and link instances). — [Palantir docs](https://palantir.com/docs/foundry/object-permissioning/overview/)
- OAG [vendor blog]: "a more expansive, decision-centric version" of RAG. LLMs get Ontology data tools plus deterministic logic tools and actions, and objects in prompts carry their links and relationships. Fine-grained controls apply "to both users and AI". — [Palantir blog: Data tools for RAG/OAG](https://blog.palantir.com/building-with-palantir-aip-data-tools-for-rag-oag-b3b509c8b0f3)
- Semantic search in AIP [vendor blog]: embeddings are stored as a vector property on an object type and queried with `nearestNeighbors(kValue)` over an object set, then exposed to an LLM as a tool in AIP Logic. Vector KNN is shown; hybrid search is not. — [Palantir blog: Semantic search](https://blog.palantir.com/building-with-palantir-aip-semantic-search-dc3adf40f6a6)
- Agent security [vendor blog]:
  - An agent's permissions combine the configuring owner, a service user or OSDK scope, and the human it is acting for.
  - Granular policies are "dynamically computed at runtime for every interaction".
  - Agent **memory (working, episodic, semantic, procedural) is stored in the Ontology under the same policies**.
  - Tool calls require access to the underlying objects, properties and links, plus "granular submission criteria". Provenance-based security blocks marked data from flowing into unsanctioned executions. — [Palantir blog: Securing agents](https://blog.palantir.com/securing-agents-in-production-agentic-runtime-1-5191a0715240)

**Bloomberg**
- ASKB (beta from 2025, opening to all 375k Terminal seats per an Oct 2026 report): specialized agents search documents, news, analytics and alt-data in parallel. **Each answer cites the original source and timestamp.** Data answers return the underlying BQL code. Client uploads are kept separate from Terminal data. No accuracy claims. — [AI Weekly (citing WSJ CIO Journal), Oct 15, 2026](https://aiweekly.co/alerts/bloomberg-opens-askb-agentic-ai-interface-to-all-terminal-users-with-custom)
- AI document search and analysis (late 2025): Q&A across transcripts, research and user documents, plus comparison tables that can be rerun for fresh data. No accuracy or eval data. — [IT Brew, Nov 2025](https://www.itbrew.com/stories/2025/11/19/bloomberg-new-ai-tool-for-terminal)
- SIGIR 2025 research [MEASURED, research]: DF-FLOPS regularization makes SPLADE-Doc learned sparse retrieval **~10× faster, reaching BM25-level latency for Apache Solr**. It cost −2.2 MRR@10 on MS MARCO and improved 12 of 13 BEIR datasets. An agentic topic-ontology paper for earnings calls also appeared at FinIR 2025. — [Tech at Bloomberg](https://www.bloomberg.com/company/stories/bloomberg-ai-engineers-publish-3-information-retrieval-research-papers-sigir-2025)

**AlphaSense** [MARKETING]
- Generative Search uses a multi-agent architecture over broker research, expert calls, filings, news, internal docs and structured financial data, with "sources fully cited and auditable". No retrieval method or accuracy metrics are published. — [AlphaSense](https://www.alpha-sense.com/resources/product-articles/generative-search-next-generation/)

### Inferences
- The Palantir Ontology maps directly onto a "brain" design:
  - **Typed entities and links** with **row/column/cell policies evaluated per request**.
  - Agent memory stored *inside* the same permissioned object model (no side-channel vector store with weaker ACLs).
  - Embeddings stored as properties on governed objects, so vector hits inherit object security.
  - Decision lineage with data versions, which supports current-over-stale and audit.
- Palantir's explicit caveats are design warnings for us. Read-time policies don't protect exports or derived data, and linked media can bypass property-level controls. Derived artifacts (summaries, embeddings, cached contexts) must inherit the strictest source label, just as Microsoft does with sensitivity-label inheritance.
- Bloomberg's per-answer source **timestamps** and investment in learned sparse retrieval point to lexical-family retrieval plus provenance as the production baseline in finance, with embeddings as an addition.

### Gaps
- No published retrieval accuracy for Bloomberg, AlphaSense or Palantir AIP.
- No official Palantir doc retrieved that states verbatim that AIP Logic tool calls are filtered by the invoking user's object policies (the community thread was unanswered). The securing-agents blog implies it.
- BloombergGPT was not revisited; it is a 2023 model, not retrieval-specific.

---

## 5. Healthcare records retrieval (Epic, Abridge)

### Takeaway
Evidence is thin for retrieval over EHRs specifically. The strongest published practice is Abridge's **claim-level evidence linking and support classification**, a verification layer rather than a retriever. Abridge's vendor benchmark reports 97% detection of unsupported claims vs 82% for GPT-4o. I found no quantified Epic retrieval or summarization accuracy, only a registered evaluation.

### Cited Findings
- Abridge "Linked Evidence": the clinician highlights note text and the supporting transcript span and audio are surfaced. — [Abridge support](https://support.abridge.com/hc/en-us/articles/30235128433811-Verify-a-Note-With-Linked-Evidence)
- Abridge confabulation pipeline [MEASURED-VENDOR]:
  - An in-house model checks each claim against the transcript and EHR context and writes its reasoning.
  - Five support classes: directly supported; reasonable inference; questionable inference; unmentioned; contradiction.
  - Severity scale: major, moderate, minimal.
  - A second system corrects, deletes or dismisses flagged claims, and clinicians review every note.
  - The model was trained on 50k+ examples and benchmarked on 10k+ encounters, with 1,000+ physician annotation hours.
  - **Detection: 97% vs GPT-4o 82%.** Precision and false-positive rates were not reported. — [Abridge whitepaper page](https://www.abridge.com/ai/science-confabulation-hallucination-elimination); [Abridge blog](https://www.abridge.com/blog/hallucinations-whitepaper)
- Academic: zero-shot LLM evidence retrieval from EHR notes was preferred by experts over a pre-LLM IR baseline. Hallucination was the main open problem, and model confidence correlated with faithfulness. — [Ahsan et al., arXiv 2309.04550 / CHIL 2024](https://arxiv.org/abs/2309.04550)
- Epic: a ClinicalTrials.gov registration exists for "An Evaluation of Epic EHR AI Outpatient Chart Summarization" (NCT07438743), but the record content could not be retrieved. — [ClinicalTrials.gov](https://clinicaltrials.gov/study/NCT07438743)

### Inferences
- Abridge's support classes are a reusable rubric for a "brain" answer layer: score every claim against retrieved evidence and fail closed on "unmentioned" or "contradiction". This complements Context Recall@k (retrieval) with a groundedness gate (generation). Note that its headline metric is detection recall, which mirrors our recall-first stance.

### Gaps
- No Epic technical or accuracy disclosures on chart search or retrieval were found.
- Abridge's evidence-linking method (alignment algorithm) and precision are undisclosed.

---

## 6. Cross-cutting: embeddings vs structured data/entity resolution/editorial metadata/lexical search, and how leaders measure

### Takeaway
None of the leaders relies on embeddings alone. The consistent pattern is **lexical/sparse retrieval + structured metadata and entity/graph signals + editorial or authority layers + embeddings as a recall booster + verification of citations**. Measurement relies on **attorney or expert gold sets with ideal-response or rubric grading**, **LLM judges calibrated against human agreement**, **online engagement A/B metrics**, and (in e-discovery only) **statistically certified recall with confidence intervals**. Retriever-level Recall@k is almost never published.

### Cited Findings
- Legal: Westlaw grounds on Key Numbers, headnotes and KeyCite ([TR](https://legal.thomsonreuters.com/blog/legal-research-meets-generative-ai/)). Lexis uses recency filtering, authority ranking and Shepard's validation ([LexisNexis](https://www.lexisnexis.com/community/insights/legal/b/thought-leadership/posts/legal-ai-citation-integrity)). Harvey notes dense embeddings miss case identifiers and entities ([Harvey](https://www.harvey.ai/blog/enterprise-grade-rag-systems)).
- Enterprise: Glean says lexical + recency handles 60–70% of queries, and uses per-customer fine-tuned embeddings plus graph signals ([jxnl.co](https://jxnl.co/writing/2025/09/11/why-glean-builds-custom-embedding-models-for-every-customer/); [Glean](https://www.glean.com/blog/hybrid-vs-rag-vector)). Microsoft's semantic index complements the lexical Graph index ([Microsoft Learn](https://learn.microsoft.com/en-us/microsoftsearch/semantic-index-for-copilot)).
- Finance: Bloomberg productionizes learned sparse retrieval at BM25 latency ([Bloomberg](https://www.bloomberg.com/company/stories/bloomberg-ai-engineers-publish-3-information-retrieval-research-papers-sigir-2025)).
- Data platforms: Palantir uses typed objects and links with embeddings as one object property ([Palantir](https://blog.palantir.com/building-with-palantir-aip-semantic-search-dc3adf40f6a6)).
- Measurement methods:
  - Thomson Reuters runs ideal-response attorney grading, 1,500 nightly automated tests, and an attorney-calibrated LLM judge ([TR](https://www.thomsonreuters.com/en-us/posts/innovation/legal-ai-benchmarking-cocounsel/)).
  - Harvey uses rubric plus Source Score ([Harvey](https://www.harvey.ai/blog/introducing-biglaw-bench)) and retrieval and tool recall for agents ([Harvey](https://www.harvey.ai/blog/how-agentic-search-unlocks-legal-research-intelligence)).
  - Glean reports context recall rate and judge–human agreement ([Glean](https://glean.com/blog/glean-ai-evaluator)).
  - Atlassian measures long-click online metrics in A/B tests ([Atlassian](https://www.atlassian.com/blog/rovo/rovo-search-quality)).
  - Bing validates LLM relevance labels against gold ([arXiv](https://arxiv.org/html/2309.10621v3)).
  - E-discovery uses stratified sampling with Clopper-Pearson or Wilson bounds ([Relativity](https://help.relativity.com/RelativityOne/Content/Relativity/aiR_for_Review/aiR_for_Review_validation_statistics.htm); [ACEDS](https://aceds.org/there-is-no-one-size-fits-all-sample-size-appropriate-for-tar-validation-part-ii/)).
- Interleaving: no source found in which these specific vendors describe interleaving experiments. Atlassian describes A/B tests only.

### Inferences
**Practices that transfer to a ≥90% Context Recall@k, zero-leakage, current-over-stale brain:**
1. **Hybrid first-stage retrieval is non-negotiable.** Use BM25 or learned sparse retrieval for IDs, names and rare terms, dense retrieval for paraphrase, and entity/graph expansion for linked items. Report per-stage recall and multiply the stages.
2. **A citator layer for staleness.** Every fact or document carries validity status (current, superseded-by, deprecated) and a timestamp. Rank and filter on it, and surface timestamps in answers (Lexis recency filter, KeyCite/Shepard's, Glean freshness, Bloomberg timestamps).
3. **Typed object model with cell-level, runtime-evaluated policies** (Palantir). Store embeddings and agent memory as governed properties, so retrieval cannot bypass ACLs. Derived artifacts inherit the strictest source label (Microsoft label inheritance).
4. **Fail-closed ACL semantics.** Unknown principal matches nobody, and never index with allow-all temporarily (Glean). Add a physical or namespace tenant partition beneath ACLs, plus bounded-latency revocation propagation tested with canary documents.
5. **Recall certification à la TAR.** Use blind expert gold labels, stratified sampling (top-k hits, near-misses, and never-retrieved), one-sided 95% Clopper-Pearson lower bounds per query class, and sample sizes chosen for the target bound. Never rely on miss-pile (elusion-style) sampling alone.
6. **Calibrated LLM judges.** Measure judge–human agreement against human–human agreement (Glean 74% vs 79%; Bing κ up to ~0.6) on first-party gold before trusting automated recall labels.
7. **Golden sets mined from failure signals.** Use reformulated searches (Glean), support tickets and feedback (Harvey), and expert-authored tasks (Thomson Reuters/Harvey), plus "unit tests" for specific behaviors such as paraphrase invariance (Glean).
8. **A claim-level grounding gate** using Abridge's five support classes and Harvey's Source Score, so recall failures downstream are caught.
9. **For agentic retrieval, measure routing/tool recall separately** (Harvey: 0.8–0.9 tool-selection precision after tuning).

### Gaps
- No vendor in scope publishes a retriever-level Recall@k at a ≥90% standard. The 90% target exceeds publicly evidenced practice, and the closest certified-recall culture (TAR) generally accepts 70–80%.
- Interleaving usage by these vendors is undocumented in public sources.
- No quantitative head-to-head published by any leader comparing embedding-only vs hybrid on its own corpus (only Glean's qualitative 60–70% lexical estimate).
