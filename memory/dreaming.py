"""
memory/dreaming.py — Nightly memory consolidation sweep.

Disabled by default (DREAMING_ENABLED=false).
When enabled, reads daily notes from the past DREAMING_LOOKBACK_DAYS days,
scores observations for likely long-term relevance, and writes candidates
above DREAMING_PROMOTION_THRESHOLD to DREAMS.md for human review.

Nothing reaches MEMORY.md automatically — DREAMS.md is the human checkpoint.
Run via the claude-memory-dreaming systemd timer, or manually:
    python memory/dreaming.py
"""

import logging
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / "workspaces" / "main"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("memory.dreaming")


def _score_line(line: str) -> float:
    """
    Heuristic score for whether a daily-note line is worth promoting.
    Higher = more likely to be a durable fact worth remembering.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return 0.0

    score = 0.3  # baseline

    # Preference / decision markers
    if re.search(r"\b(prefer|decided|always|never|rule|policy|important)\b", line, re.I):
        score += 0.3
    # Tool / tech stack mentions
    if re.search(r"\b(use|using|stack|framework|library|tool|service)\b", line, re.I):
        score += 0.15
    # Concrete values (URLs, version numbers, identifiers)
    if re.search(r"https?://|v\d+\.\d+|\b[A-Z]{2,}\b", line):
        score += 0.1
    # Conversational / vague lines get penalised
    if re.search(r"\b(maybe|might|could|think|feel|seems)\b", line, re.I):
        score -= 0.15

    return min(max(score, 0.0), 1.0)


def run_sweep(
    lookback_days: int,
    threshold: float,
    workspace: Path = WORKSPACE,
) -> int:
    """
    Sweep daily notes and write candidates to DREAMS.md.
    Returns the number of candidates written.
    """
    daily_dir = workspace / "memory"
    dreams_path = workspace / "DREAMS.md"
    cutoff = date.today() - timedelta(days=lookback_days)

    candidates: list[str] = []

    for f in sorted(daily_dir.glob("*.md")):
        try:
            file_date = date.fromisoformat(f.stem)
        except ValueError:
            continue
        if file_date < cutoff:
            continue

        lines = f.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if line.strip().startswith("-"):
                score = _score_line(line)
                if score >= threshold:
                    candidates.append(f"<!-- score={score:.2f} source={f.name} -->\n{line.strip()}")

    if not candidates:
        logger.info("No candidates above threshold %.2f", threshold)
        return 0

    # Append to DREAMS.md (preserve existing content)
    existing = dreams_path.read_text(encoding="utf-8") if dreams_path.exists() else ""
    separator = f"\n\n## Sweep {date.today().isoformat()}\n\n"
    dreams_path.write_text(existing + separator + "\n".join(candidates) + "\n", encoding="utf-8")
    logger.info("Wrote %d candidates to DREAMS.md", len(candidates))
    return len(candidates)


if __name__ == "__main__":
    enabled = os.getenv("DREAMING_ENABLED", "false").lower() == "true"
    if not enabled:
        logger.info("DREAMING_ENABLED=false — nothing to do")
        sys.exit(0)

    lookback = int(os.getenv("DREAMING_LOOKBACK_DAYS", "30"))
    threshold = float(os.getenv("DREAMING_PROMOTION_THRESHOLD", "0.6"))
    count = run_sweep(lookback_days=lookback, threshold=threshold)
    logger.info("Sweep complete: %d candidates", count)
