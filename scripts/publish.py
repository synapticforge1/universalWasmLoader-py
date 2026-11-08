"""Publish this package to PyPI — a SEPARATE, deliberate step, intentionally kept
out of release.py (PyPI uploads are irreversible: a version can never be
re-uploaded).

Reads the version from pyproject.toml, requires the matching v<version> tag to
already exist locally AND on the remote (so you publish exactly what was
released), runs a fresh `python -m build`, and uploads with `twine` only the files PyPI does
not have yet (scripts/pypi_files.py).

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
uploading. Idempotent per file: a version complete on PyPI uploads nothing and reports
success; a half-published one (an upload that failed between files) gets only its missing files.
"""
from __future__ import annotations

import glob
import os
import shutil
import sys
from pathlib import Path

import pypi_files
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

    # --- Build fresh, check, then ask PyPI which files it still needs -------------
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

    # Idempotent per FILE (scripts/pypi_files.py): a version complete on PyPI uploads nothing;
    # a half-published one uploads only its missing files. Only a 404 means "no files yet".
    if not dry_run:
        try:
            upload, notes = pypi_files.plan(
                pypi_files.local_files(ROOT / "dist", PKG, version),
                pypi_files.remote_files(PKG, version),
            )
        except (ValueError, pypi_files.PyPIError) as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(1)
        for note in notes:
            print(note)
        if not upload:
            print(f"{PKG} {version} is already complete on PyPI — nothing to upload.")
            print(f"(See https://pypi.org/project/{PKG}/{version}/)")
            sys.exit(0)
        dists = [f"dist/{name}" for name in upload]

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
        reply = input(f"Upload {', '.join(dists)} to PyPI? This is irreversible. [y/N] ")
        if reply.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            sys.exit(1)

    run(*prefix, "-m", "twine", "upload", *dists)

    if dry_run:
        print(f"Dry run complete — nothing built or uploaded; {PKG} {version} was NOT published.")
    else:
        print(f"Done: published {PKG} {version} to PyPI.")
        print(f"Verify at https://pypi.org/project/{PKG}/{version}/")


if __name__ == "__main__":
    main(sys.argv[1:])
