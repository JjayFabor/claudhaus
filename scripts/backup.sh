#!/usr/bin/env bash
# Daily backup of memory and conversation data. 14-day retention.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$ROOT/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE="$BACKUP_DIR/backup_$TIMESTAMP.tar.gz"

mkdir -p "$BACKUP_DIR"

tar -czf "$ARCHIVE" \
    -C "$ROOT" \
    --ignore-failed-read \
    data/memory.db \
    workspaces/main/MEMORY.md \
    workspaces/main/DREAMS.md \
    workspaces/main/memory \
    2>/dev/null || true

echo "Backup written: $ARCHIVE"

# Prune backups older than 14 days
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +14 -delete
echo "Old backups pruned (>14 days)"
