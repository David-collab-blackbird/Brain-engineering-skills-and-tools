"""vretrieval: search a record store for one requester, returning only what
that requester may see now, in the current version (WP-E15).

    from vretrieval import Retriever, Hit, VisibleSet

Map of the package
    access.py     who may see what: the visible set (R2), get() (R7), the exit check (R6)
    index.py      the vr_* tables in the store's own connection: content only, no text, no access data (R8)
    ranking.py    BM25 over visible records, exact cosine, reciprocal rank fusion, ties, snippets (R4, R5)
    retriever.py  the public interface; one INFO audit record per search (R9)
    models.py     Hit and VisibleSet

How a search stays inside what the requester may see
    1. The visible set is resolved from the store on every call and never cached.
    2. The records that may be scored are those the store says are, right now, active, at the
       version that was indexed, in the requester's tenant and in one of the requester's groups.
       Both channels and every statistic (document count, average length, document
       frequencies) are computed over those records alone (index rows of other records may be
       read, and are dropped before anything is counted), so nothing the requester cannot
       see can change a hit, its order or its score.
    3. Each candidate is checked against the store once more before it is returned, and the
       text returned (title, snippet) is read from the store's current version.

Choices the brief leaves open (agent access, default k, snippet, idf, ties) are listed with the
alternatives in build/questions.json. `make test` runs the engineer's acceptance tests; the
builder's own, much larger suite (about 3 minutes) is run with
    python -m pytest -q -p no:cacheprovider tests/builder
"""
from .models import Hit, VisibleSet
from .retriever import Retriever

__all__ = ["Retriever", "Hit", "VisibleSet"]
