# claude-command-center

A personal AI command center built on the Claude Agent SDK. One Telegram bot, one full-power agent, no coordination overhead. Send a message from your phone; get a senior software engineer on the other end with persistent memory, all your tools, and your MCP connectors.

---

## What this is

A single Claude-powered agent ("Main") connected to Telegram. Main handles engineering, DevOps, research, project management, and personal ops — whatever you throw at it. It has access to Bash, file tools, web search, and any MCP servers you've configured via `claude mcp`. Memory persists across sessions via plain Markdown files you can read and edit directly.

There are no sub-agents, no delegation layers, and no task queues built in. If you want Main to spawn sub-agents for specialized work, you tell Main that directly — the Claude Agent SDK's `Task` tool supports it.

---

## Prerequisites

- **Claude Code subscription** with an active `claude` CLI login (`claude --version` should work)
- **Python 3.10+**
- **Node.js 18+** (required by the `claude` CLI)
- **git**
- A Telegram account

**Important:** Do not set `ANTHROPIC_API_KEY`. Auth rides on `~/.claude/.credentials.json` (Claude CLI OAuth). Setting the API key switches billing from your subscription to metered API calls.

---

## Quick start

```bash
git clone https://github.com/your-username/claude-command-center.git
cd claude-command-center
python3 scripts/setup.py
```

The setup wizard will:
1. Check prerequisites
2. Create `.env` from `.env.example`
3. Prompt for your Telegram bot token (if not already set)
4. Create runtime directories
5. Copy soul file templates to editable `.md` files
6. Optionally create a personal `CLAUDE.personal.md` override
7. Create and populate a Python venv
8. Initialize the SQLite database

Then:

```bash
source .venv/bin/activate
# Fill in agents/shared/USER_PROFILE.md with your context
# Fill in .env: TELEGRAM_ALLOWED_USER_IDS (get your ID from /whoami after first run)
python agents/main/agent.py
```

---

## Architecture

**One agent. Full power.**

Main is a senior software engineer and general-purpose operator. It has no peers, no managers, no sub-agents built in. Its breadth comes from its tool set; its depth comes from session continuity and the memory system.

```
Telegram message
      ↓
agents/main/agent.py   ← Python bot runner
      ↓
Claude Agent SDK       ← spawns claude CLI subprocess
      ↓
Main                   ← CLAUDE.md instructions + soul layer + memory
      ↓
Tools: Bash, Read, Write, Edit, Glob, Grep, WebSearch, WebFetch, MCP connectors
```

### Dual instruction set

Every instruction file exists in two forms:

| File | Committed | Purpose |
|------|-----------|---------|
| `agents/main/CLAUDE.md` | Yes | Generic template. Works for any user out of the box. |
| `agents/main/CLAUDE.personal.md` | No (gitignored) | Your real context, preferences, business specifics. |

At startup, if `CLAUDE.personal.md` exists it's used; otherwise `CLAUDE.md`. One decision point, always logged so you know which is active.

The same pattern applies to soul files in `agents/shared/`.

---

## Memory system (Phase 4)

All memory is plain Markdown on disk. Main only "remembers" what gets written to a file. Open `workspaces/main/MEMORY.md` in any editor and see exactly what Main knows.

- **`MEMORY.md`** — long-term durable facts, preferences, decisions
- **`memory/YYYY-MM-DD.md`** — daily running context, auto-loaded for today and yesterday
- **`DREAMS.md`** — nightly consolidation candidates, human-reviewed before promotion
- **Hybrid search** — BM25 + vector embeddings, merged via RRF

---

## Configuration reference

All variables in `.env`:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `TELEGRAM_BOT_TOKEN_MAIN` | string | — | Main bot token from BotFather |
| `TELEGRAM_ALLOWED_USER_IDS` | csv | — | Telegram user IDs allowed to DM Main |
| `TELEGRAM_ALLOWED_CHAT_IDS` | csv | — | Group/channel IDs Main is active in |
| `MEMORY_EMBEDDING_PROVIDER` | enum | `local` | `local` \| `openai` \| `none` |
| `MEMORY_EMBEDDING_MODEL` | string | `all-MiniLM-L6-v2` | Model name for local embeddings |
| `MEMORY_SESSION_INDEXING` | bool | `false` | Index raw session logs for search |
| `MEMORY_SESSION_DELTA_BYTES` | int | `100000` | Bytes threshold for session index update |
| `MEMORY_SESSION_DELTA_MESSAGES` | int | `50` | Message count threshold |
| `DREAMING_ENABLED` | bool | `false` | Enable nightly memory consolidation |
| `DREAMING_LOOKBACK_DAYS` | int | `30` | Days of daily notes to consider |
| `DREAMING_PROMOTION_THRESHOLD` | float | `0.6` | Score threshold for DREAMS.md candidates |
| `OBSIDIAN_VAULT_PATH` | path | — | Absolute path to your Obsidian vault |
| `DASHBOARD_PORT` | int | `8000` | Dashboard listen port |

---

## Platform notes

### WSL2

Requires `systemd=true` in `/etc/wsl.conf` and `vmIdleTimeout=-1` in `~/.wslconfig` to prevent shutdown during idle. See `docs/wsl-keepalive.md`.

### Native Linux

Works out of the box with systemd. Install service files:

```bash
cp systemd/claude-main.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now claude-main.service
```

### macOS

Use the launchd plist in `systemd/com.claudecommandcenter.main.plist`:

```bash
cp systemd/com.claudecommandcenter.main.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.claudecommandcenter.main.plist
```

### Docker (advanced)

```bash
docker compose up -d
```

**Critical:** the `~/.claude` volume mount is required for CLI auth. Without it, the bot cannot call Claude. See `docker-compose.yml` for the mount definition.

---

## FAQ

**Q: Why not set `ANTHROPIC_API_KEY`?**  
Setting it switches billing from your Claude Code subscription to metered API calls. Auth via `~/.claude/.credentials.json` is free under your subscription.

**Q: Can Main spawn sub-agents?**  
Not by default. If you want that, tell Main directly — the Claude Agent SDK's `Task` tool supports it. Nothing needs to be built upfront.

**Q: How do I find my Telegram user ID?**  
Run the bot (Phase 1) and send it `/whoami`. It replies with your numeric user ID. Put that in `TELEGRAM_ALLOWED_USER_IDS`.

**Q: How do I reset a conversation?**  
Send `/reset` to the bot. The next message starts a fresh Claude session.

**Q: What happens when the context window fills up?**  
The memory flush system (Phase 4) writes important facts to disk before compaction occurs. Nothing is lost.

**Q: Is this safe to use on shared machines?**  
The `bypassPermissions` mode (Phase 2) gives Main full tool access. Only run this on machines you control, with the Telegram allowlist set.
