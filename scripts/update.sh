#!/usr/bin/env bash
# Upgrade Python dependencies and restart bot cleanly.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIP="$ROOT/.venv/bin/pip"

echo "Upgrading dependencies..."
"$PIP" install --upgrade -r "$ROOT/requirements.txt"
echo "Done."

# Restart bot if running under systemd
if systemctl --user is-active --quiet claude-main.service 2>/dev/null; then
    echo "Restarting claude-main.service..."
    systemctl --user restart claude-main.service
    echo "Restarted."
else
    echo "claude-main.service not running under systemd — restart manually if needed."
fi
