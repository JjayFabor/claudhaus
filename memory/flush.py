"""
memory/flush.py — Pre-compaction memory flush.

When a session's accumulated token count approaches the context window
limit, inject a silent flush turn that asks Main to write anything
worth remembering to disk before the CLI compacts the conversation.

Responses of exactly "NO_REPLY" are swallowed — invisible to the user.
"""

import logging
from typing import Optional

logger = logging.getLogger("memory.flush")

# Trigger flush when estimated tokens exceed this threshold.
# Conservative: better to flush too early than too late.
FLUSH_THRESHOLD_TOKENS = 150_000

# Estimated tokens per character (rough approximation)
CHARS_PER_TOKEN = 4

FLUSH_PROMPT = """\
Before this context window is summarized, review our conversation and \
write anything important to disk:

- Durable facts, preferences, or decisions → append to ~/MEMORY.md
- Today's context and observations → append to ~/memory/{today}.md

If there is nothing new worth saving, respond with exactly: NO_REPLY
"""


class FlushManager:
    """Tracks cumulative session length and signals when a flush is needed."""

    def __init__(self) -> None:
        self._session_chars: dict[int, int] = {}  # chat_id → char count

    def record(self, chat_id: int, text: str) -> None:
        self._session_chars[chat_id] = self._session_chars.get(chat_id, 0) + len(text)

    def reset(self, chat_id: int) -> None:
        self._session_chars.pop(chat_id, None)

    def needs_flush(self, chat_id: int) -> bool:
        chars = self._session_chars.get(chat_id, 0)
        estimated_tokens = chars // CHARS_PER_TOKEN
        return estimated_tokens >= FLUSH_THRESHOLD_TOKENS

    def flush_prompt(self, today: str) -> str:
        return FLUSH_PROMPT.format(today=today)
