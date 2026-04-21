# Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A read-only live dashboard for claudhaus — bot status, sessions, memory, tasks, skills, connectors — auto-refreshing via HTMX partials.

**Architecture:** FastAPI app with Jinja2 templates. A shared `dashboard/data.py` module queries SQLite and reads disk. HTMX polls three partial endpoints every 30 s so the page updates without a full reload. Pure handcrafted CSS — no framework. Color theme defined as CSS custom properties and reused site-wide later.

**Tech Stack:** FastAPI, Jinja2, HTMX (CDN), pure CSS. No JavaScript beyond HTMX.

---

## Color System — "Void Indigo"

The brand palette. Defined once in `style.css`, referenced everywhere.

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#07071a` | Page background |
| `--surface` | `#0d0d26` | Header, footer |
| `--card` | `#12122e` | Card backgrounds |
| `--border` | `#1c1c45` | Card borders, dividers |
| `--primary` | `#7b6ef6` | Indigo — accents, links, active |
| `--primary-dim` | `rgba(123,110,246,.12)` | Card hover glow, stat icons |
| `--secondary` | `#06d6a0` | Mint — online indicator, healthy |
| `--danger` | `#ff4d6d` | Errors, offline |
| `--warning` | `#ffd166` | Warnings, pending |
| `--text` | `#e8e8f8` | Primary text |
| `--muted` | `#5a5a7a` | Labels, timestamps, subtitles |

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `dashboard/data.py` | Create | All data queries — DB, disk, skills, connectors |
| `dashboard/app.py` | Rewrite | FastAPI routes: `/`, `/partials/stats`, `/partials/activity`, `/partials/tasks` |
| `dashboard/templates/base.html` | Create | Base template — head, nav header, HTMX wiring |
| `dashboard/templates/index.html` | Create | Full page — stat cards + panels layout |
| `dashboard/templates/_stats.html` | Create | HTMX partial — 5 stat cards |
| `dashboard/templates/_activity.html` | Create | HTMX partial — last 15 messages |
| `dashboard/templates/_tasks.html` | Create | HTMX partial — scheduled tasks list |
| `dashboard/static/style.css` | Create | Full CSS — color system, layout, cards, typography |
| `systemd/claude-dashboard.service` | Modify | Fix: EnvironmentFile, remove bad ANTHROPIC_API_KEY |
| `requirements.txt` | Modify | Add `jinja2>=3.1,<4` |
| `scripts/install-systemd.sh` | Modify | Add dashboard service to install list |

---

## Task 1: Data layer

**Files:**
- Create: `dashboard/data.py`

