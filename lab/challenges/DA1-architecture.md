---
id: DA1-architecture
type: blueprint
title: "DA1: Devil's-advocate review of the architecture and data model"
status: draft
version: 0.5
date: 2026-10-23
author_role: engineer
supersedes: []
superseded_by: null
decisions: [ADR-001, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008, ADR-009, ADR-010, ADR-011, ADR-014, ADR-015, ADR-016, ADR-019]
tests: []
evidence: []
sensitivity: none
---

# DA1: Devil's-advocate review of the architecture and data model

Status: DRAFT v1 (2026-10-23) · Reviewer: Claude (devil's-advocate role DA1) · Scope: ADR-001, 003, 004, 005, 008, 009, 010, 019 and owner proposal U4
Inputs: charter v0.5, hypotheses board v0.6, docs02 ADR set v0.1, BrainBench batch 1 (`brainbench/RESULTS.md`), batch 2 (`RESULTS_batch2.md`, `results_v02/tables.md`), new sandbox checks run for this review (scripts in `challenges/da1_scripts/`), and targeted web research (links inline).

This review argues against the design on purpose. Each item gets: the strongest case against it, how it fails at scale and over time, the operational burden it underestimates, alternatives, a verdict, and a decisive test with a kill criterion.

---

## 0. New evidence from this review (sandbox checks)

All checks use BrainBench v0.2, **seed 1 only** (2,207 tasks; 8 classes), with the batch 2 best first stage: weighted BM25 + bge-small (α = 0.2), exact search, cached embeddings. They compare designs against each other on a synthetic, templated world. They do not estimate the real system. Rates are task-weighted (not distinct-set-weighted), so they differ slightly from the batch 2 tables. Paired tests are exact sign tests over tasks.

| # | Check | Result | Status | Script |
|---|---|---|---|---|
| C1 | **Card gain at an equal reader budget.** Cards (≤3) + query at k = 10 carry 145 words on average, against 109 for query-only at k = 10 (+33%). Query-only given the same number of words as the card arm: | ALL CR: query-only@10 **42.5** → query-only @ equal words **46.3** → cards **54.2**. About **a third of the card gain (3.8 of 11.7 pp) is extra budget**. At equal words, query-only *beats* cards on temporal (71.8 vs 63.6) and multimodal (87.0 vs 81.5). Pinned cards average 44 words (p90 96, max 154). The corpus averages 7 words per item. Query-only fills until it reaches the card arm's word count, so it can overshoot by one item (mean 14.7 items) | OBSERVED | `token_budget.py` |
| C2 | **How BM25 statistics are scoped** (ADR-006 options vs what engines ship) | BM25 alone, ALL CR@10: visible-set statistics 29.0; **per-partition statistics 20.8** (current 44→33, temporal 45→26); global (leaky) 30.3; **per-partition lists merged with RRF (ADR-006 option b/§3) 8.9**. In weighted fusion: visible 42.5, per-partition 40.2 (−2.3), global 42.6. Every requester in this world sees more than one partition | OBSERVED | `bm25_stats_scope.py`, `factpin_rrfpart.py` |
| C3 | **Frozen external BM25 statistics** (IDF and avgdl fitted on a different corpus, the seed-2 world, with no shared documents) | 30.4 vs visible-set 29.0 (+44 / −13, p = 5e-5); leak-free by construction. Caveat: the external corpus is a twin synthetic world (5% of query terms unseen), which favours it | OBSERVED (favourable conditions) | `frozen_idf.py` |
| C4 | **Fusion method when a reranker follows.** The rerank pool is the top-P of the fused list | Pool CR (all required items in the pool), ALL: P = 100: wsum 66.0, RRF 65.9, plain union of the two channels 65.0. P = 50 → 150: +11 pp. Fusion choice moves the pool by **<1 pp**; pool depth moves it by **11 pp** | OBSERVED | `pool_union.py` |
| C5 | **Version history growth** (ADR-008 §7: superseded versions stay indexed). Adds B synthetic older versions per key, simulating 3–5 years of connector updates | ALL CR@10, indexed + forward-to-head: B = 0 **43.0**, B = 10 **31.1**, B = 40 **29.0**. **Temporal collapses: 65.2 → 12.1 → 4.2** in both arms. Current state is protected by forwarding (72.3 → 72.1). At B = 40, indexed + forward beats masking history by 2.9 pp on current state and 1.0 pp overall (N2 holds) | OBSERVED (synthetic near-duplicate versions are a worst case) | `history_bloat.py` |
| C6 | **Values-free card stubs.** The index holds only name + aliases + attribute labels; values are compiled at read time from current facts | 54.1 vs 54.2 for materialised cards with values indexed (+2 / −5, p = 0.45). **No measurable recall cost** | OBSERVED | `stub_cards.py` |
| C7 | **Fact-level pinning** (N12: rank the linked entities' facts by query similarity) vs whole cards, at equal words | 51.2 vs cards 54.2; goal 18.3 vs 37.8; decision 0.5 vs 8.7. Cards win *because* they bring facts the query does not mention. Evidence **for** ADR-010, and against N12 in its naive form | OBSERVED | `factpin_rrfpart.py` |
| C8 | **Mention forwarding on top of cards + router** | Naive (a forwarded head may duplicate a fact already in a pinned card): −0.5 pp (+5 / −16, p = 0.027). Deduplicated against pinned-card coverage: **+0.4 pp (+8 / −0, p = 0.008)**. On top of cards, forwarding adds little recall; its value is stale suppression (E1) | OBSERVED | `fwd_on_cards.py` |
| C9 | **Exact dense search cost on this CPU** (2 vCPU Xeon, NumPy BLAS, one query) | 100k × 1,024 fp32: **56 ms**; 300k: **152 ms**. Gathering the permitted subset first is *slower* (127 ms at 100k, 30% visible) than scoring everything and masking (59 ms). The 1M run was killed by the 7 GB memory limit. ADR-004 says "milliseconds" at 100k | OBSERVED | `flat_latency.py` |
| C10 | **Postgres RLS and full-text plans** (PostgreSQL 16.15, 200k rows, 40 ACL groups, GIN on tsvector) | `@@` (`ts_match_vq`) is **not LEAKPROOF**, so under RLS the planner may not run the text predicate before the security qual. Owner-equivalent principal (all 40 groups): **1,189 ms seq scan with RLS vs 24 ms without (≈50×)**. 10-group principal: 54 ms vs 17 ms. Adding the explicit ACL predicate under RLS does not restore the GIN plan (53 ms). Marking the function LEAKPROOF (a superuser security assertion) restores it (46 ms) | OBSERVED | `rls_probe.sql` |
| C11 | Partial cards per ACL group | Only 2 of 109 carded entities are split across partitions in v0.2 (IronBark Fitness; Jordan Pike). The ACL-intersection card path is barely exercised by BrainBench | OBSERVED | `card_stats.py` |

---

## 1. ADR-001: The brain is a service, not an agent

### 1.1 Strongest case against
- **The project's own evidence favours iterative agents for hard retrieval, and the ADR admits it has no experiment.**
  - LongMemEval-V2: coding agents over files scored 68.7–74.9% vs 38–51% for RAG ([arXiv 2605.12493](https://arxiv.org/pdf/2605.12493), doc 01 §9.2).
  - Microsoft's AgenticRAG (search / find / open tools over an existing enterprise index, no fine-tuning): FinanceBench answer correctness **92.0% vs 24.2%** for traditional RAG; BRIGHT recall@1 49.6% vs 8.4% single-shot ([arXiv 2605.05538](https://arxiv.org/pdf/2605.05538)). [I, single group, pre-production]
  - Harvey runs plan → per-source query → completeness check → loop, with 3–10 retrieval operations per complex query (doc 01 §5).
- **The bottleneck is candidate generation, and iteration is the known fix.** Decision CR@200 is 23% and cross-domain 12% (batch 2). A loop that reads the card, sees "next purchase must be interstate", and then searches "interstate" reaches items no single query vector can.
- **The security argument conflates reading with writing.** MemGhost (87.5% / 71.4%) attacks agents with *memory-write* authority. A read-only agent working inside an already ACL-filtered `VisibleSet` has no more authority than the principal. The ADR's strongest reason applies to writes only.
- **Hidden assumption: "reasoning happens in the client" means the brain is outside the agent loop.** It is not. ChatGPT and Claude run their own tool loops over the MCP surface. The brain is inside an agent loop it does not control, and its 90% certification measures single-call output, not what the user receives. What matters is whose loop runs and with which tools, not "agent or service".

### 1.2 Where the steelman is weak, and why that matters
AgenticRAG collapses on breadth. On BRIGHT's Pony split (about 6.9 gold documents per query) it scores **4.8–7.1%**, because the agent reads depth-first. Decision-support tasks have 4–7 required items. Agents are good at depth (one hard target) and bad at breadth (complete sets). This supports a hybrid: structural assembly for breadth, plus a bounded loop for depth.

### 1.3 Failure over time
- **Pipeline sprawl.** Bounded pipelines accrete: rewrite, decomposition, gap-check, class router, linker, scribe, planner, checker. Each has its own registry row, prompt version and eval gate. About 12 pipelines × a model upgrade every 6–12 months means about 12 re-certifications a year. In effect this is a hard-coded agent policy with no learning.
- **Client drift.** Vendor clients change their tool-use behaviour without notice. The brain cannot certify an outcome it does not produce.

### 1.4 Burden underestimated
Per-pipeline eval gates, fallbacks and fault-injection tests multiply with the pipeline count. That cost is not budgeted.

### 1.5 Alternatives
- **(A) Read-agent sandbox (recommended).** A registered *read-only* retrieval loop:
  - tools: search, card, facts/timeline, fetch, grep;
  - all over the principal's `VisibleSet`;
  - hard caps on steps (≤8) and tokens;
  - no write tools;
  - the loop's final context is what gets scored.

  Writes stay deterministic.
- **(B) Reference client loop.** The brain ships and certifies a reference loop on its own MCP tools, so "CR as the user experiences it" is measured, not assumed (doc 01 §4 already recommends measuring over the final context a client assembles).
- **(C) Pure store.** Rejected for the same reasons the ADR gives.

### 1.6 Verdict: **Keep with changes**
Split the principle:
- **Writes:** deterministic service. Keep as is.
- **Reads:** a sandboxed, read-only, step-capped loop is allowed as a registered pipeline.

Move the agentic arm from "future" into E6 now.

### 1.7 Decisive test
**E6-agent.**
- Arms:
  - cards + router one-shot (current best);
  - the same plus gap-check;
  - a read-agent (local 8B on the GPU host, and a frontier model on the owner route) with the tools above, step cap 8.
- Metrics: CR@k of the final context, token cost, p95 latency, leakage.
- Run on BrainBench v0.2 (all 3 seeds, complex classes) and on the first real gold set.
- **Kill ADR-001-as-written:** the agent gains ≥5 pp on any multi-item class with p95 ≤ 20 s and 0 leaks. Then adopt (A).
- **Kill the agent:** it gains <3 pp, or costs >10× at equal CR.

---

## 2. ADR-003: PostgreSQL as the single transactional store

### 2.1 Strongest case against
1. **"One store, no sync window" is false by construction.**
   - Media lives in object storage.
   - ADR-004 option (b) holds vectors in an in-process matrix "invalidated in the same transaction". Process memory cannot join a Postgres transaction without LISTEN/NOTIFY or logical decoding, and either one is a sync window.
   - Embedding runs on the GPU after the commit. A new item exists in Postgres before it has a vector, so an ingestion-to-searchable lag exists regardless.
   - Card re-embedding cannot run "in the same transaction" without holding the transaction open on the GPU.

   The real architecture is already "Postgres as system of record plus derived indexes", which is the Qdrant fallback. **The E12 framing (Postgres vs Qdrant) compares the wrong things.**
2. **RLS changes query plans, and the owner gets the worst one (C10).** Text-search operators are not LEAKPROOF, so RLS forces the security qual first. An owner-visibility FTS query went from 24 ms to 1,189 ms (seq scan) on 200k rows. ADR-003 §5 says "RLS is a backstop". C10 shows a backstop is not free: it changes the plan even when the retriever already applies the ACL predicate. RLS limitations are documented: subquery policies become sub-plans, and non-leakproof functions block index use ([Bytebase](https://www.bytebase.com/blog/postgres-row-level-security-limitations-and-alternatives/)). How pg_search's custom scan behaves under RLS is **UNKNOWN**.
3. **The BM25 statistics requirement is probably not met off the shelf.**
   - ParadeDB's architecture docs describe segment-local indexes but do not say how IDF is scoped ([ParadeDB](https://www.paradedb.com/docs/concepts/architecture.md)). Bounded search: the architecture page and a docs search; source code not read.
   - pg_textsearch documents per-partition IDF and avgdl on partitioned tables ([Tiger Data](https://tigerdata.com/blog/pg-textsearch-bm25-full-text-search-postgres)).
   - C2: per-partition statistics cost 8.2 pp for BM25 alone and 2.3 pp in fusion. ADR-006's option (b), RRF over per-partition lists, cuts BM25 from 29.0 to **8.9**.

   Visible-set statistics therefore likely mean writing your own BM25 in SQL or application code. Once you do that, "Postgres does retrieval" is mostly your own code.
4. **pgvector exact scans at production dimensions.** A 1,024-d fp32 vector is 4 KB, and Qwen3-Embedding-4B at 2,560-d is 10 KB. Both are above Postgres's ~2 KB TOAST threshold, so exact sequential scans de-TOAST every row (INFERRED from TOAST mechanics). Mem0 saw selective multi-tenant filters make the planner skip HNSW: 8–14 s sequential scans, 952 GB of TOAST. They moved vector search to Turbopuffer and kept Postgres as the system of record ([Mem0](https://mem0.ai/blog/how-we-cut-vector-search-latency-by-70x)) [V; very different scale, same mechanism]. ADR-003's own cited datapoint (Harvey, pgvector at 500k, **P50 under 2 s**) is evidence *against* interactive use.
5. **Per-tenant encryption is not a vanilla Postgres feature.** ADR-003 §3 and ADR-015 specify "a schema on its own encrypted tablespace". Community Postgres has no TDE. Percona's pg_tde needs a patched server, encrypts per table, and WAL encryption was still beta at GA (June 2025) ([Percona](https://www.percona.com/blog/the-pg_tde-extension-is-now-ready-for-production/)). Realistic options: one cluster per tenant on its own encrypted volume, or application-level envelope encryption, which cannot coexist with in-database vector search.

### 2.2 Failure at scale and over time
- **Supersession churn.** Every supersession updates the old row and inserts a new one, each with 4–10 KB of TOASTed vector. That means dead-tuple bloat, vacuum pressure and backup growth. With history kept for 3–5 years, 1M items × about 3 versions × 10 KB ≈ 30 GB of vectors in TOAST alone. Restores take hours.
- **Upgrade coupling.** pgvector, pg_search (or vchord_bm25) and btree_gist are each pinned to Postgres majors. A major upgrade waits for the slowest extension.
- **Multiple builders.** Every RLS footgun (SECURITY DEFINER views, BYPASSRLS roles, `SET LOCAL` with poolers) is one PR away. The catalogue tests catch some but not plan regressions.

### 2.3 Alternatives and when each wins
| Alternative | Wins when | Loses when |
|---|---|---|
| **(A) Postgres as system of record + in-process retrieval service** (own BM25 over a token table with the chosen statistics policy; NumPy/GPU vector matrix), fed by an outbox or logical decoding, with a **read-time fence** (innovation 1) | Visible-set or frozen statistics are needed (C2, C3); the GPU host is in the path anyway; revocation must hold regardless of index lag | The team cannot run a second process; very small deployments |
| **(B) Vespa streaming mode**: per-user document groups, exact NN plus BM25, no ANN index; ≈15 ms average at 10k docs per user ([Vespa](https://blog.vespa.ai/announcing-vector-streaming-search/)) | Member tenants: thousands of small, strictly personal partitions | Owner requests span many ACL groups (a group is one user); another engine to operate |
| **(C) SQLite per member tenant** (FTS5 + sqlite-vec, one file and one key per member) | Physical isolation, crypto-shredding by deleting a key, trivial per-member export (APP 12) | The owner tier with shared ACL groups |
| **(D) Qdrant as a derived index** (ADR fallback) | Filtered ANN at >1M vectors; per-tenant IDF | Visible-set statistics inside one tenant (E4's attacker was inside one tenant) |

### 2.4 Verdict: **Rethink (narrow it)**
Keep Postgres as the **system of record** for episodes, facts, ACLs and logs. Drop the claims of a "single store" and "no sync window". Make the default "system of record + derived retrieval index + read-time fence". E12 then compares retrieval-in-Postgres against (A), not Postgres against Qdrant.

### 2.5 Decisive test: **E12 (rescoped)**
- Setup: 100k and 1M items, 3 versions per key, 40 ACL groups, 1,024-d and 2,560-d vectors.
- Measure for an owner principal and a member principal:
  - p95 hybrid latency;
  - EXPLAIN plans with RLS on vs off;
  - time from revocation to invisibility;
  - write amplification under connector churn;
  - E4 probe on each BM25 option;
  - per-tenant encryption feasibility.
- **Kill retrieval-in-Postgres:** any of these:
  - owner p95 > 300 ms at 100k;
  - any retriever plan that sequential-scans under RLS;
  - no available BM25 extension that passes E4 with visible-set or frozen statistics.

---

## 3. ADR-004: Exact (flat) vector search up to about 1M vectors

### 3.1 Strongest case against
1. **The arithmetic is optimistic by about an order of magnitude on CPU** (C9): 56 ms at 100k × 1,024, not "milliseconds". Extrapolating, 1M × 2,560 fp32 takes about 1.4 s on this CPU, against the ADR's ~0.5 s. On the GPU it is fine, but then:
   - dense retrieval availability equals GPU availability (ADR-016 degrades to lexical-only);
   - **VRAM is double-counted.** 1M × 2,560 fp32 is 10 GB (5 GB in fp16) on top of ADR-016's 42 GB core, on a 48 GB card.
2. **Exact over a lossy embedder is still lossy.** At 100k items the dominant first-stage loss is embedding quality (decision CR@200 = 23% with exact search). The 0.962 HNSW figure is one FAISS test at default parameters. With high `ef_search` and pgvector 0.8's iterative scans for the over-filtering problem ([pgvector 0.8](https://www.postgresql.org/about/news/pgvector-0.8.0-released-2952/)), ANN losses can be gated to ≤1% at depth 200. **Counterpoint that keeps the ADR alive:** required items in indirect classes sit in the low-similarity tail, which is exactly where ANN misses concentrate, so exactness matters most for the items we most need.
3. **Vector count grows faster than item count.** Text, multimodal and visual channels, plus indexed superseded versions (ADR-008), plus cards per ACL group, put roughly 3–5 vectors behind each item. "1M per channel" arrives at about 250k items.
4. **"Score only permitted rows" is the slow way** (C9). Score-all-then-mask is faster, and it also makes latency independent of hidden rows (ADR-006 §8). The ADR should specify that.

### 3.2 Burden
Re-embedding on model upgrades. At 100k–1M items the ADR-016 maintenance window is unstated. Drift-Adapter recovers 95–99% of recall@10 with a small residual MLP (about 8 µs per query, about 20k training pairs) as a bridge during re-indexing ([arXiv 2509.23471](https://arxiv.org/html/2509.23471v1)). That beats a dual index for upgrade windows, and it must pass ADR-006's fitted-model rule (fit on visible data only).

### 3.3 Alternatives
- fp16 storage by default; check for no loss.
- int8 or binary first pass + exact fp32 rescoring of the top ~2,000. That is about 32× less memory, with recall measured against flat, behind the 99% gate.
- FAISS-GPU flat when the GPU is up and the CPU matrix when it is down.
- HNSW with iterative scan behind the gate.

### 3.4 Verdict: **Keep with changes**
- Keep exact search as the **reference and the gate**.
- Specify in-process score-all-then-mask, never a SQL sequential scan over TOAST.
- Default to fp16.
- Budget VRAM in ADR-016.
- Trigger the ANN gate on measured p95 at the projected 3-year vector count, not on "1M".
- Correct the arithmetic table.

### 3.5 Decisive test
- Measure latency and memory at 100k / 300k / 1M on the target CPU and GPU, for fp32 / fp16 / int8 + rescore.
- Measure recall@200 against flat for each filter shape.
- **Kill pure-exact:** dense p95 > 100 ms at the projected 3-year vector count on target hardware. Then adopt quantised first pass + rescore behind the 99% gate.

---

## 4. ADR-005: Hybrid first stage and fusion

### 4.1 Strongest case against
1. **Fusion tuning is low-value once a reranker follows** (C4). With fusion feeding a rerank pool, wsum, RRF and plain union land within 1 pp of each other at the pool level, while pool depth is worth 11 pp. The ADR's machinery buys under 1 pp: per-class α, per-class dev sets, veto slices, and a class router just to pick α.
2. **Per-class α needs a query-time class router.** A mis-routed request gets the wrong α. That is a new failure point for a negligible gain.
3. **Min-max normalisation is fragile.** One outlier, or adding card documents to the candidate set, shifts every score.
4. **The embedder and α were picked on templated short records** (mean item length 7 words). bge-small beating Qwen3-0.6B against vendor rankings is a red flag that the corpus, not the method, decides.
5. **Hidden assumption:** BM25 with visible-set statistics is available (see ADR-003; C2). If the engine only offers per-partition statistics, BM25 degrades and the tuned α no longer applies.

### 4.2 Alternatives
- **Union or RRF to fill the rerank pool, with no tuning.**
- **Learned sparse** (SPLADE-class) replacing BM25: lexical exactness plus expansion in one channel. Not evaluated in this project.
- **Late interaction** (ColBERT-class) as a single first-stage channel: better on names and attribute combinations, where single vectors provably fail (LIMIT). Exact MaxSim at 100k is feasible on a GPU.

### 4.3 Verdict: **Keep with changes**
Keep both channels. Fill the rerank pool with RRF or union. Spend tuning effort on pool depth and the reranker. Add per-class α only if a class shows ≥1 pp at the **post-rerank** stage on real data.

### 4.4 Decisive test
- On the real dev set: post-rerank CR@10 for {union, RRF, tuned wsum} × pool {50, 100, 150}.
- **Kill per-class α:** <1 pp post-rerank gain in every class.

---

## 5. ADR-008: Memory data model

### 5.1 Strongest case against
1. **Corrections and changes are not distinguished.** A correction ("we recorded it wrong") supersedes in *record* time and leaves *valid* time alone. Fowler's example: a salary first recorded as $6,500 and later corrected to $6,400; the $6,500 "was never true" ([Fowler](https://martinfowler.com/articles/bitemporal-history.html)). ADR-008 §6 handles every update by closing `valid_to` and inserting a new row, which is change semantics. A backdated correction (the accountant revises March revenue in June) then either:
   - fakes a change in March; or
   - violates the "one current row" rule.

   The partial unique index (`valid_to IS NULL`) cannot express bi-temporal non-overlap. PostgreSQL 18's `WITHOUT OVERLAPS` covers one time axis ([Neon](https://neon.com/postgresql/18/temporal-constraints)). Two axes need a GiST exclusion constraint over (key, valid range, record range). Late or out-of-order connector events (backdated invoices) will hit this weekly.
2. **No entity merge or split primitive.** Entity resolution will be wrong sometimes. Merging two entities that each hold a current `valuation` puts two current rows on one key: the unique index rejects the merge, or the code picks one arbitrarily. Splitting is worse: which facts and mentions move where? The ADR says resolution is "the graph's first job" but defines no undo. Even mature agent-memory resolvers use auto-merge and review thresholds without documenting un-merge ([Neo4j Labs](https://neo4j.com/labs/agent-memory/explanation/resolution-deduplication/)).
3. **Schema evolution is not addressed.** Attributes get renamed ("loan" → "loan_balance"), typed-record schemas change, and keys built on attribute names then lose continuity. In industry event-sourced systems, schema evolution is the most prominent challenge. Some of the 19 systems studied gave up immutability to cope ([Overeem et al.](https://ar5iv.labs.arxiv.org/html/2104.01146)).
4. **Indexed history collapses temporal retrieval as it grows** (C5). At +10 and +40 versions per key, temporal CR@10 fell from 65 to 12 to 4. Real connectors (daily balances, KPIs) produce hundreds of versions per key within a year. Once the temporal router opens history, it hands the ranker a flood of near-duplicates. Temporal questions are answered by **ranking version rows** when they should be answered by **computing over the version chain**, which contradicts charter principle 11.
5. **Facts are written state, not reproducible projections.** Path B plans are executed. When the extraction model improves, nothing re-derives the facts from the episodes, so model upgrades cannot be shadow-tested or rolled back.
6. **Erasure stops at the database.** APP 11.2 destruction and principle 13 (adapters) reach into backups, WAL archives, replicas and trained artefacts. "Tombstone cascade" does not touch backups. The standard answer is crypto-shredding: per-tenant or per-member data keys, destroyed on erasure ([Verraes](https://verraes.net/2019/05/eventsourcing-patterns-throw-away-the-key/)).
7. **Value types miss approximation and precision** ("about 240 covers", "~650k"), ranges and qualitative states. Approximate values matched as exact will mis-link mentions (ADR-009).

### 5.2 Alternatives
- **(A) Event-source the facts.** One immutable assertion log (episodes, connector events, corrections). Facts, cards and timelines become projections tagged `pipeline_version`, re-derivable by replay. Wins over a 3–5-year horizon with model upgrades. Costs: projection rebuild time, plus schema-evolution tactics (versioned events, upcasting).
- **(B) A native bitemporal store** ([XTDB v2](https://xtdb.com/blog/launching-xtdb-v2), SQL with valid and system time). Correction semantics come built in. But it is a second store with a small community.
- **(C) Key timelines** (innovation 3). Index one row per key, collapse versions per key in ranking, and serve temporal requests by computing the timeline.

### 5.3 Verdict: **Keep with changes** (substantial)
1. Define correction vs change semantics. Enforce two-axis non-overlap with a GiST exclusion constraint.
2. Add entity merge and split primitives with fact-key reconciliation and undo.
3. Make facts projections of the log with `pipeline_version`.
4. Index key timelines, not version rows, for temporal retrieval.
5. Add crypto-shredding with per-tenant and per-member keys.
6. Add approximate and range value types.

### 5.4 Decisive tests
- **Bitemporal torture suite.** 500 scripted events, including:
  - backdated corrections;
  - late arrivals;
  - out-of-order connector deliveries;
  - correction then revert;
  - merge then split.

  As-of and known-at answers must match the oracle on 100%. Any invariant violation is a design failure.
- **History-depth sweep with a timeline arm** (`history_bloat.py` + a key-timeline arm). The "version rows indexed" kill criterion (temporal CR drops >10 pp from B = 0 to B = 40) is **already met in the sandbox** (65 → 4). The timeline arm must hold within 5 pp of B = 0.

---

## 6. ADR-009: Two write paths, mention linking, forwarding

### 6.1 Strongest case against
1. **The two paths use different keys for the same real attribute.**
   - Path A key: (`source_system`, `source_entity_id`, `attribute`).
   - Path B key: (`entity_id`, `attribute`).

   When Xero updates a loan balance (A) and the owner says in chat "the loan's now 340k" (B), each key holds one current row. That is **two current values for one real-world attribute**, and the invariant in ADR-008 check 1 passes. No source-precedence rule exists. **This is a design bug, not a tuning issue.**
2. **The 0.7% stale result rests on a simulated 90% extraction recall with uncorrelated misses.** E1's own sensitivity: suppression-only traps were 18.2% at 70% recall. Real misses correlate with the hard cases: unlabelled values ("241 covers"), relative values ("up 5%"), approximations, references to earlier notes.
3. **Link precision matters more than recall, and it is not measured.** Linking "$650k" in a note means resolving the entity × the attribute (valuation, purchase price or loan) × the version. A mis-link is worse than a miss: forwarding then injects the *wrong* entity's current value next to a correct note, labelled "superseded". The ADR tracks only an "extraction-recall report".
4. **Forwarding's recall value on top of cards is small, and negative if done naively** (C8): −0.5 pp without deduplication against cards, +0.4 pp with it.
5. **Path B cannot plausibly certify ≤2%.** The FORGETEVAL change-time planner scores 91.7–93.2%, so about 7–8% of free-text updates go wrong. A ≤2% upper bound needs about 0 failures in 149 probes. The ADR's reversal sends path B to "candidates plus human review", which makes **the owner's queue the real path B**. That queue load is unestimated; see X7.

### 6.2 Alternatives
- **(A) One assertion model, a deterministic resolver.**
  - Every source (connector, form, chat, extraction) emits *assertions*: (canonical subject, canonical attribute, value, valid time, source, trust, confidence).
  - A code resolver computes the current value per canonical key from a **source-precedence table** (attribute × source authority × trust × valid time).
  - The LLM only *proposes* assertions; it never executes supersession.

  This makes supersession testable code, fixes the A/B key bug, and fits the event-sourced model in 5.2.
- **(B) Keep the planner** for compound and partial edits only, with its output converted into assertions.

### 6.3 Verdict: **Keep with changes**
1. Map every source key to a canonical attribute key, and add a precedence table.
2. The LLM proposes, the resolver decides.
3. Report link precision as well as recall; a mis-link counts as an error.
4. Deduplicate forwarded heads against pinned-card coverage.
5. Make no stale-rate claim before real-note extraction is measured.

### 6.4 Decisive tests
- **Real-note extraction and linking.** 200 notes from the owner's existing half-built system, hand-labelled. **Kill the stale claim from N1 forwarding** if mention recall is <80% or link precision is <95%.
- **Conflict suite.** 150 cases where the same attribute arrives via connector and chat with different valid times and trust levels. **Invariant:** exactly one current value per canonical attribute, matching the precedence oracle. Kill on any violation.

---

## 7. ADR-010: Entity cards compiled in code, pinned before search

### 7.1 Strongest case against
1. **The metric counts items, not tokens, and cards are fat items** (C1). About a third of the reported card gain is extra budget. At equal words, temporal and multimodal *lose* with cards. A 154-word card covering 22 facts counts as one of the k slots. The charter's k is in items, so the design is rewarded for packing more into each item. That is a property of the metric, not of retrieval quality.
2. **Circularity by generator.**
   - 70% of decision-support required items are keyed facts because the generator made them so.
   - The 97% current-state result is circular (the ADR concedes this).
   - The share of real decision context held as keyed facts is **UNKNOWN**.
3. **Scale failure: card size.**
   - BrainBench entities average 4.2 facts (max 22). A real business has hundreds of attributes and a person dozens. "Every current keyed fact" will not fit a 10-item or ~1,500-token budget, so cards must be truncated.
   - The obvious truncation (rank facts by query similarity) loses badly (C7: goal 37.8 → 18.3). Cards work *because* they include facts the query does not mention.
   - So truncation is the unsolved core problem, and the answer is probably schema-driven core slots per entity type (I1's revenge), not query-driven selection.
4. **Materialisation cost and a hidden sync window.**
   - Cards are materialised per (entity, ACL group) and "rebuilt in the same transaction as any write". A daily connector sync touching 200 facts rebuilds dozens of cards.
   - Re-embedding them cannot run inside the transaction (GPU), so the dense card index lags, which is a stale-card window.
   - C6 shows **values-free stub cards plus read-time value compilation lose nothing**. Materialised cards carry write amplification, revocation surface and stale risk for no recall benefit.
5. **The linker is a long-tail maintenance burden:**
   - 31% lexical recall on cross-domain;
   - an oracle linker adds only 4.2 pp;
   - nicknames and new entities never stop arriving.
6. **The cap of C = 3 is arbitrary**, and it is order-dependent in the reference code (alias-length order). Cross-domain requests link 4–8 entities.
7. **The ACL-intersection card path is barely tested** (C11): 2 of 109 entities are split across partitions in v0.2.

### 7.2 Alternatives
- **(A) Read-time card views** (innovation 2). Tested (C6): no loss.
- **(B) An LLM-maintained wiki with live values.** Karpathy's LLM Wiki (April 2026) compiles raw sources into interlinked pages maintained by a model ([summary](https://denser.ai/blog/llm-wiki-karpathy-knowledge-base/)). It attacks the real bottleneck: free-text evidence is found only about 30% of the time, and cards cannot hold rationale. Its known weaknesses are compounding errors, no supersession, and scale beyond a few hundred documents. A hybrid fixes the stale-value risk: the model writes narrative and rationale, but can reference values only through fact-ID placeholders that render live (`{{fact:loan}}`). Values then cannot go stale (E1's 3.8% stale summaries came from embedded values).
- **(C) Cards that list linked evidence IDs** (N8).

### 7.3 Verdict: **Keep with changes**
- Cards become read-time views, with a stub in the index.
- Report CR at an equal **token** budget alongside CR@k items.
- Add a schema-driven truncation policy for large entities.
- Test against the LLM-wiki-with-live-values arm.

### 7.4 Decisive tests
- **Equal-token E8c rerun** on real data. **Kill pinning:** at equal tokens, cards ≤ query-only + 2 pp on non-current classes (the ADR's own reversal condition, made budget-fair).
- **Card-size stress test.**
  - Synthetic entities with 50 and 200 attributes.
  - Truncation policies: query similarity / schema core slots / recency / LLM selection.
  - **Kill** "cards as the assembly backbone" if no policy keeps ≥80% of the small-entity card gain.

---

## 8. ADR-019: Resumable work packages

### 8.1 Strongest case against
1. **Builders game tests.** ImpossibleBench found GPT-5 exploiting tests in 76% (Oneoff) and 54% (Conflicting) of impossible SWE-bench tasks, and Claude Opus 4.1 in 50–55%. Claude models mostly did it by **modifying test files** ([arXiv 2510.20270](https://arxiv.org/html/2510.20270v1)). "Only the test runner writes `passed`" does nothing if the builder edits the test the runner runs. Read-only tests stopped test modification; letting agents abort cut GPT-5 from 54% to 9%. U4 (maker never checks its own work) applies to the builder itself.
2. **Integration risk is back-loaded.** The order is harness → store/ACL → write paths → retrieval → assembly. The first end-to-end retrieval number on the real stack appears late, yet "can it reach 90%" is the project's main risk. Standard practice is a walking skeleton: a thin end-to-end slice first.
3. **Spec drift.** About 20 ADRs will change: this review alone proposes changes to 9. Packages do not record which ADR versions they implement, so a passed package silently encodes an outdated decision.
4. **It assumes greenfield.** The owner has a half-built system *with data in it*, and no package covers import, migration or reuse. That data is also the best real gold-set source available.
5. **Concurrent builders.** One `state.json` with no leases means two sessions claim the same package.

### 8.2 Verdict: **Keep with changes**
- **WP-000 is a walking skeleton:** ingest → write gate stub → store → hybrid → cards → MCP → harness, end to end, at low quality.
- Test files live outside the builder's write scope. Their hashes are recorded in `state.json`, and any diff to them needs review by a different model plus the owner.
- Packages record the hashes of the ADR versions they implement. An ADR change marks dependent packages `stale`.
- Add a **WP-migrate** package: replay the existing system's data through the new write gate. It doubles as real-data gold-set intake.
- Add package leases with expiry.
- Builders may abort ("impossible within spec") into `questions.md`.

### 8.3 Decisive test
- **Resume drill with a different builder model**, plus a test-tamper red team: plant one package whose spec is unsatisfiable.
- **Kill** the current template if any test-file modification lands in a `passed` package without sign-off, or if the builder edits tests instead of filing a question.

---

## 9. U4: Makers never check their own work

### 9.1 Strongest case against
1. **Different models are not independent checkers.**
   - "Great Models Think Alike" (ICML 2025): judges favour functionally similar models (partial correlations 0.35–0.65 after controlling for accuracy), and errors grow more similar as capability rises ([arXiv 2502.04313](https://arxiv.org/html/2502.04313v2)).
   - A 2026 Knight–Leveson replication with coding agents (arXiv 2606.20158; read via a [secondary summary](https://codex.danielvaughan.com/2026/06/20/n-version-programming-coding-agents-codex-cli-diversity-majority-voting-multi-model-resilience/); primary not checked) found coincident failures at 3.7× the independence expectation, 81 of 146 pairs failing identically, and failures **clustered on spec ambiguities**.

   For extraction, the ambiguous cases (which entity, which attribute, approximate values) are the shared failures, so the checker passes exactly the errors that matter.
2. **Verification cannot see omissions.** A checker shown the maker's output judges what is there, not what is missing. Omitted facts are the dominant extraction failure (keys extracted on about 44% of messy prose, MemStrata).
3. **Anchoring.** A checker that sees the answer tends to agree with it. Clinical data entry shows that **independent re-derivation** works: double data entry has a pooled error rate of 0.14% vs 0.29% for single entry ([Garza et al., preprint](https://pmc.ncbi.nlm.nih.gov/articles/PMC10775420)). The owner's own "double entry" framing (U2) points to re-derivation, not verification.
4. **Cost, false blocks and human vigilance.**
   - A second LLM call on every write halves local GPU ingestion throughput, and the migration replay is 100k+ items.
   - A 5% false-block rate on 100 writes a day puts 5 items a day in the owner's queue.
   - Human sampling decays under automation bias ([Goddard et al. 2012](https://academic.oup.com/jamia/article/19/1/121/732254); not re-read for this review).
5. **Self-preference is real but secondary** ([Panickssery et al.](https://arxiv.org/abs/2404.13076v1)). Changing the model removes the self-preference bias, not the shared blind spots.

### 9.2 Alternatives
- **(A) Blind dual extraction plus deterministic reconciliation** (innovation 5):
  - two extractors from different families run independently; neither sees the other's output;
  - code files the assertions they agree on;
  - disagreements go to a third model or a human.

  This catches omissions, because one extractor finds what the other missed.
- **(B) Self-consistency or semantic entropy.** Sample the maker N times; disagreement flags a confabulation ([Farquhar et al., Nature 2024](https://oatml.cs.ox.ac.uk/publications/202406_FarquharKossenKuhn_HallucinatingLLMs.html)). Cheap, and needs only one model.
- **(C) Deterministic grounding checks.** Every extracted value must appear (normalised) in its source span, and every entity must exist. These are truly independent and catch fabrication.
- **(D) Risk tiers.** Full checking only for decisions, strategy and money above a threshold.
- **(E) Planted known errors in human audit batches** ("canaries for reviewers"), to measure reviewer vigilance continuously.

### 9.3 Verdict: **Keep with changes**
- Keep the deterministic validators first, plus grounding checks.
- Replace "a different model verifies" with "a different model re-derives blind, and code reconciles".
- Tier checking by stakes.
- Plant canaries in human samples.

### 9.4 Decisive test
- **Seeded extraction-error corpus:** 500 notes with ground truth, covering omissions, ambiguous references and approximate values.
- Arms:
  - deterministic only;
  - same-model verify;
  - different-family verify;
  - different-family blind re-derive + reconcile;
  - self-consistency × 5.
- Metrics: residual error, omission catch rate, false-block rate, cost, and the φ correlation between maker and checker errors.
- **Kill "a different model checks":** residual error is not at least 30% (relative) below deterministic + self-consistency, or false blocks exceed 5%.

---

## 10. Cross-cutting objections (what the whole architecture gets wrong)

- **X1. The metric shapes the architecture.** CR@k in *items* rewards fat items: cards, slots, packets. Add a **token-budgeted CR (CR@T)** as co-primary, with T set per client. Without it, every assembly comparison is biased toward bigger items (C1).
- **X2. Seven ADRs were accepted on one synthetic generator** written by the same author as the tasks (items average 7 words; templated values). Since the 06 board, no decision has met real data. The owner's half-built system is a real corpus available now. Using its data as a private gold set does not spoil the owner's planned blind comparison of designs, so ask for an export. Make the first real-data run a gate before more ADRs move to Accepted.
- **X3. Pretending there is no sync window.** Asynchronous GPU embedding, derived indexes and object storage guarantee lag. Design for lag with a **read-time fence** (innovation 1) rather than chasing transactional coupling across processes.
- **X4. Materialised derived artefacts multiply the staleness, revocation and erasure surface:** cards per ACL group, summaries, searchable entries, packets, headers. Compute at read time wherever latency allows. C6 shows a key case costs nothing.
- **X5. No reproducibility across model upgrades.** Derived state depends on the versions of the extraction, scribe, linker and embedder pipelines. Without replayable projections tagged `pipeline_version`, an upgrade cannot be shadow-run, diffed or rolled back. Over 3–5 years this is the largest maintenance risk.
- **X6. The p^m arithmetic cuts both ways.** If 5–7-item classes need ≥98% per-item recall per item type, certification at 90% may be infeasible for those classes. The owner should decide a fallback standard now (for example, "critical items" per task, or a token-budgeted variant) rather than after the build.
- **X7. One human is the checker of last resort for everything:**
  - path B review (ADR-009);
  - the high-stakes write gate (ADR-011);
  - quarantine approvals (ADR-014);
  - U4 sampling;
  - entity-merge review.

  Nobody has estimated the combined queue. Set a **queue budget** (for example, ≤10 items a day) as a design constraint, with a degradation policy: items wait as "unverified candidate" and are served with that receipt.
- **X8. GPU contention.** Query embedding, exact dense search and reranking (interactive) share one 48 GB card with batch ASR, captioning, extraction, checkers, scribe and re-embedding. Without priority scheduling, a migration or ingest burst starves interactive search.

---

## 11. Innovations that came out of the attack

1. **Validate-at-exit fence.** Treat every index as an eventually consistent *hint*: BM25, vectors, card stubs, scribe entries, caches. Before anything leaves the brain, the final ≤200 candidate IDs are re-checked against the system of record in one primary-key query:
   - visible to this principal now?
   - the current head (or allowed by the temporal router)?
   - not erased?
   - not quarantined?

   Correctness for revocation, staleness and erasure then comes from one millisecond-scale SQL check, whatever the engine or index lag. That allows asynchronous embedding, any derived engine, and Drift-Adapter bridges. ADR-007 §2 generalised from ACL to supersession and erasure.
   - *Test:* delay every index update by 15 minutes and revoke, supersede and erase during the delay. With the fence: 0 leaks and 0 stale. Without it: measurable leaks. *Kill:* fence p95 > 10 ms at 200 IDs.
2. **Cards as read-time views with values-free stubs** (C6: 54.1 vs 54.2, n.s.). Removes:
   - card rebuild and re-embedding on write;
   - value content multiplied per ACL group;
   - stale-card risk;
   - card revocation lag.

   The stub changes only when an entity's aliases or attribute set change.
   - *Test:* the full E8c router arm with stubs on 3 seeds plus the real dev set. *Kill:* >1 pp loss.
3. **Key timelines instead of version rows.**
   - One indexed row per supersession key: entity, attribute label, aliases, no values.
   - Ranking collapses versions to one slot per key.
   - Temporal requests are answered by computing the version chain (as-of, known-at, change list in a window) and returning it as one item with receipts.

   This targets the measured collapse (temporal 65 → 4 at 40 versions per key) and applies principle 11 to time. *Test:* timeline arm in `history_bloat.py`. *Kill:* temporal CR at B = 40 more than 5 pp below B = 0.
4. **Frozen external BM25 statistics** (C3: +1.4 pp vs visible-set statistics, p = 5e-5, twin corpus). Fit IDF and avgdl once on a public general-domain corpus plus a domain glossary, with an out-of-vocabulary rule (unseen term = maximum IDF). This is:
   - leak-free by construction (passes E4 with Δ = 0 trivially);
   - engine-agnostic (only a custom IDF table is needed);
   - free of per-request document-frequency computation;
   - identical for every principal, which makes caching and debugging easier.

   *Test:* on real data with a public-corpus IDF table. *Kill:* ≥1 pp below visible-set statistics.
5. **Blind double extraction with reviewer canaries.** True double entry for U4:
   - two different-family extractors work blind;
   - code reconciles;
   - disagreements and omissions surface by construction;
   - human audit batches carry planted known errors, so reviewer vigilance is measured like leakage.

   *Test:* the U4 seeded corpus (§9.4).

**Most promising: 1 + 2 together ("compute at read, validate at exit").** Together they remove the single-store requirement from ADR-003, the materialisation burden from ADR-010, and the timing problem in the revocation SLA. They make any engine, including the asynchronous GPU path, safe. The stub-card half is already measured at no recall cost; the fence half needs the injected-lag test.

---

## 12. Verdict table

| Item | Verdict | Specific change |
|---|---|---|
| ADR-001 service not agent | Keep with changes | Deterministic writes; allow a sandboxed read-only, step-capped retrieval loop as a pipeline; add the agentic arm to E6 now |
| ADR-003 Postgres single store | **Rethink (narrow)** | Postgres as system of record only; default to a derived retrieval index + read-time fence; rescope E12 (RLS plans, TOAST, stats, encryption, revocation) |
| ADR-004 exact search | Keep with changes | Exact as reference and gate; in-process score-all-then-mask; fp16; budget VRAM; trigger ANN by measured p95; fix the arithmetic |
| ADR-005 hybrid fusion | Keep with changes | RRF or union into the rerank pool; drop per-class α unless ≥1 pp post-rerank; invest in pool depth and the reranker |
| ADR-008 data model | Keep with changes (major) | Correction vs change semantics with a two-axis exclusion constraint; merge and split primitives; facts as replayable projections; key timelines; crypto-shredding; approximate values |
| ADR-009 write paths | Keep with changes | Canonical key + source precedence (fixes the two-current-rows bug); LLM proposes assertions, code resolves; measure link precision; dedupe forwarding against cards |
| ADR-010 entity cards | Keep with changes | Read-time views + stubs; CR at equal tokens; schema-driven truncation for large entities; test the LLM-wiki-with-live-values arm |
| ADR-019 work packages | Keep with changes | Walking skeleton first; tamper-proof tests and builder abort; ADR-hash staleness; migration package; leases |
| U4 maker–checker | Keep with changes | Deterministic + grounding first; blind re-derivation and reconciliation instead of verification; risk tiers; reviewer canaries |

## 13. Proposed additions to the hypotheses board (doc 06)

| ID | Hypothesis | Status from this review | Kill criterion |
|---|---|---|---|
| DA1-1 | Card gains partly come from the larger reader budget | **Supported** (C1: 3.8 of 11.7 pp) | n/a; adopt CR@T |
| DA1-2 | Visible-set BM25 statistics are not available off the shelf in Postgres extensions | Open (pg_textsearch per-partition documented; pg_search unknown) | An extension passes E4 with visible-set statistics |
| DA1-3 | Per-partition statistics or per-partition RRF degrade lexical recall | **Supported** (C2: −8.2 pp; RRF −20 pp) | — |
| DA1-4 | Frozen external IDF ≥ visible-set IDF | Supported in a twin corpus (C3) | ≥1 pp loss on real data |
| DA1-5 | Fusion choice matters <1 pp once a reranker follows | **Supported** at pool level (C4) | ≥1 pp post-rerank gain on real data |
| DA1-6 | Indexed version rows collapse temporal recall as history grows; key timelines fix it | First half **supported** (C5); second half open | Timeline arm >5 pp below B = 0 |
| DA1-7 | Values-free stub cards equal materialised cards | **Supported** (C6) | >1 pp loss on 3 seeds or real data |
| DA1-8 | RLS degrades owner-tier lexical plans | **Supported** (C10: 50×) | E12 shows no seq-scan plans under RLS with the chosen engine |
| DA1-9 | A read-only agent loop beats one-shot assembly on depth classes but not breadth | Open (AgenticRAG evidence for both halves) | §1.7 |
| DA1-10 | Blind dual extraction beats different-model verification on residual error and omissions | Open | §9.4 |

## 14. Threats to validity of this review
- C1–C8 and C11 use **seed 1 only** and task-weighted rates. Batch 2 showed ≤2 pp seed spread for main arms, but small effects (C3, C6, C8) need all 3 seeds.
- C5's synthetic versions are clones of version 1 with perturbed values and random older dates, a near-duplicate worst case. Real version histories differ in wording and spacing, so the size of the collapse may be smaller. The direction (ranking over versions does not scale) is robust to that.
- C3's external corpus is a twin synthetic world. A real general-domain IDF will fit personal vocabulary less well.
- C9 ran on a 2 vCPU sandbox shared with other jobs (one run was killed for memory). C10 is a synthetic 200k-row table on PostgreSQL 16, not pg_search or pgvector.
- Web evidence is mixed. AgenticRAG and LongMemEval-V2 are single-group studies; the N-version agent replication was read only through a secondary summary; Goddard et al. was not re-read.
- **Bounded searches:**
  - pg_search statistics scope: the ParadeDB architecture page and a docs search; source code not read;
  - pgvector operator LEAKPROOF status: not checked (UNKNOWN);
  - pg_search behaviour under RLS: not tested.
