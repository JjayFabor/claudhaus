"""
agents/main/shared_context.py — Shared context between bot users.

All functions accept db_path as first argument (same pattern as scheduler.py).
"""
import sqlite3
from pathlib import Path
from typing import Optional


def init_shared_context_tables(db_path: Path) -> None:
    with sqlite3.connect(db_path) as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS user_registry (
                chat_id   INTEGER PRIMARY KEY,
                user_id   INTEGER,
                username  TEXT,
                full_name TEXT,
                last_seen TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS shared_context (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                from_chat_id INTEGER NOT NULL,
                to_chat_id   INTEGER NOT NULL,
                content      TEXT NOT NULL,
                label        TEXT,
                shared_at    TEXT NOT NULL DEFAULT (datetime('now')),
                acknowledged INTEGER NOT NULL DEFAULT 0,
                revoked      INTEGER NOT NULL DEFAULT 0
            );
        """)


def db_upsert_user(
    db_path: Path,
    chat_id: int,
    user_id: int,
    username: Optional[str],
    full_name: Optional[str],
) -> None:
    with sqlite3.connect(db_path) as con:
        con.execute(
            """INSERT INTO user_registry (chat_id, user_id, username, full_name, last_seen)
               VALUES (?, ?, ?, ?, datetime('now'))
               ON CONFLICT(chat_id) DO UPDATE SET
                   user_id=excluded.user_id,
                   username=excluded.username,
                   full_name=excluded.full_name,
                   last_seen=excluded.last_seen""",
            (chat_id, user_id, username, full_name),
        )


def db_resolve_user(db_path: Path, name: str) -> Optional[tuple[int, str]]:
    """
    Resolve a name/username to (chat_id, full_name).
    Matches on username (exact, case-insensitive) or full_name (partial, case-insensitive).
    Returns None if not found. Raises ValueError if ambiguous.
    """
    name_lower = name.lstrip("@").lower()
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            """SELECT chat_id, full_name FROM user_registry
               WHERE lower(username) = ?
                  OR lower(full_name) LIKE ?""",
            (name_lower, f"%{name_lower}%"),
        ).fetchall()
    if not rows:
        return None
    if len(rows) > 1:
        names = ", ".join(r[1] or str(r[0]) for r in rows)
        raise ValueError(f"ambiguous: matches {names}")
    return rows[0][0], rows[0][1]
