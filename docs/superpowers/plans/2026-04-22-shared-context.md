# Shared Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users explicitly share specific context with other bot users, with push notification on share and on-demand pull, both injected into Claude's session.

**Architecture:** New `shared_context.py` module holds all DB helpers (following `scheduler.py` pattern — functions accept `db_path` as first arg for testability). `agent.py` imports from it, calls `upsert_user` in every message handler, injects unacknowledged shared context into `run_claude`, and registers `/share` and `/revoke` as command handlers. Pull is detected by keyword in `handle_message`.

**Tech Stack:** Python 3.12, sqlite3, python-telegram-bot 20.x, pytest

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `agents/main/shared_context.py` | **Create** | All shared context DB helpers + formatter |
| `agents/main/agent.py` | **Modify** | Import shared_context, upsert_user in handlers, inject in run_claude, register /share /revoke |
| `tests/__init__.py` | **Create** | Makes tests/ a package |
| `tests/test_shared_context.py` | **Create** | Tests for all DB helpers in shared_context.py |

---

### Task 1: Test scaffolding and DB schema

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_shared_context.py`
- Create: `agents/main/shared_context.py`

- [ ] **Step 1: Create the test package init**

```bash
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 2: Write failing tests for the two new tables**

Create `tests/test_shared_context.py`:

```python
import sqlite3
import tempfile
from pathlib import Path
import pytest

from agents.main.shared_context import init_shared_context_tables


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    init_shared_context_tables(db_path)
    return db_path


def test_tables_created(db):
    with sqlite3.connect(db) as con:
        tables = {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "user_registry" in tables
    assert "shared_context" in tables


def test_user_registry_schema(db):
    with sqlite3.connect(db) as con:
        cols = {
            row[1]
            for row in con.execute("PRAGMA table_info(user_registry)").fetchall()
        }
    assert cols == {"chat_id", "user_id", "username", "full_name", "last_seen"}


def test_shared_context_schema(db):
    with sqlite3.connect(db) as con:
        cols = {
            row[1]
            for row in con.execute("PRAGMA table_info(shared_context)").fetchall()
        }
    assert cols == {
        "id", "from_chat_id", "to_chat_id", "content",
        "label", "shared_at", "acknowledged", "revoked",
    }
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /home/jjay/JjayFiles/claude-command-center
python -m pytest tests/test_shared_context.py::test_tables_created -v
```

Expected: `ModuleNotFoundError: No module named 'agents.main.shared_context'`

- [ ] **Step 4: Create `agents/main/shared_context.py` with `init_shared_context_tables`**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_shared_context.py -v
```

Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add agents/main/shared_context.py tests/__init__.py tests/test_shared_context.py
git commit -m "feat(shared-context): DB schema + test scaffolding"
```

---

### Task 2: User registry helpers

**Files:**
- Modify: `agents/main/shared_context.py`
- Modify: `tests/test_shared_context.py`

- [ ] **Step 1: Write failing tests for upsert and resolve**

Append to `tests/test_shared_context.py`:

```python
from agents.main.shared_context import db_upsert_user, db_resolve_user


def test_upsert_user_inserts(db):
    db_upsert_user(db, chat_id=100, user_id=1, username="jay", full_name="Jay Fabor")
    with sqlite3.connect(db) as con:
        row = con.execute("SELECT * FROM user_registry WHERE chat_id=100").fetchone()
    assert row is not None
    assert row[2] == "jay"
    assert row[3] == "Jay Fabor"


def test_upsert_user_updates_on_conflict(db):
    db_upsert_user(db, chat_id=100, user_id=1, username="jay", full_name="Jay Fabor")
    db_upsert_user(db, chat_id=100, user_id=1, username="jay2", full_name="Jay Fabor Updated")
    with sqlite3.connect(db) as con:
        rows = con.execute("SELECT * FROM user_registry WHERE chat_id=100").fetchall()
    assert len(rows) == 1
    assert rows[0][2] == "jay2"


def test_resolve_user_by_username(db):
    db_upsert_user(db, chat_id=100, user_id=1, username="jay", full_name="Jay Fabor")
    result = db_resolve_user(db, "jay")
    assert result == (100, "Jay Fabor")


def test_resolve_user_by_full_name(db):
    db_upsert_user(db, chat_id=100, user_id=1, username=None, full_name="Jay Fabor")
    result = db_resolve_user(db, "Jay")
    assert result == (100, "Jay Fabor")


def test_resolve_user_case_insensitive(db):
    db_upsert_user(db, chat_id=100, user_id=1, username="JAY", full_name="Jay Fabor")
    result = db_resolve_user(db, "jay")
    assert result == (100, "Jay Fabor")


def test_resolve_user_not_found(db):
    result = db_resolve_user(db, "nobody")
    assert result is None


def test_resolve_user_ambiguous_raises(db):
    db_upsert_user(db, chat_id=100, user_id=1, username=None, full_name="Jay One")
    db_upsert_user(db, chat_id=101, user_id=2, username=None, full_name="Jay Two")
    with pytest.raises(ValueError, match="ambiguous"):
        db_resolve_user(db, "Jay")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_shared_context.py -k "upsert or resolve" -v
```

