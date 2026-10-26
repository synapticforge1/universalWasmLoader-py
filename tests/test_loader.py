from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from universal_wasm_loader import InstancePool, create_singleton, wasm_import

# The reference-set tests assert what universalWasmLoader-js's tests/loader.test.js asserts on
# the same stamped modules; the Python-only sections cover behaviour that suite does not.


# ── math_50 — numeric round-trip ──────────────────────────────────────────────

async def test_math_add(math_wasm: Path) -> None:
    exports = await wasm_import(math_wasm)
    assert exports["add"](3, 4) == 7


async def test_math_multiply(math_wasm: Path) -> None:
    exports = await wasm_import(math_wasm)
    assert exports["multiply"](2.5, 4.0) == 10.0


async def test_math_square(math_wasm: Path) -> None:
    exports = await wasm_import(math_wasm)
    assert exports["square"](5) == 25


# ── booleans_50 — bool normalization ──────────────────────────────────────────

async def test_bool_is_positive(booleans_wasm: Path) -> None:
    exports = await wasm_import(booleans_wasm)
    assert exports["isPositive"](1.0) is True
    assert exports["isPositive"](-1.0) is False


async def test_bool_in_range(booleans_wasm: Path) -> None:
    exports = await wasm_import(booleans_wasm)
    assert exports["inRange"](5.0, 0.0, 10.0) is True
    assert exports["inRange"](11.0, 0.0, 10.0) is False


async def test_bool_is_even(booleans_wasm: Path) -> None:
    exports = await wasm_import(booleans_wasm)
    assert exports["isEven"](4) is True
    assert exports["isEven"](3) is False


# ── strings_50 — string ABI (SPEC 3.0.0: callee-allocated return + cabi_post) ─

async def test_string_greet(strings_wasm: Path) -> None:
    exports = await wasm_import(strings_wasm)
    assert exports["greet"]("World") == "Hello, World!"


async def test_string_shout(strings_wasm: Path) -> None:
    exports = await wasm_import(strings_wasm)
    assert exports["shout"]("hi") == "hihi"


async def test_string_len(strings_wasm: Path) -> None:
    exports = await wasm_import(strings_wasm)
    assert exports["strLen"]("hello") == 5


# ── imports_50 — host import callbacks ────────────────────────────────────────

async def test_host_callbacks_wit(imports_wasm: Path) -> None:
    callbacks = {
        "envMul": lambda a, b: a * b,
        "envAdd": lambda a, b: a + b,
    }
    exports = await wasm_import(imports_wasm, callbacks)
    assert exports["scale"](3.0, 4.0) == 12.0
    assert exports["combine"](10, 7) == 17


# ── SPEC §10 — producer model (loader capabilities) ───────────────────────────

async def test_spec10_initialize_called(init_check_wasm_path: Path) -> None:
    # init_check.wasm has no .wit (raw exports); its _initialize sets a global to
    # 99 that getValue reads — 99 proves the loader invoked _initialize.
    mod = await wasm_import(init_check_wasm_path)
    assert mod["getValue"]() == 99


async def test_spec10_wasi_io_library_loads(wasi_io_wasm: Path) -> None:
    # wasi_io_50 is a modc lib that calls console.log → imports fd_write; it only
    # instantiates because the loader supplies the minimal WASI-P1 shim (§10.2).
    mod = await wasm_import(wasi_io_wasm)
    assert mod["logAndDouble"](21) == 42


# ── create_singleton ──────────────────────────────────────────────────────────

async def test_create_singleton_same_instance(math_wasm: Path) -> None:
    get_math = create_singleton(math_wasm)
    a = await get_math()
    b = await get_math()
    assert a is b


async def test_create_singleton_works(math_wasm: Path) -> None:
    get_math = create_singleton(math_wasm)
    math = await get_math()
    assert math["add"](1, 2) == 3


async def test_create_singleton_bool(booleans_wasm: Path) -> None:
    get_mod = create_singleton(booleans_wasm)
    mod = await get_mod()
    assert mod["isEven"](6) is True
    assert mod["isEven"](7) is False


# ── InstancePool ──────────────────────────────────────────────────────────────

async def test_instance_pool_run(math_wasm: Path) -> None:
    pool = InstancePool(math_wasm, size=2)
    assert await pool.run(lambda m: m["add"](10, 5)) == 15
    assert await pool.run(lambda m: m["square"](4)) == 16


async def test_instance_pool_concurrent(booleans_wasm: Path) -> None:
    pool = InstancePool(booleans_wasm, size=2)
    a, b = await asyncio.gather(
        pool.run(lambda m: m["isEven"](4)),
        pool.run(lambda m: m["isEven"](3)),
    )
    assert a is True
    assert b is False


async def test_instance_pool_acquire_release(math_wasm: Path) -> None:
    pool = InstancePool(math_wasm, size=1)
    inst = await pool.acquire()
    assert inst["add"](3, 3) == 6
    await pool.release(inst)
    inst2 = await pool.acquire()
    assert inst2 is inst
    assert inst2["add"](7, 8) == 15


# ── Python-only: raw load (no .wit) ───────────────────────────────────────────

async def test_raw_load(math_wasm_raw: Path) -> None:
    exports = await wasm_import(math_wasm_raw)
    assert callable(exports["add"])
    assert exports["add"](1, 2) == 3
    assert exports["add"](10, -3) == 7


async def test_host_callbacks_raw(imports_wasm_raw: Path) -> None:
    # Without a .wit, callbacks are matched by the module's own import names.
    callbacks = {
        "env_mul": lambda a, b: a * b,
        "env_add": lambda a, b: a + b,
    }
    exports = await wasm_import(imports_wasm_raw, callbacks)
    assert exports["scale"](3.0, 4.0) == pytest.approx(12.0)
    assert exports["combine"](10, 7) == 17


# ── Python-only: version pinning (`@N` vs. an exported `version` global) ──────

async def test_raw_load_version_global(versioned_wasm_path: Path) -> None:
    exports = await wasm_import(versioned_wasm_path)
    assert exports["version"] == 1


async def test_version_pinning_ok(versioned_wasm_path: Path) -> None:
    exports = await wasm_import(f"{versioned_wasm_path}@1")
    assert exports["calculate"](3, 4) == 7


async def test_version_pinning_mismatch(versioned_wasm_path: Path) -> None:
    with pytest.raises(RuntimeError, match="version mismatch"):
        await wasm_import(f"{versioned_wasm_path}@2")


async def test_version_pinning_no_global(math_wasm: Path) -> None:
    with pytest.raises(RuntimeError, match="no exported 'version' global"):
        await wasm_import(f"{math_wasm}@1")
