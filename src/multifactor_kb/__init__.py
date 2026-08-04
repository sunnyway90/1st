"""Public API for the multifactor knowledge base."""

from .core import (
    KB_ROOT,
    Chunk,
    build_ask_prompt,
    format_context,
    list_catalog,
    load_chunks,
    load_digests,
    search,
)

__all__ = [
    "KB_ROOT",
    "Chunk",
    "build_ask_prompt",
    "format_context",
    "list_catalog",
    "load_chunks",
    "load_digests",
    "search",
]
