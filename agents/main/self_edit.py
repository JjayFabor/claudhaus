"""
agents/main/self_edit.py — Safe self-editing for claudhaus source files.

Wraps the edit-compile-commit cycle so a bad change never silences the bot:
  1. Validate path is inside project root
  2. Backup the file
  3. Apply edit (targeted replacement or full rewrite)
  4. Syntax-check Python files with py_compile
  5. On failure → restore backup, return error with details
  6. On success → git add + commit, remove backup, return success
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def apply_edit(
    file_path: str,
    old_string: str | None = None,
    new_string: str | None = None,
    new_content: str | None = None,
    description: str = "agent self-edit",
    replace_all: bool = False,
) -> tuple[bool, str]:
    """
    Safely edit a project file.

    Two modes:
      - Targeted: provide old_string + new_string (replaces first occurrence,
        or all if replace_all=True)
      - Full rewrite: provide new_content

    Returns (success, message).
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = ROOT / file_path

    try:
        path.relative_to(ROOT)
    except ValueError:
        return False, f"Refusing: {file_path!r} is outside the project root."

    if not path.exists():
        return False, f"File not found: {path}"

    # Backup
    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)

    try:
        if new_content is not None:
            path.write_text(new_content, encoding="utf-8")

        elif old_string is not None and new_string is not None:
            original = path.read_text(encoding="utf-8")
            if old_string not in original:
                backup.unlink(missing_ok=True)
                return False, f"old_string not found in {path.name} — no changes made."
            if replace_all:
                updated = original.replace(old_string, new_string)
            else:
                updated = original.replace(old_string, new_string, 1)
            path.write_text(updated, encoding="utf-8")

        else:
            backup.unlink(missing_ok=True)
            return False, "Provide either (old_string + new_string) or new_content."

        # Syntax check for Python files
        if path.suffix == ".py":
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(path)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                shutil.copy2(backup, path)
                backup.unlink(missing_ok=True)
                error = (result.stderr or result.stdout).strip()
                return False, f"Syntax error — edit reverted automatically:\n{error}"

        # Commit
        rel = str(path.relative_to(ROOT))
        commit_msg = f"self-edit: {description} ({rel})"
        subprocess.run(["git", "add", str(path)], cwd=ROOT, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        committed = result.returncode == 0

        backup.unlink(missing_ok=True)

        suffix = " — committed to git" if committed else " (git commit skipped — no changes staged)"
        return True, f"Edit applied to {rel}{suffix}."

    except Exception as e:
        if backup.exists():
            shutil.copy2(backup, path)
            backup.unlink(missing_ok=True)
        return False, f"Edit failed (reverted): {e}"