Expected: `ImportError` — functions not yet defined

- [ ] **Step 3: Implement `db_upsert_user` and `db_resolve_user` in `shared_context.py`**

Append to `agents/main/shared_context.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_shared_context.py -k "upsert or resolve" -v
```

Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/main/shared_context.py tests/test_shared_context.py
git commit -m "feat(shared-context): user registry helpers"
```

---

### Task 3: Shared context DB helpers

**Files:**
- Modify: `agents/main/shared_context.py`
- Modify: `tests/test_shared_context.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_shared_context.py`:

```python
from agents.main.shared_context import (
    db_share_context,
    db_get_unacknowledged_shared,
    db_mark_acknowledged,
    db_revoke_shared,
    db_list_shared,
    format_shared_note,
)


def test_share_context_inserts(db):
    db_upsert_user(db, 100, 1, "jay", "Jay Fabor")
    row_id = db_share_context(db, from_chat_id=100, to_chat_id=200, content="hello")
    assert isinstance(row_id, int)
    with sqlite3.connect(db) as con:
        row = con.execute("SELECT * FROM shared_context WHERE id=?", (row_id,)).fetchone()
    assert row[3] == "hello"
    assert row[6] == 0  # acknowledged
    assert row[7] == 0  # revoked


def test_get_unacknowledged_empty(db):
    assert db_get_unacknowledged_shared(db, chat_id=200) == []


def test_get_unacknowledged_returns_items(db):
    db_upsert_user(db, 100, 1, "jay", "Jay Fabor")
    db_share_context(db, from_chat_id=100, to_chat_id=200, content="hello")
    items = db_get_unacknowledged_shared(db, chat_id=200)
    assert len(items) == 1
    assert items[0]["content"] == "hello"
    assert items[0]["from_name"] == "Jay Fabor"


def test_mark_acknowledged(db):
    db_upsert_user(db, 100, 1, "jay", "Jay Fabor")
    db_share_context(db, from_chat_id=100, to_chat_id=200, content="hello")
    db_mark_acknowledged(db, chat_id=200)
    assert db_get_unacknowledged_shared(db, chat_id=200) == []


def test_revoke_shared(db):
    db_upsert_user(db, 100, 1, "jay", "Jay Fabor")
    db_share_context(db, from_chat_id=100, to_chat_id=200, content="the API uses REST")
    revoked = db_revoke_shared(db, from_chat_id=100, to_chat_id=200, content_hint="API")
    assert len(revoked) == 1
    items = db_list_shared(db, to_chat_id=200)
    assert items == []


def test_list_shared_excludes_revoked(db):
    db_upsert_user(db, 100, 1, "jay", "Jay Fabor")
    db_share_context(db, from_chat_id=100, to_chat_id=200, content="keep this")
    db_share_context(db, from_chat_id=100, to_chat_id=200, content="revoke this")
    db_revoke_shared(db, from_chat_id=100, to_chat_id=200, content_hint="revoke this")
    items = db_list_shared(db, to_chat_id=200)
    assert len(items) == 1
    assert items[0]["content"] == "keep this"


