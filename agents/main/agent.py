"""
agents/main/agent.py — Main bot runner.

One Telegram bot, one Claude agent, full session persistence + memory.
"""

import asyncio
import html
import logging
import os
import re
import sqlite3
import sys
from datetime import date
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import claude_agent_sdk as sdk

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_DIR = Path(__file__).resolve().parent
SHARED_DIR = ROOT / "agents" / "shared"
WORKSPACE = ROOT / "workspaces" / "main"
DB_PATH = ROOT / "data" / "memory.db"
LOG_PATH = ROOT / "logs" / "main.log"

sys.path.insert(0, str(ROOT))

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
_handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[_handler, logging.StreamHandler()],
)
logger = logging.getLogger("main")

load_dotenv(ROOT / ".env")

# ── Config ─────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN_MAIN"]

_raw_user_ids = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS: set[int] = {
    int(x.strip()) for x in _raw_user_ids.split(",") if x.strip()
}

_raw_chat_ids = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "")
ALLOWED_CHAT_IDS: set[int] = {
    int(x.strip()) for x in _raw_chat_ids.split(",") if x.strip()
}

TG_MAX_CHARS = 4000


# ── Memory index (initialised in main()) ──────────────────────────────────────
from memory.index import MemoryIndex
from memory.search import search as _mem_search
from memory.flush import FlushManager

_mem_index: Optional[MemoryIndex] = None
_flush_mgr = FlushManager()


# ── In-process memory tools ───────────────────────────────────────────────────

@sdk.tool(
    name="memory_search",
    description="Search long-term memory and daily notes for past facts, preferences, and decisions. Call this before answering questions about past work or preferences.",
    input_schema={"query": str, "limit": int},
)
async def tool_memory_search(args: dict) -> dict:
    query = args.get("query", "")
    limit = int(args.get("limit", 5))
    if _mem_index is None:
        return {"content": [{"type": "text", "text": "Memory index not initialised."}]}
    result = _mem_search(_mem_index, query, limit=limit)
    return {"content": [{"type": "text", "text": result}]}


@sdk.tool(
    name="memory_write_long_term",
    description="Append a durable fact, preference, or decision to MEMORY.md. Use for things that should be remembered across all future sessions.",
    input_schema={"content": str},
)
async def tool_memory_write_long_term(args: dict) -> dict:
    content = args.get("content", "").strip()
    if not content:
        return {"content": [{"type": "text", "text": "Error: content is empty."}], "is_error": True}
    memory_md = WORKSPACE / "MEMORY.md"
    memory_md.parent.mkdir(parents=True, exist_ok=True)
    with memory_md.open("a", encoding="utf-8") as f:
        f.write(f"\n{content}\n")
    if _mem_index:
        _mem_index.reindex_file(memory_md)
    logger.info("memory_write_long_term: wrote %d chars", len(content))
    return {"content": [{"type": "text", "text": f"Written to MEMORY.md: {content[:80]}..."}]}


@sdk.tool(
    name="memory_write_daily",
    description="Append an observation or context note to today's daily memory file (memory/YYYY-MM-DD.md). Use for short-term context that may be useful for the next few days.",
    input_schema={"content": str},
)
async def tool_memory_write_daily(args: dict) -> dict:
    content = args.get("content", "").strip()
    if not content:
        return {"content": [{"type": "text", "text": "Error: content is empty."}], "is_error": True}
    today = date.today().isoformat()
    daily_file = WORKSPACE / "memory" / f"{today}.md"
    daily_file.parent.mkdir(parents=True, exist_ok=True)
    if not daily_file.exists():
        daily_file.write_text(f"# {today}\n\n", encoding="utf-8")
    with daily_file.open("a", encoding="utf-8") as f:
        f.write(f"- {content}\n")
    if _mem_index:
        _mem_index.reindex_file(daily_file)
    logger.info("memory_write_daily: wrote to %s", daily_file.name)
    return {"content": [{"type": "text", "text": f"Written to {daily_file.name}: {content[:80]}"}]}


