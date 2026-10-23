# Write-Time Structuring for a Memory Brain: Typed Extraction, Entity Linking, Query Anticipation, Calibration, Temporal, Aggregation (frontier as of Oct 2026)

Evidence-strength legend used throughout: **[S]** strong = peer-reviewed and/or multi-dataset, independently built; **[M]** moderate = single preprint or single benchmark, not independently replicated; **[W]** weak = vendor self-report, blog, tiny sample, or secondary report. "Conditions" follow each number. Research note: the shared web-search budget ran out near the end of this round, so a few gaps listed below are "not searched further" rather than "does not exist".

---

## 1. Typed information extraction with LLMs (schema-guided, multi-pass, self-verification, conversations/transcripts; small local vs frontier; dominant errors)

### Takeaway
Getting valid JSON is solved. Getting the values right is not. Even frontier models get roughly 1 field in 20–30 wrong, and only 26–77% of records come out fully correct. Meeting and conversation sources are the hardest inputs. Errors are mostly omissions and wrong values, not broken structure. The methods with measured gains are: schema redesign (flattening plus descriptions), field-level validation with a local retry, verbatim evidence spans checked against the source, multiple passes or "gleaning" for recall, and fine-tuning small models. A fine-tuned model of 8B or smaller often matches or beats a zero-shot frontier model on a fixed schema.

