"""
memory/search.py — Query interface for the memory index.

Thin wrapper around MemoryIndex.search() that formats results for
display to Claude as tool output.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memory.index import MemoryIndex

logger = logging.getLogger("memory.search")


def search(index: "MemoryIndex", query: str, limit: int = 5) -> str:
    """
    Search memory files. Returns a formatted string for Claude.
    Empty result returns a clear 'nothing found' message.
    """
    results = index.search(query, limit=limit)

    if not results:
        return f"No memory found for: {query!r}"

    parts: list[str] = [f"Memory search results for {query!r}:\n"]
    for i, r in enumerate(results, 1):
        parts.append(
            f"[{i}] {r['source']} (lines {r['line_start']}–{r['line_end']}, score {r['score']})\n"
            f"{r['text']}\n"
        )
    return "\n".join(parts)
