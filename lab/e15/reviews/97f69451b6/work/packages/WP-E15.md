# WP-E15: Visible-set retrieval with access pre-filter and exit check

- **Owner ADRs:** ADR-007 (access control as a pre-filter, fail closed), ADR-006 (no statistic over rows the requester cannot see), ADR-005 (hybrid first stage, RRF), ADR-004 (exact vector search), ADR-014 (quarantine), ADR-019 (work packages, resumable state)
- **Depends on:** nothing (the record store is provided)
- **Status:** approved by the engineer; ready to build

## Goal

Build `vretrieval`, a small Python module that searches a record store for one requester and returns only what that requester may see now, in the current version, with nothing hidden leaking through results, order, scores, counts or errors.

## Done line

`make test` passes every acceptance test in `tests/acceptance/`; rules R1–R12 below hold; `search()` returns the top 5 hits by default; the work is committed and `build/state.json` records the package as passed with the commit id.

## Inputs (provided; read, do not modify)

| Path | What it is |
|---|---|
| `provided/e15store/store.py` | `RecordStore`: SQLite record store (tenants, principals, ACL groups, memberships, versioned records). Read its docstrings; they are the data contract |
| `provided/e15store/embedder.py` | `embed(text) -> list[float]` (64 dims, L2-normalised, deterministic) and `tokens(text) -> list[str]` (NFKC + casefold + `\w+`) |
| `provided/fixture.json` | Made-up test data: 2 tenants, 12 principals, 7 groups, 207 records. Load with `RecordStore.from_fixture(path)` |
| `tests/acceptance/` | The engineer's acceptance tests (pytest). Run with `make test` |
| `build/state.json`, `build/questions.json` | Build state and the owner question channel (see Checkpoint and Questions) |

Python 3.13, standard library only (`sqlite3` has FTS5). `python` and `pytest` on the PATH are the project's interpreter.

### The data, briefly

- **Tenants** are hard partitions: nothing ever crosses a tenant.
- **Principals** are `person` or `agent`, `active` or `revoked`. Agents (`kind = 'agent'`) act for a person (`acts_for`). Agents also have their own membership rows, which the owner's admin tool maintains to limit what each agent may use.
- **ACL groups** belong to one tenant. **Memberships** link principals to groups. Membership rows are raw data: a row may name a group that does not exist, or a group in another tenant.
- **Records** have versions. Exactly one version is current. Each current version has one `acl_group` and a `state`: `active`, `erased` (privacy erasure; title and body emptied) or `quarantined` (held by the write gate; content kept but never served).
- The store's write methods (`put`, `erase`, `quarantine`, `reclassify`, `revoke`, `remove_membership`, …) change the world after your index was built. The store is always the truth; your index may be stale.

## Outputs

| Path | What |
|---|---|
| `src/vretrieval/` | The package (any internal layout). `from vretrieval import Retriever, Hit, VisibleSet` must work with `src/` on `sys.path` |
| Index tables | Your own tables inside `store.conn`, every name starting `vr_`. Never alter the store's own tables |
| `build/state.json` | Updated at each checkpoint |

## Interface

```python
from vretrieval import Retriever, Hit, VisibleSet

r = Retriever(store)          # builds the index from the store (vr_* tables in store.conn)
r.visible_set(principal_id)   # -> VisibleSet
r.search(query, principal_id, k=10)   # -> list[Hit], best first
r.get(record_id, principal_id)        # -> dict | None
r.refresh(record_id)          # re-index one record from the store
r.rebuild()                   # drop and rebuild the whole index from the store
```

- `VisibleSet`: frozen dataclass with `principal_id: str`, `tenant: str | None`, `groups: frozenset[str]`. Empty (`groups == frozenset()`) when nothing is visible.
- `Hit`: frozen dataclass with `id: str`, `version: int`, `title: str`, `snippet: str`, `score: float`.
  - `title` is the current version's title.
  - `snippet` is the first 120 characters of the current version's body.
  - `score` is the fused score (R5); higher is better.
- `get()` returns the record's current version as a dict with the keys of `RecordStore.current()`, or `None` (R7).

## Rules

**R1. Query handling.** Tokenise queries and documents with `e15store.tokens` (documents: title + " " + body). A query with no tokens returns `[]`. Raw query text never reaches SQL or an FTS5 `MATCH` expression: bind parameters, and if you use `MATCH`, quote every token. No query string may raise.

**R2. Visible set (ADR-007).** Resolve the requester's visible set from the store on every call; never cache it across calls.
- Unknown or revoked principal: empty.
- A person sees the groups named in their membership rows that exist and belong to the person's own tenant; every other row is ignored.
- Agents work with delegated access: an agent acts with the access of the person it acts for.
- A record is visible only if its current version's `acl_group` is in the visible set **and** the record's tenant equals the principal's tenant.

