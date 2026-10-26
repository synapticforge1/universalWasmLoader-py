from __future__ import annotations

from pathlib import Path

import pytest
import wasmtime

# The stamped reference set from universalWasmLoader-js, copied unmodified (SPEC §7, workspace
# letter H7); test_fixtures.py checks it against fixtures.json. Never edit these by hand.
FIXTURES = Path(__file__).parent / "fixtures"
# Python-only fixtures for behaviour the reference set does not carry (version pinning).
PY_FIXTURES = Path(__file__).parent / "py_fixtures"


def _stage_raw(name: str, tmp_dir: Path) -> Path:
    """Copy only the .wasm into a temp dir, so the loader finds no sibling .wit (raw path)."""
    wasm_path = tmp_dir / f"{name}.wasm"
    wasm_path.write_bytes((FIXTURES / f"{name}.wasm").read_bytes())
    return wasm_path


def _compile_wat(name: str, tmp_dir: Path) -> Path:
    # wat2wasm gives the binary module; Module.serialize() would give wasmtime's
    # precompiled artifact, which is not a .wasm file (drift L8).
    wasm_path = tmp_dir / f"{name}.wasm"
    wat_text = (PY_FIXTURES / f"{name}.wat").read_text(encoding="utf-8")
    wasm_path.write_bytes(wasmtime.wat2wasm(wat_text))
    return wasm_path


# ── reference set, WIT path (the .wit sits beside the .wasm) ────────────────────

@pytest.fixture(scope="session")
def math_wasm() -> Path:
    return FIXTURES / "math_50.wasm"


@pytest.fixture(scope="session")
def booleans_wasm() -> Path:
    return FIXTURES / "booleans_50.wasm"


@pytest.fixture(scope="session")
def strings_wasm() -> Path:
    return FIXTURES / "strings_50.wasm"


@pytest.fixture(scope="session")
def imports_wasm() -> Path:
    return FIXTURES / "imports_50.wasm"


# ── reference set, raw path (no .wit) ───────────────────────────────────────────

@pytest.fixture(scope="session")
def math_wasm_raw(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _stage_raw("math_50", tmp_path_factory.mktemp("math_raw"))


@pytest.fixture(scope="session")
def imports_wasm_raw(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _stage_raw("imports_50", tmp_path_factory.mktemp("imports_raw"))


# ── SPEC §10 fixtures (producer model — loader capabilities) ────────────────────

@pytest.fixture(scope="session")
def init_check_wasm_path() -> Path:
    """Hand-written reactor module (no .wit): `_initialize` sets a global to 99."""
    return FIXTURES / "init_check.wasm"


@pytest.fixture(scope="session")
def wasi_io_wasm() -> Path:
    """modc library that calls console.log → imports fd_write."""
    return FIXTURES / "wasi_io_50.wasm"


# ── Python-only ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def versioned_wasm_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Exports a `version` global = 1 and `calculate(a, b) = a + b`."""
    return _compile_wat("versioned", tmp_path_factory.mktemp("versioned"))
