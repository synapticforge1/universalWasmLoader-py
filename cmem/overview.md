# Overview — universalWasmLoader-py

## What this is

The **Python port** of the Universal WASM Loader. It loads and instantiates WebAssembly
modules and, when a companion `.wit` file is present, applies the Canonical ABI so the host
calls WIT exports with idiomatic Python values (numbers, `bool`, `str`) instead of raw i32/ptr
pairs. It is a direct port of the reference JavaScript implementation
(`universalWasmLoader-js`), which is the canonical source for API design, behavior, and
conformance tests. The JS repo is vendored as a git submodule at
`upstream/universalwasmloader-js/`.

- **License:** MIT (© 2026 Jon Marcum). `LICENSE` is byte-identical to the `-c`/`-zig` ports and
  ships inside the sdist (`[tool.hatch.build.targets.sdist] include`); hatchling also auto-includes
  it in the wheel's `.dist-info` (as PEP 639 `License-File`).
- **Status:** **PUBLISHED on PyPI** (`Development Status :: 5 - Production/Stable`). First release
  **1.0.0** uploaded 2026-06-19 via the OIDC Trusted-Publishing workflow; **1.0.1** uploaded
  2026-06-19 (README trimmed to a user-facing PyPI page + clearer usage example); **1.1.0** uploaded
  2026-10-21 (SPEC §10 loader capabilities; first release from the `synapticforge1` org); **1.1.1**
  uploaded 2026-10-26 20:23 UTC (2 files). **Measured 2026-11-08 (PyPI JSON API): PyPI serves ONLY
  `1.1.1`**; `/pypi/universal-wasm-loader/<v>/json` answers **404 for 1.0.0, 1.0.1 and 1.1.0** —
  they were removed from PyPI. **Owner, 2026-11-08: "yes 1.1.1 is the only one on pypi"** —
  intended. Those three version numbers stay reserved on PyPI forever. Brought to parity with the `-c` and `-zig` ports on
  2026-06-19. Live at <https://pypi.org/project/universal-wasm-loader/>.
- **Latest: 2.0.5 (2026-11-10)** on PyPI (with PEP 740 attestations) and GitHub; 2.0.4 was
  tagged but never published. Every release, newest first, with a summary
  of what changed: [release.md](release.md) § "Release History".
- **Home:** <https://github.com/synapticforge1/universalWasmLoader-py> — the **`synapticforge1`**
  GitHub organization (owner-controlled). Transferred from the personal account `jrmarcum`
  (confirmed via the GitHub API 2026-10-21); see "Repository transfer" below. The upstream JS
  reference moved with it: <https://github.com/synapticforge1/universalWasmLoader-js>.

## Repository transfer → `synapticforge1` org (recorded 2026-10-21)

Both `universalWasmLoader-py` and `universalWasmLoader-js` were transferred from `jrmarcum` to the
owner's **`synapticforge1`** organization. GitHub redirects the old `jrmarcum/...` URLs, so nothing
broke immediately.

**Done in-repo (2026-10-21):** `git remote origin` → `synapticforge1/universalWasmLoader-py.git`
(verified with `git ls-remote`); `.gitmodules` upstream URL → `synapticforge1/universalWasmLoader-js.git`
+ `git submodule sync`; `pyproject.toml` `[project.urls]` (reaches PyPI only with the next published
version); `publish.yml` comments (Trusted-Publisher owner, Actions-policy wording); README + CLAUDE.md
links. The workflow's clone URL uses `${{ github.repository }}`, so it needed no change.

**Done on PyPI (owner, 2026-10-21):** the Trusted Publisher was re-registered for Owner
`synapticforge1` (Repository `universalWasmLoader-py`, Workflow `publish.yml`, Environment `pypi`).
The OIDC claim now carries `repository_owner: synapticforge1`; the old `jrmarcum` publisher would
have made `mint-token` refuse. **Proven live 2026-10-21** — the `1.1.0` CI publish minted its token
through the new publisher.

