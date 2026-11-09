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
- **2.0.0 (SPEC 4.0.0) PUBLISHED 2026-11-08** (2 files, 19:52:37–38 UTC; PyPI latest = 2.0.0,
  releases 1.1.1 + 2.0.0, read back) — § "Release 2.0.0" below.
- **2.0.1 PUBLISHED 2026-11-09** (2 files, 15:15:19–20 UTC, per-version JSON read back) — the
  first release through the tag-triggered workflow; § "Release 2.0.1" below.
- **2.0.2 PUBLISHED 2026-11-09** (2 files, 15:27:56–57 UTC) with the first GitHub Release page made
  by CI; § "Release 2.0.2" below. Latest on PyPI and on GitHub.
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
said it did. Its settings are not readable from here (the environments API needs auth) — an
owner item in [open-work.md](open-work.md).

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
- **Registry:** PyPI, package name **`universal-wasm-loader`** (latest published **`2.0.0`**; PyPI
  serves 1.1.1 + 2.0.0, measured 2026-11-08; 1.0.0 / 1.0.1 / 1.1.0 removed, owner-confirmed; PyPI
  never reuses a version number, removed ones included).

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
  test_release_script.py # release.py's ls-remote read-back + Release-page link helpers
  fixtures/        # the -js reference set, copied unmodified (H7): {math,booleans,strings,
                   # imports,wasi_io}_50.{wasm,wit}, init_check.{wat,wasm}, fixtures.json
  py_fixtures/     # Python-only: versioned.wat (`version` global, for @N pinning)
scripts/           # pixi Python: bump_version, release, publish, compat, _common; stdlib-only
                   # pypi_files + github_release (also run by CI with the runner's python3)
.github/workflows/
  ci.yml           # the gate on every push to main / PR (pixi-locked)
  publish.yml      # on a v* tag push: checks → publish (OIDC, `pypi` env) → release (Release page)
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

**SPEC 4.0.1 (read 2026-11-09, -js `ac1de68`):** "a clarification, no loader has to change" — a
§11.1 allowance for a port whose zero-value options type means the default limit (loader-go's
case). n/a here: no `options`, no http path. This repo still DECLARES 4.0.0 (README + submodule
`1169ab9`); moving the claim is a README + surface re-baseline + submodule bump, at the owner's
word (loader-rs moved its claim when its bump script refused on the reference SPEC; this gate
reads README, so it does not refuse).

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

### Single source of truth + the three-script toolchain

**`pyproject.toml` `[project] version` is the single source of truth** for the package version;
`pixi.toml` mirrors it (kept in sync by `bump_version.py`). Three scripts key off it, all **pixi
Python** (`scripts/*.py` + shared `_common.py`; `pixi run bump|release|publish …`, or
`pixi run python scripts/<name>.py …`). Since 2026-11-08 the release's tag push STARTS the CI
publish (no reviewer pause, measured 2026-11-09); `publish.py` is the local fallback.

**Ported from Bash + Nushell 2026-10-26 (workspace letter H15).** The six `.sh` / `.nu` files were
replaced only after an equivalence run (one-time, not committed): every case run on the `.sh`
original and the `.py` port in two identical scratch clones (pinned commit dates, `origin` = a
scratch bare repo, no credentials), diffing stdout, stderr, exit code, manifests, HEAD, tags and the
remote's refs — **24 cases** (12 bump incl. dirty tree / existing tag / non-semver / not-greater,
7 release incl. two REAL tag + push runs, 5 publish incl. PyPI's "already published" and the
credentials guard): **23 identical, 1 different as declared** (`--help` loses the `.sh`'s stray
`set -euo pipefail` line). The run caught one real port slip (`export ` dropped from the
credentials hint, fixed `d465fd6`). The `.nu` forms could not be run here (`nu` absent); they were
ports of the `.sh`. **Declared differences:** messages name `scripts/*.py`; `--help` prints the
docstring; output is UTF-8 + LF on every platform; and **`publish` proceeds only on an HTTP 404**
from PyPI's JSON API — the `.sh`'s `curl -f` read ANY failure (timeout, 5xx) as "not published yet"
and went on toward the irreversible upload (the masked-HTTP-error class loader-js flagged; not
exercisable without PyPI failing, so unproven by the run).

