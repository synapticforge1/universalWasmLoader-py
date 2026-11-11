"""scripts/pypi_files.py: which dist files PyPI still needs (no network: urlopen is stubbed)."""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import time
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


# ── H33 U8: the fatal read-back (served + a PEP 740 provenance from THIS publisher) ───────

OURS = {"kind": "GitHub", "repository": "synapticforge1/universalWasmLoader-py",
        "workflow": "publish.yml", "environment": "pypi"}


def _pypi(monkeypatch: pytest.MonkeyPatch, served: dict[str, str] | None,
          provenance: dict[str, list[dict[str, str]]]) -> None:
    monkeypatch.setattr(pf, "remote_files", lambda *_a, **_k: served)

    def get_json(url: str, timeout: float = 30) -> Any:
        name = url.split("/")[-2]
        pubs = provenance.get(name)
        return None if pubs is None else {"attestation_bundles": [{"publisher": p} for p in pubs]}

    monkeypatch.setattr(pf, "get_json", get_json)


def _problems() -> list[str]:
    repo, local = "synapticforge1/universalWasmLoader-py", {WHL: "a", SDIST: "b"}
    return list(pf.readback_problems(PKG, VER, local, repo, "publish.yml", "pypi"))


def test_readback_ok_when_served_and_attested_by_us(monkeypatch: pytest.MonkeyPatch) -> None:
    _pypi(monkeypatch, {WHL: "a", SDIST: "b"}, {WHL: [OURS], SDIST: [OURS]})
    assert _problems() == []


def test_readback_accepts_a_publisher_without_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # What PyPI really reported for 2.0.5 (2026-11-10): "environment": null — the Trusted
    # Publisher is registered without one. The identity (repository + workflow) still decides.
    unconstrained = {**OURS, "environment": None}
    _pypi(monkeypatch, {WHL: "a", SDIST: "b"}, {WHL: [unconstrained], SDIST: [unconstrained]})
    assert _problems() == []


@pytest.mark.parametrize(
    ("served", "provenance", "fault"),
    [
        (None, {}, "does not serve"),
        ({WHL: "a"}, {WHL: [OURS]}, f"{SDIST}: not served"),
        ({WHL: "a", SDIST: "b"}, {WHL: [OURS]}, f"{SDIST}: no PEP 740 provenance"),
        ({WHL: "a", SDIST: "b"}, {WHL: [OURS], SDIST: [{**OURS, "workflow": "other.yml"}]},
         f"{SDIST}: no PEP 740 provenance"),
        ({WHL: "a", SDIST: "b"}, {WHL: [OURS], SDIST: [{**OURS, "repository": "evil/fork"}]},
         f"{SDIST}: no PEP 740 provenance"),
        ({WHL: "a", SDIST: "b"}, {WHL: [OURS], SDIST: [{**OURS, "environment": "staging"}]},
         f"{SDIST}: no PEP 740 provenance"),
    ],
    ids=["version-404", "file-missing", "no-provenance", "other-workflow", "other-repo",
         "other-environment"],
)
def test_readback_names_each_fault(
    monkeypatch: pytest.MonkeyPatch, served: Any, provenance: Any, fault: str
) -> None:
    _pypi(monkeypatch, served, provenance)
    problems = _problems()
    assert any(fault in p for p in problems), problems


def test_readback_main_is_fatal_after_the_wait(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / WHL).write_bytes(b"w")
    _pypi(monkeypatch, {WHL: "x"}, {})  # served, never attested
    started = time.monotonic()
    code = pf.readback_main([PKG, VER, str(tmp_path), "--repo", "o/r", "--wait", "0.3"], poll=0.1)
    assert code == 1 and time.monotonic() - started < 2.0


def test_local_files_skips_attestations(tmp_path: Path) -> None:
    (tmp_path / WHL).write_bytes(b"w")
    (tmp_path / SDIST).write_bytes(b"s")
    (tmp_path / f"{WHL}.publish.attestation").write_text("{}")
    (tmp_path / f"{SDIST}.publish.attestation").write_text("{}")
    assert set(pf.local_files(tmp_path, PKG, VER)) == {WHL, SDIST}


def test_remote_has_a_total_time_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    # 7.21: request to last byte. The stub ignores urlopen's per-socket timeout, as a dripping
    # server would; only the total limit stops it, and the elapsed bound catches a lost limit.
    def fake(*_: Any, **__: Any) -> Any:
        time.sleep(3)
        return io.BytesIO(b'{"urls": []}')

    monkeypatch.setattr(pf.urllib.request, "urlopen", fake)
    started = time.monotonic()
    with pytest.raises(pf.PyPIError, match=r"timed out after 0\.3 s"):
        pf.remote_files(PKG, VER, timeout=0.3)
    assert time.monotonic() - started < 2.0


def test_remote_200_lists_files(monkeypatch: pytest.MonkeyPatch) -> None:
    body = {"urls": [{"filename": WHL, "digests": {"sha256": "a"}}]}

    def fake(*_: Any, **__: Any) -> Any:
        return io.BytesIO(json.dumps(body).encode())

    monkeypatch.setattr(pf.urllib.request, "urlopen", fake)
    assert pf.remote_files(PKG, VER) == {WHL: "a"}
