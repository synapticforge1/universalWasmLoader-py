from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import wasmtime
from wasmtime import Engine, FuncType, Linker, Module, Store, WasiConfig

from ._abi import (
    build_component_export_proxy,
    build_component_import_env,
    resolve_import_callbacks,
)
from ._wit_parser import parse_wit


def _parse_version_suffix(path: str) -> tuple[str, int | None]:
    m = re.search(r"@(\d+)$", path)
    return (path[: m.start()], int(m.group(1))) if m else (path, None)


def _collect_raw_exports(
    module: Module, instance: wasmtime.Instance, store: Store
) -> dict[str, Any]:
    exports_obj = instance.exports(store)
    result: dict[str, Any] = {}
    for exp in module.exports:
        val = exports_obj[exp.name]
        if val is not None:
            result[exp.name] = val
    return result


# SPEC §10.2 — imports in these namespaces are satisfied by the runtime's built-in
# WASI implementation (linker.define_wasi), not the per-import stub loop.
_WASI_MODULES = ("wasi_snapshot_preview1", "wasi_unstable")


def _call_initialize(raw: dict[str, Any], store: Store) -> None:
    """SPEC §10.1 — invoke a reactor module's `_initialize` exactly once after
    instantiation, before any other export is used. No-op if not exported."""
    init = raw.get("_initialize")
    if isinstance(init, wasmtime.Func):
        init(store)


def _read_wit(wasm_path: Path) -> tuple[Path, str] | None:
    """Read the companion `.wit` (SPEC 4.0.0 §2). None ONLY when it is absent — the path does not
    end in `.wasm` (no companion name), or the file does not exist — which selects raw exports.
    Any other read failure, and a `.wit` that is not UTF-8, raises naming the `.wit`."""
    if wasm_path.suffix.lower() != ".wasm":
        return None
    wit_path = wasm_path.with_suffix(".wit")
    try:
        data = wit_path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as e:
        raise OSError(
            e.errno, f"wasm_import: cannot read .wit '{wit_path}': {e.strerror or e}"
        ) from e
    try:
        return wit_path, data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"wasm_import: invalid .wit '{wit_path}': not UTF-8 ({e})") from e


def _assert_version(raw: dict[str, Any], store: Store, expected: int, path: str) -> None:
    g = raw.get("version")
    if not isinstance(g, wasmtime.Global):
        raise RuntimeError(f"{path!r}: no exported 'version' global")
    actual = g.value(store)
    if actual != expected:
        raise RuntimeError(f"{path!r}: version mismatch — expected {expected}, got {actual}")


def _wrap_for_user(raw: dict[str, Any], store: Store) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, val in raw.items():
        if isinstance(val, wasmtime.Func):
            fn = val
            result[name] = lambda *args, f=fn: f(store, *args)
        elif isinstance(val, wasmtime.Global):
            result[name] = val.value(store)
        else:
            result[name] = val
    return result