1. **`scripts/bump_version.py` `<major|minor|patch|X.Y.Z>`** — rewrites `[project] version` in
   `pyproject.toml` (and the `pixi.toml` mirror) and commits the isolated bump. Guards: clean tree,
   strictly-greater target, no pre-existing tag, valid semver. `--dry-run` / `--no-commit`.
2. **`scripts/release.py`** — reads the version, verifies a clean tree + a fresh
   `pixi run python -m build`, tags `v<version>`, pushes branch + tag to `origin`, **reads both
   back with `git ls-remote` (exit 1 unless `main` and `v<version>^{}` are HEAD)**, and prints a
   pre-filled `releases/new?tag=…&title=…&body=…` link from the remote URL as the OWNER fallback
   (the page itself is created by `publish.yml`'s `release` job since 2026-11-09; `--notes` fills
   the body; `--no-release` prints nothing). It never
   calls the GitHub CLI (since 2026-11-09, workspace H30; it used to, and skipped the page when the
   CLI was missing). Idempotent (reuses a tag only if it points at HEAD). Rehearsed on scratch
   clones with scratch bare remotes: a real run read back `main` = `v9.9.1^{}` = HEAD, exit 0; a
   remote that dropped the tag after the push → refused, exit 1; `--dry-run` on a github.com URL
   printed the link (`body=a+%26+b%3F`) and pushed nothing. It does not upload itself, but the
   pushed `v*` tag starts `publish.yml`.
   `--dry-run` / `--no-release` / `--no-build` / `--remote`.
3. **`scripts/publish.py`** — the LOCAL fallback PyPI path (CI on the tag is the normal one).
   **Flow:** `pixi run python -m build`, `twine check`, then `scripts/pypi_files.py`'s plan (only
   404 = no files yet; files already there skipped by name), then `twine upload` of the MISSING
   files only — run inside the pixi env (this is a pixi project).
   Toolchain is auto-detected (pixi when a `pixi.toml` + the `pixi` CLI are present); force with
   `UWL_PY_TOOL=pixi|python` (the `python` fallback uses bare `python -m …`, overridable via
   `$PYTHON`/`$env.PYTHON`).
   **Auth required:** a PyPI API token in the environment — `TWINE_USERNAME=__token__` and
   `TWINE_PASSWORD=pypi-…` (or a `[pypi]` entry in `~/.pypirc`); if absent it prints exactly that
   and exits without uploading. Requires the `v<version>` tag to exist locally **and** on the
   remote. **Idempotent:** GETs `https://pypi.org/pypi/universal-wasm-loader/<version>/json` and, if
   that version already exists, reports success and uploads nothing. Prompts before the irreversible
   upload (`--yes` to skip). `--dry-run` / `--allow-dirty` / `--skip-tag-check` / `--remote`.

### CI + publish (since 2026-11-08, `4548c34`; owner: "CI on push/PR + publish on tag")

- **`.github/workflows/ci.yml`** — every push to `main` and every PR: `contents: read`, a
  tokenless fetch of exactly `$GITHUB_REF` at `$GITHUB_SHA`, no `uses:`; pixi 0.84.1 by URL +
  sha256 (`c81a1659…454a`: the release's `.sha256` = GitHub's asset digest = a local hash),
  `pixi install --locked`, lint / typecheck / test, `compat.py --snapshot`. This repo's first gate
  on GitHub outside a publish. **Measured: run 42518020978 (push of `82f78c8`, owner: "yes" to the
  push) green in every step; no Publish run on that commit (no tag), as designed.** The pixi-locked
  `checks` job of `publish.yml` shares those steps; its own first run is the next release's.
