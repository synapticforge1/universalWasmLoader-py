"""Cut a release of universalWasmLoader-py consistently.

The single source of truth for the version is `[project] version` in
pyproject.toml. This script reads it, tags the current commit `v<version>`,
pushes the branch and tag to `origin`, reads both back with `git ls-remote` (exit
1 unless they are HEAD), and (unless --no-release) prints a pre-filled web-UI
link to the GitHub Release page, as the OWNER fallback: the page itself is
created by publish.yml's `release` job (scripts/github_release.py, REST API;
since 2026-11-09). Never the GitHub CLI (workspace H30, owner 2026-11-08).

It does not upload to PyPI itself, but pushing the v<version> tag STARTS
.github/workflows/publish.yml, which uploads (since 2026-11-08; it pauses only
if the `pypi` environment requires a reviewer — on 2026-11-09 it did not
pause). scripts/publish.py stays as the local fallback; both upload only the
files PyPI does not have yet.

Usage: pixi run python scripts/release.py [options]
  --notes <text>   Release notes body (default: a generic line).
  --no-release     Push the tag only; print no Release-page owner item.
  --no-build       Skip the fresh `python -m build` verification.
  --remote <name>  Git remote to push to (default: origin).
  --dry-run        Print what would happen; make no tags/pushes/releases.
  -h, --help       Show this help.

Idempotent: if the tag already exists it is reused (must point at HEAD).
"""
from __future__ import annotations

import re
import shutil
import sys
import urllib.parse

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


def remote_refs(ls_remote: str) -> dict[str, str]:
    """`git ls-remote` output -> {ref name: object id} (peeled tags keep their `^{}` suffix)."""
    refs: dict[str, str] = {}
    for line in ls_remote.splitlines():
        oid, _, name = line.partition("\t")
        if name:
            refs[name.strip()] = oid.strip()
    return refs


def release_page_url(remote_url: str, tag: str, body: str) -> str | None:
    """The pre-filled `releases/new` page for a github.com remote; None for any other host."""
    m = re.fullmatch(r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
                     r"([^/\s]+)/([^/\s]+?)(?:\.git)?/?", remote_url)
    if m is None:
        return None
    query = urllib.parse.urlencode({"tag": tag, "title": tag, "body": body})
    return f"https://github.com/{m.group(1)}/{m.group(2)}/releases/new?{query}"


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

    # --- Read the push back: what GitHub holds, not what we sent -----------------
    if not dry_run:
        head = git("rev-parse", "HEAD").stdout.strip()
        held = remote_refs(git("ls-remote", remote).stdout)
        got_branch = held.get(f"refs/heads/{branch}", "(missing)")
        got_tag = held.get(f"refs/tags/{tag}^{{}}", held.get(f"refs/tags/{tag}", "(missing)"))
        print(f"{remote}: {branch} = {got_branch[:12]}, {tag}^{{}} = {got_tag[:12]}, "
              f"HEAD = {head[:12]}")
        if got_branch != head or got_tag != head:
            fail(f"{remote} does not hold {branch} and {tag} at HEAD after the push")

    # --- The GitHub Release page is an OWNER item (workspace H30: no GitHub CLI) --
    if make_release:
        body = notes or (
            f"Release {tag} of universalWasmLoader-py — Python port of the Universal WASM Loader."
        )
        url = release_page_url(git("remote", "get-url", remote).stdout.strip(), tag, body)
        if url:
            print("GitHub Release page: created by the Publish workflow's `release` job after "
                  "the upload.")
            print(f"OWNER, only if that job fails (web UI; skip if the page exists): {url}")

    print(f"Done: {tag}")
    print("The tag push starts the Publish workflow, which uploads to PyPI (it pauses for an "
          "approval only if the `pypi` environment requires a reviewer). "
          "(Local fallback: pixi run python scripts/publish.py)")


if __name__ == "__main__":
    main(sys.argv[1:])
