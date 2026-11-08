# Open work — items waiting on the owner (or on a later session)

Each item: what was found, how (measured / read / reasoned), and what is proposed. Nothing here
was changed without the owner. Close an item by moving its outcome into the topic file it belongs
to and deleting it here.

## 1. Release workflow: the publishing credential shares a job with third-party code (C30 (1))

**Read 2026-11-08 (record-only, reasoned, not measured)**, from workspace ledger C30
(S3D-ReportCompiler's review). **C30 (1) APPLIES here as written:** `.github/workflows/publish.yml`
is ONE job with `permissions: id-token: write`, and the same job runs `pip install -e ".[dev]"`
(build backends, wasmtime, pytest, ruff, mypy from PyPI, **unpinned**), the gate (which executes
that code), `compat.py --release` (the previous tag's tests), and `python -m build`. Every step of
the job can ask the runner for the OIDC token that `mint-token` exchanges for a PyPI upload token.
Also: the clone URL embeds `${{ github.token }}` (`https://x-access-token:…@github.com/…`), so the
token sits in `.git/config` for every later step. **C30 (2)** does not apply (no `concurrency:`);
**(3)** does not apply (no `bun fmt`).

**Proposed (the loader-dart `cb7bc26` / loader-go `2ff71ef` / loader-jvm `ec7398c` shape):** a
`checks` job (`contents: read`, no `id-token`, tokenless clone) runs install + gate + compat +
build and uploads `dist/` as an artifact; a `publish` job (`id-token: write` only, `environment:
pypi`) re-checks that the tag is still `github.sha` with `git ls-remote`, downloads `dist/`, and
runs only `twine check` + the OIDC mint + `twine upload`, with nothing installed from PyPI but
twine. The `run:`-only constraint stays (artifact transfer without `uses:` needs another channel,
e.g. a draft GitHub Release asset via `gh`, or rebuilding in the publish job from the verified
sdist hash) — a design choice for the owner.

## 2. A failed upload can strand a version (C34 (1), PyPI analogue)

**Read 2026-11-08 (record-only, reasoned).** C34 is about JSR / npm; this repo publishes to PyPI,
so (2)–(4) are n/a. The analogue of (1): `twine upload dist/*` sends the sdist and the wheel one
file at a time; a failure after the first leaves a half-published version, and PyPI never accepts
a removed file name again. The upload is the workflow's last step, so no later job is skipped, but
a re-run must upload only the missing file (`twine upload --skip-existing` would do it; today a
re-run fails on the file already there). Proposed: nothing until the owner decides item 1, which
reshapes the job.

## 3. PyPI serves only 1.1.1 (measured 2026-11-08)

`/pypi/universal-wasm-loader/json` lists one release, `1.1.1`; the per-version JSON answers
**404 for 1.0.0, 1.0.1 and 1.1.0**. This memory recorded them as published and immutable; no note
here or in the workspace records their removal. Owner: confirm it was intended (PyPI keeps those
version numbers reserved forever either way).

## 4. `InstancePool` default `size=2`; SPEC §6.2 says 4 (read 2026-11-08)

Pre-existing since 1.0.0 and not changed by the 4.0.0 work. Changing it changes the surface
(`InstancePool.__init__`'s default), which the gate counts as major, so 2.0.0 would be the cheap
moment. Owner's call.

## 5. CI installs its tools unpinned (recorded 2026-10-26, still open)

`publish.yml` installs ruff / mypy / pytest / build / twine from pip without pins, while local runs
use `pixi.lock`; a newer ruff could fail on the runner what passes here. Folds into item 1.
