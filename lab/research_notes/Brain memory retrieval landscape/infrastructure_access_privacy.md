# Self-hostable Storage/Search Infrastructure, Multi-tenant Access Control, MCP Security and Australian Privacy Constraints (as of Oct 2026)

Scope note: research conducted 23 Oct 2026. Vendor-authored benchmarks are flagged **[VENDOR]**. Nothing here is legal advice; legal items report what official or law-firm sources say. Several primary pages could not be fetched (permission timeouts) and are listed in the Gaps sections: postgresql.org RLS docs (ddl-rowsecurity), authzed.com SpiceDB querying docs, docs.vespa.ai ColBERT docs, docs.aws.amazon.com Bedrock data-protection page (quoted via a secondary source instead), Google Vertex AI ZDR page, ag.gov.au privacy reform page, milvus.io/docs/multi_tenancy.md (v2.6 version was fetched instead).

---

## Q1. Engine comparison: hybrid search, BM25, multi-vector, filtered-search recall, multi-tenancy, transactions, ops, licence

### Takeaway
Every serious candidate now offers hybrid (lexical + dense) search. They differ most in three places: (a) how they keep filtered-ANN recall high, where Qdrant's filterable HNSW + ACORN + query planner has the best published 2026 evidence; (b) native late-interaction (multi-vector) support, which is native in Qdrant, Weaviate (1.29+), Vespa, LanceDB and VectorChord, and only technical-preview in Elasticsearch; (c) transactional consistency with relational facts, which only the Postgres extensions (pgvector / pgvectorscale / VectorChord / ParadeDB) provide natively. At 10k–100k items, raw ANN throughput doesn't separate the engines. Filter correctness, tenancy isolation and operational simplicity do.

### Cited Findings

