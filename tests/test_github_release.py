"""scripts/github_release.py against an in-process mock of GitHub's REST API (no network)."""
from __future__ import annotations

import importlib.util
import json
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "github_release.py"
REPO, TAG, SHA, OTHER = "o/r", "v2.0.2", "a" * 40, "b" * 40


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("github_release", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["github_release"] = mod
    spec.loader.exec_module(mod)
    return mod


gr = _load()


class Mock:
    """GitHub state + a log of (method, path, auth, body)."""

    def __init__(self) -> None:
        self.tags: dict[str, dict[str, str]] = {}  # tag -> ref object
        self.tag_objects: dict[str, dict[str, str]] = {}  # annotated tag sha -> object
        self.releases: dict[str, dict[str, Any]] = {}
        self.log: list[tuple[str, str, str | None, Any]] = []
        self.post_status = 201

    def writes(self) -> list[tuple[str, str, str | None, Any]]:
        return [e for e in self.log if e[0] != "GET"]


@pytest.fixture
def mock() -> Iterator[tuple[Mock, str]]:
    state = Mock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: Any) -> None:
            pass

        def _send(self, code: int, doc: Any = None) -> None:
            raw = b"" if doc is None else json.dumps(doc).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            state.log.append(("GET", self.path, self.headers.get("Authorization"), None))
            p = self.path
            if p.startswith(f"/repos/{REPO}/git/ref/tags/"):
                obj = state.tags.get(p.rsplit("/", 1)[1])
                return self._send(200, {"object": obj}) if obj else self._send(404)
            if p.startswith(f"/repos/{REPO}/git/tags/"):
                obj = state.tag_objects.get(p.rsplit("/", 1)[1])
                return self._send(200, {"object": obj}) if obj else self._send(404)
            if p.startswith(f"/repos/{REPO}/releases/tags/"):
                rel = state.releases.get(p.rsplit("/", 1)[1])
                return self._send(200, rel) if rel else self._send(404)
            self._send(404)

        def do_POST(self) -> None:  # noqa: N802
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state.log.append(("POST", self.path, self.headers.get("Authorization"), body))
            if self.path != f"/repos/{REPO}/releases" or state.post_status != 201:
                return self._send(state.post_status, {"message": "nope"})
            rel = {"id": 7, "tag_name": body["tag_name"], "draft": False,
                   "html_url": f"https://example.invalid/{body['tag_name']}"}
            state.releases[body["tag_name"]] = rel
            self._send(201, rel)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()


def _run(base: str, token: str | None = "t0k", dry: bool = False, tag: str = TAG) -> int:
    return int(gr.run(REPO, tag, SHA, dry, gr.Api(base, token)))


def test_creates_the_release_then_reads_it_back(mock: tuple[Mock, str]) -> None:
    state, base = mock
    state.tags[TAG] = {"type": "commit", "sha": SHA}
    assert _run(base) == 0
    (method, path, auth, body), = state.writes()
    assert (method, path, auth) == ("POST", f"/repos/{REPO}/releases", "Bearer t0k")
    assert body["tag_name"] == TAG and body["generate_release_notes"] is True
    assert "target_commitish" not in body  # the tag already exists; nothing to target
    assert "pypi.org/project/universal-wasm-loader/2.0.2/" in body["body"]
    assert state.log[-2][1].endswith(f"/releases/tags/{TAG}")  # read back after the POST
    assert state.log[-1][1].endswith(f"/git/ref/tags/{TAG}")  # tag re-checked last


def test_rerun_is_safe_existing_release_means_done(mock: tuple[Mock, str]) -> None:
    state, base = mock
    state.tags[TAG] = {"type": "commit", "sha": SHA}
    state.releases[TAG] = {"tag_name": TAG, "draft": False, "html_url": "x"}
    assert _run(base) == 0
    assert state.writes() == []


def test_annotated_tag_is_peeled(mock: tuple[Mock, str]) -> None:
    state, base = mock
    state.tags[TAG] = {"type": "tag", "sha": "c" * 40}
    state.tag_objects["c" * 40] = {"type": "commit", "sha": SHA}
    assert _run(base) == 0
    assert len(state.writes()) == 1


@pytest.mark.parametrize("case", ["missing tag", "moved tag", "annotated tag moved"])
def test_refuses_with_no_write(mock: tuple[Mock, str], case: str) -> None:
    state, base = mock
    if case == "moved tag":
        state.tags[TAG] = {"type": "commit", "sha": OTHER}
    elif case == "annotated tag moved":
        state.tags[TAG] = {"type": "tag", "sha": "c" * 40}
        state.tag_objects["c" * 40] = {"type": "commit", "sha": OTHER}
    assert _run(base) == 1
    assert state.writes() == []


def test_dry_run_and_no_token_send_no_write(mock: tuple[Mock, str]) -> None:
    state, base = mock
    state.tags[TAG] = {"type": "commit", "sha": SHA}
    assert _run(base, dry=True) == 0
    assert _run(base, token=None) == 1
    assert state.writes() == []


def test_a_failed_post_is_a_failure(
    mock: tuple[Mock, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    state, base = mock
    state.tags[TAG] = {"type": "commit", "sha": SHA}
    state.post_status = 422
    with pytest.raises(gr.ApiError, match="HTTP 422"):
        _run(base)
    monkeypatch.setenv("GITHUB_API_URL", base)  # main() must hit the mock, never GitHub
    monkeypatch.setenv("GITHUB_TOKEN", "t0k")
    assert gr.main(["--repo", REPO, "--tag", TAG, "--sha", SHA]) == 1  # ApiError -> exit 1


def test_malformed_tag_sends_no_request(mock: tuple[Mock, str]) -> None:
    state, base = mock
    assert _run(base, tag="main") == 1
    assert state.log == []
