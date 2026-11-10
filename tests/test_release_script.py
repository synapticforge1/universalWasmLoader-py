"""scripts/release.py helpers: the ls-remote read-back and PyPI's project release list (H33 U4).
The guards themselves are rehearsed end to end against a scratch bare origin (cmem/release.md)."""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import urllib.error
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"


def _load() -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))  # release.py imports _common / pypi_files beside it
    spec = importlib.util.spec_from_file_location("release_script", SCRIPTS / "release.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rel = _load()

LS_REMOTE = (
    "21e680a433345a63e653fd920ad113332c8bf1d9\tHEAD\n"
    "21e680a433345a63e653fd920ad113332c8bf1d9\trefs/heads/main\n"
    "c41c8b9f0b112e41840f3c6841f80cdb9657d841\trefs/tags/v2.0.0\n"
    "21e680a433345a63e653fd920ad113332c8bf1d9\trefs/tags/v2.0.0^{}\n"
)


def test_remote_refs_keeps_peeled_tags_apart() -> None:
    refs = rel.remote_refs(LS_REMOTE)
    assert refs["refs/heads/main"].startswith("21e680a")
    assert refs["refs/tags/v2.0.0"].startswith("c41c8b9")  # the annotated tag object
    assert refs["refs/tags/v2.0.0^{}"].startswith("21e680a")  # the commit it peels to


def test_release_makes_no_tag_and_uploads_nothing() -> None:
    # H33 D1 / rule 3: the release script pushes main only — no `git tag`, no twine upload.
    src = (SCRIPTS / "release.py").read_text(encoding="utf-8")
    code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("#"))
    assert '"tag"' not in code and "'tag'" not in code
    assert "upload" not in code.split('"""', 2)[2]  # outside the docstring
    assert not (SCRIPTS / "publish.py").exists()


def test_pypi_versions_reads_the_project_list(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake(url: Any, **_: Any) -> Any:
        seen.append(str(url))
        return io.BytesIO(json.dumps({"releases": {"2.0.2": [], "2.0.3": []}}).encode())

    monkeypatch.setattr(rel.urllib.request, "urlopen", fake)
    assert rel.pypi_versions("universal-wasm-loader") == {"2.0.2", "2.0.3"}
    # the PROJECT list, never the version's own URL (a caching registry caches a miss)
    assert seen == ["https://pypi.org/pypi/universal-wasm-loader/json"]


def test_pypi_versions_404_is_no_project_other_errors_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake404(*_: Any, **__: Any) -> Any:
        raise urllib.error.HTTPError("u", 404, "x", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(rel.urllib.request, "urlopen", fake404)
    assert rel.pypi_versions("nope") == set()

    def fake500(*_: Any, **__: Any) -> Any:
        raise urllib.error.HTTPError("u", 500, "x", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(rel.urllib.request, "urlopen", fake500)
    with pytest.raises(RuntimeError, match="HTTP 500"):
        rel.pypi_versions("universal-wasm-loader")
