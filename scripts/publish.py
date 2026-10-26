"""Publish this package to PyPI — a SEPARATE, deliberate step, intentionally kept
out of release.py (PyPI uploads are irreversible: a version can never be
re-uploaded).

Reads the version from pyproject.toml, requires the matching v<version> tag to
already exist locally AND on the remote (so you publish exactly what was
released), runs a fresh `python -m build`, and uploads with `twine`.

Prereq order:  scripts/bump_version.py -> scripts/release.py -> scripts/publish.py

Usage: pixi run python scripts/publish.py [options]
  --yes             Don't prompt for confirmation before uploading.
  --dry-run         Print the build + upload commands; run nothing.
  --allow-dirty     Skip the clean-working-tree check.
  --skip-tag-check  Don't require the v<version> tag locally + on remote.
  --remote <name>   Git remote to check the tag against (default: origin).
  -h, --help        Show this help.

Auth-gated: needs a PyPI API token in the environment —
  TWINE_USERNAME=__token__
  TWINE_PASSWORD=pypi-XXXXXXXX        # your project-scoped token
(or a [pypi] entry in ~/.pypirc). If missing, it prints this and exits without
uploading. Idempotent: if this version is already on PyPI it reports success.
"""
from __future__ import annotations

import glob
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

from _common import ROOT, git, make_runner, python_cmd, read_version, tree_is_dirty, use_pixi

PKG = "universal-wasm-loader"


def main(argv: list[str]) -> None:
    assume_yes, dry_run, allow_dirty, skip_tag_check, remote = False, False, False, False, "origin"
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg == "--yes":
            assume_yes = True
        elif arg == "--dry-run":
            dry_run = True
        elif arg == "--allow-dirty":
            allow_dirty = True
        elif arg == "--skip-tag-check":
            skip_tag_check = True
        elif arg == "--remote":
            remote = args.pop(0) if args else ""
        elif arg in ("-h", "--help"):
            print(__doc__.strip())
            sys.exit(0)
        else:
            print(f"error: unknown argument: {arg}", file=sys.stderr)
            sys.exit(2)

    run = make_runner(dry_run)

    def guard(message: str) -> None:
        """Fatal in a real run; a warning under --dry-run so the flow is inspectable."""
        if dry_run:
            print(f"warning (ignored under --dry-run): {message}", file=sys.stderr)
            return
        print(f"error: {message}", file=sys.stderr)
        sys.exit(1)

    # --- Version / tag (source of truth: pyproject.toml) ------------------------
    version = read_version(ROOT / "pyproject.toml")
    if not version:
        print("error: could not read version from pyproject.toml", file=sys.stderr)
        sys.exit(1)
    tag = f"v{version}"
    print(f"Publishing {PKG} {version} to PyPI", flush=True)

    # --- Preflight: clean tree --------------------------------------------------
    if not allow_dirty and tree_is_dirty():
        guard("working tree is dirty — commit/stash, or pass --allow-dirty.")

    # --- Preflight: the release tag exists locally and on the remote ------------
    if not skip_tag_check:
        if git("rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode != 0:
            guard(f"tag {tag} not found locally — run scripts/release.py first "
                  "(or --skip-tag-check).")
        if f"refs/tags/{tag}" not in git("ls-remote", "--tags", remote, tag).stdout:
            guard(f"tag {tag} not on {remote} — push it (scripts/release.py) before publishing "
                  "(or --skip-tag-check).")

    # --- Idempotency: is this version already on PyPI? --------------------------
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{PKG}/{version}/json", timeout=30):
            pass
        print(f"{PKG} {version} is already on PyPI — nothing to do.")
        print(f"(See https://pypi.org/project/{PKG}/{version}/)")
        sys.exit(0)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            # Only "not found" means "not published yet"; anything else is not an answer.
            print(f"error: PyPI answered HTTP {e.code} for {PKG} {version}", file=sys.stderr)
            sys.exit(1)
    except urllib.error.URLError as e:
        print(f"error: could not reach PyPI to check {PKG} {version}: {e.reason}", file=sys.stderr)
        sys.exit(1)

    # --- Auth gate: need a PyPI token (env or ~/.pypirc) ------------------------
    if not os.environ.get("TWINE_PASSWORD") and not (Path.home() / ".pypirc").is_file():
        guard("no PyPI credentials found. Set a token and re-run:\n"
              "         export TWINE_USERNAME=__token__\n"
              "         export TWINE_PASSWORD=pypi-XXXXXXXX   # your project-scoped PyPI token\n"
              "       (or add a [pypi] entry to ~/.pypirc).")
    # Default the username to __token__ when a password/token is supplied without one.
    if os.environ.get("TWINE_PASSWORD") and not os.environ.get("TWINE_USERNAME"):
        os.environ["TWINE_USERNAME"] = "__token__"

    # --- Confirm (irreversible: a PyPI version can never be re-uploaded) --------
    if not assume_yes and not dry_run:
        reply = input(f"Upload {PKG} {version} to PyPI? This is irreversible. [y/N] ")
        if reply.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            sys.exit(1)

    # --- Build fresh, then upload -----------------------------------------------
    # This is a pixi project, so build/publish run inside the pixi env (which
    # provides `build` + `twine`). Auto-detected when a pixi.toml + the pixi CLI are
    # present; force with UWL_PY_TOOL=pixi|python.
    prefix = ["pixi", "run", "python"] if use_pixi() else [python_cmd()]
    print("+ rm -rf dist", flush=True)
    if not dry_run:
        shutil.rmtree(ROOT / "dist", ignore_errors=True)
    run(*prefix, "-m", "build")
    # The shell expanded dist/* before the call; under --dry-run there is no dist/ yet.
    dists = sorted(glob.glob("dist/*", root_dir=ROOT)) or ["dist/*"]
    run(*prefix, "-m", "twine", "check", *dists)
    run(*prefix, "-m", "twine", "upload", *dists)

    if dry_run:
        print(f"Dry run complete — nothing built or uploaded; {PKG} {version} was NOT published.")
    else:
        print(f"Done: published {PKG} {version} to PyPI.")
        print(f"Verify at https://pypi.org/project/{PKG}/{version}/")


if __name__ == "__main__":
    main(sys.argv[1:])
