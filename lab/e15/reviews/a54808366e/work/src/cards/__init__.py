"""WP-E15C: keyed facts, entity cards and context assembly.

``Brain(store)`` keeps keyed facts current (``upsert``), compiles one card per
(entity, ACL group) in code (``cards`` / ``card``), and assembles a context for one
requester (``assemble``): pinned cards for the entities the request names, then
lexically found notes, with nothing the requester may not see.
"""
from .brain import Brain
from .model import Card, ContextItem, VisibleSet

__all__ = ["Brain", "Card", "ContextItem", "VisibleSet"]
