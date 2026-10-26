"""Shared helpers for the release toolchain (bump_version.py, release.py, publish.py).

Run every script with pixi's Python from the repo root:  pixi run python scripts/<name>.py …
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The messages carry `—` and `…`; on Windows a piped stdout would otherwise be cp1252.
for _stream in (sys.stdout, sys.stderr):
    _stream.reconfigure(encoding="utf-8", newline="\n")  # type: ignore[union-attr]

_VERSION_LINE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)


def read_version(path: Path) -> str:
    """The first `version = "…"` in the file, i.e. pyproject.toml's [project] one ("" if none)."""
    m = _VERSION_LINE.search(path.read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def tree_is_dirty() -> bool:
    return git("status", "--porcelain").stdout != ""


def print_dirty_tree() -> None:
    sys.stderr.write(git("status", "--short").stdout)


def tag_exists(tag: str) -> bool:
    return git("rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode == 0


def make_runner(dry_run: bool) -> Callable[..., None]:
    def run(*cmd: str) -> None:
        """Echo + execute (stop on failure), or only echo under --dry-run."""
        print("+ " + " ".join(cmd), flush=True)
        if not dry_run:
            rc = subprocess.run(list(cmd), cwd=ROOT).returncode
            if rc != 0:
                sys.exit(rc)

    return run


def use_pixi() -> bool:
    """Build inside the pixi env when pixi.toml + the pixi CLI exist; force with UWL_PY_TOOL."""
    forced = os.environ.get("UWL_PY_TOOL", "")
    if forced == "pixi":
        return True
    if forced == "python":
        return False
    return (ROOT / "pixi.toml").is_file() and shutil.which("pixi") is not None


def python_cmd() -> str:
    return os.environ.get("PYTHON", "python")


def fail(message: str, code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)
