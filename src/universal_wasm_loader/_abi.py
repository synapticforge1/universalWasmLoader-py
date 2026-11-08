"""Canonical ABI bridge (SPEC 4.0.0 §4, §5), the Python port of universalWasmLoader-js `abi.js`.

Typed calls check their arguments and host callbacks' return values against the WIT signature
and never coerce. Every WIT import needs a callback, which is checked at load.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

import wasmtime

_S32_MIN, _S32_MAX = -(2**31), 2**31 - 1
_S64_MIN, _S64_MAX = -(2**63), 2**63 - 1


def _arg_problem(wit_type: str, v: object) -> str | None:
    """What a value of WIT type `wit_type` must be, or None when `v` is one (SPEC 4.0.0 §4).

    `bool` is a subclass of `int` in Python, so it is excluded from the integer kinds by hand;
    `f32` / `f64` take a `float` only (the floating type, as -dotnet / -jvm / -go do)."""
    if wit_type == "s32":
        ok = type(v) is not bool and isinstance(v, int) and _S32_MIN <= v <= _S32_MAX
        return None if ok else "an int in [-2147483648, 2147483647]"
    if wit_type == "s64":
        ok = type(v) is not bool and isinstance(v, int) and _S64_MIN <= v <= _S64_MAX
        return None if ok else "an int in [-2^63, 2^63 - 1]"
    if wit_type in ("f32", "f64"):
        return None if isinstance(v, float) else "a float"
    if wit_type == "bool":
        return None if isinstance(v, bool) else "a bool"
    if wit_type == "string":
        return None if isinstance(v, str) else "a str"
    raise AssertionError(f"unreachable: WIT type {wit_type!r} passed the parser")


def _show_value(v: object) -> str:
    return f"{v!r} ({type(v).__name__})"


def _signature(fd: dict) -> str:  # type: ignore[type-arg]
    params = ", ".join(f"{p['name']}: {p['type']}" for p in fd["params"])
    return f"{fd['camel_name']}({params})"


def _decode_string(memory: wasmtime.Memory, store: wasmtime.Store, ptr: int, length: int) -> str:
    return bytes(memory.read(store, ptr, ptr + length)).decode("utf-8")


def _read_i32_le(memory: wasmtime.Memory, store: wasmtime.Store, addr: int) -> int:
    return int.from_bytes(bytes(memory.read(store, addr, addr + 4)), "little", signed=True)


def _encode_string(
    memory: wasmtime.Memory,
    store: wasmtime.Store,
    realloc: wasmtime.Func,
    text: str,
) -> tuple[int, int]:
    data = text.encode("utf-8")
    ptr: int = realloc(store, 0, 0, 1, len(data))
    memory.write(store, data, ptr)
    return ptr, len(data)


def _find_callback(
    fd: dict,  # type: ignore[type-arg]
    callbacks: dict[str, Callable[..., Any]],
) -> Callable[..., Any] | None:
    # camelCase is the SPEC key; the kebab-case WIT name is also accepted (since 1.0.0).
    for key in (fd["camel_name"], fd["name"]):
        cb = callbacks.get(key)
        if callable(cb):
            return cb
    return None


def resolve_import_callbacks(
    imports: list[dict],  # type: ignore[type-arg]
    callbacks: dict[str, Callable[..., Any]] | None,
) -> dict[str, Callable[..., Any]]:
    """Map each WIT import's `wasm_key` to its host callback, or refuse the load (SPEC 4.0.0 §4):
    every WIT import needs a callback (all missing ones are named), and an import whose result is
    `string` is not supported by this ABI profile. Runs before the `.wasm` is read."""
    callbacks = callbacks or {}
    found = {fd["wasm_key"]: _find_callback(fd, callbacks) for fd in imports}
    missing = [fd for fd in imports if found[fd["wasm_key"]] is None]
    if missing:
        names = ", ".join(f'{fd["camel_name"]} (WIT "{fd["name"]}")' for fd in missing)
        plural = "s" if len(missing) > 1 else ""
        raise TypeError(f"wasm_import: no host callback for WIT import{plural}: {names}")
    string_result = [fd for fd in imports if fd["return_type"] == "string"]
    if string_result:
        names = ", ".join(f'{fd["camel_name"]} (WIT "{fd["name"]}")' for fd in string_result)
        raise NotImplementedError(
            f"wasm_import: a WIT import returning a string is not supported: {names}"
        )
    return {key: cb for key, cb in found.items() if cb is not None}


def _encode_callback_result(fd: dict, ret: object) -> Any:  # type: ignore[type-arg]
    """Check a host callback's return value against its WIT import's result and encode it for
    WASM (SPEC 4.0.0 §4: the argument rules in reverse, nothing coerced). A void import ignores
    the value; an awaitable is refused for every import, since WASM cannot wait for it."""
    rt = fd["return_type"]
    label = f'host callback {fd["camel_name"]} (WIT import "{fd["name"]}"' + (
        f" -> {rt})" if rt else ")"
    )
    if inspect.isawaitable(ret):
        if inspect.iscoroutine(ret):
            ret.close()  # never awaited: close it so Python does not warn about it later
        raise TypeError(
            f"wasm_import: {label} returned an awaitable; host callbacks must be synchronous "
            "(WASM cannot await)"
        )
    if rt is None:
        return None
    expected = _arg_problem(rt, ret)
    if expected is not None:
        raise TypeError(f"wasm_import: {label} returned {_show_value(ret)}; expected {expected}")
    if rt == "bool":
        return 1 if ret else 0
    return ret


def build_component_import_env(
    imports: list[dict],  # type: ignore[type-arg]
    resolved: dict[str, Callable[..., Any]],
    memory_ref: list[wasmtime.Memory | None],
    store: wasmtime.Store,
) -> dict[str, Callable[..., Any]]:
    """The WASM-callable wrapper for each WIT import, keyed by `wasm_key`. `resolved` comes from
    `resolve_import_callbacks`, so every import has its callback."""

    def make_wrapper(fd: dict, cb: Callable[..., Any]) -> Callable[..., Any]:  # type: ignore[type-arg]
        def wrapper(*raw_args: Any) -> Any:
            converted: list[Any] = []
            idx = 0
            for p in fd["params"]:
                val = raw_args[idx]
                idx += 1
                if p["type"] == "bool":
                    converted.append(val != 0)
                elif p["type"] == "string":
                    memory = memory_ref[0]
                    if memory is None:
                        raise RuntimeError(
                            f'wasm_import: import "{fd["name"]}" received a string before the '
                            "module's memory was available (the module exports no `memory`, or "
                            "calls it from its start function)"
                        )
                    length = int(raw_args[idx])
                    idx += 1
                    converted.append(_decode_string(memory, store, int(val), length))
                else:
                    converted.append(val)
            return _encode_callback_result(fd, cb(*converted))

        return wrapper

    return {fd["wasm_key"]: make_wrapper(fd, resolved[fd["wasm_key"]]) for fd in imports}


def build_component_export_proxy(
    raw_exports: dict[str, Any],
    wit_exports: list[dict],  # type: ignore[type-arg]
    memory_ref: list[wasmtime.Memory | None],
    store: wasmtime.Store,
    cabi_realloc_ref: list[wasmtime.Func | None],
) -> dict[str, Callable[..., Any]]:
    """A typed callable for each WIT export. A WIT export the module does not export fails the
    load here; each call checks its arguments (SPEC 4.0.0 §4)."""

    def find(fd: dict) -> wasmtime.Func | None:  # type: ignore[type-arg]
        # wasmtk emits camelCase export names (WIT `str-len` -> `strLen`), as -js looks them up;
        # the underscore form is also accepted (since 1.0.0).
        for key in (fd["camel_name"], fd["wasm_key"]):
            fn = raw_exports.get(key)
            if isinstance(fn, wasmtime.Func):
                return fn
        return None

    absent = [fd for fd in wit_exports if find(fd) is None]
    if absent:
        names = ", ".join(f'{fd["camel_name"]} (WIT "{fd["name"]}")' for fd in absent)
        plural = "s" if len(absent) > 1 else ""
        raise RuntimeError(
            f"wasm_import: the .wit declares export{plural} the module does not export: {names}"
        )

    def make_proxy(fd: dict, raw_fn: wasmtime.Func) -> Callable[..., Any]:  # type: ignore[type-arg]
        # SPEC 3.0.0+: a string-returning export returns a single i32 pointer to a callee-allocated
        # [ptr, len] pair; the host then calls cabi_post_<camelName>(retArea) if it is exported.
        cabi_post = raw_exports.get(f"cabi_post_{fd['camel_name']}")
        if not isinstance(cabi_post, wasmtime.Func):
            cabi_post = None
        params = fd["params"]
        rt = fd["return_type"]
        string_params = any(p["type"] == "string" for p in params)
        uses_strings = string_params or rt == "string"

        def call(*args: Any) -> Any:
            if len(args) != len(params):
                plural = "" if len(params) == 1 else "s"
                raise TypeError(
                    f"wasm_import: {_signature(fd)} expects {len(params)} argument{plural}, "
                    f"got {len(args)}"
                )
            for p, val in zip(params, args, strict=True):
                expected = _arg_problem(p["type"], val)
                if expected is not None:
                    raise TypeError(
                        f"wasm_import: {_signature(fd)}: parameter {p['name']} ({p['type']}) "
                        f"expects {expected}, got {_show_value(val)}"
                    )
            memory = memory_ref[0]
            realloc = cabi_realloc_ref[0]
            if uses_strings and memory is None:
                raise RuntimeError(
                    f"wasm_import: {_signature(fd)} passes a string, but the module exports no "
                    "`memory`"
                )
            if string_params and realloc is None:
                raise RuntimeError(
                    f"wasm_import: {_signature(fd)} takes a string, but the module exports no "
                    "`cabi_realloc`"
                )
            wasm_args: list[Any] = []
            for p, val in zip(params, args, strict=True):
                if p["type"] == "bool":
                    wasm_args.append(1 if val else 0)
                elif p["type"] == "string":
                    assert memory is not None and realloc is not None  # checked above
                    ptr, length = _encode_string(memory, store, realloc, val)
                    wasm_args.extend([ptr, length])
                else:
                    wasm_args.append(val)
            result = raw_fn(store, *wasm_args)
            if rt is None:
                return None
            if rt == "bool":
                return result != 0
            if rt == "string":
                assert memory is not None  # checked above
                ret_area = int(result)
                str_ptr = _read_i32_le(memory, store, ret_area)
                str_len = _read_i32_le(memory, store, ret_area + 4)
                decoded = _decode_string(memory, store, str_ptr, str_len)
                if cabi_post is not None:
                    cabi_post(store, ret_area)
                return decoded
            return result

        return call

    proxy: dict[str, Callable[..., Any]] = {}
    for fd in wit_exports:
        raw_fn = find(fd)
        assert raw_fn is not None  # absent ones refused above
        proxy[fd["camel_name"]] = make_proxy(fd, raw_fn)
    return proxy
