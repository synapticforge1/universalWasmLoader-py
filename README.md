# universalWasmLoader-py

Universal WASM loader for Python — the Python port of
[universalWasmLoader-js](https://github.com/synapticforge1/universalWasmLoader-js). Loads and
instantiates WebAssembly modules and, when a companion `.wit` file is present, applies the
Canonical ABI so you call WIT exports with idiomatic Python values (`int`/`float`, `bool`,
`str`) instead of raw i32/pointer pairs.

- **Conforms to:** the cross-language `SPEC.md` **v4.0.0**
- **PyPI package:** `universal-wasm-loader`
- **WASM runtime:** [`wasmtime`](https://pypi.org/project/wasmtime/) ≥ 26.0.0
- **License:** MIT

## Install

```sh
pip install universal-wasm-loader
```

## Usage

`wasm_import()` loads a `.wasm` module and hands you its exports as a dict of
**ready-to-call Python functions** — pull one out, bind it to a name, and call it
like any other function:

```python
import asyncio
from universal_wasm_loader import wasm_import

async def main():
    # Load the module. Exports come back as a dict of callables.
    exports = await wasm_import("./math.wasm")

    # Turn a WASM export into a Python function and call it.
    # (companion math.wit -> `calculate: func(a: s32, b: s32) -> s32`)
    calculate = exports["calculate"]
    print(calculate(1, 2))        # 3

asyncio.run(main())
```

When a companion `<name>.wit` sits next to the `.wasm`, the **Canonical ABI** is
applied automatically: kebab-case WIT names become camelCase keys, and arguments
and results are idiomatic Python values (`bool`, `str`) — no manual i32/pointer
handling:

```python
# strings_50.wasm + strings_50.wit -> greet, shout, str-len
exports = await wasm_import("./strings_50.wasm")

greet = exports["greet"]
print(greet("World"))             # "Hello, World!"   (str in, str out)
print(exports["strLen"]("hello")) # 5                 (WIT export `str-len`)
```

Loads and calls fail loudly (SPEC 4.0.0); nothing is coerced or defaulted:

- Only an **absent** `.wit` (no file, or a path that does not end in `.wasm`) gives raw exports.
  An unreadable or non-UTF-8 `.wit` raises `OSError` / `ValueError`, and so does a `.wit` that
  does not parse (an unsupported type such as `u32`, a malformed parameter, text outside the one
  `world`). A WIT export the module lacks raises `RuntimeError`.
- **Every WIT import needs a host callback** (camelCase key), checked before the `.wasm` is read;
  the `TypeError` names every missing one. A callback must return its import's WIT type (an `s32`
  import cannot return `None`, `2.9` or `True`) and must not be `async`.
- **Typed calls check their arguments:** the count, and the kind per WIT type: `s32` / `s64` take
  an `int` in range (not a `bool`), `f32` / `f64` a `float`, `bool` a `bool`, `string` a `str`.
  A wrong one raises `TypeError` naming the export and the parameter.
- A module import that nothing provides (raw mode: no callback of that name) raises at load.

`create_singleton()` (one shared instance) and `InstancePool()` (N instances for
concurrent workloads) are also exported. See the
[project on GitHub](https://github.com/synapticforge1/universalWasmLoader-py) for the
full API, examples, and source.

## Versioning

This package follows [Semantic Versioning 2.0.0](https://semver.org/). Every bump is gated: the
release tooling compares the public API (`api-surface.json`: every exported symbol with its
signature, plus the `SPEC.md` version) with the previous release, and refuses a bump lower than the
change requires. It also runs the previous release's tests against the new code.

### ⚠️ Breaking Changes

| Version | What changed | How to migrate |
| --- | --- | --- |
| _next release_ | SPEC 4.0.0. A `.wit` that exists but cannot be read or parsed is an error (it was silently ignored, loading raw); an unknown WIT type is an error (it was read as `s32`). A missing host callback fails the load (it returned `0`), and so does a module import nothing provides. Callback results and typed-call arguments are checked, not coerced: e.g. `f64` refuses an `int`, `s32` refuses a `bool` or a `float`. A path not ending in `.wasm` has no companion `.wit`. `InstancePool`'s default `size` is 4 (SPEC §6.2; it was 2). | Provide a callback for every WIT import; return its exact WIT type; pass `float` to `f32` / `f64` (`3.0`, not `3`); fix or remove a broken `.wit`; pass `size=2` to keep the old pool size. |
