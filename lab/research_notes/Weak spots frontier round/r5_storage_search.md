# Storage and Search Engine Evidence for a Self-Hosted Multi-Tenant Memory "Brain" (as of 2026-10-23)

Scope: engine choice (PostgreSQL-centric vs Qdrant), filtered-recall behaviour, RLS overhead, BM25-in-Postgres statistics scope, exact-search latency at 100k–1M, quantisation, the small-vs-large embedder anomaly, operational controls (backup/PITR/encryption).

Method note: evidence comes from (a) engine docs and changelogs, (b) **source code read from shallow git clones** taken 2026-10-23 (commit hashes listed per finding), (c) papers and independent or vendor benchmarks (vendor-authored ones are labelled **[VENDOR]**), and (d) **sandbox measurements I ran** (labelled **[SANDBOX]**). The sandbox has 2 vCPUs (AVX-512F/BW/DQ/VL/VNNI), 7 GB RAM, PostgreSQL 16.15, and no GPU. pgvector could not be compiled there because the server headers were missing and installing them was blocked. So no pgvector-in-Postgres timings were measured; Postgres RLS tests used GIN/btree only.

Repos inspected (HEAD at clone time):
- pgvector `049d604fda` (2026-10-22; control `default_version = 0.8.7`)
- paradedb `c3e82fe473` (2026-10-22; workspace version 0.26.0, changelog up to 0.26.3), plus its tantivy fork `101d03ad26` (the rev pinned in paradedb Cargo.toml)
- timescale/pg_textsearch `4efe524846` (2026-10-16; `1.6.0-dev`, latest release v1.5.0)
- tensorchord/VectorChord-bm25 `14fc2a332b` (2026-04-28)
- tensorchord/VectorChord `0768657e57` (2026-04-23)
- timescale/pgvectorscale `3ae6fccff8` (2026-10-14; `0.9.2-dev`)

Web search budget ran out partway through. Some gaps below are search gaps, not "no evidence exists".

Ledger conventions (brain research protocol):
- **[SANDBOX]** and **source-code** findings are OBSERVED.
- Statements under "Inferences" are INFERRED.
- Strength tags: independent / [VENDOR] / single study / secondary (blog).
- Numbers from different benchmarks are never directly comparable. Each carries its own conditions.
- Bounded negative searches: I searched engine docs, the GitHub repos listed above, arXiv, and the vendor blogs cited. I did **not** search VectorDBBench result pages, LanceDB/Weaviate docs, or cuVS benchmark pages (search budget exhausted).

---

## Q1. Engine choice and filtered vector search (pgvector 0.8.x, VectorChord, pgvectorscale, ParadeDB, Qdrant, LanceDB, Weaviate, Milvus)

### Takeaway
No 2025–26 independent benchmark compares all the candidate engines under restrictive filters. The best independent study (UC Merced, Feb 2026) tested pgvector 0.8.1, Milvus and FAISS only. It found that pgvector's planner often picks an approximate index plan when an exact plan would give perfect recall at similar latency. That supports the proposed design of **exact (flat) search inside a tenant/ACL-restricted candidate set**, which removes filtered-ANN recall loss at 10k–1M scale. Qdrant has the most mature filtered-ANN machinery (payload-aware HNSW edges, a cardinality-based planner, ACORN since 1.16, per-tenant IDF since 1.19), so it remains a credible fallback. Separately, **pgvector ≥0.8.2 is no longer the right floor**: 0.8.3–0.8.7 fixed HNSW-vacuum index corruption and an IVFFlat-build buffer overflow. Pin **0.8.7** (2026-10-01).

### Cited Findings