@sdk.tool(
    name="memory_read_file",
    description="Read a memory file by name. Valid values: 'MEMORY.md', 'DREAMS.md', or a date like '2026-04-21' to read that day's notes.",
    input_schema={"path": str},
)
async def tool_memory_read_file(args: dict) -> dict:
    path_arg = args.get("path", "").strip()
    if not path_arg:
        return {"content": [{"type": "text", "text": "Error: path is required."}], "is_error": True}

    if path_arg in ("MEMORY.md", "DREAMS.md"):
        target = WORKSPACE / path_arg
    elif re.match(r"^\d{4}-\d{2}-\d{2}$", path_arg):
        target = WORKSPACE / "memory" / f"{path_arg}.md"
    else:
        return {"content": [{"type": "text", "text": f"Invalid path: {path_arg!r}. Use 'MEMORY.md', 'DREAMS.md', or a YYYY-MM-DD date."}], "is_error": True}

    if not target.exists():
        return {"content": [{"type": "text", "text": f"{path_arg} does not exist yet."}]}
    text = target.read_text(encoding="utf-8")
    return {"content": [{"type": "text", "text": text or "(empty)"}]}


# ── MCP server bundling all memory tools ──────────────────────────────────────
_memory_mcp = sdk.create_sdk_mcp_server(
    name="memory",
    tools=[tool_memory_search, tool_memory_write_long_term, tool_memory_write_daily, tool_memory_read_file],
)


# ── Instruction loader ─────────────────────────────────────────────────────────
def load_instructions(agent_dir: Path) -> Path:
    """Personal override takes precedence if it exists, otherwise fall back to generic."""
    personal = agent_dir / "CLAUDE.personal.md"
    generic = agent_dir / "CLAUDE.md"
    if personal.exists():
        logger.info("Using personal instructions: %s", personal)
        return personal
    logger.info("Using generic instructions: %s", generic)
    return generic


def build_system_prompt() -> str:
    """
    Injection order:
      1. USER_PROFILE.md
      2. BUSINESS_CONTEXT.md
      3. HOUSE_RULES.md
      4. MEMORY.md  (long-term memory)
      5. memory/today.md  (today's notes)
      6. memory/yesterday.md  (yesterday's notes)
      7. CLAUDE.personal.md or CLAUDE.md
    """
    parts: list[str] = []

    for soul_file in [
        SHARED_DIR / "USER_PROFILE.md",
        SHARED_DIR / "BUSINESS_CONTEXT.md",
        SHARED_DIR / "HOUSE_RULES.md",
    ]:
        if soul_file.exists() and soul_file.stat().st_size > 0:
            parts.append(soul_file.read_text().strip())

    # Long-term memory
    memory_md = WORKSPACE / "MEMORY.md"
    if memory_md.exists() and memory_md.stat().st_size > 0:
        parts.append("## Long-term Memory\n\n" + memory_md.read_text().strip())

    # Daily notes: today and yesterday
    today = date.today()
    for delta, label in [(0, "Today"), (1, "Yesterday")]:
        d = today.replace(day=today.day - delta) if delta == 0 else \
            date.fromordinal(today.toordinal() - delta)
        daily = WORKSPACE / "memory" / f"{d.isoformat()}.md"
        if daily.exists() and daily.stat().st_size > 0:
            parts.append(f"## Daily Notes ({label}, {d.isoformat()})\n\n" + daily.read_text().strip())

    parts.append(load_instructions(AGENT_DIR).read_text().strip())
    return "\n\n---\n\n".join(parts)


# ── Database ───────────────────────────────────────────────────────────────────
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


def db_get_session(chat_id: int) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT session_id FROM sessions WHERE chat_id = ?", (chat_id,)
        ).fetchone()
    return row[0] if row else None


def db_save_session(chat_id: int, session_id: str) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """INSERT INTO sessions (chat_id, session_id, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(chat_id) DO UPDATE SET session_id=excluded.session_id,
               updated_at=excluded.updated_at""",
            (chat_id, session_id),
        )


def db_delete_session(chat_id: int) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM sessions WHERE chat_id = ?", (chat_id,))


