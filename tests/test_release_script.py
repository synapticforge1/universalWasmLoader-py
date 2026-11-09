"""scripts/release.py helpers: the ls-remote read-back and the Release-page owner item (H30)."""
from __future__ import annotations

import importlib.util
import sys
import urllib.parse
from pathlib import Path
from types import ModuleType

SCRIPTS = Path(__file__).parent.parent / "scripts"


def _load() -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))  # release.py imports _common from its own folder
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


def test_release_page_url_for_each_github_remote_form() -> None:
    for remote in (
        "https://github.com/synapticforge1/universalWasmLoader-py.git",
        "https://github.com/synapticforge1/universalWasmLoader-py",
        "git@github.com:synapticforge1/universalWasmLoader-py.git",
        "ssh://git@github.com/synapticforge1/universalWasmLoader-py.git",
    ):
        url = rel.release_page_url(remote, "v2.0.1", "notes & more?")
        assert url is not None, remote
        base, _, query = url.partition("?")
        assert base == "https://github.com/synapticforge1/universalWasmLoader-py/releases/new"
        assert urllib.parse.parse_qs(query) == {
            "tag": ["v2.0.1"], "title": ["v2.0.1"], "body": ["notes & more?"]
        }


def test_release_page_url_none_for_other_hosts() -> None:
    assert rel.release_page_url("/tmp/scratch-bare.git", "v1", "x") is None
    assert rel.release_page_url("https://gitlab.com/a/b.git", "v1", "x") is None
