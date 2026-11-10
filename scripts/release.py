"""Release universalWasmLoader-py: push `main` with its bump commit — and nothing else.

Workspace letter H33, the owner's order (2026-11-10, D1): "the CI to check first, then push the
tag, and then create the release page from the tag, then publish the package to the registry".
So this script makes and pushes NO tag (U4): pushing `main` whose `pyproject.toml` version has no
tag yet IS the release request, and `.github/workflows/publish.yml` does the rest — `checks`, then
CI's annotated tag, then the GitHub Release page, then the PyPI publish (on the tag). Nothing is
ever uploaded from this machine (H33 rule 3); a published tag never moves.

Guards, all before anything is pushed:
  1. the tree is clean (untracked files count);
  2. on `main`;
  3. HEAD = GitHub's `main` + exactly ONE commit, `bump to v<version>` (scripts/bump_version.py),
     touching only the version files;
  4. the tag v<version> absent locally and on GitHub;
  5. PyPI does not serve <version> (the PROJECT's release list, never the version's own URL: a
     caching registry caches a miss — workspace best-practices L3, loader-go);
  6. a cold gate: `pixi run gate`, `compat.py --release` on the candidate, a fresh build,
     `twine check`.
Then `git push <remote> main`, read back with `git ls-remote` (main = HEAD, and still no tag).

Usage: pixi run python scripts/release.py [--dry-run] [--remote <name>]
  --dry-run        Run every guard and the gate; push nothing.
  --remote <name>  Git remote to push to (default: origin).
  -h, --help       Show this help.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

from _common import ROOT, fail, git, print_dirty_tree, read_version, tag_exists, tree_is_dirty
from pypi_files import with_limit

PKG = "universal-wasm-loader"
VERSION_FILES = {"pyproject.toml", "pixi.toml", "README.md"}  # README: a major's stamped row


def remote_refs(ls_remote: str) -> dict[str, str]:
    """`git ls-remote` output -> {ref name: object id} (peeled tags keep their `^{}` suffix)."""
    refs: dict[str, str] = {}
    for line in ls_remote.splitlines():
        oid, _, name = line.partition("\t")
        if name:
            refs[name.strip()] = oid.strip()
    return refs


def pypi_versions(package: str, limit: float = 30) -> set[str]:
    """The versions PyPI lists for `package` (the project JSON; 404 = no project yet)."""
    url = f"https://pypi.org/pypi/{package}/json"

    def fetch() -> set[str]:
        try:
            with urllib.request.urlopen(url, timeout=limit + 5) as resp:
                return set(json.load(resp).get("releases", {}))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return set()
            raise RuntimeError(f"PyPI answered HTTP {e.code} for {url}") from e

    return with_limit(fetch, limit, url)


def step(cmd: list[str], what: str) -> None:
    print(f"+ {' '.join(cmd)}", flush=True)
    if subprocess.run(cmd, cwd=ROOT).returncode != 0:
        fail(f"{what} failed — nothing was pushed")


def main(argv: list[str]) -> None:
    dry_run, remote = False, "origin"
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--remote":
            remote = args.pop(0) if args else ""
        elif arg in ("-h", "--help"):
            print(__doc__.strip())
            sys.exit(0)
        else:
            fail(f"unknown argument: {arg}", 2)
    if shutil.which("pixi") is None:
        fail("pixi is required (this is a pixi project)")

    version = read_version(ROOT / "pyproject.toml")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        fail(f"pyproject.toml's version is not X.Y.Z: {version!r}")
    tag = f"v{version}"
    print(f"Releasing {tag} (pyproject.toml){' — DRY RUN' if dry_run else ''}", flush=True)

    # 1. clean tree (porcelain lists untracked files too)
    if tree_is_dirty():
        print("error: the tree is not clean (untracked files count):", file=sys.stderr)
        print_dirty_tree()
        sys.exit(1)

    # 2. on main
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch != "main":
        fail(f"on branch {branch!r}, not main (merge into main first: the owner's \"push\")")

    # 3. HEAD = GitHub's main + exactly the bump commit
    held = remote_refs(git("ls-remote", remote).stdout)
    remote_main = held.get("refs/heads/main", "")
    head = git("rev-parse", "HEAD").stdout.strip()
    parent = git("rev-parse", "-q", "--verify", "HEAD^").stdout.strip()
    subject = git("log", "-1", "--format=%s").stdout.strip()
    changed = set(git("diff", "--name-only", "HEAD^", "HEAD").stdout.split())
    if not remote_main:
        fail(f"{remote} has no main (could not read it with git ls-remote)")
    if remote_main == head:
        fail(f"{remote}'s main is already HEAD — bump first (scripts/bump_version.py <level>)")
    if parent != remote_main:
        fail(f"HEAD must be {remote}'s main ({remote_main[:12]}) + exactly the bump commit; "
             f"HEAD^ is {parent[:12]} (merge and push other work first)")
    if subject != f"bump to {tag}":
        fail(f"HEAD is {subject!r}, not 'bump to {tag}' (scripts/bump_version.py makes it)")
    if not changed or not changed <= VERSION_FILES:
        fail(f"the bump commit touches more than the version files: {sorted(changed)}")

    # 4. the tag absent here and on GitHub (CI makes it; a published tag never moves)
    if tag_exists(tag):
        fail(f"tag {tag} exists locally — CI makes the tag (delete a stray local tag first)")
    if f"refs/tags/{tag}" in held:
        fail(f"tag {tag} already exists on {remote}")

    # 5. PyPI does not serve the version
    try:
        if version in pypi_versions(PKG):
            fail(f"PyPI already lists {PKG} {version}")
    except (RuntimeError, OSError) as e:
        fail(f"could not ask PyPI: {e}")

    # 6. the cold gate
    step(["pixi", "run", "gate"], "the gate")
    step(["pixi", "run", "python", "scripts/compat.py", "--release"], "compat --release")
    shutil.rmtree(ROOT / "dist", ignore_errors=True)
    step(["pixi", "run", "python", "-m", "build"], "the build")
    dists = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "dist").iterdir())
    step(["pixi", "run", "python", "-m", "twine", "check", *dists], "twine check")

    if dry_run:
        print(f"Dry run: every guard and the gate passed; nothing pushed. {tag} is ready.")
        return

    # push main ONLY, then read it back
    step(["git", "push", remote, "main"], "git push")
    back = remote_refs(git("ls-remote", remote).stdout)
    print(f"{remote}: main = {back.get('refs/heads/main', '(missing)')[:12]}, HEAD = {head[:12]}, "
          f"tag {tag}: {'PRESENT' if f'refs/tags/{tag}' in back else 'absent (CI makes it)'}")
    if back.get("refs/heads/main") != head:
        fail(f"{remote} does not hold main at HEAD after the push")
    if f"refs/tags/{tag}" in back:
        fail(f"tag {tag} appeared on {remote} — only CI may make it")
    print(f"Done: main pushed. CI now checks, tags {tag}, makes the page and publishes — "
          "watch the Publish run for this commit.")


if __name__ == "__main__":
    main(sys.argv[1:])
