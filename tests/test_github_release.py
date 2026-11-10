"""scripts/github_release.py against an in-process mock of GitHub's REST API (no network)."""
from __future__ import annotations

import importlib.util
import json
import sys
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
        self.stall: str | None = None  # "headers" | "drip": a slow server for the 7.21 cases
        self.pypi_versions: set[str] = set()  # what the mock PyPI's project JSON lists
        self.dispatch_publishes = True  # a dispatch makes the mock PyPI list the version

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
            if state.stall == "headers":  # nothing at all for 3 s
                time.sleep(3)
                return self._send(404)
            if state.stall == "drip":  # headers now, then 1 byte / 0.2 s: never idle 0.5 s
                self.send_response(200)
                self.send_header("Content-Length", "100")
                self.end_headers()
                for _ in range(15):
                    self.wfile.write(b" ")
                    self.wfile.flush()
                    time.sleep(0.2)
                return None
            p = self.path
            if p == "/pypi/universal-wasm-loader/json":
                return self._send(200, {"releases": {v: [] for v in state.pypi_versions}})
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
            if self.path == f"/repos/{REPO}/git/tags":  # an annotated tag object
                obj_sha = "d" * 40
                state.tag_objects[obj_sha] = {"type": "commit", "sha": body["object"]}
                return self._send(201, {"sha": obj_sha})
            if self.path == f"/repos/{REPO}/git/refs":
                state.tags[body["ref"].removeprefix("refs/tags/")] = {"type": "tag",
                                                                      "sha": body["sha"]}
                return self._send(201, {"ref": body["ref"]})
            if self.path == f"/repos/{REPO}/actions/workflows/publish.yml/dispatches":
                if state.dispatch_publishes:
                    state.pypi_versions.add(body["ref"].removeprefix("v"))
                return self._send(204)
            if self.path != f"/repos/{REPO}/releases" or state.post_status != 201:
                return self._send(state.post_status, {"message": "nope"})
            rel = {"id": 7, "tag_name": body["tag_name"], "draft": False,
                   "html_url": f"https://example.invalid/{body['tag_name']}"}
            state.releases[body["tag_name"]] = rel
            self._send(201, rel)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True  # a stalled handler must not hold the test run
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


@pytest.mark.parametrize("stall", ["headers", "drip"])
def test_every_request_has_a_total_time_limit(mock: tuple[Mock, str], stall: str) -> None:
    # 7.21: request to LAST BYTE. "drip" never leaves the socket idle for the limit, so only a
    # total deadline stops it; the elapsed bound makes a lost limit FAIL instead of hang.
    state, base = mock
    state.stall = stall
    started = time.monotonic()
    with pytest.raises(gr.ApiError, match=r"timed out after 0\.5 s"):
        gr.run(REPO, TAG, SHA, False, gr.Api(base, "t0k", limit=0.5))
    assert time.monotonic() - started < 2.0
    assert state.writes() == []


# ── H33: CI's tag, the order check, the dispatch on the tag ──────────────────────────────────

def _api(base: str, token: str | None = "t0k") -> Any:
    return gr.Api(base, token)


def test_tag_creates_an_annotated_tag_then_reads_it_back(mock: tuple[Mock, str]) -> None:
    state, base = mock
    assert gr.make_tag(REPO, TAG, SHA, False, _api(base)) == 0
    tag_post, ref_post = state.writes()
    assert tag_post[1] == f"/repos/{REPO}/git/tags" and tag_post[2] == "Bearer t0k"
    assert tag_post[3]["object"] == SHA and tag_post[3]["type"] == "commit"
    assert ref_post[1] == f"/repos/{REPO}/git/refs"
    assert ref_post[3] == {"ref": f"refs/tags/{TAG}", "sha": "d" * 40}
    assert state.log[-1][0] == "GET"  # read back after the writes
    assert gr.tag_commit(_api(base), REPO, TAG) == SHA  # annotated, peels to the commit


