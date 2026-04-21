# agents/main/agent.py — Phase 1 implements this fully
# Stub only — structure placeholder for Phase 0

from pathlib import Path


def load_instructions(agent_dir: Path) -> Path:
    """Personal override takes precedence if it exists, otherwise fall back to generic."""
    personal = agent_dir / "CLAUDE.personal.md"
    generic = agent_dir / "CLAUDE.md"
    if personal.exists():
        return personal
    return generic


if __name__ == "__main__":
    raise SystemExit("Phase 1 not yet implemented. Run scripts/setup.py first.")
