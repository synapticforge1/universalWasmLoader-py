> **⚠️ PORTABLE PROJECT MEMORY LIVES IN `cmem/`** — start at [`cmem/INDEX.md`](cmem/INDEX.md).

> **At session start, read `../../cmem/workspace-correspondence.md`** (every row addressed to this
> repo, and every row touching the work at hand), **then the letter it points to in
> `../../cmem/handoffs.md`.** The workspace session (`../../cmem/INDEX.md`) reviews across the
> sibling repos and reports there; nothing is ever written into this repo from outside. (owner
> directive, 2026-09-20; ledger first since 2026-10-26)

> When saving new project memory, write it into the matching `cmem/` topic file (and refresh its
> pointer in `cmem/INDEX.md`). The **"update the project memory"** and **"look for code issues"**
> triggers are defined in `cmem/INDEX.md` and are binding on every agent.

# universalWasmLoader-py

Python port of the [Universal WASM Loader](https://github.com/synapticforge1/universalWasmLoader-js).
Hosted at `github.com/synapticforge1/universalWasmLoader-py` (org `synapticforge1`; moved from
`jrmarcum` 2026-10-21 — see `cmem/overview.md` "Repository transfer").
Loads and instantiates WebAssembly modules and, when a companion `.wit` file is present, applies
the Canonical ABI so you call WIT exports with idiomatic Python values (`int`/`float`, `bool`,
`str`). Built on [`wasmtime`](https://pypi.org/project/wasmtime/) (wasmtime-py). See
[`README.md`](README.md) for user-facing docs and [`cmem/overview.md`](cmem/overview.md) for the
project memory.

## Quick orientation

- `src/universal_wasm_loader/_loader.py` — core: `wasm_import`, `create_singleton`, `InstancePool`,
  version pinning (`@N` suffix vs. an exported `version` global).
- `src/universal_wasm_loader/_abi.py` — Canonical ABI bridge (bool ↔ i32, string ↔ `(ptr,len)`,
  SPEC 3.0.0 callee-allocated string returns + `cabi_post_*`).
- `src/universal_wasm_loader/_wit_parser.py` — regex WIT companion-file parser.
- `tests/` — pytest suite; `tests/fixtures/` is the stamped -js reference set (copy, never edit).
  The gate: `pixi run gate` (lint → typecheck → test, = CI).
- `pyproject.toml` `[project] version` — the single source of truth for the package version.
- `scripts/{bump_version,release,publish}.py` (pixi's Python: `pixi run bump|release|publish`) —
  the release toolchain. Bump (gated) → release (tag + push + GitHub Release) → publish (PyPI),
  publishing kept a deliberate, decoupled step. See [`cmem/overview.md`](cmem/overview.md).