- [ ] **Step 1: Write the data module**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/data.py
git commit -m "feat(dashboard): data layer — stats, activity, tasks, skills, connectors"
```

---

## Task 2: FastAPI app

**Files:**
- Rewrite: `dashboard/app.py`

- [ ] **Step 1: Write the app**

```python
# dashboard/app.py
"""
dashboard/app.py — claudhaus dashboard.
Run: uvicorn dashboard.app:app --host 127.0.0.1 --port 8000
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from dashboard.data import (
    get_stats, get_recent_activity, get_scheduled_tasks,
    get_skills, get_connectors,
)

app = FastAPI(title="claudhaus dashboard", docs_url=None, redoc_url=None)

_HERE = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")
templates = Jinja2Templates(directory=str(_HERE / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "stats": get_stats(),
        "activity": get_recent_activity(),
        "tasks": get_scheduled_tasks(),
        "skills": get_skills(),
        "connectors": get_connectors(),
    })


@app.get("/partials/stats", response_class=HTMLResponse)
async def partial_stats(request: Request):
    return templates.TemplateResponse("_stats.html", {
        "request": request,
        "stats": get_stats(),
    })


@app.get("/partials/activity", response_class=HTMLResponse)
async def partial_activity(request: Request):
    return templates.TemplateResponse("_activity.html", {
        "request": request,
        "activity": get_recent_activity(),
    })


@app.get("/partials/tasks", response_class=HTMLResponse)
async def partial_tasks(request: Request):
    return templates.TemplateResponse("_tasks.html", {
        "request": request,
        "tasks": get_scheduled_tasks(),
    })
```

- [ ] **Step 2: Create static and templates directories**

```bash
mkdir -p dashboard/static dashboard/templates
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/app.py
git commit -m "feat(dashboard): FastAPI app with HTMX partial endpoints"
```

---

## Task 3: CSS — Void Indigo theme

**Files:**
- Create: `dashboard/static/style.css`

- [ ] **Step 1: Write the stylesheet**

```css
/* dashboard/static/style.css — claudhaus · Void Indigo theme */

/* ── Tokens ─────────────────────────────────────────────────────────────── */
:root {
  --bg:           #07071a;
  --surface:      #0d0d26;
  --card:         #12122e;
  --border:       #1c1c45;
  --primary:      #7b6ef6;
  --primary-dim:  rgba(123,110,246,.10);
  --primary-glow: rgba(123,110,246,.18);
  --secondary:    #06d6a0;
  --danger:       #ff4d6d;
  --warning:      #ffd166;
  --text:         #e8e8f8;
  --muted:        #5a5a7a;
  --font:         'Inter', system-ui, -apple-system, sans-serif;
  --mono:         'JetBrains Mono', 'Fira Code', monospace;
  --radius:       10px;
  --radius-sm:    6px;
  --shadow:       0 4px 24px rgba(0,0,0,.45);
  --transition:   160ms ease;
}

/* ── Reset ──────────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 15px; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font);
  line-height: 1.6;
  min-height: 100vh;
}

/* ── Header ─────────────────────────────────────────────────────────────── */
.header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 0 2rem;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-brand {
  display: flex;
  align-items: center;
  gap: .6rem;
  font-weight: 700;
  font-size: 1rem;
  letter-spacing: -.01em;
  color: var(--text);
  text-decoration: none;
}
.header-brand svg { color: var(--primary); }
.header-meta {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  font-size: .8rem;
  color: var(--muted);
}
.status-dot {
  display: inline-flex;
  align-items: center;
  gap: .4rem;
  color: var(--secondary);
  font-weight: 500;
}
.status-dot::before {
  content: '';
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--secondary);
  box-shadow: 0 0 6px var(--secondary);
  animation: pulse 2.4s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: .4; }
}

/* ── Layout ─────────────────────────────────────────────────────────────── */
.main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1.5rem 4rem;
}
.section-title {
  font-size: .7rem;
  font-weight: 600;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: .85rem;
}

/* ── Stat cards ─────────────────────────────────────────────────────────── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: .85rem;
  margin-bottom: 2rem;
}
.stat-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.15rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: .35rem;
  transition: border-color var(--transition), box-shadow var(--transition);
}
.stat-card:hover {
  border-color: var(--primary);
  box-shadow: 0 0 0 1px var(--primary-dim), var(--shadow);
}
.stat-icon {
  width: 30px; height: 30px;
  border-radius: var(--radius-sm);
  background: var(--primary-dim);
  display: flex; align-items: center; justify-content: center;
  color: var(--primary);
  margin-bottom: .2rem;
}
.stat-value {
  font-size: 1.7rem;
  font-weight: 700;
  letter-spacing: -.02em;
  line-height: 1;
  color: var(--text);
}
.stat-label {
  font-size: .75rem;
  color: var(--muted);
  font-weight: 500;
}

/* ── Two-column panels ──────────────────────────────────────────────────── */
.panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}
@media (max-width: 760px) { .panels { grid-template-columns: 1fr; } }

/* ── Panel card ─────────────────────────────────────────────────────────── */
.panel {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}
.panel-header {
  padding: .85rem 1.15rem;
  border-bottom: 1px solid var(--border);
  font-size: .7rem;
  font-weight: 600;
  letter-spacing: .09em;
  text-transform: uppercase;
  color: var(--muted);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.panel-count {
  background: var(--primary-dim);
  color: var(--primary);
  font-size: .68rem;
  font-weight: 700;
  padding: .15rem .5rem;
  border-radius: 20px;
  letter-spacing: 0;
  text-transform: none;
}
.panel-body {
  padding: 0;
  max-height: 340px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}
.panel-empty {
  padding: 2rem;
  text-align: center;
  color: var(--muted);
  font-size: .85rem;
}

/* ── Activity rows ──────────────────────────────────────────────────────── */
.activity-row {
  display: flex;
  align-items: flex-start;
  gap: .75rem;
  padding: .7rem 1.15rem;
  border-bottom: 1px solid var(--border);
  transition: background var(--transition);
}
.activity-row:last-child { border-bottom: none; }
.activity-row:hover { background: var(--primary-dim); }
.role-badge {
  flex-shrink: 0;
  font-size: .65rem;
  font-weight: 700;
  padding: .2rem .45rem;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: .06em;
  margin-top: .15rem;
}
.role-badge.user      { background: rgba(123,110,246,.2); color: var(--primary); }
.role-badge.assistant { background: rgba(6,214,160,.15);  color: var(--secondary); }
.activity-content { flex: 1; min-width: 0; }
.activity-text {
  font-size: .85rem;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.activity-meta {
  font-size: .72rem;
  color: var(--muted);
  margin-top: .1rem;
  font-family: var(--mono);
}

/* ── Task rows ──────────────────────────────────────────────────────────── */
.task-row {
  display: flex;
  align-items: center;
  gap: .75rem;
  padding: .7rem 1.15rem;
  border-bottom: 1px solid var(--border);
  transition: background var(--transition);
}
.task-row:last-child { border-bottom: none; }
.task-row:hover { background: var(--primary-dim); }
.task-id {
  font-family: var(--mono);
  font-size: .72rem;
  color: var(--muted);
  flex-shrink: 0;
  width: 28px;
}
.task-info { flex: 1; min-width: 0; }
.task-prompt {
  font-size: .85rem;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.task-schedule {
  font-size: .72rem;
  color: var(--muted);
  font-family: var(--mono);
  margin-top: .1rem;
}
.task-status {
  flex-shrink: 0;
  width: 8px; height: 8px;
  border-radius: 50%;
}
.task-status.enabled  { background: var(--secondary); box-shadow: 0 0 5px var(--secondary); }
.task-status.disabled { background: var(--muted); }

/* ── Skills list ─────────────────────────────────────────────────────────── */
.skill-row {
  display: flex;
  align-items: center;
  gap: .75rem;
  padding: .65rem 1.15rem;
  border-bottom: 1px solid var(--border);
  transition: background var(--transition);
}
.skill-row:last-child { border-bottom: none; }
.skill-row:hover { background: var(--primary-dim); }
.skill-name {
  font-family: var(--mono);
  font-size: .8rem;
  color: var(--primary);
  flex-shrink: 0;
  min-width: 140px;
}
.skill-preview {
  font-size: .8rem;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Connector list ──────────────────────────────────────────────────────── */
.connector-row {
  display: flex;
  align-items: center;
  gap: .75rem;
  padding: .65rem 1.15rem;
  border-bottom: 1px solid var(--border);
  transition: background var(--transition);
}
.connector-row:last-child { border-bottom: none; }
.connector-row:hover { background: var(--primary-dim); }
.connector-name {
  font-weight: 600;
  font-size: .85rem;
  flex-shrink: 0;
  width: 110px;
  text-transform: capitalize;
}
.connector-name.installed   { color: var(--text); }
.connector-name.uninstalled { color: var(--muted); }
.connector-desc {
  font-size: .78rem;
  color: var(--muted);
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.connector-badge {
  flex-shrink: 0;
  font-size: .65rem;
  font-weight: 700;
  padding: .18rem .5rem;
  border-radius: 4px;
  letter-spacing: .04em;
}
.connector-badge.on  { background: rgba(6,214,160,.15); color: var(--secondary); }
.connector-badge.off { background: rgba(90,90,122,.12); color: var(--muted); }

/* ── Full-width panel modifier ───────────────────────────────────────────── */
.panel-full { grid-column: 1 / -1; }

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/static/style.css
git commit -m "feat(dashboard): Void Indigo CSS theme"
```

---

## Task 4: Base template + main page

**Files:**
- Create: `dashboard/templates/base.html`
- Create: `dashboard/templates/index.html`

- [ ] **Step 1: Write base.html**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>claudhaus</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css">
  <script src="https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js" defer></script>
</head>
<body>

<header class="header">
  <a href="/" class="header-brand">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>
    claudhaus
  </a>
  <div class="header-meta">
    <span class="status-dot">online</span>
    <span>uptime {{ stats.uptime }}</span>
  </div>
</header>

<main class="main">
  {% block content %}{% endblock %}
</main>

</body>
</html>
```

- [ ] **Step 2: Write index.html**

```html
{% extends "base.html" %}
{% block content %}

<!-- Stats -->
<p class="section-title">Overview</p>
<div id="stats-container"
     hx-get="/partials/stats"
     hx-trigger="every 30s"
     hx-swap="innerHTML">
  {% include "_stats.html" %}
</div>

<!-- Activity + Tasks -->
<div class="panels">
  <div id="activity-container"
       hx-get="/partials/activity"
       hx-trigger="every 30s"
       hx-swap="innerHTML">
    {% include "_activity.html" %}
  </div>

  <div id="tasks-container"
       hx-get="/partials/tasks"
       hx-trigger="every 30s"
       hx-swap="innerHTML">
    {% include "_tasks.html" %}
  </div>
</div>

<!-- Skills + Connectors -->
<div class="panels">
  <div class="panel">
    <div class="panel-header">
      Skills
      <span class="panel-count">{{ skills | length }}</span>
    </div>
    <div class="panel-body">
      {% if skills %}
        {% for s in skills %}
        <div class="skill-row">
          <span class="skill-name">{{ s.name }}</span>
          <span class="skill-preview">{{ s.preview }}</span>
        </div>
        {% endfor %}
      {% else %}
        <div class="panel-empty">No skills saved yet.</div>
      {% endif %}
    </div>
  </div>

  <div class="panel">
    <div class="panel-header">
      Connectors
      <span class="panel-count">{{ connectors | selectattr('installed') | list | length }} / {{ connectors | length }}</span>
    </div>
    <div class="panel-body">
      {% for c in connectors %}
      <div class="connector-row">
        <span class="connector-name {{ 'installed' if c.installed else 'uninstalled' }}">{{ c.name }}</span>
        <span class="connector-desc">{{ c.description }}</span>
        <span class="connector-badge {{ 'on' if c.installed else 'off' }}">
          {{ 'on' if c.installed else 'off' }}
        </span>
      </div>
      {% endfor %}
    </div>
  </div>
</div>

{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/templates/base.html dashboard/templates/index.html
git commit -m "feat(dashboard): base template and main index page"
```

---

## Task 5: HTMX partials

**Files:**
- Create: `dashboard/templates/_stats.html`
- Create: `dashboard/templates/_activity.html`
- Create: `dashboard/templates/_tasks.html`

- [ ] **Step 1: Write _stats.html**

```html
<div class="stats-grid">
  <div class="stat-card">
    <div class="stat-icon">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
    </div>
    <div class="stat-value">{{ stats.session_count }}</div>
    <div class="stat-label">Active sessions</div>
  </div>

  <div class="stat-card">
    <div class="stat-icon">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
    </div>
    <div class="stat-value">{{ stats.task_count }}</div>
    <div class="stat-label">Scheduled tasks</div>
  </div>

  <div class="stat-card">
    <div class="stat-icon">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
    </div>
    <div class="stat-value">{{ stats.skill_count }}</div>
    <div class="stat-label">Skills</div>
  </div>

  <div class="stat-card">
    <div class="stat-icon">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
    </div>
    <div class="stat-value">{{ stats.memory_kb }}<span style="font-size:.9rem;font-weight:500;color:var(--muted)">kb</span></div>
    <div class="stat-label">Memory</div>
  </div>

  <div class="stat-card">
    <div class="stat-icon">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
    </div>
    <div class="stat-value">{{ stats.connector_count }}</div>
    <div class="stat-label">Connectors</div>
  </div>

  <div class="stat-card">
    <div class="stat-icon">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
    </div>
    <div class="stat-value">{{ stats.daily_notes }}</div>
    <div class="stat-label">Daily notes</div>
  </div>
</div>
```

- [ ] **Step 2: Write _activity.html**

```html
<div class="panel">
  <div class="panel-header">
    Recent Activity
    <span class="panel-count">last 15</span>
  </div>
  <div class="panel-body">
    {% if activity %}
      {% for row in activity %}
      <div class="activity-row">
        <span class="role-badge {{ row.role }}">{{ row.role[:4] }}</span>
        <div class="activity-content">
          <div class="activity-text">{{ row.content }}</div>
          <div class="activity-meta">chat {{ row.chat_id }} · {{ row.created_at }}</div>
        </div>
      </div>
      {% endfor %}
    {% else %}
      <div class="panel-empty">No activity yet.</div>
    {% endif %}
  </div>
</div>
```

- [ ] **Step 3: Write _tasks.html**

```html
<div class="panel">
  <div class="panel-header">
    Scheduled Tasks
    <span class="panel-count">{{ tasks | length }}</span>
  </div>
  <div class="panel-body">
    {% if tasks %}
      {% for t in tasks %}
      <div class="task-row">
        <span class="task-id">#{{ t.id }}</span>
        <div class="task-info">
          <div class="task-prompt">{{ t.task_prompt }}</div>
          <div class="task-schedule">{{ t.schedule_str }}</div>
        </div>
        <span class="task-status {{ 'enabled' if t.enabled else 'disabled' }}"></span>
      </div>
      {% endfor %}
    {% else %}
      <div class="panel-empty">No scheduled tasks.</div>
    {% endif %}
  </div>
</div>
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/templates/_stats.html dashboard/templates/_activity.html dashboard/templates/_tasks.html
git commit -m "feat(dashboard): HTMX partials — stats, activity, tasks"
```

---

## Task 6: Wiring — systemd, requirements, install script

**Files:**
- Modify: `systemd/claude-dashboard.service`
- Modify: `requirements.txt`
- Modify: `scripts/install-systemd.sh`

- [ ] **Step 1: Fix dashboard service**

Replace contents of `systemd/claude-dashboard.service`:

```ini
[Unit]
Description=claudhaus — Dashboard
After=network-online.target claude-main.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/JjayFiles/claude-command-center
EnvironmentFile=-%h/JjayFiles/claude-command-center/.env
ExecStart=%h/JjayFiles/claude-command-center/.venv/bin/python -m uvicorn dashboard.app:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=10
StartLimitBurst=5
StartLimitIntervalSec=60

StandardOutput=append:%h/JjayFiles/claude-command-center/logs/dashboard.log
StandardError=append:%h/JjayFiles/claude-command-center/logs/dashboard.log

[Install]
WantedBy=default.target
```

- [ ] **Step 2: Add jinja2 to requirements.txt**

Add after the `httpx` line:
```
jinja2>=3.1,<4
```

- [ ] **Step 3: Add dashboard to install-systemd.sh**

In the `UNITS` array, add:
```bash
claude-dashboard.service
```

And after the main service enable block, add:
```bash
systemctl --user enable --now claude-dashboard.service
echo "  claude-dashboard.service — enabled + started"
```

- [ ] **Step 4: Commit**

```bash
git add systemd/claude-dashboard.service requirements.txt scripts/install-systemd.sh
git commit -m "feat(dashboard): wire systemd service, requirements, install script"
```

---

## Task 7: Final integration commit

- [ ] **Step 1: Update CHANGELOG**

Add `[0.13.0]` entry covering all dashboard tasks.

- [ ] **Step 2: Update README**

Add a Dashboard section after the "Platform notes" section describing how to access it (`http://localhost:8000`) and how to enable the systemd service.

- [ ] **Step 3: Push**

```bash
git push origin main
```
