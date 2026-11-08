"""SPEC 4.0.0 § 8 "Refusals": every row this port can run, one test each (or a parametrized set).

The http rows (a `.wit` answering 500, a `.wasm` answering 404 / 500, a server that never
answers) are n/a: this loader reads local files only (`Path.read_bytes`) and has no http path, so
SPEC § 11 does not apply (as loader-c). JS stand-ins: `undefined` / `null` -> `None`, `2 ** 31` ->
the int 2**31; `17n` has no Python form (one `int` type serves s32 and s64); `async` -> an
`async def` callback. Python's `bool` is an `int` subclass, so `True` is tested where an integer
is expected.

"Fails before the `.wasm` is read" is shown by writing the `.wit` beside a `.wasm` that does not
exist: the refusal, not `FileNotFoundError`, is what reaches the caller.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from universal_wasm_loader import wasm_import

FIXTURES = Path(__file__).parent / "fixtures"


def _stage(tmp_path: Path, fixture: str, wit_text: str | None) -> Path:
    """Copy `<fixture>.wasm` into tmp_path, beside `wit_text` as its `.wit` (none if None)."""
    wasm = tmp_path / f"{fixture}.wasm"
    shutil.copyfile(FIXTURES / f"{fixture}.wasm", wasm)
    if wit_text is not None:
        (tmp_path / f"{fixture}.wit").write_text(wit_text, encoding="utf-8")
    return wasm


def _mul(a: float, b: float) -> float:
    return a * b


def _add(a: int, b: int) -> int:
    return a + b


# ── § 4: every WIT import needs a host callback ──────────────────────────────────

async def test_imports_no_callbacks_names_both(imports_wasm: Path) -> None:
    with pytest.raises(TypeError, match=r"envMul \(WIT \"env-mul\"\), envAdd \(WIT \"env-add\"\)"):
        await wasm_import(imports_wasm)


async def test_imports_only_env_mul_names_env_add(imports_wasm: Path) -> None:
    with pytest.raises(TypeError, match=r"no host callback for WIT import: envAdd") as info:
        await wasm_import(imports_wasm, {"envMul": _mul})
    assert "envMul" not in str(info.value)


async def test_missing_callback_refused_before_the_wasm_is_read(tmp_path: Path) -> None:
    (tmp_path / "gone.wit").write_text(
        (FIXTURES / "imports_50.wit").read_text(encoding="utf-8"), encoding="utf-8"
    )
    with pytest.raises(TypeError, match="no host callback"):
        await wasm_import(tmp_path / "gone.wasm")


async def test_callbacks_for_names_the_wit_does_not_import_are_ignored(imports_wasm: Path) -> None:
    mod = await wasm_import(imports_wasm, {"envMul": _mul, "envAdd": _add, "other": _add})
    assert mod["combine"](10, 7) == 17


# ── § 4: a callback's return value must match the import's WIT result ───────────

@pytest.mark.parametrize(
    "bad",
    [None, 2.9, 2**31, True, "17"],
    ids=["None", "2.9", "2**31", "True", "'17'"],
)
async def test_env_add_bad_return_named(imports_wasm: Path, bad: Any) -> None:
    mod = await wasm_import(imports_wasm, {"envMul": _mul, "envAdd": lambda a, b: bad})
    with pytest.raises(TypeError) as info:
        mod["combine"](10, 7)
    msg = str(info.value)
    assert 'host callback envAdd (WIT import "env-add" -> s32)' in msg
    assert repr(bad) in msg


async def test_env_mul_async_refused(imports_wasm: Path) -> None:
    async def env_mul(a: float, b: float) -> float:
        return a * b

    mod = await wasm_import(imports_wasm, {"envMul": env_mul, "envAdd": _add})
    with pytest.raises(TypeError, match=r"host callback envMul .* returned an awaitable"):
        mod["scale"](3.0, 4.0)


def test_void_import_ignores_the_return_value() -> None:
    # No reference fixture has a void import (imports_50's would not link without its result),
    # so the void rule is checked on the wrapper's encoder. (Imported here so the rest of this
    # file still collects against an older src/, for the inversion run.)
    from universal_wasm_loader._abi import _encode_callback_result

    fd = {"name": "log", "camel_name": "log", "params": [], "return_type": None}
    assert _encode_callback_result(fd, "anything") is None


async def test_string_result_import_refused_before_the_wasm_is_read(tmp_path: Path) -> None:
    wit = (FIXTURES / "imports_50.wit").read_text(encoding="utf-8").replace(
        "import env-mul: func(p0: f64, p1: f64) -> f64;",
        "import env-mul: func(p0: f64, p1: f64) -> string;",
    )
    assert "-> string;" in wit
    (tmp_path / "gone.wit").write_text(wit, encoding="utf-8")
    refused = r"returning a string .*envMul \(WIT \"env-mul\"\)"
    with pytest.raises(NotImplementedError, match=refused):
        await wasm_import(tmp_path / "gone.wasm", {"envMul": _mul, "envAdd": _add})


# ── § 4: typed calls check arity and argument kinds, no coercion ─────────────────

@pytest.mark.parametrize(
    ("args", "names"),
    [
        (("x", 1), "parameter a (s32)"),
        ((2.7, 1), "parameter a (s32)"),
        ((1, 2**31), "parameter b (s32)"),
        ((True, 1), "parameter a (s32)"),
        ((1,), "expects 2 arguments, got 1"),
        ((1, 2, 3), "expects 2 arguments, got 3"),
    ],
    ids=["'x'", "2.7", "2**31", "True", "arity-1", "arity-3"],
)
async def test_math_add_refuses(math_wasm: Path, args: tuple[Any, ...], names: str) -> None:
    mod = await wasm_import(math_wasm)
    with pytest.raises(TypeError) as info:
        mod["add"](*args)
    assert "add(a: s32, b: s32)" in str(info.value)
    assert names in str(info.value)


async def test_math_multiply_refuses_an_int_for_f64(math_wasm: Path) -> None:
    mod = await wasm_import(math_wasm)
    with pytest.raises(TypeError, match=r"parameter a \(f64\) expects a float, got 3 \(int\)"):
        mod["multiply"](3, 4.0)


async def test_strings_greet_refuses_an_int(strings_wasm: Path) -> None:
    mod = await wasm_import(strings_wasm)
    with pytest.raises(TypeError, match=r"greet\(name: string\): parameter name \(string\)"):
        mod["greet"](42)


async def test_booleans_is_even_refuses_a_str(booleans_wasm: Path) -> None:
    mod = await wasm_import(booleans_wasm)
    with pytest.raises(TypeError, match=r"isEven\(n: s32\): parameter n \(s32\)"):
        mod["isEven"]("4")


async def test_booleans_in_range_refuses_a_bool_for_f64(booleans_wasm: Path) -> None:
    mod = await wasm_import(booleans_wasm)
    with pytest.raises(TypeError, match=r"parameter v \(f64\) expects a float, got True \(bool\)"):
        mod["inRange"](True, 0.0, 10.0)


# ── § 2: strict parsing ──────────────────────────────────────────────────────────

_MATH_WIT = (FIXTURES / "math_50.wit").read_text(encoding="utf-8")


def _math(old: str, new: str) -> str:
    return _MATH_WIT.replace(old, new, 1)


@pytest.mark.parametrize(
    ("wit_text", "fault"),
    [
        pytest.param(_math("(a: s32, b: s32)", "(a: s32 b: s32)"), "malformed", id="no-comma"),
        pytest.param(_math("square: func(x: s32)", "square: func(x: u32)"), '"u32"', id="u32"),
        pytest.param("", "it is empty", id="empty"),
        pytest.param(_MATH_WIT + "\nexport f: func();\n", "expected one", id="outside-world"),
        pytest.param(_math("(a: s32, b: s32)", "(a: s32, a: s32)"), "duplicate", id="dup-param"),
        pytest.param(_math("export square", "export add"), "duplicate export", id="dup-export"),
        pytest.param(_math("export square", "resource square"), "unsupported", id="resource"),
        pytest.param(_math("s32;\n  export mul", "s32\n  export mul"), "unsupported", id="no-;"),
    ],
)
async def test_math_wit_does_not_parse(tmp_path: Path, wit_text: str, fault: str) -> None:
    assert wit_text != _MATH_WIT  # each case's replacement must have applied
    wasm = _stage(tmp_path, "math_50", wit_text)
    with pytest.raises(ValueError, match=r"invalid \.wit '.*math_50\.wit'") as info:
        await wasm_import(wasm)
    assert fault in str(info.value)


async def test_wit_not_utf8_refused(tmp_path: Path) -> None:
    wasm = _stage(tmp_path, "math_50", None)
    (tmp_path / "math_50.wit").write_bytes(b"world w { export add: func(a: s32) -> s32; }\xff")
    with pytest.raises(ValueError, match="not UTF-8"):
        await wasm_import(wasm)


async def test_wit_export_the_module_lacks_refused(tmp_path: Path) -> None:
    wasm = _stage(
        tmp_path, "math_50", _MATH_WIT.replace("}", "  export cube: func(x: s32) -> s32;\n}")
    )
    with pytest.raises(RuntimeError, match=r"does not export: cube \(WIT \"cube\"\)"):
        await wasm_import(wasm)


# ── § 2: only an ABSENT .wit is raw ──────────────────────────────────────────────

async def test_absent_wit_loads_raw(math_wasm_raw: Path) -> None:
    mod = await wasm_import(math_wasm_raw)
    assert mod["add"](3, 4) == 7


async def test_unreadable_wit_refused(tmp_path: Path) -> None:
    # A directory where the .wit should be: it exists but cannot be read as a file.
    wasm = _stage(tmp_path, "math_50", None)
    (tmp_path / "math_50.wit").mkdir()
    with pytest.raises(OSError, match=r"cannot read \.wit '.*math_50\.wit'"):
        await wasm_import(wasm)


async def test_path_not_ending_in_wasm_has_no_companion(tmp_path: Path) -> None:
    # math.bin beside a broken math.wit: 3.0.0 read math.wit (Path.with_suffix); 4.0.0 looks
    # for no companion, so the module loads raw.
    module = tmp_path / "math.bin"
    shutil.copyfile(FIXTURES / "math_50.wasm", module)
    (tmp_path / "math.wit").write_text("not wit", encoding="utf-8")
    mod = await wasm_import(module)
    assert mod["add"](3, 4) == 7


# ── a module import bound to nothing is refused, never stubbed ───────────────────

async def test_raw_import_without_callback_refused(imports_wasm_raw: Path) -> None:
    refused = r"no host callback for module import\(s\): env::env_mul, env::env_add"
    with pytest.raises(RuntimeError, match=refused):
        await wasm_import(imports_wasm_raw)


async def test_wit_mode_import_the_wit_omits_refused(tmp_path: Path) -> None:
    wit = (FIXTURES / "imports_50.wit").read_text(encoding="utf-8").replace(
        "  import env-add: func(p0: s32, p1: s32) -> s32;\n", ""
    )
    wasm = _stage(tmp_path, "imports_50", wit)
    refused = r"the \.wit does not declare module import\(s\): env::env_add"
    with pytest.raises(RuntimeError, match=refused):
        await wasm_import(wasm, {"envMul": _mul, "env_add": _add})