- **`publish.yml` now runs on a `v*` tag push** (+ `workflow_dispatch` for re-runs), so `pixi run
  release` starts it, and it uploads without a reviewer pause (measured 2026-11-09). Per-tag
  `concurrency`, queued, never cancelled. `checks` installs `pixi.lock` (no unpinned pip) and
  builds `--no-isolation` with the locked hatchling 1.33.0 (added to the `publish` feature).
  `publish` fetches `scripts/pypi_files.py` from the repo at `github.sha` and uploads ONLY the
  files PyPI still needs; if PyPI has all of them it mints no token.
- **Per-file idempotency, both paths (`eff40fa`):** `scripts/pypi_files.py` (stdlib) — 404 = no
  files yet, any other answer an error; files already there skipped by NAME (hash reported, not
  required: the build is not reproducible). `publish.py` builds first, then plans; until then it
  read ANY file of the version as "already on PyPI", so a half-published version reported success.
  Measured against the real PyPI: complete → nothing; absent → both; partial → the missing one;
  foreign file → exit 1.
- ⚠️ A force-moved `v*` tag RE-RUNS the publish (workspace H19 note); with the planner such a run
  finds the files and uploads nothing.
- **The GitHub Release page, from CI (owner, 2026-11-09: "can we add the github release page when
  we release it via the github actions?").** A third job, `release` (`needs: publish`,
  `contents: write` only, no checkout): fetches `scripts/github_release.py` (stdlib) by
  `github.sha` and runs it with the runner's `python3` and the job's `GITHUB_TOKEN` — the REST
  API, never the GitHub CLI (H30); Python because it is this repo's language, as -dart / -jvm /
  -dotnet used theirs. Order: the tag must exist and peel (annotated followed) to `github.sha`
  (`POST /releases` would CREATE a missing tag — loader-rs's hazard); an existing Release → done,
  no write (re-runs safe); else POST with generated notes + a PyPI link on top, read back, tag
  re-checked. Proof: `tests/test_github_release.py`, 9 cases on an in-process mock API (create
  with `Bearer` and no `target_commitish`, read-back order; re-run → no write; annotated tag
  peeled; missing / moved / annotated-moved tag → refused with no write; dry run and no token →
  no write; POST 422 → exit 1; malformed tag → no request). Inverted: commit check off → exactly
  the two moved-tag cases red; dry-run guard off → exactly the dry-run case red. Read-only dry
  runs against the real GitHub: `v2.0.1` (annotated) at `4403cc1` → would create, exit 0; at
  `21e680a` → refused; `v9.9.9` → refused. **MEASURED on GitHub, 2.0.2 (run 42644832218):** the
  `release` job created Release **`v2.0.2`** — `github-actions[bot]`, not a draft, published
  15:28:04Z, body = the PyPI link + generated notes `v2.0.1...v2.0.2`, `releases/latest` =
  v2.0.2; the tag still peels to `a89b91a` (no tag created or moved), read back through the REST
  API and `ls-remote`. The re-run path (an existing Release) is covered by the mock tests only.
  **Time limits (2026-11-09, `52c754d`; workspace letter H32 / best-practice 7.21):** every
  request in `github_release.py` and `pypi_files.py` now has ONE total limit, request to last
  byte (30 s): `with_limit()` runs the request and the full body read in a worker thread joined
  with the limit. `urlopen(timeout=)` alone limits each socket operation, so a dripping server
  never tripped it. The socket timeout stays as a backstop at limit + 5 s: equal values RACED
  (under load the socket timeout won once and the error carried another message). Tests: header
  stall + body drip (1 byte / 0.2 s) on a `ThreadingHTTPServer` mock, a stalled PyPI stub; each
  must fail within 2 s. Mutants: no total limit → exactly those cases red.
  **Referred to the workspace as ledger row C41** (owner, 2026-11-09: "the release page should be
  referred back to the workspace to insure that all projects have this setup"), with a measured
  survey: wazmrt, zilc, zailc, rsxtk, loader-c, -v and -zig have no CI-made pages. The workspace
  (C41's recipient) letters the other repos; loader-py, as its creator, closes it. The workspace
  filed it as **letter H32** the same day, and the owner decided: only NEW tags get pages (no
  backfill); loader-c, -v and -zig get CI-made pages too.
  Tags up to `v2.0.1` carry the old `publish.yml` (no `release` job), so their pages are web-UI
  owner items ([open-work.md](open-work.md)).

### Publish workflow — `.github/workflows/publish.yml` (TOKEN-FREE, TWO JOBS since 2.0.0)

**Current shape (`ae51e95`, 2026-11-08, workspace C30; owner: "yes C30 applies here").** Top-level
`permissions: {}`. **`checks`** (`contents: read`, no `id-token`, TOKENLESS clone — the repo is
public) refuses unless the run is FROM tag `ref` and HEAD = `github.sha`, then runs the pip
installs, the gate, `compat.py --release`, build and `twine check`, and uploads `dist/`.
**`publish`** (`id-token: write` only, environment `pypi`) has no checkout and no build: `git
ls-remote --tags` (peeled `^{}` first) must equal `github.sha`, then it downloads `dist/`, installs
only `twine==7.0.0` (`--only-binary :all:`, own venv) and does the OIDC mint + upload below.
**`uses:`** only `actions/upload-artifact@cf430e0…` (v7.0.2) and `actions/download-artifact@9000827…`
(v8.0.2), full commit hashes verified as commits via the GitHub API — the old "never `uses:`" rule
came from the previous owner's policy; the org accepts hash-pinned actions (loader-dotnet run
42441589123). Checked locally: YAML parses to the intended graph (Bun.YAML); the tag step against
GitHub for v1.1.1 — right commit ok, wrong commit / absent tag exit 1. **Measured on GitHub: run
42517168769 (2.0.0) green in both jobs.** The text below is the history of the single-job form.

- Trigger: **`workflow_dispatch`** with a `ref` input (the release tag). Changed 2026-06-19 from
  `push: tags: v*` so a `release` tag push no longer auto-publishes — publishing stays a single
  deliberate step (local `publish` script, or this workflow run by hand). Avoids double-publishing.
- **Auth: PyPI Trusted Publishing over short-lived OIDC — NO stored token** (changed 2026-06-19 from
  a `PYPI_API_TOKEN` repo secret, at the owner's request, "so that we are not hacked"). The job sets
  `permissions: id-token: write` (+ `contents: read`) and does the OIDC dance **by hand in `run:`
  steps** (no `pypa/gh-action-pypi-publish`, which the org policy would `startup_failure`):
  (1) `curl` the runner's `ACTIONS_ID_TOKEN_REQUEST_URL`/`_TOKEN` with `&audience=pypi` → OIDC JWT;
  (2) POST `{"token": <jwt>}` to `https://pypi.org/_/oidc/mint-token` → ephemeral project-scoped PyPI
  token (minutes-long); (3) `twine upload` with `TWINE_PASSWORD=<minted token>`. Both tokens are
  `::add-mask::`ed. Nothing is persisted in secrets.
- **`run:`-only constraint — SUPERSEDED 2026-11-08.** Under `jrmarcum` the Actions policy
  permitted only owner-owned actions; ANY third-party `uses:` caused `startup_failure`. The
  `synapticforge1` org accepts hash-pinned actions (run 42517168769), so `publish.yml` now uses
  exactly two, pinned by commit (upload- / download-artifact). Rule now: no other `uses:`, and
  never one pinned by tag.
- Steps: checkout via `git clone --depth=1 --branch <input ref> <token-auth url> .`; `pip install
  --upgrade build "twine>=6.1.0" "packaging>=24.2"`; `pip install -e ".[dev]"`; the gate — `ruff
  check src/ tests/`, `mypy src/`, `pytest tests/ -v`, each a hard step (the advisory `|| true` was
  removed 2026-10-26 with the harness fix); build with `python -m build`; `twine check`; then the
  OIDC mint + `twine upload` step above.
- **twine/packaging pin (added 2026-06-19):** hatchling ships the LICENSE via PEP 639 `License-File`
  (Metadata-Version 2.4); `twine < 6.1` / `packaging < 24.2` reject that field in `twine check`
  (`InvalidDistribution: unrecognized or malformed field 'license-file'`). The `--upgrade` + floors
  force a current twine over the runner's older preinstalled one. Same floors are in the pixi
  `publish` feature for the local path.

### Required owner setup (one-time)

1. **PyPI project owned/registered** — the name `universal-wasm-loader` must exist on PyPI under an
   account you control (first upload via `publish`, or pre-register the name).
2. **Auth, two independent paths:**
   - *Local `publish` script:* export `TWINE_USERNAME=__token__` / `TWINE_PASSWORD=pypi-…`
     (project-scoped API token; or a `[pypi]` entry in `~/.pypirc`).
   - *CI workflow (on a `v*` tag push since 2026-11-08; manual-only before):* register a **Trusted Publisher** on PyPI (no stored token) — a *pending
     publisher* before the project's first upload — matching Owner **`synapticforge1`** (was
     `jrmarcum` until the 2026-10-21 transfer; **the PyPI-side publisher must be re-registered
     with the new owner before the next CI publish**), Repository `universalWasmLoader-py`,
     Workflow `publish.yml`, Environment **`pypi`**.
     **Hardening applied (2026-06-19):** the job runs in a protected GitHub Environment `pypi`
     (`environment: pypi`) with **required reviewers** + a **`v*`-tag-only** deployment rule, and the
     PyPI publisher requires that same `pypi` environment claim — so every publish pauses for a human
     approval and can only run from a release tag. ⚠️ **No longer true for the reviewer half
     (measured 2026-11-09, 2.0.1):** no pause — see [open-work.md](open-work.md).

### Release history & validation (2026-06-19)

- **Published to PyPI via the OIDC CI workflow** (owner approved the `pypi` environment each run):
  - **`1.0.0`** — first release. Required two CI fixes discovered live: the `workflow_dispatch`
    `ref` input + **"Use workflow from: Tag v1.0.0"** (so the env's `v*`-tag rule passes), and the
    **twine ≥6.1 / packaging ≥24.2** pin (older twine rejected hatchling's PEP 639 `License-File`).
    The `v1.0.0` tag was **force-moved twice** while unpublished to carry those workflow fixes
    (safe: nothing was on PyPI yet). Final `v1.0.0` tag commit: `38b44a5`.
  - **`1.0.1`** — README trimmed to a **user-facing PyPI page** (removed Develop / Release-publish /
    Required-setup / Publishing-from-CI sections; they live here in cmem) + a clearer async usage
    example using the real fixture exports (`calculate`, `greet`/`strLen`). Bumped via
    `bump-version.sh patch`, tagged `v1.0.1` (commit `d6b2b17`), pushed, published. This is the
    latest version the PyPI project page renders.
- **Both versions are immutable on PyPI** — a published version can never be re-uploaded or edited;
  to change the rendered README you publish a new version (that's why the README cleanup became
  `1.0.1`).
- **Local-publish gotcha (recorded so it isn't repeated):** the local `publish.{sh,nu}` path needs a
  `TWINE_*` **env var** — a token was once pasted directly into `publish.nu` (into the help-text
  string, which does nothing) and scrubbed before any commit (it reached **no** commit). Lesson: the
  OIDC CI path is preferred (no token touches the machine); for local use set
  `$env:TWINE_PASSWORD`/`$env.TWINE_PASSWORD`, never edit the script. The pasted token was rotated.
- **Tooling on the dev host (as of 2026-06-19):** no Python/pixi/twine (only the Windows Store `python`
  stub); `nu` 0.113.1 + `git` available → **no GitHub Release pages** for `v1.0.0`/`v1.0.1`
  (tags pushed, which is all the publish needs; a Release page is an OWNER web-UI item, see
  [open-work.md](open-work.md)). All script verification on this host was via `--dry-run` (both
  `.sh` and `.nu`); the real builds/uploads ran on the GitHub runner.
- **Tooling on the dev host (re-checked 2026-10-21):** **pixi 0.82.1** (scoop, reinstalled by the
  owner) + `uv` (scoop); `nu` is absent, so the `.sh` scripts were the ones run here. The baseline
  under `pixi run python -m pytest` matches the uv run below (13/13). The publish workflow was
  dispatched from the GitHub Actions tab (Run workflow → `ref` = the tag; "Use workflow from: Tag v…").
- **Tooling on the dev host (re-checked 2026-11-09):** pixi **0.84.1**; Bun **1.4.4** on Windows
  and WSL (one-time checks only; the latest installed, workspace H31). No GitHub CLI, by the
  owner's rule (H30): GitHub is read with `git ls-remote` and the public REST API, Actions runs
  included. Since the tag push starts the publish, no dispatch is needed.

### Release `1.1.0` (2026-10-21) — first release from `synapticforge1`

- **Contents:** `a51c8da` **feat(spec10)** — SPEC §10 loader capabilities (`_initialize` + built-in
  WASI) — hence a **minor** bump `1.0.1` → `1.1.0` (owner-confirmed); plus the `synapticforge1`
  transfer edits (repo URLs in `pyproject.toml` / README / `.gitmodules` / `publish.yml` comments),
  the first committed `pixi.lock`, and memory.
- **Flow:** `bash scripts/bump-version.sh minor` (commit `fc847fa`) → `bash scripts/release.sh`
  (pixi build of sdist + wheel, annotated tag `v1.1.0`, pushed `main` + tag; no GitHub Release
  page — an owner web-UI item) → local `pixi run python -m twine check dist/*` PASSED → owner ran the `Publish`
  workflow from the Actions tab against `v1.1.0` and approved the `pypi` environment.
- **Verified on PyPI 2026-10-21** (JSON API): latest = `1.1.0`, wheel + sdist uploaded
  22:55 UTC; PyPI's project links now show `github.com/synapticforge1/universalWasmLoader-py`.
### Release `1.1.1` (2026-10-26) — tagged, pushed, and on PyPI (uploaded 2026-10-26 20:23 UTC; measured 2026-11-08)

- **Contents** (merge `b09da41`, the workspace-conformance branch): the stamped -js reference
  fixtures (H7) and the fixed `.wat` harness (L8, 34 passed); the real gate (`pixi run gate` = CI,
  no `|| true`); a nameless import now raises `RuntimeError` instead of reaching
  `define_func(…, None, …)`; the toolchain on pixi Python (H15); the compatibility gate (H6); README
  Versioning + Breaking Changes. A **patch**: the API surface is unchanged since v1.1.0.
- **Flow (owner: "lets bump and push", then "Bump + release"):** `pixi run bump patch` — the gate's
  first real use: floor patch, v1.1.0's tests 13 / 13 on both srcs, 0 regressions → commit
  `e92e2dd` → `pixi run release`: pixi build of sdist (21,175 B) + wheel (8,951 B), annotated tag
  `v1.1.1` → `e92e2dd`, `main` and the tag pushed (read back with `ls-remote`); no GitHub Release
  page (an owner web-UI item). Locally on the tag: `compat.py --release` passes,
  `twine check` PASSED for both files.
- **Published:** PyPI serves 1.1.1 (2 files, 2026-10-26 20:23 UTC; the workspace measured it first
  and noted this memory lagged). The run itself (id, step results) was not looked up from here.

### Release `2.0.2` (2026-11-09) — PUBLISHED, with a CI-made GitHub Release page

- **Owner:** "update the project memory files, commit, push then release". A **patch**: no
  library change; it ships the CI `release` job (`a3bc61e`, pushed in `9f0679f`, CI 42644465666
  green). Memory was current at `454b770`, so nothing was committed before the release.
- **Flow:** `pixi run bump patch` → `a89b91a` (floor patch). Tag `v2.0.2` made locally;
  `compat.py --release` exit 0 there (v2.0.1's 108 tests: 108 / 0 on its src and on the new src).
  `pixi run release` reused the tag, pushed, read back `main = v2.0.2^{} = a89b91a` (exit 0).
- **Publish run 42644832218** (event `push`): `checks`, `publish`, `release` green in every step.
  PyPI: `…-2.0.2-py3-none-any.whl` sha256 `8096e9e0…`, `…-2.0.2.tar.gz` sha256 `178076ea…`.
  GitHub Release `v2.0.2` by `github-actions[bot]` (see § CI + publish). Still no reviewer pause:
  `publish` was created the second `checks` completed and started 3 s later.

### Release `2.0.1` (2026-11-09) — tagged, pushed, PUBLISHED by the tag push

- **Owner:** "update the project memory files, commit, push then release". A **patch**: no library
  change since 2.0.0 — the H30 `release.py` (`ecd736a`), the per-file upload + CI work of
  2026-11-08 (`eff40fa`, `4548c34`), the bump-hint wording (`05131e6`, `4403cc1`).
- **Flow:** `main` `12ccd26` pushed first (CI green, `gh` re-grep 0 on `origin/main`); `pixi run
  bump patch` → `0bd7f14` (floor patch); hint fix `05131e6` + `4403cc1` (the first was committed
  before its gate result was read — an E501, fixed in the second). Tag `v2.0.1` made locally at
  `4403cc1`, `compat.py --release` exit 0 there (floor patch; **v2.0.0's 92 tests: 92 / 0 on its
  src and on the new src** — Rule 3's first run over the full suite). `pixi run release` reused
  the tag, pushed, and its new read-back printed `main = v2.0.1^{} = 4403cc1` (exit 0) plus the
  Release-page OWNER link. `pixi install --locked` stays valid across a bump (the lock does not
  record the package's own version; checked).
- **Publish run 42642679890** (event `push`, the first tag-triggered run and the first pixi-locked
  `checks`): every step of both jobs green; `publish` started 4 s after `checks` — **no reviewer
  pause** (owner item). PyPI: `universal_wasm_loader-2.0.1-py3-none-any.whl` sha256 `87648e85…`,
  `universal_wasm_loader-2.0.1.tar.gz` sha256 `4b12cb29…`. CI on the same commit green.

### Release `2.0.0` (2026-11-08) — tagged, pushed, PUBLISHED

- **Owner:** "yes C30 applies here. yes 1.1.1 is the only one on pypi. yes change the instance
  pool. yes release 2.0.0". **Contents:** SPEC 4.0.0 (`568f7f3` + `bb7feb6`), `InstancePool`
  size 4 (`93cc2f3`), the two-job publish workflow (`ae51e95`), the compat Rule 4 fix (`238afa0`).
  92 tests. Floor major: SPEC 3.0.0 → 4.0.0 and `InstancePool.__init__` changed.
- **Flow:** `pixi run bump major` → `13f125a` (README row stamped `| v2.0.0 |`) → `pixi run
  release`: build (hatchling 1.33.0), annotated tag `v2.0.0` → `13f125a`, `main` + tag pushed
  (`389a460..13f125a`, read back with `ls-remote`); no GitHub Release page (an owner web-UI
  item). Then
  `compat.py --release` on the tag REFUSED (the Rule 4 bug, [compat-gate.md](compat-gate.md)), so
  CI would have stopped the publish. Fixed in `238afa0`; **on the owner's word ("Move tag to the
  fix") `v2.0.0` was MOVED from `13f125a` to the commit carrying this record**, force-pushed with
  a lease. Nothing had consumed the old tag: PyPI latest 1.1.1, no GitHub Release, no run.
- **Published by the owner's run 42517168769** (workflow_dispatch from tag `v2.0.0`, `21e680a`;
  the FIRST run of the two-job workflow): `checks` and `publish` green in every step (read through
  the public Actions API). PyPI: `universal_wasm_loader-2.0.0-py3-none-any.whl` sha256
  `75f53723…5fa1`, `universal_wasm_loader-2.0.0.tar.gz` sha256 `81a03f99…cdd6`. A local build of
  the same commit gave other hashes (`e3717971…`, `ab6a1746…`): **the build is not
  byte-reproducible across machines**, which shaped `scripts/pypi_files.py` (skip by name, report
  the hash).

- **Test baseline 2026-10-21** (`uv run --extra dev python -m pytest tests`, wasmtime from PyPI):
  **13 passed / 13 failed.** All 13 failures are the known `.wat`-fixture harness caveat ("input was
  not valid utf-8"); every string-ABI, SPEC §10 and WIT-parser test passes.
