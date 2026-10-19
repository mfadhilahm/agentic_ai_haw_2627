"""Shared evidence helpers for the team's quality checks (no role changes)."""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def redact(text: str) -> str:
    """Best-effort output cleanup; review evidence before sharing it."""
    text = re.sub(r"(?i)(bearer\s+)\S+", r"\1[REDACTED]", text)
    text = re.sub(
        r"(?i)((?:api[_-]?key|password|passwd|secret|token)\s*['\"]?\s*[:=]\s*['\"]?)[^\s'\",;]+",
        r"\1[REDACTED]", text,
    )
    text = re.sub(r"(://[^\s/:]+:)[^\s/@]+@", r"\1[REDACTED]@", text)
    return re.sub(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,})\b", "[REDACTED]", text)


def source_version() -> dict[str, Any]:
    """Identify HEAD AND local changes without storing their contents."""
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), *args], capture_output=True,
            text=True, timeout=5, check=True,
        ).stdout.strip()

    try:
        sha = git("rev-parse", "HEAD")
        dirty = bool(git("status", "--porcelain"))
    except (OSError, subprocess.SubprocessError):
        sha, dirty = None, None
    # Hash all current Python sources/tests, including untracked new modules.
    digest = hashlib.sha256()
    for folder in ("src", "tests"):
        for path in sorted((REPO_ROOT / folder).rglob("*.py")):
            digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
            digest.update(b"\0" + path.read_bytes() + b"\0")
    return {"commit_sha": sha, "working_tree_dirty": dirty, "source_sha256": digest.hexdigest()}


def write_json(path: Path, value: dict[str, Any]) -> None:
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
