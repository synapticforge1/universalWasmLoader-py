"""scripts/pypi_files.py: which dist files PyPI still needs (no network: urlopen is stubbed)."""
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

SCRIPT = Path(__file__).parent.parent / "scripts" / "pypi_files.py"
PKG, VER = "universal-wasm-loader", "2.0.0"
WHL, SDIST = "universal_wasm_loader-2.0.0-py3-none-any.whl", "universal_wasm_loader-2.0.0.tar.gz"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pypi_files", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pypi_files"] = mod
    spec.loader.exec_module(mod)
    return mod


pf = _load()


def test_nothing_on_pypi_uploads_everything() -> None:
    upload, _ = pf.plan({WHL: "a", SDIST: "b"}, None)
    assert sorted(upload) == sorted([SDIST, WHL])


def test_complete_on_pypi_uploads_nothing() -> None:
    upload, notes = pf.plan({WHL: "a", SDIST: "b"}, {WHL: "a", SDIST: "b"})
    assert upload == []
    assert all("same bytes" in n for n in notes)


def test_half_published_uploads_only_the_missing_file() -> None:
    # The wheel went up, the sdist upload failed: a re-run sends the sdist only.
    upload, _ = pf.plan({WHL: "a", SDIST: "b"}, {WHL: "a"})
    assert upload == [SDIST]


def test_rebuilt_file_with_other_bytes_is_skipped_not_reuploaded() -> None:
    upload, notes = pf.plan({WHL: "rebuilt", SDIST: "b"}, {WHL: "first"})
    assert upload == [SDIST]
    assert any("DIFFERENT bytes" in n and WHL in n for n in notes)


def test_local_files_refuses_another_version(tmp_path: Path) -> None:
    (tmp_path / WHL).write_bytes(b"w")
    (tmp_path / "universal_wasm_loader-1.1.1.tar.gz").write_bytes(b"s")
    with pytest.raises(ValueError, match="not a dist of universal-wasm-loader 2.0.0"):
        pf.local_files(tmp_path, PKG, VER)


def test_local_files_refuses_an_empty_dist(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no dist files"):
        pf.local_files(tmp_path, PKG, VER)


def test_local_files_hashes(tmp_path: Path) -> None:
    (tmp_path / WHL).write_bytes(b"w")
    (tmp_path / SDIST).write_bytes(b"s")
    got = pf.local_files(tmp_path, PKG, VER)
    assert set(got) == {WHL, SDIST}
    assert len(got[WHL]) == 64


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://pypi.org/x", code, "x", {}, None)  # type: ignore[arg-type]


def test_remote_404_means_no_files(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(*_: Any, **__: Any) -> Any:
        raise _http_error(404)

    monkeypatch.setattr(pf.urllib.request, "urlopen", fake)
    assert pf.remote_files(PKG, VER) is None


@pytest.mark.parametrize("code", [403, 500, 503])
def test_remote_other_status_is_an_error_never_not_published(
    monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    def fake(*_: Any, **__: Any) -> Any:
        raise _http_error(code)

    monkeypatch.setattr(pf.urllib.request, "urlopen", fake)
    with pytest.raises(pf.PyPIError, match=f"HTTP {code}"):
        pf.remote_files(PKG, VER)


def test_remote_unreachable_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(*_: Any, **__: Any) -> Any:
        raise urllib.error.URLError("no route")

    monkeypatch.setattr(pf.urllib.request, "urlopen", fake)
    with pytest.raises(pf.PyPIError, match="could not reach PyPI"):
        pf.remote_files(PKG, VER)


def test_remote_200_lists_files(monkeypatch: pytest.MonkeyPatch) -> None:
    body = {"urls": [{"filename": WHL, "digests": {"sha256": "a"}}]}

    def fake(*_: Any, **__: Any) -> Any:
        return io.BytesIO(json.dumps(body).encode())

    monkeypatch.setattr(pf.urllib.request, "urlopen", fake)
    assert pf.remote_files(PKG, VER) == {WHL: "a"}
