"""Create the GitHub Release page for a tag through GitHub's REST API (stdlib only).

Run by `.github/workflows/publish.yml`'s `release` job after the PyPI upload, with the job's own
`GITHUB_TOKEN` (`contents: write`). Never the GitHub CLI (workspace H30). The job fetches this file
from the repository at the checked commit, so no other code runs beside the write token (C30).

Safety, in order (workspace Tooling rule 9's hazard, found by loader-rs):
  1. the tag must already exist on GitHub and peel (annotated tags followed) to --sha, because
     `POST /releases` would otherwise CREATE a missing tag at the default branch;
  2. an existing Release for the tag means done — nothing is changed, so re-runs are safe;
  3. otherwise the Release is created (generated notes, a PyPI link on top), read back, and the
     tag is checked again.
Only HTTP 404 means "absent"; any other unexpected status is an error.

Usage: python scripts/github_release.py --repo OWNER/NAME --tag vX.Y.Z --sha COMMIT [--dry-run]
  env GITHUB_TOKEN   required unless --dry-run (reads work without it on a public repo)
  env GITHUB_API_URL default https://api.github.com (a mock server in the tests)
Exit 0 = the Release exists (created now or before) / dry run; 1 = refused or failed.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any

PYPI_PROJECT = "universal-wasm-loader"


class ApiError(Exception):
    pass


class Api:
    def __init__(self, base: str, token: str | None) -> None:
        self.base = base.rstrip("/")
        self.token = token

    def call(self, method: str, path: str, body: dict[str, Any] | None = None
             ) -> tuple[int, Any]:
        """(status, JSON) for 2xx and 404; raises ApiError for anything else."""
        req = urllib.request.Request(
            self.base + path,
            method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28",
                     "User-Agent": "universalWasmLoader-py-release"},
        )
        if body is not None:
            req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, None
            detail = e.read().decode("utf-8", "replace")[:300]
            raise ApiError(f"{method} {path}: HTTP {e.code} {detail}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise ApiError(f"{method} {path}: {e}") from e


def tag_commit(api: Api, repo: str, tag: str) -> str | None:
    """The commit `tag` peels to on GitHub (annotated tags followed); None if the tag is absent."""
    status, ref = api.call("GET", f"/repos/{repo}/git/ref/tags/{tag}")
    if status == 404:
        return None
    obj = ref["object"]
    for _ in range(5):  # a tag of a tag is legal; never loop forever
        if obj["type"] == "commit":
            return str(obj["sha"])
        if obj["type"] != "tag":
            raise ApiError(f"tag {tag} points at a {obj['type']}, not a commit")
        status, tag_obj = api.call("GET", f"/repos/{repo}/git/tags/{obj['sha']}")
        if status == 404:
            raise ApiError(f"tag object {obj['sha']} of {tag} not found")
        obj = tag_obj["object"]
    raise ApiError(f"tag {tag}: too many nested tag objects")


def find_release(api: Api, repo: str, tag: str) -> dict[str, Any] | None:
    status, rel = api.call("GET", f"/repos/{repo}/releases/tags/{tag}")
    return None if status == 404 else rel


def run(repo: str, tag: str, sha: str, dry_run: bool, api: Api) -> int:
    def say(msg: str) -> None:
        print(f"github_release: {msg}", flush=True)

    if re.fullmatch(r"v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", tag) is None:
        say(f"refused: {tag!r} is not a release tag v<semver>")
        return 1
    peeled = tag_commit(api, repo, tag)
    if peeled is None:
        say(f"refused: tag {tag} does not exist on GitHub (a POST would create it)")
        return 1
    if peeled != sha:
        say(f"refused: tag {tag} is {peeled}, not the checked commit {sha}")
        return 1
    existing = find_release(api, repo, tag)
    if existing is not None:
        say(f"Release {tag} already exists ({existing.get('html_url')}) — nothing to do")
        return 0
    if dry_run:
        say(f"dry run: would create Release {tag} at {sha}")
        return 0
    if not api.token:
        say("refused: no GITHUB_TOKEN")
        return 1
    version = tag[1:]
    body = {
        "tag_name": tag,
        "name": tag,
        "body": f"PyPI: https://pypi.org/project/{PYPI_PROJECT}/{version}/",
        "generate_release_notes": True,
        "draft": False,
        "prerelease": False,
    }
    status, created = api.call("POST", f"/repos/{repo}/releases", body)
    if status != 201:
        say(f"failed: POST /releases answered {status}")
        return 1
    back = find_release(api, repo, tag)
    if back is None or back.get("tag_name") != tag or back.get("draft"):
        say(f"failed: Release {tag} not readable as published after the POST")
        return 1
    if tag_commit(api, repo, tag) != sha:
        say(f"failed: tag {tag} no longer peels to {sha} after the POST")
        return 1
    say(f"created Release {tag}: {back.get('html_url')} (id {created.get('id')})")
    return 0


def main(argv: list[str]) -> int:
    args = {"--repo": "", "--tag": "", "--sha": ""}
    dry_run = False
    it = iter(argv)
    for arg in it:
        if arg == "--dry-run":
            dry_run = True
        elif arg in args:
            args[arg] = next(it, "")
        else:
            print(__doc__.strip(), file=sys.stderr)
            return 1
    if not all(args.values()):
        print(__doc__.strip(), file=sys.stderr)
        return 1
    api = Api(os.environ.get("GITHUB_API_URL", "https://api.github.com"),
              os.environ.get("GITHUB_TOKEN") or None)
    try:
        return run(args["--repo"], args["--tag"], args["--sha"], dry_run, api)
    except ApiError as e:
        print(f"github_release: error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