async def wasm_import(
    wasm_path: str | Path,
    host_callbacks: dict[str, Callable[..., Any]] | None = None,
) -> dict[str, Any]:
    path_str = str(wasm_path)
    cleaned, requested_version = _parse_version_suffix(path_str)
    path = Path(cleaned)

    # WIT auto-detection (SPEC 4.0.0 §2): absent -> raw exports; any other failure raises, and
    # everything the .wit alone can refuse is refused before the .wasm is read.
    wit: dict[str, Any] | None = None
    resolved: dict[str, Callable[..., Any]] = {}
    found = _read_wit(path)
    if found is not None:
        wit_path, wit_src = found
        try:
            wit = parse_wit(wit_src)
        except ValueError as e:
            raise ValueError(f"wasm_import: invalid .wit '{wit_path}': {e}") from e
        resolved = resolve_import_callbacks(wit["imports"], host_callbacks)

    wasm_bytes = await asyncio.to_thread(path.read_bytes)
    engine = Engine()
    module = Module(engine, wasm_bytes)
    store = Store(engine)

    memory_ref: list[wasmtime.Memory | None] = [None]
    cabi_realloc_ref: list[wasmtime.Func | None] = [None]

    import_env: dict[str, Callable[..., Any]] = {}
    if wit is not None:
        import_env = build_component_import_env(wit["imports"], resolved, memory_ref, store)

    linker = Linker(engine)

    # SPEC §10.2 — supply the minimal WASI Preview 1 surface from wasmtime's
    # built-in implementation so I/O-using library modules (e.g. a modc lib that
    # calls console.log → fd_write) instantiate in a host with no native WASI.
    linker.define_wasi()
    wasi_cfg = WasiConfig()
    wasi_cfg.inherit_stdout()
    wasi_cfg.inherit_stderr()
    store.set_wasi(wasi_cfg)

    # With a .wit, a function import is bound to its WIT import's wrapper; without one (raw
    # mode), to the host callback of the same name, called with raw values. An import bound to
    # nothing fails the load naming every such import — never a stub that returns 0 (it was one
    # before 2.0.0; -js fails the same load at link time).
    unbound: list[str] = []
    for imp in module.imports:
        if not isinstance(imp.type, FuncType):
            continue
        # WASI imports are handled by define_wasi above; don't double-define them.
        if imp.module in _WASI_MODULES:
            continue
        ft: FuncType = imp.type
        imp_name = imp.name
        if imp_name is None:
            # Only the module-linking proposal has nameless imports; they cannot be bound by name.
            raise RuntimeError(f"{cleaned!r}: import from {imp.module!r} has no name")
        if wit is not None:
            if imp_name in import_env:
                linker.define_func(imp.module, imp_name, ft, import_env[imp_name])
            else:
                unbound.append(f"{imp.module}::{imp_name}")
        elif host_callbacks and callable(host_callbacks.get(imp_name)):
            cb = host_callbacks[imp_name]
            linker.define_func(imp.module, imp_name, ft, lambda *a, fn=cb: fn(*a))
        else:
            unbound.append(f"{imp.module}::{imp_name}")
    if unbound:
        where = "the .wit does not declare" if wit is not None else "no host callback for"
        raise RuntimeError(
            f"wasm_import: {cleaned!r}: {where} module import(s): {', '.join(unbound)}"
        )

    instance = linker.instantiate(store, module)
    raw = _collect_raw_exports(module, instance, store)

    # SPEC §10.1 — run the reactor initializer before any other export is called.
    _call_initialize(raw, store)

    mem = raw.get("memory")
    if isinstance(mem, wasmtime.Memory):
        memory_ref[0] = mem
    realloc = raw.get("cabi_realloc")
    if isinstance(realloc, wasmtime.Func):
        cabi_realloc_ref[0] = realloc

    if requested_version is not None:
        _assert_version(raw, store, requested_version, cleaned)

    if wit is not None:
        proxy = build_component_export_proxy(
            raw, wit["exports"], memory_ref, store, cabi_realloc_ref
        )
        for name, val in raw.items():
            if name not in proxy:
                if isinstance(val, wasmtime.Func):
                    fn = val
                    proxy[name] = lambda *args, f=fn: f(store, *args)
                elif isinstance(val, wasmtime.Global):
                    proxy[name] = val.value(store)
        return proxy

    return _wrap_for_user(raw, store)


def create_singleton(
    wasm_path: str | Path,
    host_callbacks: dict[str, Callable[..., Any]] | None = None,
) -> Callable[[], Any]:
    _cache: dict[str, Any] | None = None
    _lock: asyncio.Lock | None = None

    async def get() -> dict[str, Any]:
        nonlocal _cache, _lock
        if _lock is None:
            _lock = asyncio.Lock()
        async with _lock:
            if _cache is None:
                _cache = await wasm_import(wasm_path, host_callbacks)
        return _cache

    return get


class InstancePool:
    def __init__(
        self,
        wasm_path: str | Path,
        host_callbacks: dict[str, Callable[..., Any]] | None = None,
        size: int = 4,
    ) -> None:
        # SPEC §6.2: default 4 instances (it was 2 until 2.0.0).
        self._path = wasm_path
        self._callbacks = host_callbacks
        self._size = size
        self._pool: asyncio.Queue[dict[str, Any]] | None = None
        self._lock: asyncio.Lock | None = None

    async def _ensure_ready(self) -> None:
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            if self._pool is not None:
                return
            q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
            for inst in await asyncio.gather(
                *[wasm_import(self._path, self._callbacks) for _ in range(self._size)]
            ):
                q.put_nowait(inst)
            self._pool = q

    async def acquire(self) -> dict[str, Any]:
        await self._ensure_ready()
        assert self._pool is not None
        return await self._pool.get()

    async def release(self, instance: dict[str, Any]) -> None:
        if self._pool is not None:
            await self._pool.put(instance)

    async def run(self, fn: Callable[[dict[str, Any]], Any]) -> Any:
        instance = await self.acquire()
        try:
            result = fn(instance)
            if asyncio.iscoroutine(result):
                return await result
            return result
        finally:
            await self.release(instance)