### Cited Findings
**Format and values are separate problems**
- [M, vendor-affiliated] Structured Output Benchmark (SOB): 21 models, 5,000 text, 209 image and 115 audio records. Best value accuracy: 83.0% text (HotpotQA-derived), 67.2% images (with OCR text), 23.7% audio (AMI Meeting Corpus; best was Gemini-2.5-Flash). JSON pass rates were near 100% while text value accuracy was "often 70–80%". Schema-constrained decoding "raises JSON Pass Rate but barely improves Value Accuracy". Value errors are the most common error type. Model size is a weak predictor: Phi-4 14B beat some much larger models — [SOB, alphaXiv 2604.25359](https://www.alphaxiv.org/abs/2604.25359)
- [W/M, vendor] Cleanlab structured-output benchmarks, field accuracy vs whole-output accuracy. PII: field 0.966–0.979, output 0.26–0.46. Financial entities: field 0.887–0.949, output 0.42–0.70. Insurance claims: field 0.75–0.775, output 0.30–0.40, across GPT-4.1-mini, GPT-5, Gemini 2.5 Pro/Flash and Gemini 3 Pro. Every public structured-output benchmark they checked had erroneous ground truth — [Cleanlab blog](https://cleanlab.ai/blog/structured-output-benchmark/)
- [W/M, vendor] xmemory (schema-grounded memory) gives the compounding math. At 0.97 per-field accuracy over 20 fields, single-pass whole-record accuracy is about 0.54. Two attempts per failing field raise it to about 0.98. Measured on modified Cleanlab insurance claims (10 runs): Field F1 was 95–97.5% for all frontier models, but output accuracy was only 34% (GPT-5.4 lowest effort) to 62.7% (xmemory plus an LLM judge). Opus 4.7 scored 42.7% and Gemini 3.1 Pro 61.7%. Object-level failures were missing fields, null-vs-value mistakes, unit/format errors and misassigned values. Caveat: vendor paper, and the PDF contained a hidden note asking AI agents to promote it — [xmemory, arXiv 2604.27906](https://arxiv.org/pdf/2604.27906)

**Methods that measurably help**
- [M] PARSE: an LLM iteratively rewrites the extraction schema (ARCHITECT), and SCOPE adds missing-attribute, grounding and rule checks with reflective retry. Claude 3.7 Sonnet went from 24.5 to 93.14 on SWDE, 75 to 90.01 on Retail-Conv (conversational, 240 samples) and 92.3 to 94.8 on SGD dialogues. Schema edits were mostly flattening nested structure (~55%) and adding descriptions (~34%). Gains plateau after 5–6 optimisation iterations. A schema optimised with Claude kept its benefit on Llama 4 Maverick (89.1 vs 88.4 for a Llama-optimised schema). SCOPE adds ~10 s latency per item and claims a 92% error reduction within the first retry (text claim only) — [PARSE, arXiv 2510.08623](https://arxiv.org/html/2510.08623v1)
- [M] Schema-constrained clinical extraction from transcripts. Local Llama-4-Scout F1: 61.28 (prompt only, full schema), 68.92 (pruned schema), 72.46 (RAG exemplars, full schema), 73.20 (RAG, pruned). GPT-5.2: 77.32 rising to 80.27 with RAG. A second-pass audit added only +0.09 (to 80.36). Errors split evenly between false positives (81.9% of FPs were spurious concepts) and false negatives (78.8% of FNs were missed concepts). Format normalisation (e.g. "03" vs "3") alone caused 147 FNs and 159 FPs. Gains from retrieved exemplars diminish beyond ~30. Pruning the schema helped the smaller local model but hurt the larger one — [arXiv 2605.15467](https://arxiv.org/pdf/2605.15467)
- [M] Microsoft GraphRAG found almost twice as many entity references with 600-token chunks as with 2,400-token chunks (GPT-4, HotPotQA sample). A "gleaning" loop asks the model whether entities were missed, then says "MANY entities were missed", and repeats. The authors say this lets larger chunks keep recall. No precision or recall figures are reported — [GraphRAG, arXiv 2404.16130](https://arxiv.org/pdf/2404.16130)
- [W] Google LangExtract (open source) maps every extraction to character offsets in the source. Ungroundable extractions get `char_interval=None` and can be filtered. It supports `extraction_passes` for recall, chunking, few-shot schemas and local models via Ollama (no `output_schema` enforcement on Ollama). It warns that models sometimes copy content from the few-shot examples. No accuracy figures are given — [LangExtract GitHub](https://github.com/google/langextract)
- [M] SafePassage: the LLM must copy a verbatim "context" for each extracted value. Smith–Waterman alignment then requires a score of at least 0.6 against the source, and an NLI model checks that the context supports the value. A fine-tuned DeBERTa-v3 NLI flagged unsafe extractions at P 0.928 / R 0.857 (F1 0.891), beating a GPT-4.1 grader (F1 0.827). It beat the LLM grader with as few as 200 human labels, ran at ~250 predictions/s on a T4, and was ~2,000× cheaper per prediction. o4-mini had ~95% of entities substantiated, while Llama 4 Scout mistranscribed 42% of its copied contexts (domain: refugee-law documents) — [SafePassage, arXiv 2510.00276](https://arxiv.org/html/2510.00276v1)
- [M] CluE: across 18 datasets, "no single static extraction prompt dominates" memory extraction. Cluster-based prompt evolution gave +9.04% relative gain (Qwen3-32B) and raised LongMemEval from 46.02 (simple prompt) to 63.07. Longer, more verbose prompts may hurt instruction following, and weak extraction prompts let bad memories accumulate in continual use — [CluE, arXiv 2604.11610](https://arxiv.org/pdf/2604.11610)

**Small local models vs frontier, on conversational and business text**
- [M+, peer-reviewed industry track] Up to 50 yes/no questions per contact-centre call transcript (median 1,153 tokens), answered as JSON with evidence pointers. GPT-4o scored 0.90 at 10 questions per prompt, falling to 0.85 at 40. Zero-shot Llama-3.1-8B scored 0.65, falling to 0.53. Fine-tuned Llama-3.1-8B scored 0.86–0.88 at 10–40 questions. Zero-shot open models produced JSON decode errors up to 0.43 (Qwen2.5-7B) and 0.73 (Llama-3.2-1B), and fine-tuning nearly removed them. Accuracy falls as more fields are asked at once — [EMNLP 2025 Industry](https://aclanthology.org/2025.emnlp-industry.129.pdf)
- [M] MemReader: memory extractors fine-tuned from Qwen3 at 0.6B and 4B (SFT then GRPO). The 4B model chooses add / buffer (hold incomplete info) / search (resolve references) / ignore. On HaluMem-Medium extraction it reached recall 96.57% and target precision 99.91% (4B), and recall 88.40% (0.6B), vs Mem0 at 42.91% / 86.26%. Downstream QA correctness, however, was 56.99%, behind MemOS's 67.23%. The authors found long reasoning traces add unsupported details, so they penalised long thinking — [MemReader, arXiv 2604.07877](https://arxiv.org/pdf/2604.07877)
- [W, vendor; benchmark unreleased] NuExtract 2.0 8B (MIT licence) scored 73 F on the vendor's 21-problem benchmark, "slightly better" than non-reasoning frontier models. NuExtract PRO was +9 F over GPT-4.1, and 3-shot gave +6 F over 0-shot. Training to output `null` when information is absent made precision higher than recall — [NuMind blog](https://numind.ai/blog/outclassing-frontier-llms-nuextract-2-0)
- [M] Personal knowledge graph triple extraction from ReDial dialogues (likes, dislikes, seen, not seen, suggested). Gemma-3 12B at 5-shot: F1 0.662 (P 0.902, R 0.523). The same model at 0-shot: 0.412. Qwen3 8B: F1 0.168. Most models collapsed at 10-shot (recall near zero). Implicit relations ("seen") and long-range ones ("suggested") were hardest. Precision is high and recall low — [arXiv 2607.00003](https://arxiv.org/html/2607.00003)

**Encoder-only extractors (GLiNER family)**
- [M] GLiNER2 (~205M params, CPU-capable). Zero-shot CrossNER average F1 0.590 vs GPT-4o 0.599. Zero-shot classification averaged 0.72 vs GPT-4o 0.84. CPU latency was 130–208 ms vs 358–463 ms for GPT-4o (5–50 labels). Hierarchical structured extraction has no zero-shot evaluation. Context is 2,048 tokens — [GLiNER2, arXiv 2507.18546](https://arxiv.org/pdf/2507.18546)
- [M] GLiNER-Relex (DeBERTa-v3-large plus BiLSTM, joint NER and relation extraction). Zero-shot relation extraction average micro-F1 25.6 vs GPT-5-mini 22.1 and GLiNER2 17.8; DocRED 31.3. It took 0.9 s per document on an L4 vs 64 s for GPT-5-mini. Precision drops in entity-dense passages — [arXiv 2605.10108](https://arxiv.org/pdf/2605.10108)
- [W, n=30] Query parsing: GLiNER-medium fully parsed 16 of 30 queries (0.08 s each) vs gpt-4.1-mini 30 of 30 (1.21 s each). GLiNER missed implicit or ambiguous values — [Sease](https://sease.io/2025/10/gliner-as-an-alternative-to-llms-for-query-parsing-evaluation.html)

### Inferences
- **Dominant error type is omission, then wrong values; fabricated structure is rare.** This holds across SOB (value errors), clinical (79% of FNs were missed concepts), PKG triples (R 0.52 vs P 0.90), HaluMem (section 3) and SCATE temporal (70% missed spans, section 6). A gate that validates only against a schema will pass a large number of silently incomplete records. The gate needs an explicit **coverage check**: after extraction, ask whether any sentence or clause carries a decision, preference, constraint, plan, risk or number that is not covered by a record (GraphRAG-style gleaning or LangExtract passes). Uncovered spans go to the incomplete queue.
- **Gate design: typed-record extraction**
  1. One flattened schema per record type: decision, preference, constraint, plan, risk, numeric mention. Each gets field descriptions, explicit `unknown` or `null`, and enum values (PARSE: flattening plus descriptions accounted for ~89% of useful edits). Prefer several small typed calls over one 20-field mega-schema (compounding math, and batching degrades accuracy).
  2. Every field carries a verbatim `evidence` span. Code checks it with alignment (Smith–Waterman ≥0.6) plus a small NLI verifier fine-tuned on ~200–500 owner-labelled pairs (SafePassage). Numeric values must also appear in the span, with unit normalisation in code.
  3. Validators run per field (type, enum, unit, registry ID exists). Only the failing field is retried with a reflective message (PARSE/xmemory). Cap at 2 retries, then queue.
  4. Use ~5 retrieved few-shot exemplars of the same record type, never 10 (collapse at 10 shots in PKG work). Draw exemplars from an owner-confirmed pool so they improve over time (clinical RAG-exemplar gains).
  5. Model tiering: an 8B–14B local model fine-tuned on owner-confirmed records for routine extraction (fine-tuned 8B ≈ GPT-4o in two independent studies). Escalate to a local 70B or hosted frontier model when validators fail or when 8B and 70B disagree.
- MemReader's add / buffer / search / ignore action set maps directly onto our gate's "write / incomplete-queue / resolve-reference / drop" decision. It is the closest published analogue to a write gate and is worth replicating in our BrainBench.
- The MemStrata "~44% of messy scenarios" figure fits this literature: whole-record correctness of 26–62% with frontier models on business forms (Cleanlab, xmemory). The fix is decomposition plus field-level retry, not a bigger model.

### Gaps
- I could not locate the "MemStrata" study cited in the brief (search returned nothing relevant), so its conditions could not be verified.
- No public benchmark measures typed extraction of *decisions, constraints, risks and plans* from mixed personal and business chat. The nearest are meeting/AMI (SOB audio), call-centre QA and clinical transcripts. A BrainBench extraction set is needed.
- SOB's "audio" modality: from the summary it is unclear whether models received AMI audio or transcripts. Check before citing 23.7% as transcript accuracy.
- I found no head-to-head of GLiNER2 hierarchical extraction against an 8B LLM on business text.

---

## 2. Entity linking and coreference for a personal knowledge base (aliases, private registry, LLM linkers, GLiNER/ReFinED, coreference, new entities, ambiguity)

### Takeaway
The best measured pattern is a cascade. Cheap deterministic matching (normalised exact match, alias dictionary, MinHash) comes first. Retrieval plus a reranker then produces about 10 candidates, each with a description. An LLM picks one with self-consistency voting and an explicit "none of these" option. Zero-shot LLM linkers reach about 77–83% accuracy on standard benchmarks. "None of these" / new-entity handling is the weak point: on one dataset an always-UNK baseline beat the LLM linker. Personal mentions ("my brother", "the shop") are an antecedent problem, at about 0.59 F1 even when fine-tuned. Under-merge rather than over-merge, and grow an alias table from confirmations.

### Cited Findings
- [M] LELA: candidate generation (BM25, dense or prior dictionary), then Qwen3-Reranker-4B, then an LLM choosing among the top 10 with 10-sample majority vote. Reported scores: ZESHEL normalised macro accuracy 83.11 (best true zero-shot, +8.84 over BLINK); ZELDA 76.6–77.5 (supervised best 82.3); WikilinksNED unseen mentions 68.7 (Qwen3-30B-A3B), beating ReFinED's 66.5 but behind BLINK's 75.2. On ESCO, with 813 of 1,824 mentions unlinkable, always predicting UNK (44.57) beat LELA overall (26.75–39.36): NIL handling is weak. Reranking alone gave 27.15, so the gains come from LLM joint reasoning over candidates. Removing reasoning, self-consistency or entity descriptions each hurt. Small models are sensitive to candidate order. It took ~44 s per mention (batch use). Qwen3-30B-A3B was close to Magistral-Small and faster than Qwen3-4B — [LELA, arXiv 2601.05192](https://arxiv.org/pdf/2601.05192)
- [M+, COLING 2025] LLM mention expansion ("Angelina" to "Angelina Jolie") before a T5 linker raised average F1 from 56.0 to 61.7. KORE50 (ambiguous short names) went from 50.0 to 70.6. LLM-only linking averaged 57.0 and produced hallucinated identifiers not traceable to the dictionary. LLaMA-3 70B as expander gave 61.7, vs 56.2 for LLaMA-3 8B (essentially no gain over the 56.0 baseline) — [COLING 2025](https://aclanthology.org/2025.coling-main.570.pdf)
- [M, 2022] Personal entity linking in conversations (ConEL-2, Wizard-of-Wikipedia). Rule-based detection of "my/our X" reached F1 0.903. Linking the personal mention to its earlier explicit antecedents: off-the-shelf coreference (S2E) 0.297, fine-tuned on conversations 0.589. Overall entity linking with personal entities: 0.598 F1. "Detecting personal mentions with simple rules works well. Finding their antecedents is the hard part" — [arXiv 2206.07836](https://arxiv.org/pdf/2206.07836)
- [S, ACL 2024] Maverick coreference (~500M params): CoNLL-2012 F1 83.6, beating 11–13B LLM-based systems (83.3 and below). Inference is 170× faster than seq2seq. Out-of-domain GAP is 91.1 — [Maverick](https://arxiv.org/abs/2407.21489v1)
- [W, model card] GLiNKER / GLiNER-Linker (Apache-2.0): a bi-encoder (DeBERTa-v3) that links mentions to a custom JSONL registry of `entity_id`, `label`, `description`, `entity_type`. The pipeline is L1 GLiNER mentions, L2 dictionary candidates, L3 bi-encoder disambiguation, optional L4 reranker with threshold. Precomputed entity embeddings give a claimed 10–100× speed-up. The card gives no accuracy figures — [HF model card](https://huggingface.co/knowledgator/gliner-linker-large-v1.0)
- [M+] Entity matching with LLMs (Peeters et al.). Zero-shot GPT-4 beat fine-tuned Ditto on WDC Products (F1 89.61 vs 84.90) and two other datasets. Open models were weaker, but explicit matching rules raised Mixtral by 3–17 F1, while in-context demos lowered Mixtral by ~11 F1. Fine-tuning GPT-3.5 added 4–20 F1. On unseen entities, LLMs beat transferred PLM matchers by at least 8 F1 (GPT-4 by 34) — [arXiv 2310.11244v2](https://arxiv.org/pdf/2310.11244v2)
- [W, vendor engineering blog, no metrics] Graphiti/Zep entity resolution is deterministic first:
  1. Normalised exact match.
  2. Entropy gating: short or repetitive names (e.g. a bare 4-letter first name) skip fuzzy matching and go straight to the LLM.
  3. 3-gram MinHash plus LSH, accepting a match automatically if Jaccard exceeds 0.9.
  4. LLM fallback.
  5. A second dedupe pass within each batch.

  Edges are reconciled with hybrid search (RRF). Nine built-in entity types include Preference, Requirement, Procedure and Event — [Graphiti blog](https://blog.getzep.com/graphiti-hits-20k-stars-mcp-server-1-0.md). Zep's documented policy "prefers under-merging to over-merging", because duplicates are easier to recover from than wrong merges — [Zep docs](https://help.getzep.com/how-graph-creation-works)
- [W, vendor] Mem0's 2026 algorithm scans each memory for proper nouns, quoted text and compound noun phrases. These are embedded in a separate entity layer, and an entity match at query time boosts ranking. It is fused with semantic and keyword scoring — [Mem0 blog](https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm)
- [M] Downstream effect of extraction and linking errors on LLM-built graphs (Llama-3 8B and others):
  - Minor spelling variants created new nodes in up to 67% of sampled false positives.
  - Two entities merged into one node: 18–19%.
  - Edges redirected to the wrong in-graph entity: 4–49%.
  - Node counts were inflated by up to 122.7%.
  - Graph metrics are reliable only above roughly 0.92 F1.

  — [arXiv 2506.12367](https://arxiv.org/pdf/2506.12367)
- [M] Sci-ZSEL generates LLM aliases for a subset of registry entities, filters aliases that drift towards neighbouring entities (embedding threshold 0.9), and fine-tunes the retriever on alias–mention exact matches. It helps most when mentions have no lexical overlap with entity names (43–57% of pairs in its new test sets). No numbers were available in the fetched text — [arXiv 2609.00228](https://arxiv.org/html/2609.00228)

### Inferences
- **Our 31% cross-domain linker recall is consistent with skipping the candidate and description stage.** The literature's ~60–83% figures assume (a) candidate generation with aliases, (b) entity descriptions, (c) LLM joint choice over about 10 candidates. Removing any of these measurably hurts (LELA ablations).
- **Gate design: entity linking**
  1. Detect mentions with GLiNER2, using our entity types (person, property, business, supplier, goal) with descriptions. Add a rule pass for possessive and relational mentions ("my brother", "our accountant", "the Smith St job"), and an Aho-Corasick pass over every registry alias.
  2. Resolve relational mentions through the registry graph rather than coreference: owner →brother→ Person#12. This avoids the 0.59-F1 antecedent problem. Use Maverick (~500M) only for within-item pronouns.
  3. Candidates: exact normalised alias hit, then MinHash (Jaccard >0.9) auto-accept *only* for long, high-entropy names. Low-entropy first names and nicknames always go to the LLM step with context (Graphiti entropy gate).
  4. Disambiguate with a local 30B-class MoE (Qwen3-30B-A3B class measured close to the best). Input: top 10 candidates from a reranker, each with a one-line description and recent activity. Five to ten sampled votes. An explicit "NEW ENTITY" and "AMBIGUOUS" option comes first in the list.
  5. A vote margin below threshold, or a NEW verdict, goes to the queue, not to an auto-created node. New entities are proposed with the evidence span for one-tap confirmation, because NIL detection is the weakest link (ESCO result).
  6. Every confirmed resolution appends the surface form to that entity's alias list. This is a personal lexicon that grows with use, and links that are mostly free once confirmed.
- Use the matching-rules finding: for open local models, writing explicit rules into the prompt ("same phone or ABN means same business", "first name only means prefer the entity active in the last 30 days in this area") gave +3–17 F1 on Mixtral. For GPT-4-class models the same rules cost 1–3 F1. Model-specific prompts are worth it.

### Gaps
- No 2025–26 benchmark of linking to a *private* registry with nicknames (e.g. "Bazza" to Barry). All measured numbers are Wikipedia/ontology-style. A BrainBench linking set with aliases, cross-domain mentions and NIL cases is needed.
- ReFinED was compared only indirectly (66.5 on WikilinksNED unseen, via LELA). I found no 2025–26 evaluation of ReFinED on custom knowledge bases.
- No accuracy numbers for GLiNKER or Graphiti dedupe were published.

---

## 3. Personal knowledge graph construction from chats/email (PKG, lifelogging, Zep/Graphiti, Mem0 audits, GraphRAG)

### Takeaway
Independent audits show production memory systems miss most of what they should store. HaluMem-Medium memory recall was 14–74%, and 3–82% on 1M-token histories. Update omission was 37–94%, while fabrication during updates was below 1.2%. Retrieval-only systems score 0 on counting and state-tracking. The systems that do well put interpretation on the write path: typed or structured records, event time, supersession, versioning. One finding bears directly on our searchable entry: *appending* extracted facts to the original text as an index key helps, but *replacing* the text with facts or keyphrases hurts.

### Cited Findings
- [M; note: HaluMem is co-authored by MemTensor, maker of MemOS, which scores best] HaluMem-Medium (20 users, 30,073 dialogue rounds, 14,948 memory points). Extraction results:

  | System | Recall | Target precision | Accuracy |
  |---|---|---|---|
  | Mem0 | 42.91% | 86.26% | 60.86% |
  | Mem0-Graph | 43.28% | — | 61.86% |
  | Memobase | 14.55% | — | 32.29% |
  | Supermemory | 41.53% | — | 60.83% |
  | MemOS | 74.07% | 86.25% | 59.55% |

  Updates (correct / hallucinated / omitted): Mem0 25.5 / 0.45 / 74.0%; Zep 47.3 / 0.42 / 52.3%; MemOS 62.1 / 0.42 / 37.5%. On HaluMem-Long (~1M tokens per user), Mem0's recall fell to 3.23% and update omission rose to 98.5%. QA hallucination was 15–30% across systems. Mem0 took 2,768 minutes to add the Medium dialogues. Zep's extraction could not be measured (no API) — [HaluMem, arXiv 2511.03506v3](https://arxiv.org/pdf/2511.03506v3)
- [M] MemTrace error attribution (LoCoMo, LongMemEval, RealMem). Mem0 and long-context systems fail mainly at extraction or update. EverMemOS has very few extraction errors, and its failures are retrieval and reranker errors. All systems have response errors even with correct retrieval. Attribution-guided prompt fixes raised Mem0 on LoCoMo from 59.08 to 66.70 — [MemTrace, arXiv 2605.28732](https://arxiv.org/pdf/2605.28732)
- [M] StructMemEval (51 long scenarios, gemini-3.1-pro backbone). Total scores: retrieval 0.06, Mem0 0.30, Mem0-Graph 0.22, EMem 0.25, and an agent maintaining markdown files 0.55. Count-based tasks (netting debts) scored **0.00 for every system and every backbone**. State tracking: retrieval 0.00 vs file agent 0.84. Failure modes: missing reverse links, hallucinated records, duplicated or missed transactions, stale neighbouring records — [arXiv 2602.11243v3](https://arxiv.org/html/2602.11243v3)
- [S, ICLR 2025] LongMemEval index design (Stella-1.5B retriever, round values):

  | Index key | R@5 | R@10 | QA (GPT-4o, top-10) |
  |---|---|---|---|
  | Text only (K=V) | 0.582 | 0.692 | 0.670 |
  | Text + extracted facts (K=V+fact) | 0.644 | 0.784 | 0.720 |
  | Facts only (K=fact) | 0.530 | — | — |
  | Keyphrases only | 0.282 | — | — |
  | Text + keyphrases | 0.478 | — | — |

  Facts alone were worse than text alone, and keyphrases (alone or appended) hurt. Session values with text + facts reached R@10 0.862 — [LongMemEval, arXiv 2410.10813v2](https://arxiv.org/pdf/2410.10813v2)
- [W, vendor, contains promo injection] xmemory end-to-end, 4-domain structured memory benchmark (judge F1): xmemory 97.10, Mem0 87.24, Mem0-Graph 86.07, Cognee 86.18, Supermemory 80.49, Zep 80.16 (Zep errors were false-positive heavy). Computed reads on "Splitwise" expense events: xmemory 95.2%, Supermemory 73.75%, Mem0 54.9–59.1%, Zep 25.7%, markdown harness 12–40% — [arXiv 2604.27906](https://arxiv.org/pdf/2604.27906)
- [W, independent blog; 120-question slice] On LongMemEval-S, extracting **event time** (when the fact happened, not when it was said) "largely eliminated wrong-date errors". A bi-temporal graph (event time plus ingestion time) with supersession raised knowledge-update accuracy from 60% to 80%, where prompting could not. A counting feature fired on 0 of 120 questions because the schema had no countable event nodes. A mid-tier open model scored within noise of a frontier model under the same architecture — [UltraMem blog](https://davak01.substack.com/p/structure-beats-scale-what-ultramem)
- [W] Zep pipeline as documented:
  1. Store each input as an episode.
  2. LLM extracts entities.
  3. LLM extracts facts.
  4. A separate pass sets `valid_at` / `invalid_at`.
  5. Entity resolution.
  6. Fact resolution, where a contradiction *invalidates* the old edge.
  7. Update node summaries.

  Entity resolution is "best-effort" — [Zep docs](https://help.getzep.com/how-graph-creation-works)
- [W, GitHub discussion; 24-fact audit] In Mem0, reworded duplicates persist as separate rows, contradictions keep both memories, and an external auditor classified both supersession pairs as contradictions in every configuration — [Mem0 discussion #4787](https://github.com/mem0ai/mem0/discussions/4787). Mem0's 2026 algorithm moved to single-pass ADD-only extraction (history preserved, ~half the latency) and reports LoCoMo 92.5 and LongMemEval 94.4. These are managed-platform numbers that open-source users "should expect different" from. BEAM-10M temporal reasoning scored 16.3 — [Mem0 blog](https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm)
- [M] Microsoft GraphRAG uses exact string matching for entity resolution and relies on community summarisation to absorb duplicates. It publishes no extraction precision or recall — [GraphRAG](https://arxiv.org/pdf/2404.16130). An independent re-implementation reports that GraphRAG "failures are common when LLM outputs deviate from strict JSON schemas", that LLM edge weights vary by an order of magnitude across corpora, and that indexing took about 3 h vs 5.3 min for a non-LLM variant, which scored higher QA (49.0% vs 43.9%) on a 125-question subset — [ASONAM 2025](https://webhome.cs.uvic.ca/~thomo/papers/asonam2025-graphrag.pdf)
- [M] Decoupling & Aggregation ("xMemory" hierarchy, a different project from the xmemory vendor): messages → episodes → semantic facts → themes, with top-down retrieval. On LoCoMo with Qwen3-8B: average F1 43.98 vs naive RAG 36.42. It covered all answer tokens with ~975 tokens vs ~1,979 for RAG — [arXiv 2602.02007](https://arxiv.org/html/2602.02007v1)

### Inferences
- **The "free-text item ~30% found" bottleneck is what you would expect** if items are stored as text without fact-augmented keys and without typed records. HaluMem shows most stored memories are never extracted at all. LongMemEval shows adding fact keys gives about +6 to +9 points of recall. StructMemEval shows counting and state questions are impossible without structured records.
- **Gate design: searchable entry**
  1. Keep the original text as the primary key.
  2. Append the extracted, normalised fact sentences (entity names *and* registry aliases resolved, so "Bazza's invoice" also reads "Barry Smith (supplier, ABC Plumbing) invoice").
  3. Do not replace the text, and do not use keyphrase-only keys (both measured as harmful).
  4. Put generated questions in a separate index (section 5).
- **Supersession**: copy Zep's invalidate-don't-delete pattern plus bi-temporal fields (event time, recorded time, valid-from, valid-to). Make "update vs contradiction vs new" a typed decision with its own confidence, because the Mem0 audit shows judges mislabel supersession as contradiction. Low-margin cases go to the queue.
- Update omission (37–98%) dominates update fabrication (<1.2%). So the gate's update step should actively search for prior records about the same entity and record type before writing (MemReader's "search" action), rather than relying on similarity collisions.

### Gaps
- No independent audit of Zep/Graphiti *extraction* precision or recall exists (HaluMem could not measure it). No 2025–26 audit of GraphRAG extraction error rates on chat or email was found.
- No 2025–26 PKG-from-email benchmark was found. Lifelogging-specific PKG work was not reached before the search budget ran out.

---

## 4. Confidence calibration of LLM extraction (verbalised, self-consistency, logprobs) and human-in-the-loop burden

### Takeaway
No single confidence signal is good enough on its own:
- Verbalised confidence is overconfident and saturates near the top, so no threshold separates right from wrong well.
- Logprobs are inconsistent and increasingly unavailable on hosted models.
- Self-consistency is a weak-to-moderate signal. It works best on mid-tier models (exactly our local 8B–70B), but frontier models can be confidently wrong about half the time when they agree.

The best measured approaches combine signals: multi-call verifiers (CONSTRUCT), distractor-normalised confidence (DiNCo), simulated-annotator agreement with thresholds calibrated on a few hundred human labels (Trust or Escalate), and above all source grounding (SafePassage: 86% of unsupported values caught). Humans reviewing AI suggestions catch surface errors (~80%) but miss rule or semantic errors (~31%), and extra correction steps make them flag less.

### Cited Findings
- [S, ICLR 2026] DiNCo, measured on small open models (Qwen3-8B, Qwen3-1.7B, Llama-3.2-3B, Gemma-3-4B; TriviaQA). Plain verbalised confidence had ECE 0.189–0.387 and AUC 0.70–0.83. Distractor-normalised confidence cut ECE by ~0.17 and raised AUC by ~0.08 on average. DiNCo at 10 calls beat self-consistency at 100. "VC scores saturate at high confidence, so no threshold can reject many false claims without also rejecting many true ones." Logprob MSP was competitive on ECE for some models — [DiNCo](https://arxiv.org/html/2509.25532v1)
- [M] Agreement audit (53 runners × 50 samples, GPQA and AIME): agreement is a "positive but weak predictor" of correctness (rho 0.20–0.59). The most consistent frontier model had agreement ≥0.8 on 77% of GPQA entries, and ~48% of those were wrong. The signal is most useful for "unsaturated mid-tier models" — [arXiv 2607.08065](https://www.alphaxiv.org/abs/2607.08065)
- [S, ICLR 2025] Trust or Escalate. Confidence comes from agreement across 5 simulated annotator personas. This roughly halved ECE and raised AUROC ~13% vs verbalised or predictive probability (GPT-4, AlpacaEval). Abstention thresholds were set on ~500 human labels with a statistical guarantee. Cascade Mistral-7B → GPT-3.5 → GPT-4: at a 90% human-agreement target it covered 55.7% of items (guarantee held 90.8% of runs); at an 80% target, ~79% coverage. Items it abstained on were genuinely more subjective (human inter-annotator agreement 0.815 vs 0.902) — [ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/file/08dabd5345b37fffcbe335bd578b15a0-Paper-Conference.pdf)
- [M, vendor] CONSTRUCT per-field trust scoring for structured outputs (5 verifier calls, scored with GPT-4.1-mini, 4 extraction benchmarks): highest AUROC per document and per field, beating LLM-as-judge and logprobs. "Logprobs are inconsistent across models." Removing any one verifier call cut AUROC by 3.2–5.7% relative. The "review only 1–5% of cases" figure is a deployment claim, not measured — [arXiv 2603.18014](https://arxiv.org/html/2603.18014v2)
- [M] Logprob access is disappearing: "Claude never returned logprobs, and Gemini dropped them at 3.1 Pro." A verbalised recipe cut adaptive ECE on newer flagships (e.g. Sonnet 4.5 from 9.1% to 3.3%) without hurting accuracy, though it cost 1.2–2.7 points of balanced accuracy on pre-2025 models — [arXiv 2609.10996](https://arxiv.org/html/2609.10996v1)
- [M+, Findings ACL 2025] Picking the lowest-confidence 20% of LLM classifications for human review: per-item verbalised confidence beat random for GPT-4o, GPT-4o-mini and Llama-3.1-8B. Mistral-7B failed on one task. Asking the model to pick the k least-confident items from a list was unreliable (invalid lists, order sensitivity) — [ACL Findings 2025](https://aclanthology.org/2025.findings-acl.836.pdf)
- [M] Grounding as a confidence signal: a span alignment plus NLI check flags 85.7% of unsupported extractions at 92.8% precision — [SafePassage](https://arxiv.org/html/2510.00276v1)
- [S-design, M-generalisation] Human review of AI pre-annotations (randomised; 2,784 Prolific annotators extracting emissions values from report tables):
  - Overall accuracy was 66–68%.
  - Digit and spelling errors were corrected ~82% of the time, wrong-cell errors ~77%, errors needing knowledge of annotation rules only 31%.
  - Requiring a correction after flagging an error *reduced* error flagging (under-reporting to save effort).
  - Favourable attitudes to AI predicted lower accuracy.
  - Seeing early AI errors did not raise later vigilance.
  - Performance bonuses had no effect.

  — [arXiv 2509.08514](https://arxiv.org/html/2509.08514v1)

### Inferences
- **Gate design: confidence routing.** Combine cheap, mostly local signals into one "needs owner" score, rather than trusting any single one:
  1. Grounding fails (span alignment below 0.6, or NLI says not supported) → do not write; queue.
  2. Validator failure after retries → queue.
  3. Disagreement between the local 8B and local 70B extraction or link, or a self-consistency vote margin below threshold. Self-consistency is *more* informative on mid-tier local models than on frontier ones.
  4. Verbalised confidence, DiNCo-style (ask about the extracted value and about plausible distractor values, then normalise), only as a tie-breaker.
  5. A stakes flag per record type and field (money, legal, health, member data, irreversible decisions).

  Send to the owner only stakes AND (any uncertainty signal). Calibrate thresholds on ~500 owner-labelled items with the Trust-or-Escalate fixed-sequence procedure, so the residual error rate on auto-accepted records has a stated bound.
- **Omissions are invisible to confidence scoring.** All the calibration methods above score extracted values. A missed record has no confidence. Coverage checks (section 1) must feed the queue separately.
- **One-tap confirmation design**, from the human-review RCT:
  - Show the source sentence with the extracted value highlighted, in plain language ("Decision: switch cleaning supplier to X from 1 March — correct?").
  - Make confirm/reject one tap, with correction as an *optional, separate* step. Required corrections suppress flagging.
  - Expect owners to catch surface errors (wrong number, wrong name) but not wrong record type or a misread rule. Keep semantic-type ambiguity out of the owner's queue, or phrase it as an explicit choice ("Is this a decision or just an idea?").
  - Track the per-owner rejection rate. A falling rate alongside falling dwell time is the rubber-stamping signature.
- Projected burden: no direct measurement exists. With ~55–80% auto-coverage at 80–90% agreement targets (Trust or Escalate) and stakes filtering, a reasonable working assumption to test in BrainBench is that a few percent of items need confirmation. Treat this as a hypothesis, not a result.

### Gaps
- No study measures calibration of *field-level extraction* confidence on open 8B–70B models for conversational business text, or owner acceptance rates over months (fatigue). The RCT was too short to observe fatigue.
- CONSTRUCT's AUROC values exist only in figures. I did not obtain numbers.
- No evidence was found on optimal confirmation UI (one-tap vs batch digest) for personal assistants.

---

## 5. Doc2query / query anticipation at index time, and capturing the user's own vocabulary over time

### Takeaway
Generated questions or queries at index time help, sometimes a lot: +16% MRR on MS MARCO with filtering, and about +20 points context precision across six RAG datasets for hypothetical-question embeddings. But they are noisy. Filtering out ~70% of generated queries *improves* results. Appending generated text to a document's dense embedding can hurt, while a separate query index fused with the document score works best. LLM-written "situating context" prefixes cut retrieval failures 35–49%, or 67% with reranking. Learning vocabulary from user feedback (click or query logs as document expansion) is old but well evidenced (+17–28% MRR). I found no 2025–26 personal-lexicon work.

### Cited Findings
- [S, ECIR 2023] Doc2Query--: scoring generated queries with a relevance model and keeping only the top 30% raised MS MARCO Dev RR@10 from 0.279 to 0.323 (+16%, significant) and TREC DL'19 nDCG@10 from 0.627 to 0.670 (not significant). The index shrank 33% and query latency fell 23%. Unfiltered generation needs ~2.9× more GPU time to match. Hallucinated queries "add index terms without improving retrieval" — [Doc2Query--](https://arxiv.org/pdf/2301.03266)
- [M] Doc2Query++ (topic- and keyword-guided LLM generation of 30 queries per document, BEIR subsets): it beat Doc2Query and Doc2Query-- on every dataset, for both BM25 and Contriever. "Naive appending injects semantic noise and harms dense retrievers." For example, on SciFact (dense), Doc2Query-- scored 0.6498 vs 0.6574 with no expansion. Dual-index fusion (separate query-embedding index, max-pooled, fused with the document score at α=0.5) consistently beat appending. SciFact dense nDCG@10 went from 0.6574 to 0.7289 — [arXiv 2510.09557](https://arxiv.org/html/2510.09557v1)
- [M] HyPE (hypothetical prompt embeddings: questions generated per chunk at index time, each embedded with a pointer back to its chunk). Averaged over 6 datasets: retriever context precision 42.3 (naive) vs 63.5 (HyPE) vs 41.6 (HyDE); claim recall 53.6 vs 71.5. The Single-Topic dataset at k=1 went from 28.7 to 68.8 precision. MS MARCO got slightly worse (68.7 vs 73.6). Noise sensitivity worsened (21.0 vs 13.8). Generated questions were not filtered — [arXiv 2607.29402](https://arxiv.org/pdf/2607.29402)
- [S] LongMemEval: appending extracted facts to keys gave about +6 to +9 points recall, while keyphrase keys hurt (section 3 table) — [LongMemEval](https://arxiv.org/pdf/2410.10813v2)
- [W/M, vendor] Contextual Retrieval: an LLM writes a 50–100-token context per chunk, prepended before embedding and BM25. Top-20 failure rate went from 5.7% to 3.7% (−35%), to 2.9% with BM25 (−49%), and to 1.9% with reranking (−67%). One-off cost ≈ $1.02 per million document tokens with caching. A custom contextualiser prompt with a glossary "may outperform" the generic one — [Anthropic](https://www.anthropic.com/news/contextual-retrieval)
- [M, 2019] NeuDEF: expanding documents with the user queries that led to clicks on them gave MRR +20.9% on head, +28.1% on torso and +16.6% on tail queries (Sogou logs). Documents with no clicks fall back to the base ranker — [arXiv 1908.02938](https://arxiv.org/pdf/1908.02938)
- [M] LLM-generated aliases for registry entities, filtered for drift towards neighbouring entities, help most when mentions share no words with entity names — [Sci-ZSEL](https://arxiv.org/html/2609.00228)

### Inferences
- **Gate design: anticipated-question index**
  1. Generate ~10–30 short questions and phrasings per item with the local 8B model, using the registry's aliases and nicknames, the owner's past query phrasings for this entity or area, and the record type. Exclude values, per the brief.
  2. Score each against the item text with a local cross-encoder or reranker and keep the top ~30–50% (Doc2Query--).
  3. Store them as **separate vectors pointing to the item**, plus a BM25 field, not appended into the item embedding. At query time, max-pool question hits per item and fuse with the item score at α≈0.5 (Doc2Query++/HyPE).
  4. Prepend a contextual prefix (entity, area and time placement) to the item text before embedding (Contextual Retrieval).
- **Personal vocabulary loop** (NeuDEF adapted). When the owner searches, fails, rephrases, then opens or confirms item X, add the failed query wording as an anticipated question on X, and its novel terms as aliases on X's entities. This is a reformulation log used as document expansion. It grows the user's own vocabulary without generating it. Guard against pollution with the same relevance filter and an expiry for unused expansions.
- Watch the HyPE noise-sensitivity regression. If many near-duplicate questions point to the same item, a reader can be swamped by repeated context. Deduplicate items after max-pooling, before reading.

### Gaps
- I found no 2025–26 paper on personal lexicons or learning aliases from an individual's reformulations. Evidence is from web-search click logs (2019 and earlier). The search budget ran out before searching "query reformulation mining 2025".
- No study measures doc2query-style expansion on *short personal notes or chat messages*. All gains are on passages or chunks. HyPE's MS MARCO regression hints that short, lexically clear texts gain less.

---

## 6. Temporal extraction (relative date normalisation, event vs plan vs done status, tense)

### Takeaway
LLMs resolving relative time end-to-end are unreliable. Implicit relative references ("last month", "yesterday") scored 34–74% vs 75–92% for explicit dates, and accuracy falls 29–39% as the number of events grows. Vague references scored 26–45%. The robust pattern: the LLM identifies the span and emits a *structured, executable* time expression, and code resolves it against the item's timestamp. A 0.5B model fine-tuned this way beat GPT-4.1 prompting (0.59 vs 0.51). Most errors are missed time expressions. Event status (happened / possible / negated / underspecified) is weak for LLMs: GPT-4 macro-F1 ~43, 7–8B models ~27–28, and the "possibly not" and "underspecified" classes are near-unsolved.

### Cited Findings
- [M] SCATE code generation: the model outputs Python SCATE code per time expression, the code is executed, and runtime failures are discarded. TempEval-2013 test: GPT-4.1 0.51, Claude 3.7 0.49 (vs 0.38 with interval-style few-shot). Qwen2.5-0.5B fine-tuned on CC-News synthetic plus TempEval data: 0.59; trained on TempEval alone: 0.01. In the best small model's errors, 70% were missed temporal expressions, 10% boundary, 10% nested structure, 5% type and 5% granularity. Guidance: "next quarter" maps to Next with a quarter-level Repeating shift, and "last <weekday>" to Last with a Repeating shift — [arXiv 2507.06450](https://arxiv.org/pdf/2507.06450)
- [M] TRAVELER (3,300 questions over household-event histories): explicit references 75% (Llama3-8B) to 92% (Llama3-70B); implicit relative to speech time 34% (Gemma-7B) to 74% (Llama3-70B); vague 26–45%. Growing histories from 5 to 100 events cut implicit accuracy by 29–39%. Llama3-70B slightly beat GPT-4 on explicit and implicit. The paper has some internal number inconsistencies — [arXiv 2505.01325](https://arxiv.org/pdf/2505.01325)
- [S] LongMemEval time-aware query expansion (the LLM turns the question into a time range that filters the search). With GPT-4o as expander, temporal-reasoning R@5 rose from 0.684 to 0.722. With Llama-3.1-8B it was 0.677, slightly worse, because the 8B model "tends to hallucinate or over-extract time ranges" — [LongMemEval](https://arxiv.org/pdf/2410.10813v2)
- [S, EMNLP Findings 2024] MAVEN-FACT event factuality, 5 classes: CT+ certain happened, PS+ possibly happened, PS− possibly not, CT− certain not, Uu underspecified. Macro-F1: fine-tuned DMBERT 47.6; GPT-4 + CoT 42.8; Mistral-7B 27.7; LLaMA-3 + CoT 27.0. GPT-4 per class: CT+ 94.5, PS+ 49.8, CT− 42.6, PS− 21.6, Uu 5.4. LLMs often cannot point to the words that support their factuality label — [MAVEN-FACT](https://arxiv.org/html/2407.15352v1)
- [M] Allen-interval event relations in narratives (101,880 pairs): best macro-F1 0.270 (DeepSeek). Overlap relations scored ≤0.07 F1. Only 6.1% of passages had an absolute anchor date, and 58% of events sat next to relative cues. Macro-F1 fell from 0.494 (8–15 events) to 0.132 (>40 events) — [arXiv 2610.17402](https://arxiv.org/html/2610.17402)
- [M] TIDE (evolving regulations, versions and dates): Relative-Time QA scored 59.66 (GPT-5.2) to 68.03 (Claude) *even with gold documents in context*. Models flagged altered provisions 78.9% of the time but identified the altered fact only 18.6% without grounding — [arXiv 2608.08512](https://arxiv.org/pdf/2608.08512)
- [W] Extracting event time rather than conversation date "largely eliminated wrong-date errors". The advice is to keep date maths, counting and latest-value resolution in code — [UltraMem blog](https://davak01.substack.com/p/structure-beats-scale-what-ultramem). Mem0's own BEAM-10M temporal reasoning score is 16.3 (vendor) — [Mem0 blog](https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm)

### Inferences
- **Gate design: temporal**
  1. Span detection: LLM plus a rule pass (dates, weekdays, "next/last/this X", "EOFY", "Q3", "after settlement"). The rule pass targets the dominant *missed-span* error.
  2. For each span, the LLM emits a structured expression: `{anchor: item_timestamp | other_event_id, op: last|next|this|before|after|nth, unit: day|week|month|quarter|fy, n, granularity}`.
  3. A deterministic resolver (Python/SCATE-style) computes the interval. Australian financial-year and quarter conventions are configured, not guessed.
  4. Store `event_time` (interval plus granularity), `recorded_at`, `valid_from/to`. Never let the LLM write the resolved ISO date directly.
- **Status typing**: use a factuality label on every plan, decision or event record: done (CT+) / planned-intended / possible (PS+) / cancelled-not done (CT−) / unclear (Uu). PS− and Uu are near-unsolved for LLMs, so route Uu and low-margin PS± to the incomplete queue. Ask the owner "did X happen?" only when stakes are high.
- A cheap, high-value future fine-tune: a 0.5–1B local temporal-expression model trained on LLM-generated synthetic data, which is exactly how the SCATE 0.5B model beat GPT-4.1.

### Gaps
- No benchmark measures "plan vs done" status transitions across *multiple* messages, such as a plan in March and a completion mention in May. This needs a BrainBench case set.
- No accuracy figures for rule systems (HeidelTime, SUTime, Duckling) vs LLMs on conversational text were found in this round.

---

## 7. Aggregation: text-to-SQL accuracy (BIRD, Spider 2.0) for a small personal schema; table-augmented memory; compute over extracted tables vs retrieval for find-all questions

### Takeaway
For "how many / total / list all" questions, retrieval fails structurally. Every memory system scored 0.00 on counting in StructMemEval, RAG scored 0% on TAG aggregation queries, and a counting feature fired on 0 of 120 LongMemEval questions without countable event rows. Computing over typed tables works if the schema is simple and documented. Frontier models reach ~94–95% on BIRD-style simple schemas when judged leniently (55–61% under strict scoring). A short semantic document adds 17–23 points. Predefined metrics (a semantic layer) fail loudly instead of returning wrong numbers. Open 7B text-to-SQL models reach ~68% on BIRD test. Public leaderboards are noisy: over half of some benchmarks' gold annotations contain errors.

### Cited Findings
- [W, secondary reports; conflicting] BIRD top scores, 2026. Google's Gemini-SQL2 was reported at 80.04% execution accuracy (#1, June 2026), with GPT-5.5-xhigh at ~72.8% and Claude Opus 4.6 at ~70.9% — [The Decoder](https://the-decoder.com/google-researchs-gemini-sql2-tops-text-to-sql-benchmarks-by-a-wide-margin/). Another 2026 write-up gives AskData + GPT-4o at 81.95% as leader and human performance at 92.96% — [Beancount research log](https://beancount.io/bean-labs/research-logs/2026/06/06/bird-benchmark-text-to-sql-real-database-gap). Conflict: the two sources name different leaders. Check the official leaderboard.
- [M, vendor; official leaderboard entry] Arctic-Text2SQL-R1 on BIRD test: 7B 68.47%, 14B 70.04%, 32B 71.83% (May 2025). The 7B is reported to beat OmniSQL-7B and DeepSeek-V3 — [Snowflake](https://www.snowflake.com/en/blog/engineering/arctic-text2sql-r1-sql-generation-benchmark/)
- [M] Annotation errors: 52.8% of BIRD Mini-Dev and 62.8% of Spider 2.0-Snow annotations contain errors. Re-scoring 16 BIRD agents after correction shifted ranks by up to ±9. Two agents tied at the top with 81% on the corrected subset — [Kang group write-up](https://ddkang.substack.com/p/pervasive-annotation-errors-break)
- [W, careful blog] On BIRD Mini-Dev (500 questions, ~7 tables per database, 2–3-hop joins), three frontier models scored 55.6–60.7% under strict scoring but **94–95%** under realistic scoring (format tolerance plus LLM judge). The spread between models shrank to 0.3–1.4 points. Column comments added +1.1 points overall: +8.7 on the hardest schema, −2.9 on the easiest. "Good data modeling *is* the semantic layer" — [MotherDuck](https://motherduck.com/blog/bird-bench-and-data-models.md)
- [M] A paired test of a semantic document (Contoso retail, 25 tables, 99 questions, single shot): a ~4 KB markdown document of measures, conventions and disambiguation rules raised accuracy from 45.5–50.5% to 67.7–68.7% (+17 to +23 points, McNemar p ≤0.0015) for Opus 4.7, Sonnet 4.6 and GPT-5.4. The models were statistically indistinguishable within each condition — [arXiv 2604.25149](https://arxiv.org/pdf/2604.25149)
- [W, vendor, 11 questions × 20 runs] dbt 2026. Before modelling changes: text-to-SQL 64.5% vs semantic layer 72.7%. After 3 small modelling changes: text-to-SQL 90.0% (Sonnet 4.6) / 84.1% (GPT-5.3-codex) vs semantic layer 98.2% / 100%. Text-to-SQL failures are "plausible but wrong". Semantic-layer failures are errors, not wrong data — [dbt blog](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026?version=2)
- [W, secondary] Spider 2.0 (enterprise warehouses): original o1-preview agent 21.3%, GPT-4o 10.1%; ReFoRCE ~30–31 on Lite and Snow — [AIWiki](https://www.aiwiki.ai/wiki/spider_2/raw). A provider self-report claims 52.9% on Lite (Oct 2026) — [BenchLM](https://www.benchlm.ai/benchmarks/spider2Lite). Spider 2.0 is not representative of a small personal schema.
- [M, CIDR 2025] TAG benchmark (80 BIRD-derived queries needing world knowledge or semantic reasoning): Text2SQL 0.17, RAG 0.00, retrieval + LM rank 0.02, Text2SQL + LM 0.13, hand-written TAG pipelines 0.55 — [TAG](https://vldb.org/cidrdb/papers/2025/p11-biswal.pdf)
- [M] StructMemEval: count-based tasks scored 0.00 for every memory system and backbone. Even the best agent (markdown files) had "duplicated or missed transactions" — [arXiv 2602.11243](https://arxiv.org/html/2602.11243v3)
- [W, vendor] Computed reads over natural-language expense events: a schema-grounded store scored 95.2%, vs Mem0 54.9–59.1%, Zep 25.7% and a markdown harness 12–40% — [arXiv 2604.27906](https://arxiv.org/pdf/2604.27906)
- [W] "A counting feature fired on 0 of 120 questions because the schema had no countable event nodes" — [UltraMem blog](https://davak01.substack.com/p/structure-beats-scale-what-ultramem)

### Inferences
- **Gate design: tables for aggregation.**
  1. Every typed record lands in a relational table: `records(id, type, entity_ids[], area, status, event_time_start/end, recorded_at, valid_from/to, source_item_id, confidence, confirmed_by)`, plus per-type tables (`numeric_mentions(record_id, quantity, unit, currency, fact_id)`, `decisions`, `plans`, `risks`).
  2. Keep it at about 7–10 tables, plainly named, joins of 3 hops or fewer. This is the regime where frontier models score ~94% leniently and where open 7–32B text-to-SQL models are viable.
  3. Write a ≤4 KB semantic document defining measures and owner vocabulary ("spend", "the gym", "this FY"). Measured at +17 to +23 points.
  4. Two answer paths:
     - Predefined, parameterised metric queries (semantic-layer style) for frequent high-stakes aggregates (totals, counts by area or entity, open risks). These fail loudly when out of scope.
     - Text-to-SQL (local Arctic-class 7–32B model, hosted fallback) for ad hoc questions, with the executed SQL and row count shown in the answer.
  5. The router sends "how many / total / list all / which … ever" to SQL, not to vector search.
- This is the strongest argument for the write gate: *find-all questions are only answerable if the records were extracted and typed at write time*. Recall at extraction (section 1, omissions) caps find-all accuracy, so extraction coverage is a direct KPI for aggregation.
- Distrust leaderboard deltas under ~5 points (annotation noise of 50%+). Evaluate on our own schema with a hand-checked gold set.

### Gaps
- No published benchmark of text-to-SQL over a *small personal or small-business* schema with messy owner phrasing. Beancount notes that BIRD results do not establish this.
- No direct head-to-head of "compute over extracted tables" vs "retrieve and let the LLM count" on find-all questions over 10k personal items. StructMemEval and xmemory are the closest, and one is vendor-run.
- I found no accuracy figures for small (≤8B) models on BIRD with lenient scoring.

---

## 8. Activity-trail and context signals for inferring which area a request is about (session context, recently viewed items)

### Takeaway
Evidence that session or activity context improves intent inference exists, but the gains are small and conditional:
- Product-type intent: +0.7 to +2.5 points F1, and −2.5 when the session moves from narrow to broad.
- TREC iKAT: personal context more often *lowered* retrieval performance than raised it.

Strong actions (added to cart, i.e. opened or edited) carry more signal than clicks or views. Use context as a soft prior or boost, never a hard filter. The one robust context signal is time: time-range narrowing helps temporal recall.

### Cited Findings
- [M] Session context for product-type intent (50k test queries, 6k+ classes, DeBERTa-v3-small), weighted F1 vs current query alone (82.92):

  | Context added | Change |
  |---|---|
  | Previous query | +0.80 |
  | Previous query, broad-to-narrow only | +2.50 |
  | Previous query, narrow-to-broad only | −2.54 |
  | Previous added-to-cart item attributes | +2.22 |
  | Previous clicked item attributes | +0.70 |

  — [arXiv 2406.01702](https://arxiv.org/html/2406.01702v1)
- [S, TREC 2024 track overview] iKAT personal knowledge base. The best F1 for identifying relevant personal statements was 0.4775–0.4935, with only ~5–10% of statements relevant. "In most cases, PTKB dependence led to lower performance" for personalised turns. Personalised query rewriting helped one team (nDCG@5 0.5111 vs 0.4979). Personal-statement relevance gets harder deeper into a conversation — [TREC iKAT 2024 overview](https://trec.nist.gov/pubs/trec33/papers/Overview_ikat.pdf)
- [S] Time-aware query expansion (the LLM infers a time range to narrow the search) improved temporal recall with a strong expander. An 8B expander hallucinated ranges — [LongMemEval](https://arxiv.org/pdf/2410.10813v2)
- [W, thesis] Indaleko (unified personal index, 31M files) uses "memory anchors" (temporal, spatial, social, task, environmental), with timestamps as the primary filter. It cites the encoding-specificity principle (recall improves when retrieval cues match encoding context). The fetched excerpt had no quantitative comparison with content-only search, and the thesis excludes user studies — [arXiv 2602.20507](https://arxiv.org/pdf/2602.20507)
- [W, vendor] Glean lists "people-to-people connections", "department affinity", location personalisation and per-customer click fine-tuning as ranking signals. No metrics — [Glean blog](https://glean.com/blog/enterprise-ai-knowledge-graph)

### Inferences
- **Gate design: area classification at write time, and area inference at read time.**
  - At write time, classify area from content (GLiNER2 multi-label with descriptions, LLM fallback) and from linked entities (an entity's home area). Store multi-area labels, not one.
  - At read time, use the open dashboard section and recently *edited or confirmed* items as a soft boost (e.g. RRF-fused prior). Exclude raw views, which are the click analogue with weak signal.
  - Decay the boost when the new query looks broader than the session (the narrow-to-broad pattern, where context hurt).
  - Never filter by inferred area, because iKAT shows personal context can mislead.
- The dashboard's "packet" design (the section the user has open routes the assistant) is the closest analogue to added-to-cart context: explicit and deliberate. The literature supports it as a prior and does not support it as a hard partition.

### Gaps
- No 2025–26 quantitative study of "recently viewed or edited items" improving intent or area routing in personal assistants or enterprise search. Vendors (Glean) publish no numbers. Searches on personal re-finding and desktop activity context could not be completed (search budget exhausted).
- No evidence on combining activity trails with LLM query rewriting for multi-area personal knowledge bases. This is a candidate BrainBench experiment: query-only vs query + open section vs query + last-3-edited, measuring routing accuracy and harm on area-switching queries.