def test_format_shared_note(db):
    db_upsert_user(db, 100, 1, "jay", "Jay Fabor")
    db_share_context(db, from_chat_id=100, to_chat_id=200, content="use REST not GraphQL")
    items = db_get_unacknowledged_shared(db, chat_id=200)
    note = format_shared_note(items)
    assert "Jay Fabor" in note
    assert "use REST not GraphQL" in note
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_shared_context.py -k "share or revoke or list or acknowledged or note" -v
```

Expected: `ImportError` — functions not yet defined

- [ ] **Step 3: Implement the helpers in `shared_context.py`**

Append to `agents/main/shared_context.py`:

```python
def db_share_context(
    db_path: Path,
    from_chat_id: int,
    to_chat_id: int,
    content: str,
    label: Optional[str] = None,
) -> int:
    """Insert a shared context item. Returns the new row id."""
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            """INSERT INTO shared_context (from_chat_id, to_chat_id, content, label)
               VALUES (?, ?, ?, ?)""",
            (from_chat_id, to_chat_id, content, label),
        )
        return cur.lastrowid


def db_get_unacknowledged_shared(db_path: Path, chat_id: int) -> list[dict]:
    """Return unacknowledged, non-revoked shared items for chat_id."""
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """SELECT sc.id, sc.from_chat_id, sc.content, sc.shared_at,
                      COALESCE(ur.full_name, cast(sc.from_chat_id as text)) as from_name
               FROM shared_context sc
               LEFT JOIN user_registry ur ON ur.chat_id = sc.from_chat_id
               WHERE sc.to_chat_id = ? AND sc.acknowledged = 0 AND sc.revoked = 0
               ORDER BY sc.shared_at ASC""",
            (chat_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def db_mark_acknowledged(db_path: Path, chat_id: int) -> None:
    """Mark all unacknowledged shared items for chat_id as read."""
    with sqlite3.connect(db_path) as con:
        con.execute(
            "UPDATE shared_context SET acknowledged=1 WHERE to_chat_id=? AND acknowledged=0",
            (chat_id,),
        )


def db_revoke_shared(
    db_path: Path, from_chat_id: int, to_chat_id: int, content_hint: str
) -> list[int]:
    """
    Soft-delete shared items from from_chat_id to to_chat_id matching content_hint.
    Matches by label (exact) or content substring. Returns list of revoked row ids.
    """
    hint_lower = content_hint.lower()
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            """SELECT id FROM shared_context
               WHERE from_chat_id=? AND to_chat_id=? AND revoked=0
                 AND (lower(label)=? OR lower(content) LIKE ?)""",
            (from_chat_id, to_chat_id, hint_lower, f"%{hint_lower}%"),
        ).fetchall()
        ids = [r[0] for r in rows]
        if ids:
            con.execute(
                f"UPDATE shared_context SET revoked=1 WHERE id IN ({','.join('?' * len(ids))})",
                ids,
            )
    return ids


