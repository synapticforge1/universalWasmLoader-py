"""scripts/pypi_attest.py: PEP 740 signing in the publish job (H33 U8). The real signature needs
CI's OIDC identity, so the third-party modules are FAKES here: the tests prove the plan, the
refusals, and that no ambient credential means exit 1 with nothing written (never an
interactive flow)."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "pypi_attest.py"
WHL = "universal_wasm_loader-2.0.4-py3-none-any.whl"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pypi_attest", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pa = _load()


def _fake_modules(monkeypatch: pytest.MonkeyPatch, credential: str | None) -> list[str]:
    signed: list[str] = []

    class Signer:
        def __enter__(self) -> Signer:
            return self

        def __exit__(self, *_: Any) -> None:
            pass

    class Attestation:
        def __init__(self, name: str) -> None:
            self.name = name

        @staticmethod
        def sign(_signer: Any, dist: Any) -> Attestation:
            signed.append(dist.name)
            return Attestation(dist.name)

        def model_dump_json(self) -> str:
            return f'{{"signed": "{self.name}"}}'

    class Distribution:
        def __init__(self, name: str) -> None:
            self.name = name

        @staticmethod
        def from_file(path: Path) -> Distribution:
            return Distribution(path.name)

    class SigningContext:
        @staticmethod
        def from_trust_config(_cfg: Any) -> SigningContext:
            return SigningContext()

        def signer(self, _identity: Any, cache: bool = True) -> Signer:
            return Signer()

    mods = {
        "pypi_attestations": {"Attestation": Attestation, "Distribution": Distribution},
        "sigstore": {},
        "sigstore.models": {"ClientTrustConfig": type("C", (), {"production": staticmethod(
            lambda: object())})},
        "sigstore.oidc": {"IdentityToken": lambda c: ("token", c),
                          "detect_credential": lambda: credential},
        "sigstore.sign": {"SigningContext": SigningContext},
    }
    for name, attrs in mods.items():
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        monkeypatch.setitem(sys.modules, name, m)
    return signed


def test_attestation_name_is_what_twine_looks_for() -> None:
    assert pa.attestation_path(Path(f"dist/{WHL}")).name == f"{WHL}.publish.attestation"


def test_plan_refuses_missing_files_and_existing_attestations(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no dist files"):
        pa.plan([])
    with pytest.raises(ValueError, match="is not a file"):
        pa.plan([str(tmp_path / WHL)])
    (tmp_path / WHL).write_bytes(b"w")
    (tmp_path / f"{WHL}.publish.attestation").write_text("{}")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        pa.plan([str(tmp_path / WHL)])


def test_no_ambient_credential_refuses_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    signed = _fake_modules(monkeypatch, credential=None)
    (tmp_path / WHL).write_bytes(b"w")
    assert pa.main([str(tmp_path / WHL)]) == 1
    assert signed == []
    assert not (tmp_path / f"{WHL}.publish.attestation").exists()


def test_signs_each_file_beside_it(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    signed = _fake_modules(monkeypatch, credential="ambient-oidc")
    sdist = "universal_wasm_loader-2.0.4.tar.gz"
    for name in (WHL, sdist):
        (tmp_path / name).write_bytes(b"x")
    assert pa.main([str(tmp_path / WHL), str(tmp_path / sdist)]) == 0
    assert signed == [WHL, sdist]
    assert (tmp_path / f"{sdist}.publish.attestation").read_text() == f'{{"signed": "{sdist}"}}'
