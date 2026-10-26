"""Bump the project version in pyproject.toml (the single source of truth).

Updates `[project] version` to the next semver, keeps pixi.toml's mirror in
sync, commits the one-line change, and stops there — tagging/pushing/releasing
is scripts/release.py's job. Typical flow:

    pixi run python scripts/bump_version.py minor   # 1.0.0 -> 1.1.0, commits the bump
    pixi run python scripts/release.py              # tags v1.1.0, pushes, GitHub Release

Usage: pixi run python scripts/bump_version.py <major|minor|patch|X.Y.Z> [options]
  major|minor|patch   Increment that semver component (resets lower ones).
  X.Y.Z               Set an explicit version (must be valid semver).
  --no-commit         Edit the manifests only; don't commit.
  --dry-run           Print the new version + planned actions; change nothing.
  -h, --help          Show this help.

Refuses to run on a dirty tree (so the bump lands as an isolated commit) and
rejects a target that isn't strictly greater than the current version or whose
tag already exists. Then runs the compatibility gate (scripts/compat.py) against
the last release tag and refuses a bump below its floor, a stale api-surface.json,
a patch/minor whose previous-tag tests regress, or a major with no Breaking
Changes row.
"""
from __future__ import annotations

import re
import sys

import compat
from _common import (
    ROOT,
    fail,
    make_runner,
    print_dirty_tree,
    read_version,
    tag_exists,
    tree_is_dirty,
)

SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
LOOSE_SEMVER_ARG = re.compile(r"^[0-9].*\.[0-9].*\.[0-9]")  # the original .sh's glob case
FIRST_PLAIN_VERSION = re.compile(r'^(version\s*=\s*)"[0-9]+\.[0-9]+\.[0-9]+"', re.MULTILINE)


def main(argv: list[str]) -> None:
    pyproject = ROOT / "pyproject.toml"
    pixi = ROOT / "pixi.toml"
    do_commit, dry_run, spec = True, False, ""

    for arg in argv:
        if arg == "--no-commit":
            do_commit = False
        elif arg == "--dry-run":
            dry_run = True
        elif arg in ("-h", "--help"):
            print(__doc__.strip())
            sys.exit(0)
        elif arg in ("major", "minor", "patch") or LOOSE_SEMVER_ARG.match(arg):
            spec = arg
        else:
            fail(f"unknown argument: {arg}", 2)

    if not spec:
        fail("missing bump spec (major|minor|patch|X.Y.Z). See --help.", 2)

    run = make_runner(dry_run)

    # --- Current version (first `version = "X.Y.Z"`, i.e. the [project] one) ------
    cur = read_version(pyproject)
    if not SEMVER.match(cur):
        fail(f"current version in pyproject.toml is not plain semver: '{cur or '<empty>'}'")
    ma, mi, pa = (int(x) for x in cur.split("."))

    # --- Compute target ---------------------------------------------------------
    if spec == "major":
        new = f"{ma + 1}.0.0"
    elif spec == "minor":
        new = f"{ma}.{mi + 1}.0"
    elif spec == "patch":
        new = f"{ma}.{mi}.{pa + 1}"
    else:
        if not SEMVER.match(spec):
            fail(f"'{spec}' is not valid semver (X.Y.Z).", 2)
        new = spec

    # --- Validate (strictly greater, tag free) ----------------------------------
    def key(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in v.split("."))

    if key(new) <= key(cur):
        fail(f"target {new} is not greater than current {cur}.")
    if tag_exists(f"v{new}"):
        fail(f"tag v{new} already exists.")

    print(f"Bumping version: {cur} -> {new}", flush=True)

    # --- Preflight: clean tree --------------------------------------------------
    if do_commit and not dry_run and tree_is_dirty():
        print("error: working tree is dirty — commit or stash so the bump is isolated.",
              file=sys.stderr)
        print_dirty_tree()
        sys.exit(1)

    # --- The compatibility gate (scripts/compat.py; never skipped) --------------
    level = compat.level_between(cur, new)
    previous = compat.tags()
    problems = compat.check(level, previous[-1] if previous else None)
    if problems:
        for p in problems:
            print(f"error: refused: {p}", file=sys.stderr)
        sys.exit(1)

    # --- Apply ------------------------------------------------------------------
    # Replace only the first `version = "..."` line in pyproject.toml (the [project]
    # field), and pixi.toml's mirror, preserving formatting and line endings.
    if not dry_run:
        for path in (pyproject, pixi):
            if path.is_file():
                data = path.read_bytes().decode("utf-8")
                path.write_bytes(
                    FIRST_PLAIN_VERSION.sub(rf'\g<1>"{new}"', data, count=1).encode("utf-8")
                )
    print(f'+ set version = "{new}" in pyproject.toml (and pixi.toml mirror)', flush=True)

    # Rule 4: a major stamps its version into README's `_next release_` Breaking Changes row.
    readme = ROOT / "README.md"
    stamp_row = level == "major" and compat.has_next_release_row()
    if stamp_row:
        if not dry_run:
            text = readme.read_bytes().decode("utf-8")
            readme.write_bytes(
                text.replace(compat.NEXT_RELEASE_ROW, f"| v{new} |", 1).encode("utf-8")
            )
        print(f"+ stamp v{new} into README's Breaking Changes row", flush=True)

    if do_commit:
        run("git", "add", "pyproject.toml")
        if pixi.is_file():
            run("git", "add", "pixi.toml")
        if stamp_row:
            run("git", "add", "README.md")
        run("git", "commit", "-m", f"Bump version: v{cur} -> v{new}")

    print(f"Done: {new}")
    if do_commit:
        print(f"Next: pixi run python scripts/release.py   "
              f"# tags v{new}, pushes, creates the GitHub Release")


if __name__ == "__main__":
    main(sys.argv[1:])
