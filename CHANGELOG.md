# Changelog

All notable changes to this project are documented here.

## [Unreleased]

## [0.0.1] — Phase 0 — 2026-04-21

### Added
- Full project directory structure
- `.gitignore` covering credentials, workspaces, personal overrides
- `.env.example` with all configuration variables documented
- `requirements.txt` with core and phase-gated dependencies
- `agents/main/CLAUDE.md` — generic committed instruction template
- `agents/shared/*.example.md` — soul file templates (USER_PROFILE, BUSINESS_CONTEXT, HOUSE_RULES)
- `agents/main/agent.py` — stub with `load_instructions()` utility
- `scripts/setup.py` — idempotent first-run wizard
- `scripts/backup.sh` — daily backup with 14-day retention
- `scripts/update.sh` — pip upgrade with session-safe restart
- systemd user units: `claude-main.service`, `claude-dashboard.service`, `claude-memory-dreaming.service/.timer`
- macOS launchd plist: `com.claudecommandcenter.main.plist`
- `Dockerfile` and `docker-compose.yml` with `~/.claude` volume mount
- `docs/wsl-keepalive.md` — WSL2 systemd + idle timeout setup
- `docs/cloudflare-tunnel.md` — phone access to dashboard
- GitHub issue templates and PR template
- `LICENSE` (MIT)
- `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`
- `BUILD_PLAN.md` — complete build plan for all phases
- Stub modules: `memory/`, `dashboard/`, `obsidian/`
