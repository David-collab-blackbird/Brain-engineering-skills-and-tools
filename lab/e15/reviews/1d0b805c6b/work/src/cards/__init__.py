"""WP-E15C: keyed facts, entity cards and context assembly.

    from cards import Brain, Card, ContextItem, VisibleSet

The public interface is described in packages/WP-E15C.md.
"""
from .brain import Brain
from .model import Card, ContextItem, VisibleSet

__all__ = ["Brain", "Card", "ContextItem", "VisibleSet"]
