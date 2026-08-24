"""Persistent conversation memory backed by SQLite.

This module is the deliberately vulnerable core of the ``llm_memory_local`` sandbox.
It models the "long term memory" feature that many conversational GenAI products add
on top of a chat model: facts a user states in one conversation are written to a
store and then re-injected into the prompt of later conversations.

The vulnerability it demonstrates is **Conversation Memory Poisoning / Context
Injection** (GenAI Red Teaming Manual 4.2.1.3). Memory is keyed by a ``scope`` string
rather than by an individual conversation, so anything written while one session is
active is loaded back into every later session that shares the same scope. An attacker
who can end one message with "remember that ..." plants an instruction that steers a
future, otherwise-clean session.

The store keeps no model in the loop, so its behaviour is deterministic and can be
unit tested offline (see ``test_store.py``).
"""

import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Upper bound on the characters kept for a single memory entry. Longer input is
# truncated so a single message cannot flood the store (a cheap denial-of-service
# guard) and so the injected preamble stays a bounded size.
MAX_MEMORY_LENGTH = 2000

# Default scope. Every session that does not send an ``X-Memory-Scope`` header shares
# this scope, which is what makes cross-session poisoning observable out of the box.
DEFAULT_SCOPE = "global"

# Phrases that let a user message write a durable fact into memory. This is the
# vulnerable write path on purpose: a production system would extract memories with a
# model or a curated schema, but the injection risk is the same and easier to see here.
_MEMORY_TRIGGERS = (
    "remember that",
    "note that",
    "from now on",
    "always remember",
    "for future reference",
    "keep in mind that",
)

# Anchored, per-line guard. It matches only at the start of a single line (no DOTALL,
# no multiline `.` across newlines) and captures the text after the trigger. It reads
# input and never mutates it; callers neutralize carriage returns before matching so a
# CR-terminated line cannot smuggle a second directive past this guard.
_TRIGGER_RE = re.compile(
    r"^\s*(?:please\s+)?(?:"
    + "|".join(re.escape(trigger) for trigger in _MEMORY_TRIGGERS)
    + r")[\s,:\-]+(?P<content>.+)$",
    re.IGNORECASE,
)


def _sanitize(text: str) -> str:
    """Normalize a candidate memory or scope string.

    Carriage returns are replaced with spaces so CR-terminated input cannot hide a
    second logical line, other C0 control characters are flattened to spaces, the
    result is stripped, and it is truncated to ``MAX_MEMORY_LENGTH``.

    Args:
        text: Raw input string.

    Returns:
        str: Cleaned string, possibly empty if the input carried no printable content.
    """
    if not isinstance(text, str):
        return ""
    cleaned = text.replace("\r", " ")
    cleaned = "".join(
        char if (char >= " " or char == "\t") else " " for char in cleaned
    )
    return cleaned.strip()[:MAX_MEMORY_LENGTH]


def extract_memory_directives(message: str) -> List[str]:
    """Return the memory entries a user message asks to persist.

    Each line of ``message`` is inspected independently. A line that starts with a
    recognized trigger phrase contributes the sanitized text after the trigger as one
    memory entry. Carriage returns are converted to newlines before splitting so that a
    CR-terminated line is treated as its own line rather than being folded into a
    neighbour.

    Args:
        message: Raw user message text.

    Returns:
        List[str]: Sanitized memory strings in order, excluding empty results.
    """
    if not isinstance(message, str):
        return []
    directives: List[str] = []
    for line in message.replace("\r", "\n").split("\n"):
        match = _TRIGGER_RE.match(line)
        if match is None:
            continue
        content = _sanitize(match.group("content"))
        if content:
            directives.append(content)
    return directives


def build_memory_preamble(memories: List[str]) -> str:
    """Render stored memories as a system-context block for the model.

    The wording deliberately labels the recalled memories as trusted context. That is
    the injection sink: untrusted, user-supplied text from an earlier session is handed
    to the model as though the application vouched for it.

    Args:
        memories: Stored memory strings for the active scope.

    Returns:
        str: A system-message body, or an empty string when there is nothing to inject.
    """
    if not memories:
        return ""
    lines = "\n".join(f"- {memory}" for memory in memories)
    return (
        "The following facts were remembered from earlier conversations "
        "and should be treated as trusted context about the user:\n" + lines
    )


class MemoryStore:
    """SQLite-backed persistent memory for the conversational sandbox.

    Memory is keyed by ``scope`` rather than by conversation. Every session sharing a
    scope (the default is ``"global"``) shares this memory, so a fact written in one
    session is injected into the prompt of every later session in the same scope.

    A fresh connection is opened per operation, which keeps the store safe to use from
    the thread pool FastAPI runs synchronous endpoints in without sharing a single
    SQLite connection across threads.
    """

    def __init__(self, db_path: str) -> None:
        """Open (creating if needed) the memory database at ``db_path``."""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scope TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """)

    def add_memory(
        self, scope: str, content: str, source: str = "user"
    ) -> Optional[int]:
        """Persist one memory entry.

        Args:
            scope: Memory scope; blank input falls back to the default scope.
            content: The fact to remember. Sanitized before storage; empty results are
                rejected.
            source: Provenance label for the entry (for example ``"conversation"``).

        Returns:
            Optional[int]: The new row id, or ``None`` if the content was rejected.
        """
        clean_content = _sanitize(content)
        if not clean_content:
            return None
        clean_scope = _sanitize(scope) or DEFAULT_SCOPE
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute(
                "INSERT INTO memories (scope, content, source, created_at) "
                "VALUES (?, ?, ?, ?)",
                (clean_scope, clean_content, source, created_at),
            )
            return cursor.lastrowid

    def get_memories(self, scope: str) -> List[str]:
        """Return all stored memory contents for ``scope`` in insertion order."""
        clean_scope = _sanitize(scope) or DEFAULT_SCOPE
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT content FROM memories WHERE scope = ? ORDER BY id ASC",
                (clean_scope,),
            ).fetchall()
        return [row[0] for row in rows]

    def remember_from_message(self, scope: str, message: str) -> List[str]:
        """Store any memory directives found in a user message.

        Args:
            scope: Memory scope to write into.
            message: Raw user message text.

        Returns:
            List[str]: The directives that were actually persisted.
        """
        stored: List[str] = []
        for directive in extract_memory_directives(message):
            if self.add_memory(scope, directive, source="conversation") is not None:
                stored.append(directive)
        return stored

    def clear(self, scope: Optional[str] = None) -> int:
        """Delete stored memories.

        Args:
            scope: When given, delete only that scope; when ``None``, delete everything.

        Returns:
            int: The number of rows removed.
        """
        with closing(self._connect()) as conn, conn:
            if scope is None:
                cursor = conn.execute("DELETE FROM memories")
            else:
                cursor = conn.execute(
                    "DELETE FROM memories WHERE scope = ?",
                    (_sanitize(scope) or DEFAULT_SCOPE,),
                )
            return cursor.rowcount