def db_log(chat_id: int, role: str, content: str) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO conversations (chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, role, content),
        )


# ── Allowlist ──────────────────────────────────────────────────────────────────
def is_allowed(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    if user_id is None or chat_id is None:
        return False
    is_dm = chat_id == user_id
    if is_dm:
        return user_id in ALLOWED_USER_IDS
    return user_id in ALLOWED_USER_IDS and chat_id in ALLOWED_CHAT_IDS


# ── Markdown → Telegram HTML ──────────────────────────────────────────────────
def md_to_html(text: str) -> str:
    result = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            lang = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(html.escape(lines[i]))
                i += 1
            code_body = "\n".join(code_lines)
            if lang:
                result.append(f"<pre><code class='language-{html.escape(lang)}'>{code_body}</code></pre>")
            else:
                result.append(f"<pre>{code_body}</pre>")
            i += 1
            continue

        if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|[-| :]+\|\s*$", lines[i + 1]):
            table_lines = []
            while i < len(lines) and "|" in lines[i]:
                if not re.match(r"^\s*\|[-| :]+\|\s*$", lines[i]):
                    cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    table_lines.append("  ".join(cells))
                i += 1
            result.append("<pre>" + html.escape("\n".join(table_lines)) + "</pre>")
            continue

        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            result.append("<b>" + _inline(m.group(2)) + "</b>")
            i += 1
            continue

        if re.match(r"^[-*_]{3,}\s*$", line):
            result.append("─────────────────────")
            i += 1
            continue

        result.append(_inline(line))
        i += 1

    return "\n".join(result)


def _inline(text: str) -> str:
    parts = re.split(r"(`[^`]+`)", text)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            out.append("<code>" + html.escape(part[1:-1]) + "</code>")
        else:
            p = html.escape(part)
            p = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", p)
            p = re.sub(r"__(.+?)__", r"<b>\1</b>", p)
            p = re.sub(r"\*(.+?)\*", r"<i>\1</i>", p)
            p = re.sub(r"_(.+?)_", r"<i>\1</i>", p)
            p = re.sub(r"~~(.+?)~~", r"<s>\1</s>", p)
            p = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', p)
            out.append(p)
    return "".join(out)


# ── Message chunker ────────────────────────────────────────────────────────────
def chunk_text(text: str, max_len: int = TG_MAX_CHARS) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    pos = 0
    while pos < len(text):
        remaining = text[pos:]
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        slice_ = text[pos : pos + max_len]
        cut = slice_.rfind("\n\n")
        if cut == -1:
            cut = slice_.rfind("\n")
        if cut == -1:
            cut = slice_.rfind(" ")
        if cut <= 0:
            cut = max_len
        else:
            cut += 1
        chunks.append(text[pos : pos + cut].strip())
        pos += cut
    return [c for c in chunks if c]


# ── Claude query ───────────────────────────────────────────────────────────────
async def run_claude(prompt: str, chat_id: int, silent: bool = False) -> str:
    """
    Run one Claude turn. Returns the final text reply.
    silent=True suppresses NO_REPLY responses (used for flush turns).
    """
    session_id = db_get_session(chat_id)
    system_prompt = build_system_prompt()

    options = sdk.ClaudeAgentOptions(
        system_prompt=system_prompt,
        cwd=str(WORKSPACE),
        resume=session_id,
        permission_mode="bypassPermissions",
        setting_sources=["user"],
        mcp_servers={"memory": _memory_mcp},
        allowed_tools=[
            "Bash", "Read", "Write", "Edit", "Glob", "Grep",
            "WebSearch", "WebFetch", "TodoWrite",
            "memory_search", "memory_write_long_term",
            "memory_write_daily", "memory_read_file",
        ],
    )

    reply_parts: list[str] = []
    new_session_id: Optional[str] = None

    try:
        async for event in sdk.query(prompt=prompt, options=options):
            if isinstance(event, sdk.AssistantMessage):
                for block in event.content:
                    if isinstance(block, sdk.TextBlock):
                        reply_parts.append(block.text)
                if event.session_id:
                    new_session_id = event.session_id
            elif isinstance(event, sdk.ResultMessage):
                if event.session_id:
                    new_session_id = event.session_id
    except sdk.CLINotFoundError:
        logger.error("claude CLI not found")
        return "Error: claude CLI not found. Make sure `claude` is installed and authenticated."
    except sdk.CLIConnectionError as e:
        logger.error("Claude connection error: %s", e)
        db_delete_session(chat_id)
        return "Connection error — session reset. Please try again."
    except Exception as e:
        logger.exception("Unexpected error from Claude: %s", e)
        return f"Error: {e}"

    if new_session_id:
        db_save_session(chat_id, new_session_id)

    reply = "".join(reply_parts).strip()

    if silent and reply == "NO_REPLY":
        return ""

    return reply or "(no response)"


# ── Pre-compaction flush ───────────────────────────────────────────────────────
async def maybe_flush(chat_id: int) -> None:
    """Fire a silent flush turn if the session is approaching context limits."""
    if not _flush_mgr.needs_flush(chat_id):
        return
    logger.info("Flushing memory for chat %d before compaction", chat_id)
    today = date.today().isoformat()
    flush_prompt = _flush_mgr.flush_prompt(today)
    reply = await run_claude(flush_prompt, chat_id, silent=True)
    _flush_mgr.reset(chat_id)
    if reply:
        logger.info("Flush produced output: %s...", reply[:60])


# ── Handlers ───────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    await update.message.reply_text("Main is online. Send me anything.")


async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    user = update.effective_user
    chat = update.effective_chat
    await update.message.reply_text(
        f"<b>User ID:</b> <code>{user.id}</code>\n"
        f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
        f"<b>Username:</b> @{user.username or '—'}\n"
        f"<b>Name:</b> {user.full_name}",
        parse_mode=ParseMode.HTML,
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    chat_id = update.effective_chat.id
    db_delete_session(chat_id)
    _flush_mgr.reset(chat_id)
    await update.message.reply_text("Session reset. Next message starts a fresh conversation.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    if not is_allowed(update):
        return

    chat_id = update.effective_chat.id
    user_text = update.message.text
    db_log(chat_id, "user", user_text)
    _flush_mgr.record(chat_id, user_text)

    # Fire flush turn if we're near the context limit (transparent to user)
    await maybe_flush(chat_id)

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    typing_task = asyncio.create_task(_keep_typing(context, chat_id))

    try:
        reply = await run_claude(user_text, chat_id)
    finally:
        typing_task.cancel()

    db_log(chat_id, "assistant", reply)
    _flush_mgr.record(chat_id, reply)

    formatted = md_to_html(reply)
    for chunk in chunk_text(formatted):
        try:
            await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
        except Exception:
            await update.message.reply_text(chunk)


async def _keep_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    try:
        while True:
            await asyncio.sleep(4)
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except asyncio.CancelledError:
        pass


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception in handler", exc_info=context.error)


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    global _mem_index

    init_db()
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "memory").mkdir(exist_ok=True)
    (WORKSPACE / "sessions").mkdir(exist_ok=True)

    # Seed memory files so they always exist for appending
    for seed in [WORKSPACE / "MEMORY.md", WORKSPACE / "DREAMS.md"]:
        seed.touch(exist_ok=True)
    today_note = WORKSPACE / "memory" / f"{date.today().isoformat()}.md"
    if not today_note.exists():
        today_note.write_text(f"# {date.today().isoformat()}\n\n", encoding="utf-8")

    # Build memory index and start file watcher
    _mem_index = MemoryIndex(WORKSPACE)
    _mem_index.build()
    _mem_index.start_watcher()

    instruction_file = load_instructions(AGENT_DIR)
    logger.info("Starting Main — instructions: %s", instruction_file.name)
    logger.info("Allowed user IDs: %s", ALLOWED_USER_IDS)
    logger.info("Memory index ready — watcher running")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("whoami", cmd_whoami))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Polling for messages...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