**The filtered-HNSW problem (engine-neutral evidence)**
- Filters can break up HNSW's connected graph. On 1M points with default m=16, nodes averaged about 21 layer-0 links. Filtering out 96% of points left fewer than one surviving link per node, so search gets stuck before it reaches the true matches. — [Qdrant, "Filtered Vector Search: What ACORN Fixes, and What Fixes ACORN", 7 Aug 2026 [VENDOR]](https://qdrant.tech/articles/filtered-vector-search-acorn/)
- pgvector applies filters *after* the approximate index scan. With HNSW and the default `hnsw.ef_search`=40, a condition matching 10% of rows returns about 4 matches on average. — [pgvector README (v0.8.7)](https://github.com/pgvector/pgvector)
- Independent academic study (UC Merced, Feb 2026) evaluated FAISS, Milvus and pgvector. Its findings: "Milvus achieves superior recall stability through hybrid approximate/exact execution"; pgvector's cost-based optimiser can choose approximate index scans even when an exact sequential scan would give perfect recall at similar latency; and "partition-based indexes (IVFFlat) outperform graph-based indexes (HNSW) for low-selectivity queries". The study releases a filtered extension of ANN-Benchmarks and the MoReVec relational dataset. — [Amanbayev et al., arXiv:2602.11443, Feb 2026](https://arxiv.org/html/2602.11443v1)

**Qdrant**
- Two repairs for filtered search. (1) **Filterable HNSW** at index time adds extra edges between points that share an indexed payload value. Edges are built per field, not per field combination, so AND filters aren't covered. Index build rose from 116 s to 507–652 s (4.4–5.6x) on 1M points, and values shared by more than about 19% of the collection got no extra edges. (2) **ACORN-1** at query time, enabled per request with `acorn.enable` and off by default, applies below `max_selectivity` (default 0.4) and was tested on v1.18.2. A **query planner** picks between ACORN, full scan, the payload index and filterable HNSW. — [Qdrant ACORN article, Aug 2026 [VENDOR]](https://qdrant.tech/articles/filtered-vector-search-acorn/)
- Benchmark (1M deep-image-96, Recall@10, hnsw_ef=64) [VENDOR]:
  - At 1% selectivity: plain graph 0.1%, plain+ACORN 67.7%, filterable HNSW 99.8% at 1.0 ms.
  - For two-keyword AND filters at 4%: filterable HNSW 63.7%, planner+ACORN 99.9% at 13.9 ms.
  - At 0.012% selectivity, the planner routes to the payload index: 100% at 1.3 ms.
  - With defaults (planner on), enabling ACORN raised the 4% intersection from 39.7% to 100% recall. Latency rose 5–7x when the planner stayed on the graph.
  - Authors advise "measuring recall per filter shape, since a single aggregate figure can hide failing filters." — [Qdrant ACORN article](https://qdrant.tech/articles/filtered-vector-search-acorn/)
- Multi-tenancy:
  - Qdrant recommends one shared collection with a tenant payload field indexed with `is_tenant: true` (v1.11+), which co-locates a tenant's data on disk. Setting `payload_m` with `m=0` builds per-tenant HNSW links.
  - User-defined sharding (`shard_key`) is available, and **tiered multitenancy** (v1.16+) promotes large tenants to dedicated shards (suggested threshold ~20k points; avoid >~1,000 dedicated shards).
  - "Creating a separate collection for each tenant is rarely the most efficient approach."
  - BM25/IDF statistics are shard-wide by default. The `idf` parameter (v1.19+) scopes them per tenant. — [Qdrant multitenancy guide](https://qdrant.tech/documentation/guides/multiple-partitions/)
- Qdrant 1.19 (5 Aug 2026) added per-tenant IDF for BM25, language-neutral BM25 processing (stemming and stopwords can be disabled), and Turbo4 4-bit storage that also applies to multi-vector (ColBERT-style) collections. — [Qdrant 1.19 release blog [VENDOR]](https://qdrant.tech/blog/qdrant-1.19.x/)
- Access control:
  - Admin API key (v1.2) and read-only key (v1.7).
  - **JWT RBAC** (v1.9) grants `r`/`rw` per collection.
  - A `value_exists` claim makes a token valid only while a point with given key-values exists, so tokens can be revoked by changing data.
  - The docs do **not** describe JWTs that force payload filters onto search results. Row-level restriction inside a shared collection must therefore be enforced by the application's filter. — [Qdrant security docs](https://qdrant.tech/documentation/security/)

**Weaviate**
- ACORN filter strategy since v1.27 (opt-in). Pre-filtering with brute force is used for small filters (`flatSearchCutOff`). "Sweeping" degrades on restrictive, low-correlation filters, where ACORN is "up to 10x" faster. At 20% selectivity, sweeping could reach half of ACORN's throughput at the same recall (500k Cohere BEIR objects). — [Weaviate blog, 19 Nov 2024 [VENDOR]](https://weaviate.io/blog/speed-up-filtered-vector-search)
- Native multi-vector (ColBERT/ColPali/ColQwen late interaction) since **v1.29**, usable in hybrid queries. The docs cite ~25 kB per object vs 6 kB for a 1536-d single vector. — [Weaviate multi-vector tutorial](https://docs.weaviate.io/weaviate/tutorials/multi-vector-embeddings)
- Multi-tenancy: "each tenant is stored on a separate shard" and data in one tenant isn't visible to others. Tenant states are ACTIVE, INACTIVE and OFFLOADED (to cloud storage), and auto-tenant creation is off by default. — [Weaviate multi-tenancy docs](https://docs.weaviate.io/weaviate/manage-collections/multi-tenancy)

**Milvus**
- Milvus 2.5 (Dec 2024) added built-in full-text search via Sparse-BM25. Raw text is inserted without embedding, BM25 stats update as data arrives, and text match uses Tantivy analyzers. — [Zilliz blog [VENDOR]](https://zilliz.com/blog/milvus-2-5-built-in-full-text-search-advanced-query-optimization-and-more)
- Multi-tenancy tiers (v2.6 docs) — [Milvus multi-tenancy docs v2.6](https://milvus.io/docs/v2.6.x/multi_tenancy.md):
  - Database level: 64 tenants by default, RBAC supported, strongest isolation.
  - Collection level: 65,536 tenants by default, RBAC supported.
  - Partition level: 1,024 per collection, **no RBAC**.
  - Partition-key level: millions of tenants, **no RBAC**, weakest isolation.

**Vespa**
- Native ColBERT embedder (Feb 2024). Token embeddings are stored as mixed tensors (e.g. `tensor<int8>(dt{}, x[16])`), and MaxSim runs as a ranking expression in phased ranking. The post advises against HNSW on these tensors. Binarised document vectors give up to 32x storage reduction. Array input (Vespa 8.303.17+) lets each paragraph get its own ColBERT representation. As a second-phase reranker over e5-small-v2 top-50, it raised trec-covid nDCG@10 from 0.7449 to 0.7939. — [Vespa blog [VENDOR]](https://blog.vespa.ai/announcing-colbert-embedder-in-vespa/)

**LanceDB**
- Multivector MaxSim search supports **cosine only**, and an IVF_PQ index is recommended. Unindexed multivector search is brute force. LanceDB Cloud rejects brute-force multivector KNN at a row threshold ~10x lower than for single-vector columns. Deployments: OSS, Cloud and Enterprise. — [LanceDB multivector docs](https://docs.lancedb.com/search/multivector-search)

**Elasticsearch / OpenSearch**
- Elasticsearch added an **AGPLv3** option alongside SSPL 1.0 and ELv2 (reported 6 Sep 2024). — [IT Brief Australia](https://itbrief.com.au/story/elastic-reintroduces-open-source-licence-for-elasticsearch-kibana)
- Elasticsearch `rank_vectors` field (8.18) stores multiple vectors per doc for "second order ranking documents with max-sim similarity" via `script_score` with `maxSimDotProduct`. It is in **technical preview** and "may be changed or removed". — [Elastic docs 8.18](https://www.elastic.co/guide/en/elasticsearch/reference/8.18/rank-vectors.html)
- Elastic's `semantic_text` vs OpenSearch's `semantic` field (ES 9.1 vs OS 3.1, Aug 2025). Elastic: default ELSER model, default chunking, BBQ quantisation, and RRF hybrid in one retriever request. OpenSearch: needs a registered model, chunking is off by default, and hybrid needs a search pipeline. — [Elastic Search Labs, 12 Aug 2025 [VENDOR, Elastic]](https://www.elastic.co/search-labs/blog/elasticsearch-semantic-text-vs-opensearch-semantic-field)

**Typesense**
- Scoped search API keys are HMAC-derived locally from a search-only parent key. Embedded `filter_by` parameters "will be automatically applied by Typesense" and "users will not be able to override them". This supports multi-tenant documents in one collection filtered by user/org/role. Revoking the parent invalidates all scoped keys. — [Typesense API keys docs v27.1](https://typesense.org/docs/27.1/api/api-keys.html)

**Postgres family (see also Q2)**
- **pgvector 0.8.x**:
  - Iterative index scans (0.8.0+) via `hnsw.iterative_scan = strict_order | relaxed_order`, capped by `hnsw.max_scan_tuples` (default 20,000).
  - Filtering guidance: partial indexes for a few filter values, `PARTITION BY LIST` for many.
  - Multitenancy guidance is to use list partitioning or separate tables, "since a shared approximate index lets one tenant's vectors affect another's recall".
  - Types and index limits: `vector` up to 2,000 indexed dims, `halfvec` 4,000, `bit` 64,000, `sparsevec` HNSW up to 1,000 non-zeros.
  - Hybrid search = Postgres FTS + RRF or cross-encoder. — [pgvector README](https://github.com/pgvector/pgvector)
- **CVE-2026-3172**: buffer overflow in pgvector's parallel HNSW index build, affecting 0.6.0–0.8.1. It lets a database user leak data from other relations or crash the server (CVSS 8.1). Published 25 Feb 2026. — [Tenable CVE page](https://www.tenable.com/cve/CVE-2026-3172)
- **pgvectorscale**: StreamingDiskANN ("disk-backed HNSW variant") + Statistical Binary Quantization. **Label-based filtered search** works only with a `smallint[]` label column and the `&&` operator, built into the index. Other filters fall back to pgvector post-filtering. For in-memory datasets, "stick with hnsw". — [Nile pgvectorscale docs](https://www.thenile.dev/docs/extensions/pgvectorscale)
- **VectorChord**:
  - `vchordrq` index = IVF + RaBitQ with reranking; GPU-buildable.
  - Depends on pgvector types. Prefilter guide and Multi-Vector (MaxSim) retrieval guide exist.
  - **Dual-licensed AGPLv3 or ELv2**.
  - Vendor claims: up to 5x faster queries and 16x faster index builds than pgvector HNSW; 100M 768-d vectors in 32 GB at 35 ms P50 @ recall 95%. — [VectorChord docs [VENDOR]](https://docs.vectorchord.ai/vectorchord/getting-started/overview.html)
  - Hybrid via `vchord_bm25` (Block-WeakAnd BM25 index, tokenizer) + RRF in application code. On four BEIR sets, RRF beat dense on SCIDOCS and SciFact but trailed it on FiQA and Quora, and a cross-encoder rerank was best on all four. — [VectorChord hybrid search docs](https://docs.vectorchord.ai/vectorchord/use-case/hybrid-search.html)
- **ParadeDB pg_search**: BM25 via Tantivy inside Postgres, with "standard SQL and ACID transactions". **AGPLv3** (Community); Enterprise is commercial. Latest version 0.26.2, released 16 Oct 2026. Its benchmark list includes a "Permissioned Search (Score Sort)" case. — [PGXN pg_search](https://pgxn.org/dist/pg_search)

**2025–26 benchmark evidence (all have vendor ties)**
- Tiger Data (pgvectorscale's vendor; authors say they are "biased towards Postgres") ran 50M Cohere 768-d embeddings at 99% recall on a single node:
  - Postgres (pgvector 0.6.1 + pgvectorscale 0.7.0): p50 31.07 ms, p95 60.42 ms, p99 74.60 ms, **471.57 QPS**.
  - Qdrant 1.13.4: p50 30.75 ms, p95 36.73 ms, p99 38.71 ms, **41.47 QPS**.
  - Qdrant had better tail latency; Postgres had ~11x the throughput.
  - Index build: pgvectorscale ~11.1 h (single-threaded), Qdrant ~3.3 h. — [Tiger Data blog, Apr 2025 [VENDOR]](https://www.tigerdata.com/blog/pgvector-vs-qdrant)
- MariaDB.org benchmark (Mar 2026, vendor-adjacent; MariaDB placed first): dbpedia-openai-1M, 1536-d, ~94% recall.
  - QPS: MariaDB/RediSearch ~850–1000; Weaviate, pgvectorscale and pgvecto.rs ~470–570; pgvector ~250; OpenSearch, Qdrant and Milvus ~90–150.
  - Several engine versions were old (Qdrant 1.5.1, Weaviate 1.19 beta, Milvus 2.4.1).
  - No filtered-search results. — [MariaDB.org [VENDOR-ADJACENT]](https://mariadb.org/big-vector-search-benchmark-10-databases-comparison/)

### Inferences
- At 10k–100k items, unfiltered ANN performance in any of these engines is far above need: even the slowest result above is ~90 QPS at 1M vectors. The deciding factors are filter-correct recall, access-control enforcement, BM25 quality and operational burden, not raw QPS.
- Unfiltered benchmarks (MariaDB, Tiger Data) say almost nothing about permission-filtered retrieval, which is this project's hard case. The only rigorous filtered evidence found is Qdrant's (vendor) and the UC Merced paper (independent, but it doesn't test Qdrant or Weaviate). A builder should run a per-filter-shape recall test on their own data, as Qdrant itself recommends.
- At small scale (≤100k), a per-user access filter often matches only hundreds to a few thousand items. That falls in the "very selective" regime, where the right plan is exact/brute-force scoring over the permitted set. Qdrant's planner does this automatically. Postgres does it if the planner chooses a B-tree/bitmap scan on ACL columns followed by exact distance sort. Exact search over a few thousand vectors is cheap and gives 100% recall.
- Licence summary (only items verified this session): ParadeDB pg_search AGPLv3; VectorChord AGPLv3/ELv2; Elasticsearch AGPLv3/SSPL/ELv2. For a self-hosted internal system, AGPL is generally workable, but it matters if the service is offered to external users (gym members) over a network. A builder should get legal review.

### Gaps
- Licences of Qdrant, Weaviate, Milvus, Vespa, LanceDB, Typesense, OpenSearch, pgvector and pgvectorscale were not verified from primary sources this session. Training knowledge, unverified: Qdrant, Milvus, Vespa, LanceDB and OpenSearch Apache-2.0; Weaviate BSD-3; Typesense GPL-3.0; pgvector and pgvectorscale PostgreSQL licence.
- No independent 2025–26 benchmark was found that compares *filtered* recall across Qdrant, Weaviate, Milvus and pgvector with the same harness. VectorDBBench filtered results weren't retrieved.
- Vespa docs (docs.vespa.ai/en/rag/colbert.html) were blocked. Vespa's BM25 + tensor hybrid and multi-tenancy features are not documented here beyond the 2024 blog.
- Milvus multi-vector / late-interaction support was not verified.
- No primary data was found on OpenSearch document-level security or Elasticsearch DLS interaction with kNN in 2025–26.

---

## Q2. Is a single Postgres-centric stack (relational facts + vectors + BM25 + RLS) viable at 10k–100k vs a specialised vector DB?

### Takeaway
Yes, at this scale the evidence supports a Postgres-centric stack. The combination is: pgvector, or VectorChord for multi-vector; pg_search or vchord_bm25 for BM25; relational and temporal tables for facts with validity periods; and RLS or application-enforced ACL predicates. Its unique advantage is one ACID transaction across facts, ACLs, text and vectors, so there is no sync lag. That removes a whole class of leakage: a revoked permission still present in a separate vector index. The main risks are filtered-ANN recall loss (fixable with iterative scans, partial indexes or partitions, or exact scans over small permitted sets) and RLS pitfalls: bypass roles, views, LEAKPROOF and planner effects, and connection pooling.

### Cited Findings
- pg_search keeps data and BM25 search in one database with "standard SQL and ACID transactions". — [PGXN pg_search](https://pgxn.org/dist/pg_search)
- VectorChord is "fully compatible with pgvector data types and syntax", and it and vchord_bm25 run inside Postgres alongside each other (vchord-suite image). — [VectorChord overview](https://docs.vectorchord.ai/vectorchord/getting-started/overview.html); [VectorChord hybrid search](https://docs.vectorchord.ai/vectorchord/use-case/hybrid-search.html)
- Supabase's documented "RAG with Permissions" pattern: RLS on `document_sections` with a policy joining to `documents.owner_id = auth.uid()`. Because RLS applies to every `select`, similarity search with `<#>` returns only rows the user can access, and extra filters still respect the policy. Multi-owner access uses a `document_owners` join table. External identity is supported via a session variable (`app.current_user_id`) set at the start of every request, or a custom JWT. Caveat: RLS is latency-sensitive; measure with the query plan analyser. — [Supabase docs](https://supabase.com/docs/guides/ai/rag-with-permissions)
- RLS footguns (Bytebase, 5 Sep 2025):
  - Superusers and table owners are exempt by default; use `FORCE ROW LEVEL SECURITY` and never give app roles BYPASSRLS.
  - Views created by privileged roles bypass policies; use `security_invoker = true` (PG15+).
  - Materialized views, exports and background jobs copy data outside policy coverage.
  - Non-LEAKPROOF functions in policies can block index pushdown, causing full scans.
  - Pooled connections share one role, so set the tenant in per-transaction session variables and prevent clients from setting `app.*`.
  - Timing side channels can leak row existence. — [Bytebase](https://www.bytebase.com/blog/postgres-row-level-security-footguns/)
- The planner must apply RLS checks before non-LEAKPROOF functions. One example: a pg_trgm GIN index was ignored under RLS because ILIKE wasn't LEAKPROOF. "RLS can add performance overhead even for simple queries." — [pganalyze 5mins of Postgres E28 (2022)](https://pganalyze.com/blog/5mins-postgres-row-level-security-bypassrls-security-invoker-views-leakproof-functions)
- pgvector recommends list partitioning or separate tables for tenant isolation, because a shared approximate index lets one tenant's vectors affect another's recall. Iterative scans mitigate under-filled results. — [pgvector README](https://github.com/pgvector/pgvector)
- The pgvector optimiser may choose an approximate index scan even when an exact sequential scan would give perfect recall at similar latency. — [arXiv:2602.11443](https://arxiv.org/html/2602.11443v1)
- Specialised engines lead on tail latency at large scale: Qdrant p99 38.7 ms vs Postgres 74.6 ms at 50M/99% recall. Postgres leads on throughput. [VENDOR] — [Tiger Data](https://www.tigerdata.com/blog/pgvector-vs-qdrant)

### Inferences
- With RLS, the policy predicate is evaluated as a filter on rows coming out of the vector index scan. This is effectively *post-filtering* inside the database, so it is **leak-safe but recall-unsafe**: correct rows only, but possibly fewer than k. This needs to be verified with EXPLAIN on the builder's schema. The mitigations: enable `hnsw.iterative_scan`; partition or partial-index by tenant or visibility class; or, for small permitted sets, force an exact scan (B-tree on ACL, then `ORDER BY distance`).
- A practical "zero-leakage" Postgres design:
  - Every retrievable row (chunk, image region, video segment, fact, graph edge) carries ACL columns, or joins to an ACL table.
  - All retrieval runs as a non-owner role with FORCE RLS.
  - Identity is set per transaction with `SET LOCAL` or `set_config(..., true)` from a verified token, never from model output.
  - BM25 (pg_search/vchord_bm25), vectors and graph-hop queries all hit the same RLS-protected tables, so ranking, snippets and counts are computed only over visible rows. pg_search's "Permissioned Search" benchmark suggests ParadeDB has optimised this path; not verified.
  - BM25 IDF statistics may still be corpus-global in pg_search and vchord_bm25. Global IDF can in principle leak the existence or frequency of terms in hidden documents through score differences. Qdrant explicitly fixed the per-tenant version of this in 1.19. Whether pg_search or vchord_bm25 compute IDF over the RLS-visible set is unknown (see Gaps).
- Keep pgvector ≥0.8.2 (CVE-2026-3172 affects 0.6.0–0.8.1 and allows cross-relation data leakage by a database user).
- A specialised vector DB adds a second source of truth that must be ACL-synchronised, and deletion and revocation must propagate. For 10k–100k items, that complexity buys little performance.

### Gaps
- The official PostgreSQL RLS documentation page was blocked. Default-deny semantics and the referential-integrity bypass weren't quoted from source.
- No source confirmed whether pgvector's distance operators are LEAKPROOF, or how RLS quals interact with HNSW `ORDER BY ... LIMIT` plans. Needs a builder test.
- Unknown whether ParadeDB pg_search or vchord_bm25 BM25 statistics (IDF, doc counts) are computed over all rows or only RLS-visible rows. This is a potential score side channel to test.
- No public benchmark of RLS overhead on hybrid vector + BM25 queries at 100k rows was found.

---

## Q3. Access-control patterns for RAG, leakage failure modes, and OWASP LLM Top 10 2025

### Takeaway
Pre-filtering, meaning authorisation applied inside the retrieval query before ranking and top-k, is the only pattern that satisfies "no leakage via ranking, snippets or counts" while still returning a full k results. Post-filtering is leak-safe only if nothing derived from unfiltered candidates is exposed (counts, scores, cache entries, logs), and it degrades recall. ReBAC/ABAC engines (OpenFGA, SpiceDB, Cerbos) integrate by producing either an ID list or a query-plan filter that is pushed into the vector or BM25 query. The newest failure mode, retrieval pivots in hybrid vector + graph RAG, requires authorisation at *every* hop, not just the seed retrieval.

### Cited Findings
- **OWASP LLM08:2025 Vector and Embedding Weaknesses** — [OWASP GenAI](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/):
  - Risks: unauthorised access via misaligned access controls; "context leakage between users or queries" in multi-tenant setups; embedding inversion that can "recover significant amounts of source information"; data poisoning; behaviour alteration.
  - Scenario: groups sharing one vector DB see each other's embeddings retrieved.
  - Mitigations: "permission-aware vector stores" with "strict logical and access partitioning of datasets"; accept data only from verified sources; detect hidden content (e.g. white-on-white prompt injection in a résumé); tag data by access level; "detailed immutable logs of retrieval activities".
  - No specific mitigation is given for embedding inversion.
- **OpenFGA RAG patterns** — [OpenFGA docs](https://openfga.dev/docs/modeling/agents/rag-authorization):
  - Pre-filter: `ListObjects`, then pass IDs as a vector-search metadata filter. It "guarantees all results are authorized" but adds overhead when users can access most documents.
  - Post-filter: `BatchCheck` on candidates. Over-fetch "2-3x your target count"; it may return fewer than k.
- **Cerbos**: `PlanResources` produces a query plan (e.g. `KIND_CONDITIONAL` on department/region) that "can be converted into a metadata filter that can be applied to the vector store query". Each vector store needs its own adapter. — [Cerbos RAG recipe (v0.42)](https://docs.cerbos.dev/cerbos/0.42.0/recipes/ai/rag-authorization)
- **SpiceDB** has a LangChain retriever (`langchain-spicedb`, authzed/langchain-spicedb). Mechanism details were not retrieved. — [LangChain retrievers index](https://docs.langchain.com/oss/python/integrations/retrievers/spicedb.md)
- **Typesense scoped keys** embed non-overridable `filter_by` ACLs in the API key itself. This is server-enforced pre-filtering. — [Typesense docs](https://typesense.org/docs/27.1/api/api-keys.html)
- **Qdrant JWT RBAC** restricts per collection, not per payload value. Row-level filters in shared collections are the application's responsibility. — [Qdrant security docs](https://qdrant.tech/documentation/security/)
- **Milvus**: RBAC is available only at the database and collection tenancy levels, not partition or partition-key. — [Milvus multi-tenancy v2.6](https://milvus.io/docs/v2.6.x/multi_tenancy.md)
- **Retrieval pivot attacks (hybrid vector + graph RAG)** — [Thornton, arXiv:2602.08668v2, Feb 2026](https://arxiv.org/html/2602.08668v2):
  - An authorised vector seed links to a shared entity (e.g. a vendor), and a 2-hop graph expansion reaches another tenant's confidential documents. Leakage happened at pivot depth 2 across all corpora.
  - Retrieval pivot rate (RPR) ≈0.95 on a synthetic enterprise corpus (vector-only = 0.0), 0.695 on Enron (50k emails), 0.085 on SEC 10-K.
  - It occurs even **without injection**, via benign queries naming bridge entities.
  - Fix: **per-hop authorisation at graph expansion**. It reduced leakage to 0 in all tested configurations with negligible latency, provided tenant and sensitivity labels are system-assigned rather than set by uploaders. Labels were tested with up to 5% mislabels.
- **Per-tenant BM25 statistics**: Qdrant documents that BM25/IDF scoring uses shard-wide statistics by default, and v1.19 added per-tenant IDF. This confirms that shared corpus statistics are a real cross-tenant coupling in scoring. — [Qdrant multitenancy guide](https://qdrant.tech/documentation/guides/multiple-partitions/); [Qdrant 1.19](https://qdrant.tech/blog/qdrant-1.19.x/)
- **Shared-index recall coupling**: pgvector notes a shared approximate index lets one tenant's vectors affect another's recall. — [pgvector README](https://github.com/pgvector/pgvector)
- **RLS side channels**: timing differences can leak row existence. — [Bytebase](https://www.bytebase.com/blog/postgres-row-level-security-footguns/)

### Inferences
- Recommended layered pattern for a zero-leakage brain:
  1. The identity comes from a validated OAuth token (see Q4), never from the LLM.
  2. Resolve the principal's grants (OpenFGA `ListObjects` / SpiceDB `LookupResources` / Cerbos `PlanResources`, or native Postgres ACL tables).
  3. Push the grants as a pre-filter into *every* retriever (BM25, dense, multi-vector, graph traversal, time-filtered fact queries).
  4. Re-check final candidates with a BatchCheck or Check as defence in depth before content enters the prompt.
  5. Log retrievals immutably (OWASP LLM08).
- Leakage channels to design out explicitly:
  - Post-filter counts ("12 results, 3 shown").
  - Global BM25 IDF/df statistics.
  - Score-normalisation across hidden docs in fusion.
  - Semantic or response caches keyed only on query text. Key caches by principal or ACL hash.
  - Precomputed summaries, clusters or "memory consolidation" outputs that mix sources of different visibility. A derived item must inherit the *intersection* of its sources' ACLs.
  - Graph entities that bridge tenants (per-hop auth).
  - Snippets and highlights computed before filtering.
  - Embedding inversion if raw vectors are exposed. Never return vectors to clients.
  - Materialized views and exports that bypass RLS.
  - Timing.
- Prompt injection can't be prevented at the model layer. Any retrieval tool the model calls must therefore be bound to the *user's* authorisation context server-side, so injected instructions ("search all tenants") can't widen scope.
- Health data (gym member injuries) should be a separate sensitivity class with its own labels and possibly a physically separate partition or schema. The OWASP "strict logical and access partitioning" language supports this.

### Gaps
- SpiceDB documentation (LookupResources, consistency/ZedTokens and the "new enemy" problem) was blocked. Revocation-consistency guarantees aren't cited here.
- No primary source was found for documented semantic-cache cross-tenant leaks in production RAG (CVE-level). NVD CVE-2025-25282 couldn't be read.
- OWASP LLM01 (prompt injection) and LLM02 (sensitive information disclosure) pages were not fetched. Only LLM08 is cited.
- No source quantified OpenFGA ListObjects latency with large ID lists, or the practical cut-over between pre- and post-filtering.

---

## Q4. MCP security: OAuth 2.1 per-user authorisation (2025-11-25 spec), token passthrough, confused deputy

### Takeaway
The current MCP spec (2025-11-25) makes the MCP server an OAuth 2.1 **resource server**. It must validate that every token was issued *for it* (audience binding via RFC 8707 resource indicators), it must not accept or pass through any other token, and it must verify every request because sessions must not be used for authentication. For a multi-user brain exposed via MCP, this means per-user tokens with narrow scopes. The server derives the user identity from the token and applies that user's ACL to every retrieval.

### Cited Findings
- Authorisation is OPTIONAL in MCP, but HTTP transports that support it SHOULD conform. STDIO transports SHOULD NOT follow the spec and instead retrieve credentials from the environment. It is based on OAuth 2.1 draft-13, RFC 8414, RFC 7591 (DCR), RFC 9728 (Protected Resource Metadata) and Client ID Metadata Documents. — [MCP Authorization spec 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
- MCP servers **MUST** implement RFC 9728 Protected Resource Metadata. Client ID Metadata Documents are SHOULD (most common case). DCR is MAY, "for backwards compatibility". — [MCP Authorization spec](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
- Clients **MUST** send the RFC 8707 `resource` parameter (canonical MCP server URI) in both authorization and token requests. Clients MUST implement PKCE with S256 and MUST refuse to proceed if `code_challenge_methods_supported` is absent. — [MCP Authorization spec](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
- Normative quotes — [MCP Authorization spec](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization):
  - "MCP servers **MUST** validate that access tokens were issued specifically for them as the intended audience"
  - "MCP servers **MUST NOT** accept or transit any other tokens"
  - "The MCP server **MUST NOT** pass through the token it received from the MCP client" to upstream APIs (it must obtain a separate upstream token)
  - "take all necessary steps to ensure no data is returned to unauthorized parties"
  - Authorization MUST be included in every HTTP request; tokens MUST NOT be in query strings
  - Short-lived access tokens SHOULD be used; refresh tokens MUST rotate for public clients
- Step-up authorisation: 403 with `WWW-Authenticate: Bearer error="insufficient_scope", scope="..."`. Clients acting for users SHOULD re-authorise with the increased scope. — [MCP Authorization spec](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
- **Token passthrough** is "explicitly forbidden". Risks: security-control circumvention, loss of audit trail, trust-boundary breaks, and use of the server as an exfiltration proxy with a stolen token. — [MCP Security Best Practices 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices)
- **Confused deputy**:
  - Vulnerable conditions: an MCP proxy using a static client ID upstream, plus DCR, plus an upstream consent cookie, plus no per-client consent.
  - Proxies MUST keep a per-user registry of approved client_ids and show an MCP-owned consent page (client name, scopes, redirect_uri, CSRF protection, anti-framing).
  - Exact redirect_uri matching is required.
  - `state` must be single-use and set only after consent. — [MCP Security Best Practices](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices)
- **Session hijacking**: "MCP servers that implement authorization **MUST** verify all inbound requests. MCP Servers **MUST NOT** use sessions for authentication." Session IDs must be secure random, and SHOULD be bound to the user (`<user_id>:<session_id>`). — [MCP Security Best Practices](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices)
- **Scope minimisation**: start with minimal scopes such as `mcp:tools-basic` and elevate incrementally. Common mistakes include wildcard scopes and "treating claimed scopes in token as sufficient without server-side authorization logic". — [MCP Security Best Practices](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices)
- **SSRF** in OAuth metadata discovery: block private and link-local ranges (incl. 169.254.169.254), enforce HTTPS, use egress proxies. — [MCP Security Best Practices](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices)

### Inferences
- For the brain, the MCP server is the policy enforcement point. It maps the token `sub` (plus group and role claims or an FGA lookup) to the retrieval ACL context. Every tool (search, get_item, list, graph_expand, count) applies it. No tool should take a user, tenant or ACL as a model-supplied argument.
- Scopes should separate sensitivity classes (e.g. `memory:read:personal`, `memory:read:business`, `memory:read:health`). Combine them with server-side FGA, because the spec warns scopes alone are insufficient.
- If the brain calls downstream services such as model APIs or Google Drive, it must use its own separate credentials, never the client's token.

### Gaps
- No 2026 MCP spec revision after 2025-11-25 was checked. A newer revision may exist; the builder should check modelcontextprotocol.io for the latest version.
- The MCP authorization extensions repository (ext-auth) was not reviewed. It may contain enterprise-managed authorisation or token-exchange patterns.

---

## Q5. Australian privacy constraints and data-residency options (hosting and model APIs)

### Takeaway
Gym member injury and training data is **health information, which is sensitive information**. Collecting it generally requires consent and must be reasonably necessary. A gym providing services in relation to physical health is likely a "health service provider" covered by the Privacy Act regardless of the $3M small-business threshold; the builder should confirm this with a lawyer. Sending personal information to an overseas model API is likely an APP 8 cross-border disclosure. The entity remains accountable (s16C) unless the provider is contractually confined, so that it counts as a "use" with effective control retained, or an exception applies. As of Oct 2026, Australia-region inference is available for Claude via **Amazon Bedrock (AU cross-region: Sydney + Melbourne)**. It is **not** available on Anthropic's first-party API (only `us`/`global`). OpenAI offers Australian data residency to approved API enterprise customers. Google Vertex lists australia-southeast1, but per-model availability couldn't be confirmed. Privacy reform: tranche 1 is law (Dec 2024); the statutory tort has been live since 10 Jun 2025; ADM transparency starts 10 Dec 2026. Tranche 2 exists only as an exposure draft (Aug 2026), which proposes 72-hour breach notification, a controller/processor split and a "fair and reasonable" test.

### Cited Findings

**Coverage and sensitive information**
- Small business = annual turnover ≤$3M, but the Act covers **health service providers regardless of turnover**. These are defined as businesses that "provide services in relation to physical, emotional, psychological and mental health". — [OAIC small business page](https://www.oaic.gov.au/privacy/privacy-for-organisations/small-business)
- APP 3.3: an entity "may only solicit and collect sensitive information if the individual consents" (unless an APP 3.4 exception applies), and collection must be reasonably necessary. Consent must be informed, voluntary, current and specific, and given by someone with capacity. Express consent is generally preferable, and consent can't be inferred from silence. Permitted health situations (s16B) cover providing a health service only where collection is required or authorised by law, or under professional confidentiality rules. — [OAIC APP Guidelines ch. 3](https://oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-3-app-3-collection-of-solicited-personal-information)
- OAIC (Oct 2025): "Many Australians view their health information as being particularly sensitive." Health service providers made the most NDB notifications in 2023-24 (217) and received the most complaints in 2024-25 (411). — [OAIC HIM conference keynote](https://www.oaic.gov.au/news/speeches/national-health-information-management-conference-2025-keynote-health-data-privacy-trends-and-challenges)

**APP 8 cross-border disclosure and APP 11**
- APP 8 requires reasonable steps (generally an enforceable contract) so that an overseas recipient complies with the APPs. **s16C** makes the Australian entity liable for the recipient's breaches, even if reasonable steps were taken. — [OAIC APP Guidelines ch. 8](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-8-app-8-cross-border-disclosure-of-personal-information)
- Giving data to an overseas cloud provider can be a **use, not a disclosure**, where a binding contract limits the provider to storage and access, subcontractors are bound, and "the contract gives the entity effective control". Factors: the ability to access, change, retrieve and permanently delete the data; who else has access; security. The entity still "holds" the information and remains responsible under APP 11. Routing data in transit through overseas servers is usually a use. — [OAIC APP 8 guidelines paras 8.10, 8.14–8.15](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-8-app-8-cross-border-disclosure-of-personal-information)
- APP 8 exceptions — [OAIC APP 8 guidelines](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-8-app-8-cross-border-disclosure-of-personal-information):
  - Informed consent after being "expressly inform[ed] ... that if they consent to the disclosure, this principle will not apply". The individual loses redress under the Act.
  - Reasonable belief that the recipient is bound by a substantially similar law with accessible enforcement.
- OAIC AI guidance (Oct 2024, updated Jan 2025):
  - "do not enter personal information, and particularly sensitive information, into publicly available AI chatbots".
  - Use or disclose only for the primary purpose (APP 6) unless consent or a reasonably expected related secondary purpose applies.
  - Consider "whether personal information could be disclosed outside of Australia".
  - Update privacy policies to cover AI use.
  - Due diligence "should not amount to a 'set and forget' approach". — [OAIC guidance on commercially available AI products](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products)

**Notifiable Data Breaches**
- 1,205 NDB notifications in calendar 2025 (+8% on 1,112 in 2024). Health service providers were the top sector (225, 19%), and malicious or criminal activity caused 716. The scheme requires reporting breaches "likely to result in serious harm". — [OAIC media release, 6 Jul 2026](https://www.oaic.gov.au/news/media-centre/data-breach-notifications-increase-to-all-time-high-in-2025,-new-ndb-stats-show)

**Reform status**
- Tranche 1, *Privacy and Other Legislation Amendment Act 2024*: Royal Assent 10 Dec 2024. — [MinterEllison](https://www.minterellison.com/articles/draft-tranche-2-privacy-reforms-what-they-mean-for-businesses)
  - It introduced the statutory tort, tiered penalties, doxxing offences and Children's Code groundwork. — [Allens, Sep 2026](https://www.allens.com.au/insights-news/insights/2026/09/a-new-era-for-privacy-what-the-proposed-privacy-act-reforms-mean-in-practice/)
  - Statutory tort for serious invasions of privacy commenced **10 June 2025**. — [Kennedys](https://kennedyslaw.com/en/thought-leadership/article/2025/australia-introduces-statutory-tort-of-serious-invasion-of-privacy-apac)
  - ADM transparency (new APPs 1.7–1.9, requiring privacy policies to describe automated decisions) commences **10 December 2026**. — [Corrs](https://corrs.com.au/insights/automated-decision-making-preparing-for-the-new-transparency-obligation)
  - The OAIC must publish the Children's Online Privacy Code by 10 Dec 2026. — [Allens](https://www.allens.com.au/insights-news/insights/2026/09/a-new-era-for-privacy-what-the-proposed-privacy-act-reforms-mean-in-practice/)
- Tranche 2: exposure draft *Privacy Amendment (Personal Data Protection) Bill 2026* released by AGD on **31 Aug 2026**; submissions closed **18 Sep 2026**; no commencement date. — [MinterEllison](https://www.minterellison.com/articles/draft-tranche-2-privacy-reforms-what-they-mean-for-businesses); [HSF Kramer](https://www.hsfkramer.com/insights/2026-09/the-draft-tranche-2-privacy-act-reforms-whats-there-whats-new-and-whats-missing)
  - Key proposals: a "fair and reasonable" test replacing much of APPs 3, 4 and 6; controller/processor (new s16D, where processors are still bound by APP 1 and APP 11 and controllers are liable for processor acts); **72-hour** OAIC breach notification; APP 11 duties to map holdings, assess security regularly and destroy unneeded data; and adding precise geolocation and biometric information to "sensitive information". — [HSF Kramer](https://www.hsfkramer.com/insights/2026-09/the-draft-tranche-2-privacy-act-reforms-whats-there-whats-new-and-whats-missing); [MinterEllison](https://www.minterellison.com/articles/draft-tranche-2-privacy-reforms-what-they-mean-for-businesses); [Allens](https://www.allens.com.au/insights-news/insights/2026/09/a-new-era-for-privacy-what-the-proposed-privacy-act-reforms-mean-in-practice/)
  - The small-business exemption ($3M) and employee-records exemption **remain**. The amended "discloses" definition says mere transmission or storage (incl. overseas) is not disclosure unless the information is made "accessible", which Allens calls unclear. Government intends to introduce legislation before end of 2026; Allens recommends at least two years' implementation. — [Allens](https://www.allens.com.au/insights-news/insights/2026/09/a-new-era-for-privacy-what-the-proposed-privacy-act-reforms-mean-in-practice/)

**Model API residency and retention (as of Oct 2026)**
- **Anthropic first-party API**: `inference_geo` supports only `"us"` and `"global"` (Claude 4.6+). US-only costs 1.1x. Workspace (storage) geo: "Currently, `"us"` is the only available workspace geo." On Bedrock and Google-managed Vertex, the region is set by the endpoint or inference profile instead. — [Claude data residency docs](https://platform.claude.com/docs/en/manage-claude/data-residency)
- **Anthropic retention**: under ZDR, "Anthropic does not store customer prompts or responses at rest after the API response is returned". ZDR is by request via sales, per organisation. Not ZDR-eligible: Files API, Batch (29-day), code execution, MCP connector, Agent Skills and others. Certain "Covered Models" require 30-day retention. Flagged content may be retained up to 2 years even with ZDR. — [Claude API and data retention docs](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention)
- **Anthropic in Australia**: (July 2026) "exploring adding local capacity through our third-party partners in Australia". It has an MOU with the Australian government committing it to the government's Data Centre Expectations. No in-region first-party inference was announced. — [Forbes Australia, 8 Jul 2026](https://forbes.com.au/news/innovation/australia-is-the-worlds-biggest-claude-user-now-anthropic-wants-more)
- **Amazon Bedrock AU cross-region inference** for Claude Sonnet 4.5 and Haiku 4.5 (31 Oct 2025): Sydney (ap-southeast-2) and Melbourne (ap-southeast-4). Bedrock "processes the inference requests within the geographic boundaries" of Australia; profile IDs e.g. `au.anthropic.claude-sonnet-4-5-20250929-v1:0`. — [AWS ML blog](https://aws.amazon.com/blogs/machine-learning/introducing-amazon-bedrock-cross-region-inference-for-claude-sonnet-4-5-and-haiku-4-5-in-japan-and-australia/)
- **Bedrock data handling**: "Amazon Bedrock doesn't store or log your prompts and completions" and "doesn't use your prompts and completions to train any AWS models and doesn't distribute them to third parties." Quoted from AWS docs by a secondary source. — [Simon Willison, 5 Dec 2024](https://simonwillison.net/2024/Dec/5/amazon-bedrock-data-protection/)
- **OpenAI** (25 Nov 2025): data residency regions include **Australia**. API Platform: "requests made through region-specific Projects are handled in-region, and model requests and responses are not stored at rest". Available to enterprise customers approved for advanced data controls. ChatGPT Enterprise/Edu get at-rest residency. — [OpenAI announcement](https://openai.com/index/expanding-data-residency-access-to-business-customers-worldwide)
- **Google Vertex AI**: the data-residency table has a column for "Australia (australia-southeast1)". The fetched copy didn't show which models are marked. "Requests submitted to a `global` endpoint may be processed in any Google Cloud location around the world, and therefore don't provide any data residency guarantees." — [Vertex AI data residency](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/data-residency)
- **Azure OpenAI**: "data is stored in the same region as the endpoint". Prompts "may be processed between regions within the geography". This is a Microsoft Q&A answer, not authoritative documentation. — [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/1704944/azure-openai-regional-data-use)
- **Australian sovereign providers** exist, e.g. AUCloud and Vault Cloud. Search results only; certifications were not verified. — [AUCloud platform overview](https://docs.australiacloud.com.au/latest/Platform_Overview); [Vault Cloud](https://vaultcloud.com.au/)

### Inferences
- Hosting:
  - Self-hosting the brain (DB, indexes, embeddings, rerankers) on Australian infrastructure keeps storage out of APP 8. Options include AWS Sydney/Melbourne, an Australian provider or on-prem.
  - Running **embedding and reranking models locally** (open-weight) avoids sending raw content offshore at ingest. Ingest is the highest-volume flow.
  - APP 11 duties (and tranche 2's mapping and destruction duties) apply regardless of where data is hosted.
- Model calls: for prompts that may contain health or other sensitive information, the most defensible option found is **Claude via Bedrock AU inference profiles**, which keeps processing in Australia. Alternatives are OpenAI API region-specific Projects in Australia (enterprise approval needed) and Vertex australia-southeast1 if the model is listed. Anthropic first-party API calls currently route to the US or globally, so they are offshore disclosure or use. If used, add ZDR, contractual controls and privacy-policy disclosure, or route health-class content away from them. A policy router keyed on sensitivity labels (the same labels used for ACLs) can enforce this.
- Practical pattern for "zero leakage + privacy": sensitivity labels drive (a) retrieval ACL, (b) which model endpoint may see the content, and (c) retention and destruction schedules. Members' health data gets express consent at collection, with a notice that names the AI processing and any overseas recipients.
- The 72-hour breach notification (if enacted) and the record NDB volumes favour immutable retrieval logs (OWASP LLM08) that can reconstruct exactly which content was exposed to which principal.

### Gaps
- The AGD privacy reform page (ag.gov.au) was blocked. Tranche 2 status comes from law-firm summaries; no official AGD text was quoted.
- The NDB scheme's 30-day assessment and "as soon as practicable" notification rules weren't fetched from OAIC in this session.
- No source confirmed whether a gym or personal-training business is a "health service provider" under the Act. The OAIC definition is broad, but the classification needs legal advice.
- The Bedrock AU profile was confirmed only for Sonnet 4.5 and Haiku 4.5 (Oct 2025). Availability of newer Claude models (4.6+/5.x) via AU profiles wasn't verified. The AWS Bedrock data-protection page itself was blocked; it's quoted via a secondary source.
- The Vertex AI ZDR page was blocked, as was confirmation of which Gemini models run in australia-southeast1.
- Azure OpenAI Australia East data-zone or in-region guarantees weren't confirmed from official docs.
- IRAP and other certification status of Australian sovereign providers wasn't verified.
- Whether APP 8 is triggered when a provider processes in-memory only, with no storage (ZDR) and contractual restrictions, isn't directly addressed by OAIC. Para 8.14's "effective control" factors are the closest guidance.
