"""Which of this release's dist files does PyPI still need? (stdlib only)

An upload sends the sdist and the wheel one file at a time, so a failure between them leaves a
version half-published, and PyPI never accepts a file name twice (a removed one included). Both
publish paths ask this module first and upload ONLY the missing files:
  - `.github/workflows/publish.yml`'s publish job fetches this file by the verified commit and
    runs it (it is never taken from the checks job, whose output third-party code could change);
  - `scripts/publish.py` imports it.

Only HTTP 404 means "this version has no files yet"; any other answer is an error, never read as
"not published" (the masked-HTTP-error class). A file already on PyPI is skipped by NAME. Its
sha256 is compared and reported: the build is not byte-reproducible across machines (measured
2026-11-08: the CI and a local build of the same commit differ), so a re-run that rebuilds is
expected to differ, and the commit identity is checked elsewhere.

Usage: python scripts/pypi_files.py <package> <version> <dist-dir>
  stdout: one path per line, the files to upload (none: the version is complete on PyPI)
  stderr: what was skipped and why
  exit 0 = a plan; 1 = a dist file that does not belong to <package> <version>; 2 = PyPI error
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class PyPIError(Exception):
    """PyPI gave no usable answer (an HTTP status other than 200 / 404, or no connection)."""


def remote_files(package: str, version: str, timeout: float = 30) -> dict[str, str] | None:
    """{filename: sha256} of `version` on PyPI; None when PyPI answers 404 (no files yet)."""
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            doc: dict[str, Any] = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise PyPIError(f"PyPI answered HTTP {e.code} for {url}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise PyPIError(f"could not reach PyPI for {url}: {e}") from e
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
        if not path.is_file():
            continue
        if not (path.name.startswith(prefix + "-") or path.name == prefix + ".tar.gz"):
            raise ValueError(f"{path.name} is not a dist of {package} {version}")
        found[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not found:
        raise ValueError(f"{dist} holds no dist files")
    return found


def main(argv: list[str]) -> int:
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
