"""Which of this release's dist files does PyPI still need? (stdlib only)

An upload sends the sdist and the wheel one file at a time, so a failure between them leaves a
version half-published, and PyPI never accepts a file name twice (a removed one included). The
publish job (the ONLY publish path since workspace H33: nothing uploads from a workstation) asks
this module first and uploads ONLY the missing files. It fetches this file by the verified commit
and runs it (it is never taken from a job whose output third-party code could change).
After the upload, `readback` is the fatal U8 read-back: every built file served by PyPI, each
with a PEP 740 provenance from this repo's publish.yml in the `pypi` environment.

Only HTTP 404 means "this version has no files yet"; any other answer is an error, never read as
"not published" (the masked-HTTP-error class). The request carries one 30 s limit, request to
last byte (workspace best-practice 7.21). A file already on PyPI is skipped by NAME. Its
sha256 is compared and reported: the build is not byte-reproducible across machines (measured
2026-11-08: the CI and a local build of the same commit differ), so a re-run that rebuilds is
expected to differ, and the commit identity is checked elsewhere.

Usage: python scripts/pypi_files.py <package> <version> <dist-dir>
  stdout: one path per line, the files to upload (none: the version is complete on PyPI)
  stderr: what was skipped and why
  exit 0 = a plan; 1 = a dist file that does not belong to <package> <version>; 2 = PyPI error
       python scripts/pypi_files.py readback <package> <version> <dist-dir> --repo OWNER/NAME
         [--workflow publish.yml] [--environment pypi] [--wait 300]
  exit 0 = served and attested; 1 = not within --wait (fatal)
  env PYPI_URL default https://pypi.org (a mock server in the tests)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


class PyPIError(Exception):
    """PyPI gave no usable answer (an HTTP status other than 200 / 404, or no connection)."""


def with_limit(fn: Callable[[], T], limit: float, what: str) -> T:
    """Run `fn` (a request AND its full body read) under ONE total time limit — request to last
    byte (workspace best-practice 7.21). `urlopen(timeout=)` limits each socket operation only, so
    a server that drips its body would never trip it. On timeout the worker thread is abandoned
    (a daemon; this is a short-lived process)."""
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


def pypi_base() -> str:
    return os.environ.get("PYPI_URL", "https://pypi.org").rstrip("/")


def get_json(url: str, timeout: float = 30) -> Any:
    """The JSON at `url`, None on 404; PyPIError for any other answer or no answer in time."""

    def fetch() -> Any:
        try:
            with urllib.request.urlopen(url, timeout=timeout + 5) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise PyPIError(f"PyPI answered HTTP {e.code} for {url}") from e

    try:
        return with_limit(fetch, timeout, url)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise PyPIError(f"could not reach PyPI for {url}: {e}") from e


def readback_problems(
    package: str, version: str, local: dict[str, str], repo: str, workflow: str,
    environment: str,
) -> list[str]:
    """What is still wrong with `version` on PyPI (workspace H33 U8, fatal read-back): every built
    file must be served, and each must carry a PEP 740 provenance from THIS repo's `workflow` in
    `environment` (PyPI's integrity API). [] = all good."""
    remote = remote_files(package, version)
    if remote is None:
        return [f"PyPI does not serve {package} {version} yet"]
    problems: list[str] = []
    for name in sorted(local):
        if name not in remote:
            problems.append(f"{name}: not served by PyPI")
            continue
        url = f"{pypi_base()}/integrity/{package}/{version}/{name}/provenance"
        doc = get_json(url)
        publishers = [b.get("publisher") or {} for b in (doc or {}).get("attestation_bundles", [])]
        ours = [p for p in publishers
                if p.get("kind") == "GitHub"
                and str(p.get("repository", "")).lower() == repo.lower()
                and p.get("workflow") == workflow and p.get("environment") == environment]
        if not ours:
            problems.append(f"{name}: no PEP 740 provenance from {repo} {workflow} [{environment}]"
                            f" (found: {publishers or 'none'})")
    return problems


def remote_files(package: str, version: str, timeout: float = 30) -> dict[str, str] | None:
    """{filename: sha256} of `version` on PyPI; None when PyPI answers 404 (no files yet).
    `timeout` is the TOTAL limit, request to last byte."""
    url = f"{pypi_base()}/pypi/{package}/{version}/json"

    def fetch() -> dict[str, Any] | None:
        try:
            # The socket timeout is a backstop only, LOOSER than the total limit, so the total
            # deadline always decides (equal values race).
            with urllib.request.urlopen(url, timeout=timeout + 5) as resp:
                doc: dict[str, Any] = json.load(resp)
                return doc
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise PyPIError(f"PyPI answered HTTP {e.code} for {url}") from e

    try:
        doc = with_limit(fetch, timeout, url)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise PyPIError(f"could not reach PyPI for {url}: {e}") from e
    if doc is None:
        return None
    return {u["filename"]: u["digests"]["sha256"] for u in doc.get("urls", [])}


def dist_prefix(package: str, version: str) -> str:
    """The file-name prefix of every dist of `package` `version` (PEP 625 / PEP 427)."""
    return f"{re.sub(r'[-_.]+', '_', package).lower()}-{version}"


def plan(
    local: dict[str, str], remote: dict[str, str] | None
) -> tuple[list[str], list[str]]:
    """(local file names to upload, notes). `local` and `remote` map file name -> sha256."""
    if remote is None:
        return sorted(local), ["PyPI has no files for this version yet"]
    upload: list[str] = []
    notes: list[str] = []
    for name in sorted(local):
        if name not in remote:
            upload.append(name)
        elif remote[name] == local[name]:
            notes.append(f"{name}: already on PyPI, same bytes — skipped")
        else:
            notes.append(f"{name}: already on PyPI with DIFFERENT bytes (a rebuild of the same "
                         "commit; the build is not byte-reproducible) — skipped, never "
                         "re-uploaded")
    for name in sorted(set(remote) - set(local)):
        notes.append(f"{name}: on PyPI, not in this build — left as it is")
    return upload, notes


def local_files(dist: Path, package: str, version: str) -> dict[str, str]:
    """{filename: sha256} of `dist`; raises ValueError for a file of another package / version."""
    prefix = dist_prefix(package, version)
    found: dict[str, str] = {}
    for path in sorted(dist.iterdir()):
        if not path.is_file() or path.name.endswith(".publish.attestation"):
            continue  # a PEP 740 attestation travels WITH its dist; it is not one
        if not (path.name.startswith(prefix + "-") or path.name == prefix + ".tar.gz"):
            raise ValueError(f"{path.name} is not a dist of {package} {version}")
        found[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not found:
        raise ValueError(f"{dist} holds no dist files")
    return found


def readback_main(argv: list[str], poll: float = 15.0) -> int:
    """`readback <package> <version> <dist> --repo R [--workflow W] [--environment E]
    [--wait SECONDS]`: poll until readback_problems() is empty; exit 1 (fatal) if it never is."""
    opts = {"--repo": "", "--workflow": "publish.yml", "--environment": "pypi", "--wait": "300"}
    positional: list[str] = []
    it = iter(argv)
    for arg in it:
        if arg in opts:
            opts[arg] = next(it, "")
        else:
            positional.append(arg)
    if len(positional) != 3 or not opts["--repo"]:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    package, version, dist = positional[0], positional[1], Path(positional[2])
    try:
        local = local_files(dist, package, version)
    except ValueError as e:
        print(f"pypi_files: {e}", file=sys.stderr)
        return 1
    deadline = time.monotonic() + float(opts["--wait"])
    while True:
        try:
            problems = readback_problems(package, version, local, opts["--repo"],
                                         opts["--workflow"], opts["--environment"])
        except PyPIError as e:
            problems = [str(e)]
        if not problems:
            print(f"pypi_files: read back {package} {version}: {len(local)} file(s) served, each "
                  f"with a PEP 740 provenance from {opts['--repo']} {opts['--workflow']}")
            return 0
        if time.monotonic() >= deadline:
            for p in problems:
                print(f"pypi_files: READ-BACK FAILED: {p}", file=sys.stderr)
            return 1
        time.sleep(min(poll, max(0.0, deadline - time.monotonic())))


def main(argv: list[str]) -> int:
    if argv[:1] == ["readback"]:
        return readback_main(argv[1:])
    if len(argv) != 3 or argv[0] in ("-h", "--help"):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    package, version, dist = argv[0], argv[1], Path(argv[2])
    try:
        local = local_files(dist, package, version)
    except ValueError as e:
        print(f"pypi_files: {e}", file=sys.stderr)
        return 1
    try:
        remote = remote_files(package, version)
    except PyPIError as e:
        print(f"pypi_files: {e}", file=sys.stderr)
        return 2
    upload, notes = plan(local, remote)
    for note in notes:
        print(f"pypi_files: {note}", file=sys.stderr)
    for name in upload:
        print(dist / name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
