"""Persistent conversation memory package.

Exposes the SQLite-backed :class:`~app.memory.store.MemoryStore` and the helper
functions that implement the sandbox's Conversation Memory Poisoning scenario.
"""

from app.memory.store import (
    DEFAULT_SCOPE,
    MemoryStore,
    build_memory_preamble,
    extract_memory_directives,
)

__all__ = [
    "DEFAULT_SCOPE",
    "MemoryStore",
    "build_memory_preamble",
    "extract_memory_directives",
]