**R2a. No standing owner access** (owner decision, 2026-10-23). The business owner sees only the groups he is a member of. Member-health groups are never granted by role, title or ownership.

**R3. Pre-filter, not post-filter (ADR-007).** Every channel scores only visible records. Never take a global top-k and filter it afterwards. If at least k visible records match, return k hits.

**R4. No statistic over unseen rows (ADR-006).** BM25 document frequencies, document count and average document length are computed over the requester's visible records only. Any normalisation runs over permitted candidates only. Changing, adding or removing records the requester cannot see must not change anything the requester can observe: which hits, their order, or their scores.

**R5. Channels and fusion (ADR-005, ADR-004).**
- *Lexical:* BM25 with k1 = 1.2 and b = 0.75 over document tokens. Candidates: visible records with BM25 > 0.
- *Dense:* exact cosine between `embed(query)` and `embed(title + "\n" + body)`. Document vectors are computed at index time and stored in your `vr_` tables, not recomputed per query. Candidates: visible records with cosine ≥ 0.2.
- Each channel ranks its candidates (best first) and keeps at most 200.
- *Fusion:* reciprocal rank fusion, `score = Σ over channels of 1 / (60 + rank)` with rank starting at 1; a record missing from a channel gets nothing from it.
- Results are ordered by descending score. Ties, in each channel and after fusion, are broken by record id ascending (so order never depends on storage order).

**R6. Exit check (ADR-007, ADR-014).** Before returning, re-validate every candidate against the record store, using the visible set resolved for this request:
- the record exists and its current version's state is `active`;
- the version you indexed is still the current version (otherwise drop it until it is re-indexed);
- the current version is visible (R2).

Return text (title, snippet) only from the current version. Dropped candidates are replaced by the next-best candidates, so the caller still gets up to k hits. The snippet should be the part of the text that best matches the query.

**R7. "Not found" and "denied" are indistinguishable (ADR-007).** `get()` reads the store directly and returns the current version only if it is `active` and visible to that principal (R2); otherwise `None`, whether the id is unknown, hidden, erased or quarantined. Neither `get()` nor `search()` raises for unknown principals or ids, and nothing they return or log reveals how many hidden records exist or match.

**R8. Index.** The constructor indexes the current version of every record whose state is `active`; erased and quarantined records are never indexed. `refresh(record_id)` re-indexes that record from the store (or removes it if it is no longer active); `rebuild()` starts again from the store.

**R9. Audit log.** Each `search()` logs one INFO record on the logger named `vretrieval`, naming the principal id and the number of hits returned. Never log titles or bodies.

**R10. Decision markers.** Put a comment `# DECISION: ADR-007` at the visible-set and exit-check code, `# DECISION: ADR-006` at the statistics code and `# DECISION: ADR-005` at the fusion code.

**R11. No hard-coded identities.** No principal, group, tenant or record id from the fixture appears in `src/`. The module must work on any data.

**R12. Engineer-owned files.** Do not edit `tests/acceptance/` or `provided/`. If you believe a test or a provided file is wrong, record a test-change request (below) instead.

## Steps (each safe to re-run)

1. Read `provided/e15store/` and this brief. Set up `src/vretrieval/` (a stub exists).
2. Visible set (R2, R2a) and `get()` (R7).
3. Index (R8) and the two channels with visible-set statistics (R4, R5).
4. Fusion, exit check, snippets and logging (R5, R6, R9).
5. Run `make test`; checkpoint.

## Acceptance tests

- Command: `make test` (exit code 0 on pass).
- Files: every `test_*.py` in `tests/acceptance/`.
- Further held-out acceptance tests, drawn from rules R1–R12, are run by the engineer after the build. Passing `make test` is necessary, not sufficient.

## Checkpoint

After each step that leaves the tests no worse: commit with a message naming the step, and update `build/state.json` (`status`: todo | in_progress | passed | blocked; `done`: steps finished; `next`: the next step; `last_commit`). A fresh session must be able to resume from the repository alone.

## Questions for the owner

Write each question as an entry in `build/questions.json`: `{"topic": "...", "question": "...", "blocking": true|false}`, and say so in your final message. A test-change request is an entry with `"topic": "test-change"`, naming the test and the reason. The owner reads the file when your session ends and answers in the next message.

## Out of scope

Rerankers, caching, graph expansion, connectors, concurrency, performance tuning beyond "a search over the fixture takes well under a second", any user interface.

## Known pitfalls

- SQLite's built-in FTS5 `bm25()` uses statistics over every row in the FTS table, including rows the requester cannot see (R4).
- Filtering a global top-k returns fewer than k hits and leaks through counts (R3).
- An index built earlier can hold records that were since erased, quarantined, reclassified or replaced by a newer version (R6).