def test_tag_already_here_is_done_elsewhere_refused_both_without_writes(
    mock: tuple[Mock, str]
) -> None:
    state, base = mock
    state.tags[TAG] = {"type": "commit", "sha": SHA}
    assert gr.make_tag(REPO, TAG, SHA, False, _api(base)) == 0
    state.tags[TAG] = {"type": "commit", "sha": OTHER}
    assert gr.make_tag(REPO, TAG, SHA, False, _api(base)) == 1  # a published tag never moves
    assert state.writes() == []


def test_tag_dry_run_and_no_token_write_nothing(mock: tuple[Mock, str]) -> None:
    state, base = mock
    assert gr.make_tag(REPO, TAG, SHA, True, _api(base)) == 0
    assert gr.make_tag(REPO, TAG, SHA, False, _api(base, token=None)) == 1
    assert state.writes() == []


def test_check_needs_the_tag_here_and_its_page(mock: tuple[Mock, str]) -> None:
    state, base = mock
    assert gr.check(REPO, TAG, SHA, _api(base)) == 1  # no tag
    state.tags[TAG] = {"type": "commit", "sha": SHA}
    assert gr.check(REPO, TAG, SHA, _api(base)) == 1  # no page yet: page comes before publish
    state.releases[TAG] = {"tag_name": TAG, "draft": False, "author": {"login": "bot"}}
    assert gr.check(REPO, TAG, SHA, _api(base)) == 0
    state.tags[TAG] = {"type": "commit", "sha": OTHER}
    assert gr.check(REPO, TAG, SHA, _api(base)) == 1  # tag elsewhere
    assert state.writes() == []


def test_dispatch_starts_publish_on_the_tag_then_waits_for_pypi(
    mock: tuple[Mock, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    state, base = mock
    monkeypatch.setenv("PYPI_URL", base)
    state.tags[TAG] = {"type": "commit", "sha": SHA}
    state.releases[TAG] = {"tag_name": TAG, "draft": False}
    assert gr.dispatch(REPO, TAG, SHA, False, _api(base), wait=5, poll=0.05) == 0
    (method, path, auth, body), = state.writes()
    assert path == f"/repos/{REPO}/actions/workflows/publish.yml/dispatches"
    assert body == {"ref": TAG, "inputs": {"ref": TAG}} and auth == "Bearer t0k"


def test_dispatch_refuses_without_the_page_and_skips_when_published(
    mock: tuple[Mock, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    state, base = mock
    monkeypatch.setenv("PYPI_URL", base)
    state.tags[TAG] = {"type": "commit", "sha": SHA}
    assert gr.dispatch(REPO, TAG, SHA, False, _api(base), wait=1) == 1  # no page: refused
    state.releases[TAG] = {"tag_name": TAG, "draft": False}
    state.pypi_versions.add(TAG[1:])
    assert gr.dispatch(REPO, TAG, SHA, False, _api(base), wait=1) == 0  # re-run: already there
    assert state.writes() == []


def test_dispatch_fails_when_pypi_never_lists_the_version(
    mock: tuple[Mock, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    state, base = mock
    monkeypatch.setenv("PYPI_URL", base)
    state.tags[TAG] = {"type": "commit", "sha": SHA}
    state.releases[TAG] = {"tag_name": TAG, "draft": False}
    state.dispatch_publishes = False  # the dispatched run fails: PyPI never lists it
    started = time.monotonic()
    assert gr.dispatch(REPO, TAG, SHA, False, _api(base), wait=0.6, poll=0.1) == 1
    assert time.monotonic() - started < 3.0


def test_main_routes_the_commands(mock: tuple[Mock, str], monkeypatch: pytest.MonkeyPatch) -> None:
    state, base = mock
    monkeypatch.setenv("GITHUB_API_URL", base)
    monkeypatch.setenv("GITHUB_TOKEN", "t0k")
    args = ["--repo", REPO, "--tag", TAG, "--sha", SHA]
    assert gr.main(["tag", *args]) == 0
    assert gr.main(["check", *args]) == 1  # tag made, page not yet
    assert gr.main(["page", *args]) == 0
    assert gr.main(["check", *args]) == 0
    assert gr.main(["bogus", *args]) == 1


def test_malformed_tag_sends_no_request(mock: tuple[Mock, str]) -> None:
    state, base = mock
    assert _run(base, tag="main") == 1
    assert state.log == []