**pgvector versions and security floor**
- CVE-2026-3172: buffer overflow in **parallel HNSW index build**. Affects pgvector 0.6.0–0.8.1, fixed in 0.8.2 (2026-02-25). CVSS 3.1 = 8.1 (AV:N/AC:L/PR:L). An authenticated user issuing crafted queries during a concurrent parallel build can leak data from other relations or crash the server. "Updating the underlying EDB product version alone may not apply the fix to existing databases": you must run `ALTER EXTENSION vector UPDATE` in each database. — [EDB CVE-2026-3172 assessment](https://www.enterprisedb.com/docs/security/assessments/cve-2026-3172); also tracked at [Debian](https://security-tracker.debian.org/tracker/CVE-2026-3172), [Red Hat](https://access.redhat.com/security/cve/CVE-2026-3172), [Ubuntu](https://ubuntu.com/security/CVE-2026-3172)
- pgvector CHANGELOG (repo HEAD 049d604fda), releases after 0.8.2:
  - 0.8.3 (2026-06-17): "Fixed possible index corruption with HNSW vacuuming"
  - 0.8.4 (2026-06-30): "Fixed `hnsw graph not repaired` error with HNSW vacuuming", plus a fix for inserts during HNSW vacuuming
  - 0.8.6 (2026-07-29): IVFFlat build overflow on 32-bit, and memory use for IVFFlat scans in nested loops
  - 0.8.7 (2026-10-01): "Fixed buffer overflow with IVFFlat index build" (issue #1036)
  - 0.9.0 (unreleased) drops PG13/14.
  - Source: [pgvector CHANGELOG.md](https://raw.githubusercontent.com/pgvector/pgvector/master/CHANGELOG.md)
- pgvector compiles with `-march=native` by default (`OPTFLAGS = -march=native` in the Makefile). Distro or portable builds use `make OPTFLAGS=""`, which affects SIMD distance speed. pgvector has explicit AVX-512 VPOPCNTDQ paths for bit (Hamming/Jaccard) distances in `src/bitutils.c`. — [pgvector README "Installation Notes"](https://raw.githubusercontent.com/pgvector/pgvector/master/README.md); source `src/bitutils.c` @049d604fda

**pgvector filtering semantics (docs)**
- "With approximate indexes, filtering is applied *after* the index is scanned. If a condition matches 10% of rows, with HNSW and the default `hnsw.ef_search` of 40, only 4 rows will match on average." Iterative scans (0.8.0+) continue until enough rows are found or `hnsw.max_scan_tuples` (default 20,000) or `ivfflat.max_probes` is reached. `strict_order` keeps exact distance order. `relaxed_order` "provides better recall" but can return slightly out-of-order rows; a materialized CTE restores strict order. `hnsw.scan_mem_multiplier` should be raised if raising `max_scan_tuples` doesn't help. For exact search without an index, raise `max_parallel_workers_per_gather`. — [pgvector README](https://raw.githubusercontent.com/pgvector/pgvector/master/README.md)
- Only a few distinct filter values? pgvector recommends **partial indexes**. — same source

**Independent academic evidence**
- **UC Merced, Feb 2026** (Amanbayev, Tsan, Dang, Rusu; arXiv 2602.11443).
  - Setup: Milvus 2.6.6, FAISS 1.12.0, **pgvector 0.8.1 on PG16**. New MoReVec dataset (768-d gte-base embeddings; up to 2.6M reviews and 551k movies). Global selectivity from 0.03% to 50%. Single-threaded, in-memory.
  - Findings:
    1. The pgvector optimizer "often picks approximate index scans over exact plans, even when a sequential scan or attribute-index plan would give perfect recall at similar latency".
    2. Under post-filtering, recall "drops sharply as k grows, since the candidate pool is bounded by efSearch". Recall "can jump to 1.0 when the optimizer switches to a sequential scan".
    3. Milvus stays stable through a brute-force fallback that triggers when more than 93% of rows are filtered out (1–5 ms per segment, 100% recall).
    4. The paper **did not evaluate pgvector's iterative scan**.
  - Recommendations: fall back to exact search when candidates run out; scale efSearch with k; index metadata columns; verify with EXPLAIN ANALYZE; force sequential-scan or attribute-index plans for very selective filters; IVFFlat for selectivity ≲5%, HNSW for ≳20%.
  - Source: [arXiv 2602.11443](https://arxiv.org/pdf/2602.11443)
- **Fudan, PVLDB, Sep 2025** (arXiv 2509.07789), unified filtered-ANN benchmark (ACORN-γ/ACORN-1, UNG, Filtered/Stitched-DiskANN, NHQ, CAPS, post-filter HNSW/IVF-PQ, pre-filter brute force).
  - "Post-filtering algorithms tend to lose throughput more rapidly at low selectivity."
  - Pre-filter brute force "maintain[s] a relatively high QPS" when filtering leaves few candidates.
  - ACORN-γ "often behaves like brute force at low selectivity".
  - For equality/containment filters (≈ tenant/ACL labels), UNG is the default pick; under very low selectivity, filter-then-search (UNG, ACORN-1, pre-filter brute force) is preferred.
  - Source: [arXiv 2509.07789](https://arxiv.org/pdf/2509.07789)
- **ETH Zurich, v3 Apr 2026** (arXiv 2507.21989), FANNS methods on 4096-d stella_en_400M_v5 arXiv embeddings (2.7M).
  - At 2.7M, FDANN-stitched, CAPS and UNG "fail to exceed 25% recall" (possibly a tuning issue).
  - "Embedding characteristics vary significantly across models, and most FANNS performance depends on them."
  - Specialized methods beat versatile ones by up to 10×.
  - Lowest selectivity tested was 0.2, so this paper says nothing about tenant-scale (≤1%) filters.
  - Source: [arXiv 2507.21989](https://arxiv.org/pdf/2507.21989)

**Vendor benchmarks**
- **[VENDOR, AWS] pgvector 0.8.0 vs 0.7.4 on Aurora** (2025-05-28; 10M synthetic products, 384-d, db.r8g.4xlarge).
  - Category filter (~10% selectivity), top-10: 0.7.4 recall was 10% at ef_search=40 and **0% at ef_search=200**. 0.8.0 with ef_search=200 + relaxed_order reached 100% recall, 85.7 ms.
  - Category + title filter (~2%), top-100: 0.7.4 recall 1% → 0.8.0 100% at 70.7 ms.
  - The post mixes "p99" and "average" labels for latency.
  - Source: [AWS Database Blog](https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/)
- **[VENDOR, Tiger Data/Timescale] pgvector+pgvectorscale vs Qdrant** (2025-04-29; 50M Cohere 768-d; r6id.4xlarge; Qdrant 1.13.4; pgvector 0.6.1 + pgvectorscale 0.7.0).
  - At 99% recall: Postgres p50 31.07 ms, p99 74.60 ms, 471.57 QPS. Qdrant p50 30.75 ms, p99 38.71 ms, 41.47 QPS.
  - Index build: Postgres ~11.1 h, Qdrant ~3.3 h.
  - **No filtered queries were tested.** The authors say they are "biased towards Postgres" and "struggled to find good Qdrant HNSW parameters".
  - Source: [Tiger Data blog](https://www.tigerdata.com/blog/pgvector-vs-qdrant)
- **[VENDOR, Qdrant] ACORN** (benchmarked on Qdrant 1.18.2, 1M deep-image-96, hnsw_ef=64).
  - Single keyword, 20% match: plain graph 62.9% recall → ACORN 98.9% at 4.4 ms. Filterable HNSW 94.8% at 1.2 ms.
  - Single keyword, 1% match: ACORN 67.7% vs filterable HNSW 99.8%.
  - Two keywords, 4% intersection: ACORN 95.2% at 7.7 ms vs filterable HNSW 63.7%.
  - Default planner, ACORN off → on: 4% intersection went 39.7% → 100% (7.3 ms).
  - Payload-aware extra edges raise 1M-point build time from 116 s to 507–652 s (4.4–5.6×). Edges are built **per field, not per field combination**, so AND filters across two fields may be poorly connected.
  - Source: [Qdrant ACORN article](https://qdrant.tech/articles/filtered-vector-search-acorn/index.md)
- **[VENDOR, Qdrant] 1.16** (2025-11-19). ACORN on 5M×96-d with ~4% passing the filter: ef=64 + ACORN gave 97.2% at 13.86 ms vs 53.34% at 1.25 ms; ef=512 without ACORN gave only 71.13%. Also added: tiered multitenancy, `text_any` full-text condition, and conditional updates. — [Qdrant 1.16 release](https://qdrant.tech/blog/qdrant-1.16.x/index.md)
- **[VENDOR, VectorChord]** `vchordrq.prefilter` (since v0.4.0, default off; not supported by `vchordg`) evaluates the WHERE filter before distance computation. Recommended only for strict **and** cheap filters. Reported QPS gain on LAION-5m: ~200% at 1% selectivity, ~5% at 10%. No recall numbers given. — [VectorChord prefilter docs](https://docs.vectorchord.ai/vectorchord/usage/prefilter.html)
- **pgvectorscale** (repo 3ae6fccff8, 0.9.2-dev):
  - Label filtering uses Filtered-DiskANN, with labels as `smallint[]` (range −32768..32767) in the index (`CREATE INDEX ... USING diskann (embedding vector_cosine_ops, labels)`) and queried with `&&`.
  - Arbitrary WHERE clauses fall back to **post-filtering**.
  - Implication: smallint labels can't directly encode >32k tenants/ACL groups.
  - Source: [pgvectorscale README](https://raw.githubusercontent.com/timescale/pgvectorscale/main/README.md)
- **ParadeDB vector support** (0.26.x docs in repo c3e82fe473): ParadeDB now has its own vector storage in the Tantivy index, switching from flat to IVF when a segment passes `paradedb.vector_clustering_threshold` (default 500 docs), with `paradedb.vector_cluster_max_probe` (default 0.02 of clusters per segment). `partition_by` (Beta) gives segment pruning by tenant ID. — `docs/reference/configuration.mdx`, `docs/reference/indexing/partition-by.mdx` in [paradedb repo](https://github.com/paradedb/paradedb)

**Qdrant multitenancy primitives** (docs)
- `is_tenant` keyword index (v1.11+) co-locates each tenant's points.
- `payload_m` with `m: 0` builds per-tenant HNSW graphs. Global queries then get slow, and `payload_m` must be set explicitly or it inherits `m=0`.
- Tiered multitenancy (v1.16+): promote a large tenant from the fallback shard to a dedicated shard at roughly 20k points; keep under ~1,000 dedicated shards.
- Isolation by payload partition **depends on every query including the tenant filter**. The docs don't describe server-side filter enforcement.
- Source: [Qdrant multitenancy docs](https://qdrant.tech/documentation/manage-data/multitenancy/)
- JWT RBAC (v1.9+) scopes tokens per **collection** (`r`/`rw`) plus a `value_exists` claim. It **does not inject payload filters**, so row-level isolation inside a shared collection stays app-enforced. — [Qdrant security docs](https://qdrant.tech/documentation/guides/security/index.md)
- [Third-party, not verified] An Aug 2026 blog says an exact filtered search (`exact: true`) still has to identify eligible points first, and can run long on broad filters. It also says payload indexes added after ingestion don't add filter-aware HNSW edges until the graph is rebuilt. — [OneUptime blog, 2026-08-28](https://oneuptime.com/blog/post/2026-08-28-qdrant-filtered-query-timeouts-payload-indexes-exact-hnsw/markdown)

### Inferences
- With per-tenant/ACL candidate sets of ≤100k rows, exact scoring of the candidate set sidesteps filtered-ANN recall loss entirely. The UC Merced and Fudan papers both point to pre-filter + brute force as the robust choice at low selectivity. In Postgres this means **forcing the plan**: btree/partition prune on tenant/ACL → exact `ORDER BY embedding <=> q LIMIT k` over the surviving rows, with no HNSW index (or `SET enable_indexscan=off` locally). A cost-based planner won't reliably make that choice.
- If an HNSW index is added later, as pgvector ≥0.8, set `hnsw.iterative_scan = relaxed_order` + materialized CTE, raise `hnsw.max_scan_tuples` above 20,000 for small tenants, and **measure the "returns-k rate"** (fraction of queries returning a full k). Recall loss under post-filtering is silent.
- Qdrant has the stronger filtered-ANN engine (filterable HNSW + ACORN + planner), but isolation is app-enforced. That conflicts with the "RLS forced" principle unless a gateway enforces filters.
- Pgvector version policy: pin ≥0.8.7 and disable parallel HNSW builds for untrusted-role databases.
- **Devil's advocate on "Postgres-centric".**
  - Steelman for Qdrant-primary: better filtered-ANN machinery; a query-time per-tenant IDF corpus (1.19), which Postgres BM25 extensions lack; faster index builds ([VENDOR] 3.3 h vs 11.1 h at 50M); tiered multitenancy.
  - Counter: at 10k–1M with exact search, Qdrant's ANN advantages don't apply. Postgres gives transactional consistency between facts, ACLs and vectors, plus WAL PITR and forced RLS. Qdrant isolation is app-enforced, its snapshots aren't PITR, and its upgrade window is one minor version.
  - **Verdict: keep Postgres-centric, with changes.** Pin pgvector ≥0.8.7. Always send an explicit tenant predicate alongside RLS. Partition by tenant for BM25 statistics. Keep a GPU-resident exact-search mirror as the 1M-scale escape hatch, rather than Qdrant as the first fallback.
  - **Decisive test / kill criterion:** on the GPU server at 1M vectors (1024-d) with tenant partitions, if p95 end-to-end first-stage latency (BM25 + exact dense over the tenant-pruned partition, as the app role under RLS) exceeds 150 ms, or the returns-k rate drops below 100% for any tenant, move dense search to the GPU mirror (or Qdrant) and keep Postgres as the source of truth.

### Gaps
- No 2025–26 independent benchmark covering VectorChord, ParadeDB vectors, LanceDB or Weaviate under restrictive (≤1%) filters was found; search budget ran out before LanceDB/Weaviate-specific queries. VectorDBBench's own filtered results pages could not be retrieved.
- The UC Merced paper did not test pgvector iterative scans, so no independent numbers on iterative scan recall versus selectivity at tenant-scale selectivity were found.
- The Hashnode article "Filtered vector search in pgvector can silently lose recall" (Varun Sharma) reportedly has measurements, but they could not be fetched.

---

## Q2. Row-level security overhead, planner pitfalls, multi-tenant patterns

### Takeaway
RLS overhead is small when the policy column is btree-indexed and the policy uses a per-statement constant (`current_setting`). It becomes an order-of-magnitude penalty when the query predicate is **not leakproof**: full-text `@@`, `LIKE`, `@>`, and every pgvector distance operator. Postgres must then evaluate the policy first and can't combine the user's index with the tenant index. **[SANDBOX] measured 17 ms with RLS vs 1.5–2 ms with an explicit tenant predicate (≈8–12×) for a rare-term FTS query on 1M rows.** Adding an explicit `tenant_id = $1` to every query alongside forced RLS restores good plans while keeping RLS as the safety net. Declarative LIST partitioning by tenant gets runtime partition pruning even from an RLS-only `current_setting()` predicate (sandbox: 19 of 20 partitions pruned).

### Cited Findings
- Postgres docs:
  - Policy expressions are "evaluated for each row prior to any conditions or functions coming from the user's query. (The only exceptions to this rule are `leakproof` functions...)".
  - Superusers and `BYPASSRLS` roles always bypass RLS. Table owners bypass it unless `FORCE ROW LEVEL SECURITY` is set.
  - "Referential integrity checks... always bypass row security", so watch for "covert channel" leaks through unique/FK checks.
  - Source: [PostgreSQL docs, Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- Stephen Frost (RLS co-author), 2019: functions not marked leakproof "aren't going to be able to be pushed down" below RLS checks, so GIN/GiST indexes may go unused. The leakproof check can't be disabled; `ALTER FUNCTION ... LEAKPROOF` (superuser) is the only override and is safe only if the function can't leak through errors. — [pgsql-general, 2019-08-13](https://www.postgresql.org/message-id/20190813213930.GO16436%40tamriel.snowman.net)
- Bytebase (2025-09-05, qualitative): non-leakproof policy functions can force full scans; subqueries/joins inside policies run per row; index the policy columns; test as a non-owner role (owners bypass); `security_invoker = true` views on PG15+; per-transaction `SET` with poolers. — [Bytebase RLS footguns](https://www.bytebase.com/blog/postgres-row-level-security-footguns.md)
- Supabase docs: index the policy filter columns; wrap per-statement functions as `(select auth.uid())` so they're cached as an InitPlan; scope policies `TO` specific roles; use `security definer` functions to avoid RLS on joined tables. Their published diagnostic: 171 ms seq-scan over 100k rows with RLS and no usable index. — [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security); [Supabase RLS performance](https://supabase.com/docs/guides/database/postgres/row-level-security-performance)
- **[SANDBOX] leakproof status in PG 16.15** (`pg_proc.proleakproof`): `int4eq`, `int8eq`, `texteq`, `uuid_eq` = **true**. `ts_match_vq` (tsvector @@ tsquery), `textlike`, `arraycontains` (@>), `jsonb_contains` = **false**. The pgvector 0.8.7 SQL install script contains **zero** `LEAKPROOF` declarations (grep of `sql/vector.sql` @049d604fda), so no vector distance operator is leakproof.
- **[SANDBOX] RLS plan/timing test.** PG 16.15, 1,000,000 rows, 100 tenants × 10k rows, btree on `tenant_id`, GIN on `tsvector`, policy `tenant_id = current_setting('app.tenant')::int`, FORCE RLS, non-owner role, `max_parallel_workers_per_gather=0`, warm cache.
  - Rare term (1 match), superuser, no tenant filter: GIN bitmap only, **0.24 ms**.
  - Same query under RLS (role app): plan = btree bitmap on tenant (10k rows) → heap → `Filter: tsv @@ ...` (Rows Removed 9,999). **GIN not used.** Times 17.1, 24.8, 18.0 ms.
  - Superuser + explicit `tenant_id = 8 AND tsv @@ ...`: BitmapAnd of both indexes, **1.45–2.06 ms**.
  - Wrapping the policy as `(select current_setting(...))` (InitPlan) **did not** restore GIN use (16.3 ms).
  - Common terms (two-term AND matching 0 of 10k tenant rows): RLS-only 102.5 ms; RLS + explicit tenant predicate 20.5 ms (Postgres adds a `One-Time Filter` comparing the setting to the literal); superuser explicit 40.7 ms (it chose a BitmapAnd with a 50k-row GIN scan).
  - Ranked FTS (`ORDER BY ts_rank ... LIMIT 10`): RLS 25.5 ms vs superuser explicit 18.1 ms.
- **[SANDBOX] partitioning + RLS.** 400k rows LIST-partitioned into 20 tenant partitions, same `current_setting` policy, no explicit tenant predicate. EXPLAIN shows `Subplans Removed: 19`: runtime pruning works off the RLS predicate (8.5 ms for a LIKE filter over the one 20k-row partition).
- ParadeDB pg_search source (c3e82fe473) handles RLS deliberately. RLS SubPlan quals are "evaluated via plan.qual" after the Tantivy scan. When deferred RLS quals exist, the base scan declines LIMIT pushdown ("WHERE clause contains predicates that must be evaluated after the scan, for example to respect row-level security policies"). Non-leakproof heap filters are ordered after RLS quals by `security_level`. Changelog 0.21.15: "Fixed RLS policies that get planned as SubPlans". 0.26.0 fixed deadlocks when RLS policies re-enter tokenizer lookups. — `pg_search/src/postgres/customscan/basescan/mod.rs`, `qual_inspect.rs`; `docs/project/changelog/0.21.15.mdx`, `0.26.0.mdx` in [paradedb repo](https://github.com/paradedb/paradedb)
- pg_textsearch has a superuser GUC `pg_textsearch.allow_rls` (default on). Setting it off rejects BM25 indexes on RLS-protected tables. — [pg_textsearch README](https://raw.githubusercontent.com/timescale/pg_textsearch/main/README.md)
- pg_trickle blog (undated, no measurements): the planner may not see RLS conditions when choosing partial indexes, so add an explicit `WHERE tenant_id = 42` to hit a per-tenant partial index. Small tenants in a shared HNSW table can exhaust `hnsw.max_scan_tuples` before returning k results. — [pg_trickle multi-tenant vector search with RLS](https://pgxn.org/dist/pg_trickle/0.36.0/blog/multi-tenant-vector-search-rls.html)

### Inferences
- Pattern to implement:
  1. FORCE RLS on all tenant tables; the app role has no BYPASSRLS and doesn't own the tables.
  2. The app **also** sends `tenant_id = $1` (and an ACL predicate) explicitly in every query, so the planner can use per-tenant partial indexes, partition pruning and BitmapAnd.
  3. RLS acts as the backstop, not the access path.
  4. CI asserts via EXPLAIN that hot queries use the expected indexes when run as the app role.
- Partial indexes, including BM25 partial indexes, are only chosen when the query itself carries the matching predicate. Inferred from pg_textsearch's "Partial indexes require explicit index naming" and the pg_trickle note; not independently measured.
- Do not mark pgvector or FTS operators LEAKPROOF to "fix" plans. Error messages can leak values (Frost).
- LIST/HASH partitioning by tenant (or tenant bucket) gives both runtime pruning under RLS and per-partition BM25 statistics (Q3). The cost is planner overhead with many partitions; not measured here.

### Gaps
- No published measurement of RLS overhead specifically on pgvector HNSW/flat queries or ParadeDB BM25 queries was found (search budget exhausted). The sandbox could not build pgvector.
- Planning-time overhead at thousands of partitions (schema-per-tenant vs partition-per-tenant vs shared table) was not measured or found.

---

## Q3. BM25 in Postgres: statistics scope (IDF/avgdl), RLS/WHERE awareness, getting per-partition statistics

### Takeaway
**None of the three Postgres BM25 engines computes IDF over the RLS-visible or WHERE-filtered set.** All use physical **per-index** statistics: every indexed row, including rows hidden by RLS and, for pg_textsearch and Tantivy, deleted-but-not-yet-compacted rows. The tested IDF leak is therefore expected behaviour, and pg_textsearch documents it as a known limitation. **The supported way to get per-tenant statistics is one index per tenant scope**: a partitioned table (each partition gets its own BM25 index and statistics, documented by pg_textsearch) or partial indexes `WHERE tenant_id = X` (supported by pg_textsearch, vchord_bm25 and ParadeDB, queried by explicit index name). ParadeDB's `partition_by` only prunes segments; statistics stay index-wide. Qdrant ≥1.19 is the only engine reviewed with a **query-time** statistics corpus filter (`params.idf.corpus`).

### Cited Findings

**pg_textsearch (Timescale; v1.5.0 released, 1.6.0-dev at 4efe524846; PG17/18 only)**
- "BM25 corpus statistics include all indexed rows, including rows hidden by RLS. A user who already knows a term can infer frequency information affected by inaccessible rows, though the index does not reveal unknown terms. This is analogous to Elastic's security limitation." — [pg_textsearch README, Limitations: Row-Level Security](https://raw.githubusercontent.com/timescale/pg_textsearch/main/README.md)
- "BM25 statistics are local to each partition. Scores are comparable within a partition but may use different IDF scales across partitions. Query individual partitions when cross-row score comparability matters." — same README, "Partitioned Tables"
- Partial indexes are supported (`CREATE INDEX ... USING bm25(content) WITH (text_config='english') WHERE category_id = 1`) but "require explicit index naming via `to_bm25query()`"; the implicit `<@>` syntax skips them. — same README
- Standalone scoring (no index scan, e.g. after a btree pre-filter) "still uses corpus statistics from the selected BM25 index". Boolean filter + ranking is "not yet optimized as a single index scan": PG evaluates the filter, scores the matching rows standalone, then sorts. — same README
- ARCHITECTURE.md: corpus totals and term frequencies are captured once per statement per physical index. "These are physical index statistics, not MVCC-filtered corpus statistics." — [pg_textsearch ARCHITECTURE.md](https://raw.githubusercontent.com/timescale/pg_textsearch/main/ARCHITECTURE.md)
- Source: `metap->total_docs += docs_delta` in `src/memtable/log.c`; per-query IDF cache in `src/types/query.c`; `scoring/snapshot.c` sums `total_docs` across sources @4efe524846.
- Version history: v1.1.0 added partial and expression indexes plus concurrent writes; v1.2.0 physical replication; v1.4.0 faster filtered top-k; v1.5.0 background compaction plus Boolean and phrase queries. — README version table

**ParadeDB pg_search (Tantivy; repo 0.26.x at c3e82fe473; tantivy fork 101d03ad26)**
- Scoring always uses `EnableScoring::enabled_from_searcher(searcher)` (`pg_search/src/index/reader/index.rs`, `fn enable_scoring`). The Searcher is the whole index.
- Tantivy's `impl Bm25StatisticsProvider for Searcher` sums `total_num_tokens` and `doc_freq` over **all segment readers**. `total_num_docs` sums `segment_reader.max_doc()`, which **counts deleted docs** until merge. — `src/query/bm25.rs` lines 41–63 in [paradedb/tantivy fork](https://github.com/paradedb/tantivy)
- So statistics are index-wide: not per segment, not filtered by WHERE or RLS. Segment pruning (`paradedb.enable_segment_pruning`, `partition_by` Beta) skips segments for matching but doesn't change the Searcher used for statistics. Inferred from code paths: all `enable_scoring` callers pass `self.searcher`. Not runtime-verified.
- ParadeDB supports partial indexes "using the same syntax as Postgres" (`docs/reference/indexing/indexing-partial.mdx`) and partitioned tables (`docs/concepts/limitations.mdx`). A partitioned parent gets one Tantivy index per partition, so statistics are per partition. Inferred, not explicitly documented.
- ParadeDB is a covering index: one per table, columns fixed at creation; adding columns needs REINDEX. — `docs/concepts/limitations.mdx`

**vchord_bm25 (TensorChord; repo 14fc2a332b, last commit 2026-04-28)**
- README: "bm25 score... depends on a global document frequency". Create the index "so that we can collect the global document frequency". Queries name the index explicitly: `to_bm25query('index_name', ...)`. — [VectorChord-bm25 README](https://raw.githubusercontent.com/tensorchord/VectorChord-bm25/main/README.md)
- Source: `search.rs` and `evaluate.rs` read `number_of_documents` and `sum_of_document_lengths` from the index's jump tuple. `idf = ln((N+1)/(n_t+0.5))` in `crates/bm25/src/bm25.rs:285`. Statistics are per index; filters are applied by PostgreSQL afterwards.
- Partial indexes are supported and exercised in tests: `CREATE INDEX ... USING bm25 (...) WHERE id % 2 = 0`, queried with `to_bm25query(..., 'documents_passage_bm25_0')`. Using the full index's name with a filtered WHERE errors ("expected index"). — `tests/sqllogictest/bm25query.slt`
- Limitation: returns at most `bm25_catalog.bm25_limit` docs (default 100; −1 = brute force) to PostgreSQL. Stricter filters need a larger limit, otherwise results are silently truncated. — README "Limitation"
- Repo activity: last commit 2026-04-28 at clone time vs Oct 2026 for paradedb and pg_textsearch. Maintenance cadence risk (inference).

**Native Postgres FTS**
- `ts_rank`/`ts_rank_cd` "do not use any global information". No IDF, so no cross-tenant statistics leak, but weaker ranking. "Ranking can be expensive since it requires consulting the tsvector of each matching document." — [PostgreSQL docs 12.3 Controlling Text Search](https://www.postgresql.org/docs/current/textsearch-controls.html)

**Qdrant (comparison)**
- BM25 statistics (doc count, per-term doc counts, avg length) are computed "over all points in the shard being queried". In multi-shard collections "each shard uses its own statistics". Deleted or updated docs linger in statistics until segments are rebuilt. — [Qdrant full-text search docs](https://qdrant.tech/documentation/search/text-search/full-text-search/index.md)
- **v1.19.0 (2026-08-05): per-tenant scoring statistics.** `params.idf.corpus` takes a payload filter (e.g. on `group_id`) defining the statistics population, independent of the retrieval filter; default `global`. If the corpus matches nothing, it falls back to constant term weights (and disables BM25 length normalisation). With user-defined sharding, the corpus filter doesn't reach across shards and "can silently compute partial statistics". — [Qdrant multitenancy docs](https://qdrant.tech/documentation/manage-data/multitenancy/); [Qdrant 1.19 release](https://qdrant.tech/blog/qdrant-1.19.x/index.md)
- Elastic documents the same class of leak (statistics include docs the user can't see). — referenced by [pg_textsearch README](https://raw.githubusercontent.com/timescale/pg_textsearch/main/README.md) → [Elastic security limitations](https://www.elastic.co/docs/deploy-manage/security/limitations)

### Inferences
- **Per-partition statistics recipe (Postgres):**
  - `PARTITION BY LIST (tenant_id)` for large tenants, plus a `HASH (tenant_id)` or default partition for the long tail.
  - Create the BM25 index on the parent so each partition gets its own index and statistics.
  - Queries must hit a single partition (explicit `tenant_id = $1`) so scores are comparable.
  - Caveat: long-tail tenants sharing a hash or default partition still share statistics with each other. Exact per-tenant isolation needs one partition per tenant, or partial indexes per tenant (fine for tens to hundreds of tenants; impractical for thousands).
- **ACL-level isolation within a tenant** (documents hidden from some users of the same tenant) can't be achieved by any of these engines: statistics are per index, not per ACL. Options:
  1. Accept intra-tenant leakage, a documented, Elastic-equivalent risk.
  2. Compute BM25 at query time over the ACL-visible candidate set. At ≤100k rows per tenant this is feasible with a sparse tf matrix, or Postgres FTS + application-side IDF from a per-ACL-group `df` table.
  3. Use `ts_rank` (no IDF) for ACL-restricted subsets.
  4. Qdrant `idf.corpus` with an ACL filter, which is the only native option.
- **Verdict on "per-partition lexical statistics required": keep.** Every Postgres BM25 engine reviewed computes statistics per physical index (OBSERVED in source and docs), so partition-per-tenant or partial-index-per-tenant is the only native route.
  - **Decisive test:** repeat the hidden-document IDF leak test against pg_textsearch on a LIST-partitioned table (one partition per tenant) and against a per-tenant partial index. Pass = a score for a known term is bit-identical before and after inserting N hidden docs into *another* tenant.
  - **Kill criterion:** any score change → the engine leaks across partitions → fall back to application-side BM25 over the candidate set.
- Deleted-document statistics drift (Tantivy `max_doc`, pg_textsearch physical stats, Qdrant segment stats) is another small leak channel: a deleted secret document still affects IDF until merge or compaction. Run compaction/merge after deletes of sensitive content.

### Gaps
- Not runtime-verified for ParadeDB: whether a partial ParadeDB index yields statistics limited to its predicate. Strongly implied, since a Tantivy index only contains the rows it indexed, but no doc states it.
- Not verified: whether pg_textsearch's statistics snapshot on a partitioned parent queried without pruning mixes per-partition IDFs (README says scores are not comparable across partitions).

---

## Q4. Exact (brute-force) vector search latency at 100k–1M (CPU AVX-512, GPU, Postgres seq scan)

### Takeaway
Exact search is **memory-bandwidth-bound**: latency ≈ (n × d × bytes per element) ÷ effective bandwidth. **[SANDBOX] On 2 vCPUs with AVX-512 (NumPy/OpenBLAS fp32), single-query top-150 took ~24 ms at 100k×768, ~32 ms at 100k×1024, ~115 ms at 100k×4096, ~131 ms at 1M×384 and ~247 ms at 1M×768 (~12–14 GB/s effective).** A real server with 16–64 cores and 8–12 memory channels should be roughly 5–20× faster, but that's an inference, not measured. A 1M×768 fp32 matrix is 3.07 GB and fits easily in GPU memory, where brute force is a single GEMM. FAISS documents GPU flat as 5–10× faster than CPU and best with batched queries. Inside Postgres, pgvector exact search is a sequential scan, parallelisable with `max_parallel_workers_per_gather`, and will be slower than a contiguous in-memory matrix because of tuple overhead. Sub-second at 1M on CPU is realistic; sub-50 ms at 1M×768 fp32 per query needs many cores, a GPU, or quantised first-pass + rescoring.

### Cited Findings
- **[SANDBOX]** NumPy 2.5.3 + OpenBLAS 0.3.34 (DYNAMIC_ARCH), 2 vCPUs (AVX-512F/BW/DQ/VL/VNNI), random fp32, single query = GEMV + argpartition top-150, best of 7 (median in brackets):

  | Vectors × dims | Best (median) | Data scanned | Effective bandwidth |
  |---|---|---|---|
  | 100k × 768 | 23.9 ms (29.8) | 0.31 GB | 12.9 GB/s |
  | 100k × 1024 | 31.8 ms (37.0) | 0.41 GB | — |
  | 100k × 4096 | 114.5 ms (141.7) | 1.64 GB | — |
  | 1M × 384 | 131 ms (146) | 1.54 GB | — |
  | 1M × 768 | 247 ms (258) | 3.07 GB | 12.4 GB/s |

  - Batch of 32 queries at 1M×768: 1,439 ms total = **45 ms/query** (GEMM amortises memory traffic).
  - fp16 matmul in NumPy: 3,837 ms (no native fp16 BLAS on CPU; use int8 or real fp16 kernels instead).
  - 1-bit binary (1M × 768 bits = 96 MB), NumPy popcount Hamming + top-1500: **65 ms** (NumPy-level, not SIMD-optimised; FAISS IndexBinaryFlat or USearch would be faster).
  - Threat to validity: the 2 vCPUs were **shared with other agents' concurrent processes** during the runs, so these are pessimistic upper bounds.
- FAISS GPU wiki: GPU is "5x - 10x faster than the corresponding CPU implementation". Performance is best with batched queries. Flat indexes "may be compute-bound rather than memory-bandwidth-bound". k and nprobe are limited to ≤2048 on GPU (matters for a top-150 rerank pool: fine). — [FAISS wiki: Faiss on the GPU](https://github.com/facebookresearch/faiss/wiki/Faiss-on-the-GPU)
- FAISS wiki, 2018 (old hardware): SIFT1M (1M×128) batch flat search took 9.1 s CPU vs 0.753 s on a Titan X GPU for the full query batch (batch size not given). — [FAISS wiki: Indexing 1M vectors](https://github.com/facebookresearch/faiss/wiki/Indexing-1M-vectors/d7df9b4bce370e54c15e96cd8a2fb2bf041025e7)
- Neon (2023): pgvector seq-scan exact search on 10k GIST vectors took ~36–39.5 ms (4 vCPU, 16 GB); "starts to become costly" at 50k+ (no numbers in text). — [Neon blog](https://neon.com/blog/optimizing-vector-search-performance-with-pgvector)
- pgvector: "To speed up queries without an index, increase `max_parallel_workers_per_gather`." Normalised vectors should use inner product "for best performance". — [pgvector README](https://raw.githubusercontent.com/pgvector/pgvector/master/README.md)
- [VENDOR, Qdrant] An exact filtered search in Qdrant must first identify eligible points, then brute-force score them. — [OneUptime 2026-08-28](https://oneuptime.com/blog/post/2026-08-28-qdrant-filtered-query-timeouts-payload-indexes-exact-hnsw/markdown) (third-party blog)
- UC Merced: Milvus brute-force fallback over filtered segments took 1–5 ms per typical segment with 100% recall. — [arXiv 2602.11443](https://arxiv.org/pdf/2602.11443)

### Inferences
- Budget math for the GPU server, **[inference from bandwidth]**:
  - 1M×1024 fp32 = 4.1 GB. At ~1–3 TB/s HBM, one GEMV pass is ~1.5–4 ms plus launch overhead.
  - 100k×1024 is 0.41 GB, sub-millisecond on GPU; ~3–8 ms on a 32-core DDR5 CPU at ~100–200 GB/s effective.
  - Brute force on GPU is effectively free at the target scale. On CPU, 1M×1024 exact search costs ~20–40 ms on a big server: acceptable at the planned rerank budget.
- Postgres exact search: flat `ORDER BY embedding <=> q LIMIT k` over a **tenant-pruned partition** of ≤100k rows is the sweet spot. A whole-table 1M scan in Postgres will likely be several hundred ms even with parallel workers. That's inferred from tuple overhead plus the sandbox bandwidth; not measured, because pgvector couldn't be built in the sandbox.
- For 1M-scale exact search outside Postgres, keep a GPU-resident (FAISS GpuIndexFlatIP or cuVS brute-force) mirror of the vectors keyed by row id. Apply tenant/ACL as an id-allowlist bitmap, then hydrate rows from Postgres. Decouples ANN speed from Postgres scan speed.

### Gaps
- No measured pgvector exact-scan numbers at 100k/1M (any dims) with parallel workers were found or produced; pgvector couldn't be compiled in the sandbox.
- No 2025–26 cuVS brute-force latency figures for single queries at 1M were retrieved (search budget exhausted). GPU numbers above are inference plus the old FAISS wiki.

---

## Q5. Quantisation (binary / int8 / Matryoshka) impact on recall for exact search; rescoring

### Takeaway
On real embeddings, int8 keeps ~97–100% of retrieval quality without rescoring and ~99% with rescoring. Binary keeps ~92.5% without rescoring and ~96% with rescoring for well-behaved models, but is **highly model-dependent**: e5-base-v2 retains only 74.8%. **[SANDBOX]** on synthetic Gaussian-mixture vectors, binary first-pass + fp32 rescoring of top-400 recovered only 41% recall@10, a reminder that the result depends on the embedding distribution. Validate quantisation on your own corpus and embedder. Treat binary only as a first pass over ≥4–10× oversampled candidates with fp32/fp16 rescoring.

### Cited Findings
- Hugging Face, embedding quantization, MTEB Retrieval NDCG@10 as % of fp32:
  - mxbai-embed-large-v1 (1024-d): int8 97%, binary 96.45% with rescoring (92.5% without).
  - Cohere-embed-english-v3.0: int8 100%, binary 94.6%.
  - all-MiniLM-L6-v2 (384-d): int8 90.79%, binary 93.79%.
  - e5-base-v2 (768-d): int8 94.68%, **binary 74.77%**, attributed to "dimension collapse".
  - nomic-embed-text-v1.5: binary 87.7%.
  - Rescoring setup: multiplier 4 (rescore 400 for top-100); multipliers 1–10 showed no further gain.
  - Speed: binary exact search (FAISS, 1024-d) 15–45× faster than fp32. int8 (USearch) 3–4.8× faster.
  - Caveat: quantization "doesn't universally work with all embedding models".
  - The Matryoshka + binary combination (1024→128, ~3% drop) is labelled an untested suspicion.
  - Source: [HF blog: Embedding Quantization](https://huggingface.co/blog/embedding-quantization)
- [VENDOR, Qdrant 1.16] Inline storage (1M LAION 512-d, 2-bit quantisation, low RAM): 86.92% accuracy at 211 QPS vs 53.32% at 20 QPS without inline storage. — [Qdrant 1.16](https://qdrant.tech/blog/qdrant-1.16.x/index.md)
- [VENDOR, Qdrant 1.19] TurboQuant `Turbo4` datatype stores 4-bit codes **without** full-precision originals: ~9× storage cut, but "Qdrant can't rescore candidates, so recall may suffer". — [Qdrant 1.19](https://qdrant.tech/blog/qdrant-1.19.x/index.md)
- [VENDOR, VectorChord] RaBitQ quantisation with "autonomous reranking". `rabitq8` claimed "<1% recall loss". `rabitq4` "for constrained situations that favor low storage over high precision". The docs say quantisation compromises precision "noticeably" and results may vary across versions and machines. — [VectorChord README](https://raw.githubusercontent.com/tensorchord/VectorChord/main/README.md); [VectorChord quantization types](https://docs.vectorchord.ai/vectorchord/usage/quantization-types.html)
- Qwen3-Embedding-0.6B supports MRL output dims 32–1024 (default 1024). — [HF model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- LIMIT paper (Google DeepMind, ICLR 2026): embedding dimension bounds the number of distinct top-k subsets representable. Free-embedding extrapolations put the critical corpus size at ~500k docs for 512-d, 1.7M for 768-d, 4M for 1024-d (cubic-fit extrapolation, not measured). Models truncated with MRL down to 32-d lose performance as dimension falls. BM25 "do[es] very well" on LIMIT thanks to its higher (sparse) dimensionality. — [arXiv 2508.21038](https://arxiv.org/html/2508.21038v2)
- **[SANDBOX]** Synthetic clustered data (200k × 768, 2,000 Gaussian centroids + noise, L2-normalised; 200 noisy queries; ground truth = fp32 exact top-10):
  - int8 (per-dimension symmetric scale), no rescoring: R@10 = 0.80
  - sign-binary, no rescoring: 0.061
  - binary + fp32 rescore of top-40: 0.13; top-100: 0.225; top-400: 0.41
  - Synthetic isotropic noise is a worst case for sign-binarisation and **not representative of real embeddings**. Reported as a caution, not as an estimate.

### Inferences
- At 10k–1M with a GPU, quantisation isn't needed for latency: fp16 1M×1024 is 2 GB. Its only role is RAM/disk savings or CPU-only deployments. Use int8 or fp16 for the exact first stage. If binary is used, oversample ≥10× (k=150 → 1,500 candidates) and rescore in fp32. Run a per-embedder recall check, since e5-base-style collapse is real.
- Avoid storage formats that discard originals (Qdrant Turbo4, VectorChord `rerank_in_table` trades latency instead) for the >90% success target.
- MRL truncation compounds with LIMIT's dimension bound. Don't truncate below ~768 for 1M-scale corpora without measuring.

### Gaps
- No 2025–26 independent study of Matryoshka truncation + binary/int8 with rescoring on retrieval benchmarks was retrieved (search budget exhausted).
- Didn't test quantisation on real bge-small/Qwen3 embeddings of the project corpus. Recommended as a builder test.

---

## Q6. Small vs large embedders: when small beats large; synthetic benchmark validity

### Takeaway
The bge-small > Qwen3-Embedding-0.6B result on a templated synthetic corpus is **plausible and not, by itself, evidence that bge-small is better on real data**. There are three documented mechanisms:
1. Public leaderboard rank orders reverse on custom data (Chroma: jina-v3 > text-embedding-3-large on MTEB, reversed on real W&B queries).
2. Naively generated synthetic queries are "too easy", with high lexical overlap, and inflate scores (Chroma).
3. Qwen3-Embedding *requires* an instruction prefix on queries (1–5% gain per the model card), plus last-token pooling with left padding. Missing any of these handicaps it.

Templated corpora also have tiny effective vocabularies and near-duplicate documents, which puts a premium on lexical/identifier discrimination where BM25 and small BERT-style models are competitive. LIMIT shows single-vector embedders of every size are capacity-bounded on combinatorial queries where BM25 excels. **[SANDBOX] on a templated IT-ticket corpus (n=150 per query type), bge-small beat Qwen3-0.6B on paraphrase R@1 (0.887 vs 0.800, overlapping CIs), Qwen3 beat bge-small on identifier queries (0.24 vs 0.13), and BM25 dominated identifiers (1.00) while failing paraphrases (0.07).** The ranking flips with query type. A single aggregate score on a templated corpus can't pick an embedder, and the hybrid first stage is what makes the system robust.

### Cited Findings
- **Chroma Generative Benchmarking** (Apr 7, 2025; Hong, Troynikov, Huber, McGuire):
  - On WandBot production queries (2,003 unique; 693 manually labelled), text-embedding-3-large beat jina-embeddings-v3 (Recall@10 0.552 vs 0.511), the reverse of their MTEB English order.
  - "Naively generated queries on WandBot scored higher than ground truth", which "could overstate real performance".
  - On Wikipedia-en, 11.91% of naive synthetic queries had >0.9 cosine similarity to the public ground-truth query (memorisation).
  - Context + example-steered generation brought query–document similarity distributions closer (KL 0.159 vs 0.207 naive), but Recall@10 on synthetic queries stayed above ground truth for all four models (e.g. text-embedding-3-small 0.530 vs 0.439).
  - The report doesn't compute Spearman correlations.
  - Source: [Chroma research: Generative Benchmarking](https://www.trychroma.com/research/generative-benchmarking)
- Nomic (2024, vendor): Nomic Embed ranks ~50th on static MTEB but similar to top-10 models ~70× bigger on MTEB Arena. Many newer models train on BEIR/MTEB training sets or benchmark-like synthetic data, and "your application performance may not strongly correlate" with leaderboard results if your documents differ. — [Nomic blog](https://home.nomic.ai/blog/posts/evaluating-embedding-models)
- Qwen3-Embedding-0.6B card:
  - "Each query must come with a one-sentence instruction" in the format `Instruct: {task}\nQuery:{query}`. Instructions "typically yield an improvement of 1% to 5%".
  - Documents take no instruction.
  - Last-token pooling with **left padding**; transformers ≥4.51.0 (older versions error on `qwen3`); flash-attention-2 recommended.
  - MTEB Eng v2 mean 70.70.
  - Source: [HF Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- LIMIT (ICLR 2026): SOTA single-vector embedders (GritLM, Qwen3-Embedding, Gemini, E5-Mistral, Arctic-L v2, Promptriever; 1024–4096-d) "struggle" on a simple combinatorial retrieval task. BM25 does "very well". Even multi-vector models struggle. — [arXiv 2508.21038](https://arxiv.org/html/2508.21038v2)
- ETH FANNS benchmark: "Embedding characteristics vary significantly across models", and index/filter performance depends on them. Swapping embedders changes ANN behaviour, not just relevance. — [arXiv 2507.21989](https://arxiv.org/pdf/2507.21989)
- **[SANDBOX] Templated IT-ticket corpus.**
  - Corpus: 1,500 docs from one template: ticket ID `TCK-#####-X`, one of 20 names, 8 devices, 6 symptoms, 4 events, team, priority.
  - Two query sets of 300 each:
    - **ID**: "status of ticket TCK-…", an exact-identifier lookup.
    - **PARA**: paraphrased symptom description using first name + synonym device/symptom/event (e.g. "Grace's display screen displays nothing since an electrical outage").
  - Models: BM25 (Okapi, k1=1.2, b=0.75); bge-small-en-v1.5 with and without its query prefix; Qwen3-Embedding-0.6B with and without the instruction. Each was loaded via sentence-transformers 6.2.0 with its default pooling.
  - Final run size: 800 docs, 150 ID queries, 150 PARA queries (shrunk after OOM kills on a shared 7 GB sandbox).
  - Qwen3 ran in fp32 via sentence-transformers. Its shipped config uses `pooling_mode_lasttoken: true`, so pooling was correct.
  - The Qwen3 no-instruction arm was **OOM-killed twice**, so that arm is missing.
  - Wilson 95% CIs, n=150 each:

  | Arm | ID R@1 | ID R@10 | PARA R@1 | PARA R@10 |
  |---|---|---|---|---|
  | BM25 | **1.000** [0.975–1.0] | 1.000 | 0.067 [0.037–0.118] | 0.420 [0.344–0.500] |
  | bge-small-en-v1.5 + query prefix | 0.133 [0.088–0.197] | 0.293 [0.226–0.371] | **0.887** [0.826–0.928] | **1.000** [0.975–1.0] |
  | bge-small-en-v1.5, no prefix | 0.087 [0.051–0.143] | 0.240 | 0.853 [0.788–0.901] | 1.000 |
  | Qwen3-Embedding-0.6B + instruction | 0.240 [0.179–0.314] | 0.493 [0.414–0.573] | 0.800 [0.729–0.856] | 0.987 [0.953–0.996] |

  - Readings:
    1. **The anomaly reproduces in direction**: bge-small beats Qwen3-0.6B on paraphrase R@1 (0.887 vs 0.800). The Wilson CIs overlap, and per-query paired data wasn't retained, so the difference is **not shown to be significant**.
    2. On identifier lookups, Qwen3 is better than bge-small (0.24 vs 0.13), but **both dense models fail badly** (R@10 ≤0.49), while BM25 is perfect.
    3. BM25 fails on paraphrase (R@1 0.067).
    4. bge-small's query prefix adds ~3 points (not significant).
  - Threats to validity:
    - Single template.
    - The first name appears verbatim in both query and doc.
    - Docs are near-duplicates differing only in slot values, which favours models whose embeddings are dominated by slot tokens.
    - CPU fp32 only; n=150; no paired test.
  - Status: OBSERVED in a single sandbox study, synthetic.
  - Scripts: `/tmp/claude-0/-home-claude/4c8492a6-f948-5903-9334-5b76eec5c7f7/scratchpad/emb/exp3.py` and `exp4.py`

### Inferences
- Before concluding "small beats large", the builder should re-run the sandbox comparison with:
  1. Qwen3 instruction prefix on queries only; left padding, last-token pooling (sentence-transformers handles this if the model's own config is used).
  2. bge-small's query prefix applied consistently.
  3. A **non-templated, real or human-written query set** of ≥200 queries.
  4. Per-query-type breakdown (identifier / lexical / paraphrase / multi-hop).
  5. Bootstrap confidence intervals: with n≈100–300, differences under ~5 points are often noise.
- Templated synthetic corpora systematically favour lexical matchers and penalise models trained for semantic generalisation. Combined with Chroma's finding that synthetic queries over-estimate quality, the templated benchmark should be treated as a **regression and plumbing test**, not a model-selection test.
- Architecturally the anomaly argues for the planned **hybrid BM25 + dense first stage**. If BM25 handles identifier and lexical queries, the dense model's job narrows to paraphrase and semantic recall, where larger instruction-tuned models usually win.

### Gaps
- No peer-reviewed 2025–26 study isolating "templated corpus → small model wins" was retrieved (search budget exhausted before that query).
- Chroma didn't publish rank correlations between synthetic and real queries, so the size of rank-reversal risk isn't quantified beyond individual model pairs.

---

## Q7. Operational: backups, PITR, per-tenant encryption at rest (Postgres 2026 vs Qdrant)

### Takeaway
Postgres gives WAL-based PITR, natively and via pgBackRest/Barman. Qdrant gives point-in-time **snapshots** only: per node, per collection or full storage, restorable only to the same or next minor version, with no WAL-based PITR documented. Neither engine offers true **per-tenant** encryption at rest in its open-source form. Percona's `pg_tde` (2.1, Nov 2025; PG 18.1 supported) gives per-table internal keys wrapped by **per-database** principal keys in Vault/OpenBao/KMIP. Per-tenant keys therefore mean database-per-tenant, or application-level envelope encryption with pgcrypto or a client-side library. Qdrant's docs don't cover encryption at rest; disk-level (LUKS) encryption is the implied route.

### Cited Findings
- **Percona pg_tde:**
  - Envelope encryption: per-table internal keys wrapped by a per-database principal key; principal keys in a KMS (HashiCorp Vault or KMIP); local keyring "not recommended for production".
  - The `tde_heap` access method encrypts tables and indexes.
  - Early tests showed ~10% overhead.
  - Requires Percona's patched PostgreSQL. Community PostgreSQL only had the older `tde_heap_basic`.
  - Source: [Percona blog (Jan 2025, updated 2026)](https://www.percona.com/blog/your-datas-not-safe-until-its-tde-safe-heres-how/)
- pg_tde 2.1.0 (2025-11-28):
  - Adds PostgreSQL 18.1 support, shipped as a separate RPM/DEB for PG18 and in Percona Docker images.
  - Key providers: Vault (with namespaces), OpenBao, Akeyless CipherTrust (KMIP).
  - **Standard `pg_basebackup`, `pg_checksums`, `pg_resetwal`, `pg_rewind`, `pg_waldump` don't work on encrypted clusters**: use the `pg_tde_` equivalents.
  - Known issue: rotating keys or providers during `pg_tde_basebackup` can break standbys and corrupt encrypted data.
  - Source: [pg_tde 2.1 release notes](https://pg-tde-docs-pr-584.onrender.com/release-notes/release-notes-v2.1.html) (doc-preview host; treat as unofficial mirror)
- Qdrant snapshots: collection-level, or full storage (single-node only). Created per node. S3 storage since v1.10 (GCS/Azure/prefix since v1.20). Restore priorities `replica`, `snapshot`, `no_sync`. **Compatibility: same minor or next minor only.** The docs don't mention PITR or incremental/WAL backups. Qdrant Cloud uses disk-level backups. — [Qdrant snapshots docs](https://qdrant.tech/documentation/snapshots/)
- Qdrant security:
  - Connections "unencrypted by default" (TLS opt-in since v1.2).
  - Admin and read-only API keys; key rotation via `alt_api_key` (v1.17).
  - JWT RBAC (v1.9, HS256, per-collection access).
  - Audit logging (v1.17).
  - Encryption at rest isn't covered.
  - Source: [Qdrant security docs](https://qdrant.tech/documentation/guides/security/index.md)
- Qdrant 1.19 removed the legacy `/search`, `/recommend`, `/discover` endpoints. Self-hosted upgrades must step through each minor version. Combined with the snapshot compatibility window, this creates operational upgrade discipline. — [Qdrant 1.19](https://qdrant.tech/blog/qdrant-1.19.x/index.md)
- ParadeDB scales vertically on one primary (largest seen: 10 TB). It supports read replicas (Enterprise) and logical replication, but DDL isn't replicated. — `docs/concepts/limitations.mdx` in [paradedb repo](https://github.com/paradedb/paradedb)
- Australian Privacy Principle 11 (OAIC guidelines):
  - Entities must take "such steps as are reasonable in the circumstances" to protect personal information. "Encrypting data" is an example technical measure (11.12), and "failing to keep adequate backups" counts as a form of loss (11.22).
  - APP 11.2: data no longer needed must be destroyed or de-identified, including copies "archived or... held as back-ups" (11.39). Data that can't be destroyed can be put "beyond use" with "access controls including logs and audit trails" (11.51–11.52).
  - Source: [OAIC APP Guidelines Chapter 11](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-11-app-11-security-of-personal-information)
- pg_textsearch v1.2.0 added physical replication support; v1.3.1 added standby-safe page reclaim. — [pg_textsearch README version table](https://raw.githubusercontent.com/timescale/pg_textsearch/main/README.md)

### Inferences
- Postgres-centric wins on recovery: one WAL stream covers facts, ACLs, BM25 and vectors **transactionally**, so PITR restores a consistent brain. A Postgres + Qdrant split needs coordinated snapshot points and a reconciliation job (outbox pattern), and can't do true PITR on the vector side.
- Per-tenant crypto-shredding (delete a tenant by destroying its key) is only practical with application-level envelope encryption of content columns. Embeddings and BM25 indexes would then also need per-tenant isolation, since indexes over plaintext leak content. Embeddings are invertible to a meaningful degree; that's a known result, not retrieved here. Practical route: database-per-tenant (pg_tde per-database principal key) for high-assurance tenants, shared cluster plus volume encryption for the rest.
- APP 11.2 makes **backups part of the deletion problem**. When a tenant or member requests deletion, WAL archives and base backups still hold the data until they age out. Options:
  1. A documented retention window, so backups expire within N days, treated as "beyond use" with access logging per OAIC 11.51–11.52.
  2. Per-tenant envelope keys, so deletion = key destruction (crypto-shredding), which also covers backups.
  - Qdrant snapshots raise the same issue.
- Extension compatibility risk: pg_tde requires Percona's PG build. pgvector, pg_textsearch (PG17/18) and ParadeDB must be compiled and tested against it, and pg_tde's replacement backup tools must be integrated with pgBackRest-style workflows. This combination isn't verified anywhere I found.

### Gaps
- Not found: confirmation that pgBackRest supports pg_tde-encrypted clusters in 2026, or that ParadeDB/pg_textsearch/pgvector are certified on Percona Server for PostgreSQL 18 with pg_tde.
- Not found: Qdrant's official position on encryption at rest (docs page silent); search budget exhausted.
- Not found: whether community PostgreSQL 19 merges any TDE hooks.
