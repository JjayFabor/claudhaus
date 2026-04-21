# dashboard/data.py
"""
dashboard/data.py — Read-only data queries for the dashboard.
All functions are synchronous (called from FastAPI with run_in_executor if needed).
"""
import sqlite3
import time
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "memory.db"
WORKSPACE = ROOT / "workspaces" / "main"
SHARED_DIR = ROOT / "agents" / "shared"
SKILLS_DIR = ROOT / "agents" / "main" / "skills"
LOG_PATH = ROOT / "logs" / "main.log"

_start_time = time.time()  # dashboard process start (proxy for uptime display)


def get_stats() -> dict:
    """Single dict with all stat-card values."""
    stats = {
        "session_count": 0,
        "task_count": 0,
        "skill_count": 0,
        "memory_kb": 0,
        "connector_count": 0,
        "dreams_count": 0,
        "daily_notes": 0,
        "uptime": _uptime_str(),
    }
    try:
        with sqlite3.connect(DB_PATH) as con:
            stats["session_count"] = con.execute(
                "SELECT COUNT(*) FROM sessions"
            ).fetchone()[0]
            stats["task_count"] = con.execute(
                "SELECT COUNT(*) FROM scheduled_tasks WHERE enabled=1"
            ).fetchone()[0]
    except Exception:
        pass

    memory_md = WORKSPACE / "MEMORY.md"
    if memory_md.exists():
        stats["memory_kb"] = round(memory_md.stat().st_size / 1024, 1)

    dreams = WORKSPACE / "DREAMS.md"
    if dreams.exists():
        stats["dreams_count"] = sum(
            1 for l in dreams.read_text(encoding="utf-8").splitlines()
            if l.strip().startswith("-")
        )

    daily_dir = WORKSPACE / "memory"
    if daily_dir.exists():
        stats["daily_notes"] = len(list(daily_dir.glob("*.md")))

    SKILLS_DIR.mkdir(exist_ok=True)
    stats["skill_count"] = len(list(SKILLS_DIR.glob("*.md")))

    try:
        import sys; sys.path.insert(0, str(ROOT))
        from agents.main.connectors import get_installed_connectors
        stats["connector_count"] = len(get_installed_connectors())
    except Exception:
        pass

    return stats


def get_recent_activity(limit: int = 15) -> list[dict]:
    """Last N conversation turns from the DB."""
    rows = []
    try:
        with sqlite3.connect(DB_PATH) as con:
            rows = con.execute(
                "SELECT chat_id, role, content, created_at FROM conversations "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    except Exception:
        pass
    return [
        {
            "chat_id": r[0],
            "role": r[1],
            "content": r[2][:160] + ("…" if len(r[2]) > 160 else ""),
            "created_at": r[3],
        }
        for r in rows
    ]


def get_scheduled_tasks() -> list[dict]:
    rows = []
    try:
        with sqlite3.connect(DB_PATH) as con:
            rows = con.execute(
                "SELECT id, chat_id, task_prompt, schedule_str, enabled, created_at "
                "FROM scheduled_tasks ORDER BY id DESC"
            ).fetchall()
    except Exception:
        pass
    return [
        {
            "id": r[0],
            "chat_id": r[1],
            "task_prompt": r[2][:120] + ("…" if len(r[2]) > 120 else ""),
            "schedule_str": r[3],
            "enabled": bool(r[4]),
            "created_at": r[5],
        }
        for r in rows
    ]


def get_skills() -> list[dict]:
    SKILLS_DIR.mkdir(exist_ok=True)
    result = []
    for f in sorted(SKILLS_DIR.glob("*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        preview = next((l.strip() for l in lines if l.strip()), "")[:100]
        result.append({"name": f.stem, "preview": preview})
    return result


def get_connectors() -> list[dict]:
    try:
        import sys; sys.path.insert(0, str(ROOT))
        from agents.main.connectors import get_installed_connectors, REGISTRY
        installed = set(get_installed_connectors())
        return [
            {"name": name, "installed": name in installed,
             "description": info.get("description", "")}
            for name, info in REGISTRY.items()
        ]
    except Exception:
        return []


def _uptime_str() -> str:
    secs = int(time.time() - _start_time)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"