def db_list_shared(db_path: Path, to_chat_id: int) -> list[dict]:
    """Return all non-revoked shared items for chat_id, newest first."""
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """SELECT sc.id, sc.from_chat_id, sc.content, sc.shared_at, sc.label,
                      COALESCE(ur.full_name, cast(sc.from_chat_id as text)) as from_name
               FROM shared_context sc
               LEFT JOIN user_registry ur ON ur.chat_id = sc.from_chat_id
               WHERE sc.to_chat_id=? AND sc.revoked=0
               ORDER BY sc.from_chat_id, sc.shared_at DESC""",
            (to_chat_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def format_shared_note(items: list[dict]) -> str:
    """Format a list of shared items as a system note for Claude injection."""
    if not items:
        return ""
    lines = []
    for item in items:
        date_str = item["shared_at"][:10]
        lines.append(f"From {item['from_name']} ({date_str}): {item['content']}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
python -m pytest tests/test_shared_context.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/main/shared_context.py tests/test_shared_context.py
git commit -m "feat(shared-context): shared context DB helpers"
```

---

### Task 4: Wire into `init_db` and upsert user on every message

**Files:**
- Modify: `agents/main/agent.py`

- [ ] **Step 1: Import shared_context module in `agent.py`**

Find the imports block at the bottom of the `from agents.main import ...` section (around line 64). Add after the scheduler import:

```python
from agents.main.shared_context import (
    init_shared_context_tables,
    db_upsert_user,
    db_resolve_user,
    db_share_context,
    db_get_unacknowledged_shared,
    db_mark_acknowledged,
    db_revoke_shared,
    db_list_shared,
    format_shared_note,
)
```

- [ ] **Step 2: Call `init_shared_context_tables` in `init_db`**

Find `init_db()` (around line 907). After `init_scheduler_table(DB_PATH)`, add:

```python
def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS sessions (
                chat_id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
    init_scheduler_table(DB_PATH)
    init_shared_context_tables(DB_PATH)   # <-- add this line
```

- [ ] **Step 3: Add `upsert_user` helper function in `agent.py`**

Find the `# ── Allowlist` section (around line 959). Add this function after `db_log`:

```python
def upsert_user(update: Update) -> None:
    """Record the sender in user_registry so they can be resolved by name for sharing."""
    user = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else None
    if user is None or chat_id is None:
        return
    db_upsert_user(DB_PATH, chat_id, user.id, user.username, user.full_name)
```

- [ ] **Step 4: Call `upsert_user` in `handle_message`**

Find `handle_message` (around line 1447). Add the call right after the `is_allowed` check:

```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    if not is_allowed(update):
        return
    upsert_user(update)   # <-- add this line
    ...
```

- [ ] **Step 5: Call `upsert_user` in `handle_photo`, `handle_voice`, `handle_document`**

In each of the three handlers, add `upsert_user(update)` immediately after the `is_allowed` check (same pattern as Step 4).

`handle_photo` (around line 1293):
```python
    if not is_allowed(update):
        return
    upsert_user(update)   # <-- add
```

`handle_voice` (around line 1342):
```python
    if not is_allowed(update):
        return
    upsert_user(update)   # <-- add
```

`handle_document` (around line 1385):
```python
    if not is_allowed(update):
        return
    upsert_user(update)   # <-- add
```

- [ ] **Step 6: Verify the bot starts without errors**

```bash
cd /home/jjay/JjayFiles/claude-command-center
python -c "from agents.main.agent import init_db; init_db(); print('OK')"
```

Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add agents/main/agent.py
git commit -m "feat(shared-context): wire init_db and upsert_user in all handlers"
```

---

### Task 5: Inject unacknowledged shared context into `run_claude`

**Files:**
- Modify: `agents/main/agent.py`

- [ ] **Step 1: Modify `run_claude` to prepend unacknowledged shared context**

Find `run_claude` (around line 1116). After `_current_chat_id.set(chat_id)` and before building `options`, add the injection block:

```python
async def run_claude(prompt: str, chat_id: int, silent: bool = False) -> str:
    _current_chat_id.set(chat_id)

    # Inject any unacknowledged shared context as a system note
    shared = db_get_unacknowledged_shared(DB_PATH, chat_id)
    if shared:
        note = format_shared_note(shared)
        prompt = (
            f"[System: The following context was shared with you by other users]\n"
            f"{note}\n"
            f"---\n\n"
            f"{prompt}"
        )
        db_mark_acknowledged(DB_PATH, chat_id)

    session_id = db_get_session(chat_id)
    system_prompt = build_system_prompt()
    ...
```

- [ ] **Step 2: Verify the bot imports and starts cleanly**

```bash
python -c "from agents.main.agent import run_claude; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add agents/main/agent.py
git commit -m "feat(shared-context): inject unacknowledged shared context into run_claude"
```

---

### Task 6: `/share` command handler

**Files:**
- Modify: `agents/main/agent.py`

- [ ] **Step 1: Implement `cmd_share` handler**

Find the block of `cmd_*` functions (around line 1240). Add this new function before `handle_photo`:

```python
async def cmd_share(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /share @username <content>   or   /share Name: <content>

    Shares content with the resolved user and sends them a push notification.
    """
    if not update.message or not is_allowed(update):
        return
    upsert_user(update)

    chat_id = update.effective_chat.id
    text = update.message.text or ""

    # Strip the /share command prefix
    body = text.removeprefix("/share").strip()
    if not body:
        await update.message.reply_text(
            "Usage: /share @username <content>\n"
            "Example: /share @jay here's what we decided about the API"
        )
        return

    # Parse target: @username or "Name:" prefix
    m = re.match(r"^(@\S+|[\w][\w\s]*?)[:]\s+(.+)$", body, re.DOTALL)
    if not m:
        # Try "@handle content" form (no colon)
        m2 = re.match(r"^(@\S+)\s+(.+)$", body, re.DOTALL)
        if not m2:
            await update.message.reply_text(
                "Usage: /share @username <content>  or  /share Name: <content>"
            )
            return
        target_raw, content = m2.group(1), m2.group(2).strip()
    else:
        target_raw, content = m.group(1), m.group(2).strip()

    try:
        result = db_resolve_user(DB_PATH, target_raw)
    except ValueError as e:
        await update.message.reply_text(f"Could not resolve user: {e}")
        return

    if result is None:
        await update.message.reply_text(
            f"No user found matching '{target_raw}'. "
            "They need to have messaged the bot at least once."
        )
        return

    to_chat_id, to_name = result
    if to_chat_id == chat_id:
        await update.message.reply_text("You can't share context with yourself.")
        return

    from_name = update.effective_user.full_name or str(chat_id)
    db_share_context(DB_PATH, from_chat_id=chat_id, to_chat_id=to_chat_id, content=content)

    # Push notification to recipient
    push_text = f"📤 <b>{html.escape(from_name)}</b> shared something with you:\n{html.escape(content)}"
    try:
        await context.bot.send_message(to_chat_id, push_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.warning("Could not push share notification to %d: %s", to_chat_id, e)

    await update.message.reply_text(f"Shared with {to_name}.")
```

- [ ] **Step 2: Register the handler in `main()`**

Find the `app.add_handler` block (around line 1582). Add:

```python
    app.add_handler(CommandHandler("share", cmd_share))
```

Place it alongside the other command handlers, before the MessageHandler lines.

- [ ] **Step 3: Verify the bot starts cleanly**

```bash
python -c "from agents.main.agent import cmd_share; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add agents/main/agent.py
git commit -m "feat(shared-context): /share command with push notification"
```

---

### Task 7: `/revoke` command handler

**Files:**
- Modify: `agents/main/agent.py`

- [ ] **Step 1: Implement `cmd_revoke` handler**

Add this function right after `cmd_share`:

```python
async def cmd_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /revoke @username <content or label>

    Soft-deletes matching shared context and notifies recipient.
    """
    if not update.message or not is_allowed(update):
        return
    upsert_user(update)

    chat_id = update.effective_chat.id
    text = update.message.text or ""
    body = text.removeprefix("/revoke").strip()

    if not body:
        await update.message.reply_text(
            "Usage: /revoke @username <content hint>\n"
            "Example: /revoke @jay API decision"
        )
        return

    m = re.match(r"^(@\S+|[\w][\w\s]*?)[:\s]\s*(.+)$", body, re.DOTALL)
    if not m:
        await update.message.reply_text(
            "Usage: /revoke @username <content hint>"
        )
        return

    target_raw, content_hint = m.group(1), m.group(2).strip()

    try:
        result = db_resolve_user(DB_PATH, target_raw)
    except ValueError as e:
        await update.message.reply_text(f"Could not resolve user: {e}")
        return

    if result is None:
        await update.message.reply_text(f"No user found matching '{target_raw}'.")
        return

    to_chat_id, to_name = result
    from_name = update.effective_user.full_name or str(chat_id)

    revoked_ids = db_revoke_shared(
        DB_PATH, from_chat_id=chat_id, to_chat_id=to_chat_id, content_hint=content_hint
    )

    if not revoked_ids:
        await update.message.reply_text(
            f"No matching shared context found for '{content_hint}'."
        )
        return

    # Notify recipient
    snippet = content_hint[:80]
    notif = (
        f"🚫 <b>{html.escape(from_name)}</b> revoked shared context: "
        f"<i>{html.escape(snippet)}</i>"
    )
    try:
        await context.bot.send_message(to_chat_id, notif, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.warning("Could not send revoke notification to %d: %s", to_chat_id, e)

    await update.message.reply_text(
        f"Revoked {len(revoked_ids)} item(s) shared with {to_name}."
    )
```

- [ ] **Step 2: Register the handler in `main()`**

```python
    app.add_handler(CommandHandler("revoke", cmd_revoke))
```

- [ ] **Step 3: Verify**

```bash
python -c "from agents.main.agent import cmd_revoke; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add agents/main/agent.py
git commit -m "feat(shared-context): /revoke command"
```

---

### Task 8: Pull handler (on-demand retrieval)

**Files:**
- Modify: `agents/main/agent.py`

- [ ] **Step 1: Add `_is_pull_request` detector and `_handle_pull` function**

Add both functions before `handle_message` (around line 1447):

```python
_PULL_PATTERNS = [
    r"shared with me",
    r"what did .{1,30} share",
    r"show shared",
    r"shared context",
    r"anything shared",
]
_PULL_RE = re.compile("|".join(_PULL_PATTERNS), re.IGNORECASE)


def _is_pull_request(text: str) -> bool:
    return bool(_PULL_RE.search(text))


async def _handle_pull(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display all shared context for this user and inject it into their session."""
    chat_id = update.effective_chat.id
    items = db_list_shared(DB_PATH, to_chat_id=chat_id)

    if not items:
        await update.message.reply_text("Nothing has been shared with you yet.")
        return

    # Group by sender
    grouped: dict[str, list[dict]] = {}
    for item in items:
        grouped.setdefault(item["from_name"], []).append(item)

    lines = ["📥 <b>Shared with you:</b>\n"]
    for from_name, sender_items in grouped.items():
        lines.append(f"<b>From {html.escape(from_name)}</b> ({len(sender_items)} item(s))")
        for item in sender_items:
            date_str = item["shared_at"][:10]
            lines.append(f"  • <i>({date_str})</i> {html.escape(item['content'])}")
        lines.append("")

    formatted = "\n".join(lines).strip()
    await update.message.reply_text(formatted, parse_mode=ParseMode.HTML)

    # Inject into Claude session so the AI knows about it
    note = format_shared_note(items)
    inject_prompt = (
        f"[System: The user just pulled their shared context. Inject into your awareness.]\n"
        f"{note}\n"
        f"---\n\n"
        f"The user asked to see their shared context. I've shown them the list above. "
        f"Acknowledge briefly."
    )
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    typing_task = asyncio.create_task(_keep_typing(context, chat_id))
    try:
        reply = await run_claude(inject_prompt, chat_id)
    finally:
        typing_task.cancel()

    if reply and reply != "(no response)":
        for chunk in chunk_text(md_to_html(reply)):
            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
            except Exception:
                await update.message.reply_text(chunk)
```

- [ ] **Step 2: Call `_handle_pull` in `handle_message` before `run_claude`**

In `handle_message`, add pull detection right after `_flush_mgr.record(chat_id, user_text)`:

```python
    db_log(chat_id, "user", user_text)
    _flush_mgr.record(chat_id, user_text)

    # Handle pull requests before passing to Claude
    if _is_pull_request(user_text):
        await _handle_pull(update, context)
        return

    # Fire flush turn if we're near the context limit (transparent to user)
    await maybe_flush(chat_id)
    ...
```

- [ ] **Step 3: Add `/shared` command**

Add a one-liner command function:

```python
async def cmd_shared(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Alias for pulling shared context via command."""
    if not update.message or not is_allowed(update):
        return
    upsert_user(update)
    await _handle_pull(update, context)
```

Register in `main()`:

```python
    app.add_handler(CommandHandler("shared", cmd_shared))
```

- [ ] **Step 4: Verify**

```bash
python -c "from agents.main.agent import _is_pull_request; assert _is_pull_request('what did Jay share with me'); print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add agents/main/agent.py
git commit -m "feat(shared-context): pull handler — /shared command + keyword detection"
```

---

### Task 9: Restart and smoke test

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 2: Restart the bot**

```bash
systemctl restart main-agent   # or however the service is managed
```

- [ ] **Step 3: Smoke test share flow**

From your Telegram account:
1. Send `/share @otherusername test: this is shared context`
2. Verify you receive: `Shared with [name].`
3. On the other account, verify push notification arrives

- [ ] **Step 4: Smoke test pull flow**

From the recipient account:
1. Send `what did [name] share with me?`
2. Verify the list appears with the shared item

- [ ] **Step 5: Smoke test revoke**

From your account:
1. Send `/revoke @otherusername test`
2. Verify the recipient gets a revocation notification
3. On recipient: send `show shared context` — item should be gone

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat(shared-context): complete — share, push, pull, revoke, session injection"
```
