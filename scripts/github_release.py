"""CI's release steps through GitHub's REST API (stdlib only), in the owner's order (workspace
letter H33, D1): checks → `tag` → `page` → `dispatch` (the PyPI publish, on the tag).

Run by `.github/workflows/publish.yml`'s jobs with each job's own `GITHUB_TOKEN`. Never the GitHub
CLI (workspace H30). Each job fetches this file from the repository at the checked commit, so no
other code runs beside a write token (C30).

  tag       the annotated tag on --sha (H33 U6): there = done, elsewhere = refused, read back
  page      the GitHub Release page (U7), below; the default when no command is given
  check     read-only: the tag peels to --sha AND its page exists — the publish run's guard
  dispatch  start publish.yml ON THE TAG (the `pypi` environment admits only `v*` refs), then
            wait (--wait seconds, fatal) until PyPI's project list names the version

The page, in order (workspace Tooling rule 9's hazard, found by loader-rs):
  1. the tag must already exist on GitHub and peel (annotated tags followed) to --sha, because
     `POST /releases` would otherwise CREATE a missing tag at the default branch;
  2. an existing Release for the tag means done — nothing is changed, so re-runs are safe;
  3. otherwise the Release is created (generated notes, a PyPI link on top), read back, and the
     tag is checked again.
Only HTTP 404 means "absent"; any other unexpected status is an error. Every request carries
its own 30 s limit, request to last byte (workspace best-practice 7.21; letter H32).

Usage: python scripts/github_release.py [tag|page|check|dispatch] --repo OWNER/NAME
         --tag vX.Y.Z --sha COMMIT [--dry-run] [--wait SECONDS]
  env GITHUB_TOKEN   required for writes (reads work without it on a public repo)
  env GITHUB_API_URL default https://api.github.com (a mock server in the tests)
  env PYPI_URL       default https://pypi.org (a mock server in the tests)
Exit 0 = done (made now or before) / dry run; 1 = refused or failed.
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, TypeVar

PYPI_PROJECT = "universal-wasm-loader"
T = TypeVar("T")


class ApiError(Exception):
    pass


def with_limit(fn: Callable[[], T], limit: float, what: str) -> T:
    """Run `fn` (a request AND its full body read) under ONE total time limit — request to last
    byte (workspace best-practice 7.21). `urlopen(timeout=)` limits each socket operation only, so
    a server that drips its body would never trip it. On timeout the worker thread is abandoned
    (a daemon; this is a short-lived CI process)."""
    box: dict[str, Any] = {}

    def run() -> None:
        try:
            box["value"] = fn()
        except BaseException as e:  # re-raised in the caller's thread below
            box["error"] = e

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(limit)
    if worker.is_alive():
        raise TimeoutError(f"{what}: timed out after {limit:g} s (request to last byte)")
    if "error" in box:
        raise box["error"]
    return box["value"]  # type: ignore[no-any-return]


class Api:
    def __init__(self, base: str, token: str | None, limit: float = 30.0) -> None:
        self.base = base.rstrip("/")
        self.token = token
        self.limit = limit

    def call(self, method: str, path: str, body: dict[str, Any] | None = None
             ) -> tuple[int, Any]:
        """(status, JSON) for 2xx and 404; ApiError for anything else, a timeout included."""
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

        def exchange() -> tuple[int, Any]:
            try:
                # The socket timeout is a backstop only, set LOOSER than the total limit so the
                # total deadline always decides (equal values raced; seen once under load).
                with urllib.request.urlopen(req, timeout=self.limit + 5) as resp:
                    raw = resp.read()
                    return resp.status, json.loads(raw) if raw else None
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return 404, None
                detail = e.read().decode("utf-8", "replace")[:300]
                raise ApiError(f"{method} {path}: HTTP {e.code} {detail}") from e

        try:
            return with_limit(exchange, self.limit, f"{method} {self.base}{path}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
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


TAG_PATTERN = re.compile(r"v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?")


def say(msg: str) -> None:
    print(f"github_release: {msg}", flush=True)


def make_tag(repo: str, tag: str, sha: str, dry_run: bool, api: Api) -> int:
    """H33 U6: CI's annotated tag on `sha` — there already = done (a re-run), elsewhere = refused
    (a published tag never moves); else `POST git/tags` + `POST git/refs`, then read back."""
    if TAG_PATTERN.fullmatch(tag) is None:
        say(f"refused: {tag!r} is not a release tag v<semver>")
        return 1
    peeled = tag_commit(api, repo, tag)
    if peeled == sha:
        say(f"tag {tag} already on {sha} — nothing to do")
        return 0
    if peeled is not None:
        say(f"refused: tag {tag} exists on {peeled}, not {sha}; a published tag never moves")
        return 1
    if dry_run:
        say(f"dry run: would create the annotated tag {tag} on {sha}")
        return 0
    if not api.token:
        say("refused: no GITHUB_TOKEN")
        return 1
    status, obj = api.call("POST", f"/repos/{repo}/git/tags", {
        "tag": tag, "message": f"universalWasmLoader-py {tag}", "object": sha, "type": "commit",
    })
    if status != 201:
        say(f"failed: POST git/tags answered {status}")
        return 1
    status, _ = api.call("POST", f"/repos/{repo}/git/refs",
                         {"ref": f"refs/tags/{tag}", "sha": obj["sha"]})
    if status != 201:
        say(f"failed: POST git/refs answered {status}")
        return 1
    if tag_commit(api, repo, tag) != sha:
        say(f"failed: tag {tag} does not peel to {sha} after it was made")
        return 1
    say(f"created the annotated tag {tag} (object {obj['sha'][:12]}) on {sha}")
    return 0


def check(repo: str, tag: str, sha: str, api: Api) -> int:
    """The owner's order, asserted by the publish run: the tag peels to `sha` AND its page exists
    (checks → tag → page → publish). Read-only."""
    peeled = tag_commit(api, repo, tag)
    if peeled != sha:
        say(f"refused: tag {tag} is {peeled or 'absent'}, not {sha}")
        return 1
    page = find_release(api, repo, tag)
    if page is None or page.get("draft"):
        say(f"refused: no published Release page for {tag} yet (the page comes before publish)")
        return 1
    say(f"order holds: {tag} = {sha[:12]}, page by {(page.get('author') or {}).get('login')}")
    return 0


def pypi_lists(version: str, limit: float = 30) -> bool:
    """Does PyPI's PROJECT release list name `version`? (Never the version's own URL before it
    exists: a caching registry caches a miss — workspace best-practices L3.)"""
    url = os.environ.get("PYPI_URL", "https://pypi.org").rstrip("/") + f"/pypi/{PYPI_PROJECT}/json"

    def fetch() -> bool:
        try:
            with urllib.request.urlopen(url, timeout=limit + 5) as resp:
                return version in json.load(resp).get("releases", {})
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            raise ApiError(f"GET {url}: HTTP {e.code}") from e

    return with_limit(fetch, limit, url)


def dispatch(repo: str, tag: str, sha: str, dry_run: bool, api: Api, wait: float,
             poll: float = 15.0) -> int:
    """Start the publish ON THE TAG (`workflow_dispatch` of publish.yml with ref = the tag): the
    `pypi` environment admits only `v*` refs, and a GITHUB_TOKEN-made tag starts no run. Then wait
    (fatal) until PyPI lists the version, so this run's result is the publish's."""
    if check(repo, tag, sha, api) != 0:
        return 1
    if dry_run:
        say(f"dry run: would dispatch publish.yml on {tag}")
        return 0
    if not api.token:
        say("refused: no GITHUB_TOKEN")
        return 1
    if pypi_lists(tag[1:]):
        say(f"PyPI already lists {tag[1:]} — nothing to dispatch")
        return 0
    status, _ = api.call("POST", f"/repos/{repo}/actions/workflows/publish.yml/dispatches",
                         {"ref": tag, "inputs": {"ref": tag}})
    if status != 204:
        say(f"failed: the dispatch answered {status}")
        return 1
    say(f"dispatched publish.yml on {tag}; waiting up to {wait:g} s for PyPI to list {tag[1:]}")
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        time.sleep(min(poll, max(0.0, deadline - time.monotonic())))
        try:
            if pypi_lists(tag[1:]):
                say(f"PyPI lists {tag[1:]}")
                return 0
        except (ApiError, TimeoutError, OSError) as e:
            say(f"(PyPI not readable yet: {e})")
    say(f"failed: PyPI did not list {tag[1:]} within {wait:g} s — see the dispatched run")
    return 1


COMMANDS = ("tag", "page", "check", "dispatch")


def main(argv: list[str]) -> int:
    command = argv[0] if argv and argv[0] in COMMANDS else "page"
    rest = argv[1:] if argv and argv[0] in COMMANDS else argv
    args = {"--repo": "", "--tag": "", "--sha": "", "--wait": "1200"}
    dry_run = False
    it = iter(rest)
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
    repo, tag, sha = args["--repo"], args["--tag"], args["--sha"]
    try:
        if command == "tag":
            return make_tag(repo, tag, sha, dry_run, api)
        if command == "check":
            return check(repo, tag, sha, api)
        if command == "dispatch":
            return dispatch(repo, tag, sha, dry_run, api, float(args["--wait"]))
        return run(repo, tag, sha, dry_run, api)
    except ApiError as e:
        print(f"github_release: error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
