# WP-E15C: Keyed facts, entity cards and context assembly

- **Owner ADRs:** ADR-008 (memory data model: keyed facts with validity), ADR-009 (path A keyed upsert; forward to head at read time), ADR-010 (entity cards compiled in code; context assembly), ADR-007 (access control as a pre-filter, fail closed; derived artefacts inherit the intersection of their sources' ACLs), ADR-006 (no statistic over rows the requester cannot see), ADR-019 (work packages)
- **Depends on:** nothing (the store is provided)
- **Status:** approved by the engineer; ready to build

## Goal

Build `cards`, a Python module that keeps keyed facts current (path A upsert with supersession), compiles one entity card per (entity, ACL group) deterministically in code, and assembles a context for one requester: pinned cards for entities named in the request, then free-text notes found by lexical search, with stale quoted values forwarded to their current head, and nothing the requester may not see leaking through any of it.

## Done line

`make test` passes every acceptance test in `tests/acceptance/`; rules R1–R14 hold; `assemble()` returns at most 8 items by default; the work is committed and `build/state.json` records the package as passed with the commit id.

## Inputs (provided; read, do not modify)

| Path | What it is |
|---|---|
| `provided/factstore/store.py` | `FactStore`: SQLite store of tenants, principals, ACL groups, memberships, entities with aliases, keyed fact versions and notes with value mentions. Its docstrings are the data contract |
| `provided/factstore/text.py` | `tokens(text)` (NFKC + casefold + `\w+`) and `canonical_json(obj)` |
| `provided/fixture.json` | Made-up data: 2 tenants, 9 principals, 6 groups, 14 entities, ~120 fact versions, ~90 notes. Load with `FactStore.from_fixture(path)` |
| `tests/acceptance/` | The engineer's acceptance tests (pytest). Run with `make test` |
| `build/state.json`, `build/questions.json` | Build state and the owner question channel |

Python 3.13, standard library only.

### The data, briefly

- **Tenants, principals, ACL groups, memberships:** as in WP-E15. Principals are `person` or `agent`, `active` or `revoked`. Agents act for a person (`acts_for`). Agents also have their own membership rows, which the owner's admin tool maintains to limit what each agent may use. Membership rows are raw data and may name missing groups or groups in another tenant.
- **Entities** belong to one tenant and have a canonical name and aliases (`store.entities()`, `store.aliases(entity_id)`).
- **Fact versions** are keyed by `(source_system, source_entity_id, attribute)`. Each version has `entity_id`, `attribute`, `value` (text), `valid_from` (ISO date), `source`, `acl_group`, `superseded_by` (version id or null) and a monotonically increasing `id`. Exactly one version per key is the head (`superseded_by IS NULL`), unless the key was released.
- **Notes** are free text with an `acl_group`, a `state` (`active` / `erased` / `quarantined`) and zero or more **mentions**: a mention links a note to the fact version whose value the note quotes (`store.mentions(note_id)`).

## Outputs

| Path | What |
|---|---|
| `src/cards/` | The package. `from cards import Brain, Card, ContextItem, VisibleSet` must work with `src/` on `sys.path` |
| Derived tables | Your own tables inside `store.conn`, every name starting `cd_`. Never alter the store's own tables except through the store's methods |
| `build/state.json` | Updated at each checkpoint |

## Interface

```python
from cards import Brain, Card, ContextItem, VisibleSet

b = Brain(store)                                   # compiles all cards from the store
b.visible_set(principal_id)                        # -> VisibleSet
b.upsert(source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source, acl_group)
                                                   # -> int (the head version id after the call)
b.cards(entity_id, principal_id)                   # -> tuple[Card, ...]: the requester's visible cards, ordered by acl_group
b.card(entity_id, principal_id)                    # -> Card | None: the first of cards(), or None
b.assemble(request, principal_id, k=10)            # -> list[ContextItem]
b.rebuild()                                        # recompile every card from the store
```

- `VisibleSet`: frozen dataclass `principal_id: str`, `tenant: str | None`, `groups: frozenset[str]`.
- `Card`: frozen dataclass `entity_id: str`, `acl_group: str`, `text: str`, `fact_ids: tuple[int, ...]` (the fact version ids it lists, ascending), `digest: str` (sha256 hex of `text`).
- `ContextItem`: frozen dataclass `kind: str` (`"card"` or `"note"`), `ref: str` (entity id for cards, note id for notes), `text: str`, `reason: str` (`"card"` or `"search"`), `annotations: tuple[str, ...]` (sorted).

## Rules

**R1. Visible set (ADR-007).** Resolve per call from the store; never cache across calls. Unknown or revoked principal: empty. A person sees the groups named in their membership rows that exist and belong to their own tenant. Agents work with delegated access: an agent acts with the access of the person it acts for. Nothing ever crosses a tenant.

**R2. No standing owner access** (owner decision, 2026-10-23). The business owner sees only groups he is a member of. Member-health groups are never granted by role, title or ownership.

**R3. Path A upsert (ADR-009).** In one transaction:
- if the key has a head with an identical `value`, `valid_from`, `acl_group` and `entity_id`: no-op, return the head's id;
- otherwise insert a new version (`store.insert_fact(...)`), set the old head's `superseded_by` to the new id (`store.supersede(old, new)`), and return the new id;
- then recompile every card that listed the old head or lists the new version, in the same transaction (R6).
Upsert never deletes rows. A failure leaves the store and every card as before the call.

**R4. Cards (ADR-010).** One card per (entity, ACL group) that holds at least one **head** fact of that entity in that group. A card is compiled **in code** from rows, never from free text:
- line 1: `# <canonical name>`;
- line 2: `aliases: <aliases sorted, comma-separated>` (omit the line if none);
- then one line per head fact, sorted by attribute then fact id: `<attribute>: <value> (valid_from <date>, source <source>)`.
- Lines are joined with `\n`; no trailing newline. Same rows → byte-identical text (determinism).
`fact_ids` lists exactly the head fact ids on the card.

**R5. Card ACL (ADR-007 §4).** A card's `acl_group` is the group of the facts on it. A card never mixes facts from different groups: an entity with facts in two groups has two cards. A requester sees a card only if its group is in their visible set and the entity's tenant equals the requester's tenant.

**R6. Freshness.** After `upsert` returns, no card holds a superseded value, and every card whose head facts changed has been recompiled (new text and digest). A card whose last head fact moved to another group disappears from the old group.

**R7. Linking.** An entity is linked from a request if the `tokens()` of its canonical name or of any alias occur as a contiguous run in the `tokens()` of the request (so the name "Zephyr Linen" matches the request "zephyr linen's invoice"). Only entities in the requester's tenant can be linked. When two matches overlap, the longer match wins (equal length: lower entity id); the shorter entity is not linked from that position.

**R8. Assembly (ADR-010 §3).**
1. Link entities in the request (R7).
2. Pin up to **3** visible cards of linked entities, ordered by first match position in the request, then entity id. If an entity has several visible cards, pin them all (they count toward the 3) ordered by `acl_group`.
3. Fill the remaining `k − pinned` slots with notes found by BM25 (k1 = 1.2, b = 0.75) over the **active, visible** notes only (statistics over visible notes only, R10). Ties by note id ascending.
4. Never return the same note twice; never return a note whose state is not `active` now.
5. Each item carries `reason`: `"card"` for pinned cards, `"search"` for notes.

**R9. Forward to head (ADR-009 §5).** For each note returned, for each of its mentions whose fact version has been superseded (`superseded_by` is not null): follow `superseded_by` to the head (`store.head_of`). If the head exists and the requester can see its group, add the annotation `quoted value superseded on <valid_from of the head>; current value <head value>`. If the key has no head (it was released) or the head is not visible to the requester, add `quoted value superseded` with no date and no value. Annotations are ordered by mention order. Cards carry no annotations.

**R10. No statistic over unseen rows (ADR-006).** BM25 statistics (document count, document frequencies, average length) are computed over the requester's visible active notes only. Changing notes the requester cannot see must not change which items they get, their order, or their annotations.

**R11. Exit check.** Before returning, re-validate every item against the store: a card's facts are still heads and visible; a note is still `active` and visible. Replace dropped items with the next candidates so the caller still gets up to `k`.

**R12. "Not found" equals "denied".** `cards()` returns `()` and `card()` returns `None` for an unknown entity, an entity with no visible card, or an unknown or revoked principal. No method raises for unknown ids or principals. Nothing returned or logged reveals hidden rows.

**R13. Decision markers.** `# DECISION: ADR-010` at card compilation and assembly, `# DECISION: ADR-009` at upsert and forwarding, `# DECISION: ADR-007` at the visible set and card ACL.

**R14. No hard-coded identities; engineer-owned files.** No principal, group, tenant, entity, note or fact id from the fixture in `src/`. Do not edit `tests/acceptance/` or `provided/`; file a test-change request instead.

## Steps (each safe to re-run)

1. Read `provided/factstore/` and this brief; set up `src/cards/` (a stub exists).
2. Visible set (R1, R2), `card()` ACL (R5, R12).
3. Card compiler and derived tables (R4, R5), `rebuild()`.
4. Upsert with supersession and same-transaction recompilation (R3, R6).
5. Linking, BM25 over visible notes, assembly, forwarding, exit check (R7–R11).
6. `make test`; checkpoint.

## Acceptance tests

`make test` (exit 0 on pass), every `test_*.py` in `tests/acceptance/`. Further held-out acceptance tests drawn from R1–R14 are run by the engineer after the build.

## Checkpoint

After each step that leaves the tests no worse: commit; update `build/state.json` (`status`: todo | in_progress | passed | blocked; `done`; `next`; `last_commit`). A fresh session must be able to resume from the repository alone.

## Questions for the owner

Write each question to `build/questions.json` as `{"topic": "...", "question": "...", "blocking": true|false}` and say so in your final message. A test-change request is an entry with `"topic": "test-change"`. The owner reads the file when your session ends and answers in the next message.

## Out of scope

Path B (free-text planner), embeddings, rerankers, class router, scope slots, media.

## Known pitfalls

- SQLite FTS5 `bm25()` computes statistics over every row in the table (R10).
- A card compiled once and cached goes stale after an upsert (R6).
- An entity with facts in two groups needs two cards; merging them leaks (R5).
- A forwarding annotation can leak a value from a group the requester cannot see (R9).
