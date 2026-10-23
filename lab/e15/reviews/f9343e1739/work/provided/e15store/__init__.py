"""Provided infrastructure for WP-E15. Do not modify."""
from .embedder import DIM, embed, tokens
from .store import RecordStore, load_fixture

__all__ = ["RecordStore", "load_fixture", "embed", "tokens", "DIM"]
