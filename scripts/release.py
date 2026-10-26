"""Cut a release of universalWasmLoader-py consistently.

The single source of truth for the version is `[project] version` in
pyproject.toml. This script reads it, tags the current commit `v<version>`,
pushes the branch and tag to `origin`, and (unless --no-release) creates the
matching GitHub Release. It does NOT publish to PyPI — that is a separate,
deliberate step (scripts/publish.py).

Usage: pixi run python scripts/release.py [options]
  --notes <text>   Release notes body (default: a generic line).
  --no-release     Push the tag only; skip creating a GitHub Release.
  --no-build       Skip the fresh `python -m build` verification.
  --remote <name>  Git remote to push to (default: origin).
  --dry-run        Print what would happen; make no tags/pushes/releases.
  -h, --help       Show this help.

Idempotent: if the tag already exists it is reused (must point at HEAD); an
existing GitHub Release is left untouched. Degrades gracefully if `gh` is
missing/unauthenticated (the tag is still pushed).
"""
from __future__ import annotations

import shutil
import subprocess
import sys

from _common import (
    ROOT,
    fail,
    git,
    make_runner,
    print_dirty_tree,
    python_cmd,
    read_version,
    tag_exists,
    tree_is_dirty,
    use_pixi,
)


def main(argv: list[str]) -> None:
    notes, make_release, do_build, remote, dry_run = "", True, True, "origin", False
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg == "--notes":
            notes = args.pop(0) if args else ""
        elif arg == "--no-release":
            make_release = False
        elif arg == "--no-build":
            do_build = False
        elif arg == "--remote":
            remote = args.pop(0) if args else ""
        elif arg == "--dry-run":
            dry_run = True
        elif arg in ("-h", "--help"):
            print(__doc__.strip())
            sys.exit(0)
        else:
            fail(f"unknown argument: {arg}", 2)

    run = make_runner(dry_run)

    # --- Derive version from pyproject.toml (source of truth) -------------------
    version = read_version(ROOT / "pyproject.toml")
    if not version:
        fail("could not read version from pyproject.toml")
    tag = f"v{version}"
    print(f"Releasing {tag} (from pyproject.toml)", flush=True)

    # --- Preflight checks -------------------------------------------------------
    if tree_is_dirty():
        print("error: working tree is dirty — commit or stash before releasing.", file=sys.stderr)
        print_dirty_tree()
        sys.exit(1)

    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    print(f"On branch: {branch}", flush=True)

    # If the tag already exists, it must point at the current commit.
    if tag_exists(tag):
        tagged = git("rev-parse", f"{tag}^{{commit}}").stdout.strip()
        if tagged != git("rev-parse", "HEAD").stdout.strip():
            print(f"error: tag {tag} exists but does not point at HEAD.", file=sys.stderr)
            print("       Bump the version in pyproject.toml or move the tag deliberately.",
                  file=sys.stderr)
            sys.exit(1)
        print(f"tag {tag} already exists at HEAD — reusing.", flush=True)
        existed = True
    else:
        existed = False

    # --- Verify it builds -------------------------------------------------------
    # This is a pixi project; build inside the pixi env. Auto-detected when a
    # pixi.toml + the pixi CLI are present; force with UWL_PY_TOOL=pixi|python.
    if do_build:
        print("Verifying build (fresh sdist + wheel)…", flush=True)
        print("+ rm -rf dist", flush=True)
        if not dry_run:
            shutil.rmtree(ROOT / "dist", ignore_errors=True)
        if use_pixi():
            run("pixi", "run", "python", "-m", "build")
        else:
            run(python_cmd(), "-m", "build")

    # --- Tag, push, release -----------------------------------------------------
    if not existed:
        run("git", "tag", "-a", tag, "-m", f"universalWasmLoader-py {tag}")

    run("git", "push", remote, branch)
    run("git", "push", remote, tag)

    if make_release:
        if shutil.which("gh") is None:
            print("warning: gh CLI not found — skipping GitHub Release (tag is pushed).",
                  file=sys.stderr)
        elif subprocess.run(["gh", "auth", "status"], capture_output=True).returncode != 0:
            print("warning: gh is not authenticated — skipping GitHub Release (tag is pushed).",
                  file=sys.stderr)
            print(f"         Run 'gh auth login' (or set GH_TOKEN), then: gh release create {tag}",
                  file=sys.stderr)
        elif subprocess.run(["gh", "release", "view", tag], capture_output=True).returncode == 0:
            print(f"GitHub Release {tag} already exists — leaving it untouched.")
        else:
            body = notes or (
                f"Release {tag} of universalWasmLoader-py — "
                "Python port of the Universal WASM Loader."
            )
            run("gh", "release", "create", tag, "--title", tag, "--notes", body)

    print(f"Done: {tag}")
    print("To publish to PyPI (separate, deliberate step): pixi run python scripts/publish.py")


if __name__ == "__main__":
    main(sys.argv[1:])