**Confirmed since:** the `synapticforge1` Actions policy accepts hash-pinned `uses:` (this repo's
run 42517168769, 2026-11-08). **The `pypi` environment does NOT pause for a reviewer** (measured
2026-11-09: 2.0.1's run started `publish` 4 s after `checks`); the 2026-06-19 hardening below
said it did. **Owner, 2026-11-09: "no" to adding a reviewer** — no pause is the decided
behaviour (re-measured on 2.0.2 and 2.0.3).

The PyPI package name (`universal-wasm-loader`) and the PyPI account are unaffected by the transfer.
The JSR scope `@jrmarcum/...` used by the JS upstream is a JSR scope, not a GitHub owner, and is
not changed by this move.

## Language / runtime

- **Language:** Python ≥ 3.11 (classifiers list 3.11 / 3.12 / 3.13).
- **WASM runtime:** [`wasmtime`](https://pypi.org/project/wasmtime/) (wasmtime-py) `>=26.0.0`,
  the only runtime dependency. The loader uses wasmtime's core API — `Engine`, `Module`,
  `Store`, `Linker`, `Instance`, `Memory`, `Func`, `Global` — NOT the higher-level Component
  Model API. Canonical ABI marshalling is implemented by hand in `_abi.py`.
- **Package/env manager:** pixi (conda-forge channel for Python; PyPI for deps). Editable
  install of the package itself plus a `dev` feature for the test/lint/type tools.
- **Build backend:** hatchling (wheel packages `src/universal_wasm_loader`).
- **Registry:** PyPI, package name **`universal-wasm-loader`** (latest published **`2.0.5`**,
  2026-11-10; 2.0.4 never published; 1.0.0 / 1.0.1 / 1.1.0 removed, owner-confirmed; PyPI never reuses a version number,
  removed ones included). Releases: [release.md](release.md).

## Repository layout

```text
src/universal_wasm_loader/
  __init__.py      # public re-exports: wasm_import, create_singleton, InstancePool
  _loader.py       # core: wasm_import(), create_singleton(), InstancePool, version pinning
  _wit_parser.py   # STRICT WIT parser, a port of -js wit-parser.js 2.0.0 (parse_wit; SPEC 4.0.0 §2)
  _abi.py          # Canonical ABI bridge: callback resolution, import env, export proxy, checks
tests/
  conftest.py      # pytest fixtures: paths into fixtures/, raw staging, versioned.wat -> .wasm
  test_loader.py   # loader + ABI integration tests
  test_refusals.py # SPEC 4.0.0 §8 "Refusals", every non-http row
  test_fixtures.py # fixtures/ = the stamped reference set (sha256 vs fixtures.json)
  test_wit_parser.py
  test_pypi_files.py # scripts/pypi_files.py (urlopen stubbed; no network)
  test_github_release.py # scripts/github_release.py on an in-process mock API (no network)
  test_release_script.py # release.py: the ls-remote read-back, PyPI's project list, no tag
  test_pypi_attest.py # scripts/pypi_attest.py (fake sigstore modules; no network)
  fixtures/        # the -js reference set, copied unmodified (H7): {math,booleans,strings,
                   # imports,wasi_io}_50.{wasm,wit}, init_check.{wat,wasm}, fixtures.json
  py_fixtures/     # Python-only: versioned.wat (`version` global, for @N pinning)
scripts/           # pixi Python: bump_version, release (pushes main only), compat, _common;
                   # stdlib-only pypi_files + github_release, and pypi_attest (CI's publish venv),
                   # each fetched by commit and run by CI with the runner's python3
.github/workflows/
  ci.yml           # the gate on every push to main / PR (pixi-locked)
  publish.yml      # push of main: checks → tag → release (page) → dispatch; the dispatched run
                   # on the tag: build → publish (OIDC, `pypi`, PEP 740) — see release.md
upstream/universalwasmloader-js/   # git submodule (reference impl + SPEC.md)
```

## Public API surface (what actually exists)

Idiomatic Python equivalents of the reference loader's `wasmImport` / `createSingleton` /
`InstancePool`. All three are re-exported from the package root (`__init__.py`).

- **`async wasm_import(wasm_path, host_callbacks=None) -> dict[str, Any]`** (`_loader.py`)
  — the entry point. Reads the `.wasm` bytes (off-thread via `asyncio.to_thread`), looks for a
  sibling `.wit`, instantiates via a `Linker`, and returns a dict of exports.
  - `wasm_path` is `str | Path`; a trailing `@N` suffix pins a version
    (`_parse_version_suffix`), validated against an exported `version` **global**
    (`_assert_version`, raises `RuntimeError` on mismatch / missing).
  - With a WIT file: returns the camelCase-keyed **export proxy** with ABI translation
    applied (`build_component_export_proxy`); raw exports not described by WIT are passed
    through.
  - Without a WIT file: returns raw exports wrapped for direct calling
    (`_wrap_for_user` — `Func` → callable, `Global` → its value).
  - `host_callbacks` is a flat dict of host functions the module imports. With a `.wit`: every
    WIT import needs one (camelCase key, or the kebab WIT name), resolved BEFORE the `.wasm` is
    read (`resolve_import_callbacks`), then wrapped with ABI adaptation
    (`build_component_import_env`). Without a `.wit` (raw): bound by the module's own import
    name, raw values. **Any non-WASI function import bound to nothing fails the load naming
    every one** (since 2.0.0; until 1.1.1 a no-op stub `_make_noop` returned 0, deleted).
  - **SPEC §10 producer model (loader capabilities):**
    - **§10.1** — after instantiation, `_call_initialize` runs a reactor module's
      `_initialize` export exactly once before any other export is called (no-op if absent).
    - **§10.2** — the minimal WASI Preview 1 surface is supplied by wasmtime-py's built-in
      implementation: `linker.define_wasi()` + a `WasiConfig` (`inherit_stdout/stderr`) set on
      the `Store`. Imports in the `wasi_snapshot_preview1` / `wasi_unstable` namespaces
      (`_WASI_MODULES`) are skipped in the stub loop so they resolve to real WASI, letting
      I/O-using library modules (e.g. a `modc` lib that calls `console.log` → `fd_write`)
      instantiate in a host with no native WASI. Covered by the `test_spec10_*` tests
      (`init_check.wasm`, `wasi_io_50.wasm`).
- **`create_singleton(wasm_path, host_callbacks=None) -> Callable[[], Awaitable[dict]]`**
  — returns an async getter that instantiates once and returns the same instance on every
  call (CLI / DLL pattern). Guarded by an `asyncio.Lock`.
- **`class InstancePool(wasm_path, host_callbacks=None, size=4)`** (SPEC §6.2; `size=2` until
  2.0.0, changed `93cc2f3` on the owner's "yes change the instance pool") — N independent instances
  in an `asyncio.Queue`; `await acquire()` / `await release(inst)` / `await run(fn)`
  (acquire → call → release, awaits coroutine results). Server / concurrent-workload pattern.

## Canonical ABI (as implemented in `_abi.py`)

- **argument / result checks (SPEC 4.0.0 §4, `_arg_problem`)** — no coercion: `s32` / `s64` an
  `int` in range and NOT a `bool` (Python's `bool` is an `int` subclass, excluded by hand);
  `f32` / `f64` a `float` only (an `int` is refused — the "floating type" reading -dotnet / -jvm
  / -go chose; JS accepts any number because it has one number type); `bool` a `bool`; `string` a
  `str`. Typed calls check arity + kinds (`TypeError` naming export + parameter); host-callback
  returns are checked the same way (`TypeError` naming callback, WIT import, result type, value;
  wasmtime-py re-raises a host function's exception to the export's caller unchanged, measured
  2026-11-08); an awaitable return is refused (a coroutine is closed first); void ignores it.
- **numbers** (`s32`/`s64`/`f32`/`f64`) — passed straight through once checked.
- **bool** ↔ i32: params `1 if v else 0`; returns `result != 0`.
- **string** ↔ `(ptr: i32, len: i32)`:
  - **params** — UTF-8 encode, allocate via the module's exported `cabi_realloc(0, 0, 1, len)`,
    write bytes into exported `memory`, pass `(ptr, len)` as two args (`_encode_string`).
  - **returns** — see conformance note below.
- **naming** — kebab-case WIT names → camelCase keys for the proxy; underscore form
  (`kebab_to_wasm_key`) for wasmtime export/import lookup. Imports resolve callbacks by
  camelCase first, then raw name.

The WIT parser (`_wit_parser.py`) is STRICT since 2.0.0: a port of -js `wit-parser.js` 2.0.0,
same grammar and messages; anything outside it raises `ValueError` (until 1.1.1 it was loose
regex: unknown types read as `s32`, malformed parameters dropped, garbage = an empty world).

## SPEC 4.0.0 — ✅ IMPLEMENTED on local `main` (2026-11-08, workspace ledger C29)

Commits **`568f7f3`** (surface re-baseline alone: README `SPEC.md` v4.0.0, `api-surface.json`
`"spec": "4.0.0"`, 7 symbols unchanged; submodule `d9f6860` → `1169ab9` = -js tag `v2.0.0`),
**`bb7feb6`** (behaviour + tests + README Breaking row). Item by item:
(1) §2 absent = `FileNotFoundError` or a path not ending in `.wasm` (1.1.1's `Path.with_suffix`
made `math.bin` read `math.wit`); any other read failure → `OSError` "cannot read .wit '<path>'",
non-UTF-8 → `ValueError`; the `except Exception: wit = None` is gone. (2) §2 strict parser →
`ValueError` "invalid .wit '<path>': …"; a WIT export the module lacks → `RuntimeError`.
(3) §4 every WIT import needs a callback, all missing named (`TypeError`), and a string-result
import (`NotImplementedError`), both BEFORE the `.wasm` is read; callback returns checked.
(4) §4 typed calls check arity + kinds; no kind-specific accessors here, so that half is n/a.
(5) §11 **n/a**: local files only, no http path, so no `options` argument (as loader-c).
Also removed: the raw-mode 0-stub for unbound imports, and two silent fall-throughs on a string
with no `memory` / `cabi_realloc` (passed the `str` through / returned the raw pointer).
**The check, §8 Refusals:** every non-http row is a test (`tests/test_refusals.py`). Tests 34 →
91, gate green. **Inverted:** the new suite on v1.1.1's src → 57 failed / 34 passed (26 unchanged
tests + 8 the old code also met). v1.1.1's 26 behaviour tests pass on the new src; its 8 parser
tests call 3.0.0 internals (`parse_wit_funcs`; `parse_wit_type("unknown") == "s32"`), not required
at a major floor. `compat.py`: floor **major** (`SPEC.md v3.0.0 -> v4.0.0`); `bump major --dry-run`
ALLOWED → 2.0.0. **Version decision: MAJOR, 2.0.0** — not bumped; bump / push / release are the
owner's. Fixtures unchanged. The one remaining divergence, `InstancePool`'s default `size=2` vs
SPEC §6.2's 4, was fixed the same day (`93cc2f3`, owner) and is in 2.0.0.

**SPEC 4.0.1 — CLAIMED since `fdca3d9` (owner, 2026-11-10: "spec is on 4.0.1").** "A
clarification, no loader has to change" (-js `ac1de68`, released in -js v2.0.3): a §11.1 allowance
for a port whose zero-value options type means the default limit (loader-go's case). n/a here: no
`options`, no http path, so no behaviour change. README declares `SPEC.md` **v4.0.1**,
`api-surface.json` `"spec": "4.0.1"` (re-baseline alone, Rule 5), the submodule moved `1169ab9` →
`15388fd` (-js v2.0.3). compat floor since v2.0.5: patch. It reaches PyPI with the next release.

## SPEC conformance status — ✅ ALIGNED TO SPEC 3.0.0 (2026-06-15) — history; 4.0.0 above

The cross-language `SPEC.md` is at **v3.0.0 (2026-06-15)**, a **BREAKING** change to the
string / aggregate **return** convention. **This port now implements the SPEC 3.0.0
canonical callee-allocated return path.**

- **SPEC 3.0.0 (implemented):** a string/aggregate-returning export returns a single **i32
  pointer** to a callee-allocated `[ptr, len]` pair in linear memory. The host reads the two
  little-endian i32 words at that pointer, decodes UTF-8, **then calls the paired
  `cabi_post_<name>(retPtr)` export** (where `<name>` is the camelCase export name, e.g.
  `greet` → `cabi_post_greet`) to let the callee free that memory; if that export is absent
  the post-call is skipped.
- **Superseded:** the old caller-allocated 8-byte out-param convention, and the even older
  multi-value `(ptr, len)` tuple return this port used previously.

The string-return marshalling lives in:

> **`src/universal_wasm_loader/_abi.py`**, function **`build_component_export_proxy`** →
> inner **`make_proxy` / `call`**.

`make_proxy` captures `cabi_post_<camel_name>` from `raw_exports` at proxy-construction time.
The `call` closure: encodes string params unchanged (UTF-8 → `cabi_realloc(0,0,1,len)` →
write → pass `(ptr,len)`); calls the export with ONLY those params, capturing the **single
i32** return (`ret_area`); reads `str_ptr` / `str_len` via the new `_read_i32_le` helper at
`ret_area` / `ret_area+4`; decodes; calls `cabi_post(...)` if present; returns the `str`.

**Export-key lookup fix (required by this work):** `build_component_export_proxy` now resolves
each raw export by `camel_name` (falling back to `wasm_key`), matching wasmtk's camelCase
export names and the JS reference's lookup by `tsName`. Previously it used only the
underscore `wasm_key`, so any multi-word export (e.g. WIT `str-len` → exported `strLen`) was
not found in the proxy and fell through to the raw-export passthrough — which failed for a
string-param export because the arg was never encoded to `(ptr, len)`.

Numerics/bool params and returns, and string **params**, are unchanged and remain spec-correct.

> **Note:** there is no repo-local `SPEC.md` copy to update — the authoritative `SPEC.md`
> lives in the JS reference submodule (`upstream/universalwasmloader-js/SPEC.md`), which is a
> separate upstream repo and is not edited from here.

## Tests

- Runner: `pytest` via `pixi run test` (`asyncio_mode = "auto"`, `pytest-asyncio`).
- **Fixtures = the stamped reference set (workspace letter H7, 2026-10-26).** `tests/fixtures/`
  holds exactly universalWasmLoader-js's 12 fixtures + `fixtures.json`, copied byte for byte from
  -js `36aa661` (on its `origin/main`); stamp = wasmtk `4a5c3cf668d`
  (`v2.0.3-64-g4a5c3cf`, `synapticforge1/wasmtk`). **COPY the stamp, never regenerate it**
  (`git describe` output depends on the clone — loader-dart's finding). To update: re-copy every
  `*.wasm`, `*.wit`, `*.wat` and `fixtures.json` from -js `tests/`; never edit one by hand.
  `test_fixtures.py` fails on a missing file, changed bytes, or an unlisted `.wasm/.wit/.wat`
  (inverted 2026-10-26: a flipped byte, CRLF in a `.wit`, a deleted `.wit`, a stray `.wat` — each
  caught for its own reason; the unmodified copy clean). `.gitattributes` (`* text=auto eol=lf`,
  `*.wasm binary`) keeps the text fixtures' bytes = the stamp on every clone.
- `test_loader.py`: the reference-set tests assert what -js `tests/loader.test.js` asserts on the
  same modules (math, booleans, strings, imports via WIT, SPEC §10 `init_check` / `wasi_io_50`,
  `create_singleton`, `InstancePool` incl. concurrent); **Python-only** sections add the raw path
  (`math_50` / `imports_50` staged without their `.wit`; raw callbacks by the module's own import
  names `env_mul` / `env_add`) and `@N` version pinning (ok, mismatch, no `version` global) on
  `tests/py_fixtures/versioned.wat` — the reference set has no `version` global.
  Inverted 2026-10-26: deleting `booleans_50.wit` failed exactly the stamp test and the five bool
  tests (`assert 1 is True`: the raw path returns the i32).
- `test_wit_parser.py` covers the WIT parser; `test_refusals.py` the SPEC 4.0.0 refusals;
  `test_pypi_files.py` the upload planner.
- **Baseline 2026-11-09: 120 passed, 0 failed** (`pixi run gate`). Before: 117 (CI release job), 108 (H30), 105
  (2026-11-08, also CI run 42518020978), 92 (+ pool size), 91 (SPEC 4.0.0), **2026-10-26: 34
  passed** (`pixi run test`). The old harness bug (drift L8:
  `conftest` compiled `.wat` with `Module.serialize()`, which yields wasmtime's precompiled
  artifact, not a `.wasm`, so 13 tests failed "input was not valid utf-8") is gone: the one
  remaining `.wat` is compiled with `wasmtime.wat2wasm`.

## Build / release flow (REWORKED 2026-06-19 — parity with `-c`/`-zig`)

- Dev tooling: `pixi run lint` (ruff), `pixi run fmt` (ruff format), `pixi run typecheck`
  (mypy strict), `pixi run test` (pytest).
- **The gate: `pixi run gate`** = lint → typecheck → test (added 2026-10-26; a test task alone is
  not a gate). `ci.yml` (every push / PR) and `publish.yml`'s `checks` job run the same three
  commands in the same order, each able to fail the job before the build. Inverted 2026-10-26: an unsorted import failed it at lint; a planted
  `tuple[int, str]` return failed it at mypy (lint passing). The four pre-existing `src/` findings
  were fixed with it (two UP035 `collections.abc.Callable`, one unused `type: ignore`, and
  `_loader.py`'s nameless import — `ImportType.name` is `Optional` for the module-linking proposal —
  now a `RuntimeError` instead of `define_func(…, None, …)`). Since `4548c34` (2026-11-08) CI
  installs the same `pixi.lock` (pixi 0.84.1 pinned by sha256), so CI and local runs use one set of
  tool versions (until then CI pip-installed them unpinned).
- Build: hatchling wheel + sdist via `pixi run python -m build` (local: isolated, fetches
  hatchling; CI: `--no-isolation` with the locked hatchling 1.33.0). The packaging tools
  (`hatchling`, `build`, `twine`) live in a **`publish` pixi feature** (`pixi.toml`), included in
  the default environment. `pixi.lock` is committed (first added 2026-10-21; last regenerated
  2026-11-08 by pixi 0.84.1, which CI pins); `.pixi/` and `dist/` are gitignored, as are a stray
  `uv.lock` and the machine-local `.claude/`. pixi warns that `pixi.toml`'s `[project]` table
  should be renamed `[workspace]` (deprecation only; not yet changed). **The build is not
  byte-reproducible across machines** (measured 2026-11-08, 2.0.0).

### Release tooling, CI, and every release record → [release.md](release.md)

🔒 Moved 2026-11-10 (workspace H33 U11: ONE place per project, `cmem/release.md` § "Release
History", newest first). There: **How a release runs** (the owner's order — `pixi run bump
<level>` → `pixi run release` pushes `main` only → CI checks → CI tags → the page → the publish
on the tag, with PEP 740 attestations), the **Release History** (2.0.3 → 1.0.0, a summary each,
run ids and read-backs), and **how the release workflow got here** (OIDC by hand, C30's split,
per-file upload, H30 / H32 / 7.21, the `pypi` environment). `pyproject.toml` `[project] version`
is the single source of truth; `pixi.toml` mirrors it (`bump_version.py` syncs both). The
detailed pre-H33 history of the scripts and the single- / two-job workflow is in git history
(this file before `release.md` was made).

- **Test baseline 2026-10-21** (`uv run --extra dev python -m pytest tests`, wasmtime from PyPI):
  **13 passed / 13 failed.** All 13 failures are the known `.wat`-fixture harness caveat ("input was
  not valid utf-8"); every string-ABI, SPEC §10 and WIT-parser test passes.
