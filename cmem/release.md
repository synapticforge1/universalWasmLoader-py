# release.md — how a release runs, and the Release History (newest first)

🔒 One place for every release record (owner, 2026-11-10; workspace letter H33 D3 / U11). The
records below were MOVED here from `overview.md` (a pointer is left there). Each entry: what
changed, how it went out, the run id, and what was read back.

## How a release runs (workspace H33, the owner's order; since `9c6d3bd`, 2026-11-10)

🔒 **"the CI to check first, then push the tag, and then create the release page from the tag, then
publish the package to the registry"** (owner, 2026-11-10, D1). The owner's words (H34,
[working-rules.md](working-rules.md) § Owner commands): "release" = "push" (memory → commit →
merge into `main` → push) → then this. **The level (patch / minor / major) is the owner's; ask
if it was not given.** Nothing tags or uploads from the owner's machine.

1. **`pixi run bump <major|minor|patch>`** (`scripts/bump_version.py`; U1–U3) — the level is
   required; refuses a dirty tree (untracked count), a stale `api-surface.json`, a level below the
   floor, red previous-tag tests (patch / minor), a major without its Breaking row; commits
   **`bump to vX.Y.Z`** (version files only; a major also stamps README's row).
2. **`pixi run release`** (`scripts/release.py`; U4) — guards: clean tree; on `main`; HEAD =
   GitHub's `main` + exactly the bump commit; the tag absent here and on GitHub; PyPI's PROJECT
   list without the version; a cold gate (gate, `compat --release`, build, `twine check`). Then it
   pushes **`main` only** and reads it back (main = HEAD, still no tag). `--dry-run` runs all of it
   and pushes nothing.
3. **CI, `.github/workflows/publish.yml`, the run started by that push** — `checks` (U5: token-less
   clone; "is this a release?" = the version untagged → new / tagged HERE → re-run / else none;
   the gate; `compat --release` on the candidate; the publish dry run) → `tag` (U6: CI's annotated
   `vX.Y.Z` on `github.sha` via REST, there = done, elsewhere = refused, read back) → `release`
   (U7: the page from the tag, H32's order, PyPI link on top) → `dispatch` (starts `publish.yml`
   ON THE TAG, then waits — fatal, 25 min — until PyPI lists the version).
4. **CI, the dispatched run (ref = the tag)** — `build` (the locked hatchling) → `publish` (U8:
   environment `pypi`, `id-token` only; the order holds — tag here AND its page; plan the missing
   files; sign PEP 740 attestations; `twine upload --attestations`; then the FATAL read-back:
   every file served, each with a provenance from this repo's `publish.yml` in `pypi`).
   Why two runs: the `pypi` environment admits only `v*` refs (deployment policy, read through the
   public API 2026-11-10), and a `GITHUB_TOKEN`-made tag starts no run.
5. **After (U10, by hand):** in a scratch venv, `pip install universal-wasm-loader==X.Y.Z` and run
   a fixture (e.g. `add(3, 4)` = 7); check the page (`releases/latest`) and
   `pypi.org/integrity/universal-wasm-loader/X.Y.Z/<file>/provenance`. Record it below (U11).
6. **Failure (U12):** "Re-run failed jobs" on the failed run — each job skips what is done (tag
   there = done; page there = done; PyPI files there = skipped). Never a new tag for the same
   code, never a moved tag.

**MEASURED on GitHub by 2.0.5 (2026-11-10):** the whole order, CI's tag, the dispatch on the tag,
the Sigstore signature, the upload with attestations, PyPI's provenance. Two lessons from 2.0.4 /
2.0.5, both fixed: twine must be GIVEN each attestation with its dist; PyPI reports this project's
publisher without an environment. **Before that (the rehearsal):** 141 tests incl. mock-API
cases for `tag` / `check` / `dispatch` / the read-back / signing; 7 one-line mutants each caught;
read-only runs against the real GitHub (`tag`, `check`, `dispatch --dry-run`) and PyPI (the
read-back FAILS on 2.0.3 — no provenance — and passes on `pypi-attestations` 0.0.31 with its
real publisher); "is this a release?" on the real tags; a 12-case rehearsal of bump + release
against a scratch bare origin (every guard refused with nothing pushed; the real run pushed
`main` with NO tag). **UNMEASURED on GitHub until the next release:** CI's tag, the dispatch on
the tag, the attestation signature, the provenance read-back.

## Release History (newest first)

### 2.0.5 — 2026-11-10 · patch · the first PUBLISHED release in the owner's order, with PEP 740

**What changed:** no library change. It ships the H33 release order (CI checks → CI's tag → the
page → the PyPI publish on the tag), PEP 740 attestations, and the fix for 2.0.4's failure
(`a8c950d`: twine is given each attestation with its dist).
**Out (owner: "release", level patch; then "Release 2.0.5 now"):** `bump to v2.0.5` `3d86f5c`;
`release.py` pushed `main` only (no tag; read back). The push run **42926145910**, all green:
`checks` → `tag`, CI's annotated `v2.0.5` (object `a9b7b95`, peels to `3d86f5c`) → `release`, the
page by `github-actions[bot]` (23:47:57Z) → `dispatch`, which saw PyPI list 2.0.5. The dispatched
run **42926306108**: `build` ✓, then `publish`: the order check, the plan, the signing and **the
upload ✓** (`…-2.0.5-py3-none-any.whl` sha256 `4b70f712…` 23:49:41Z; `…-2.0.5.tar.gz`
`8c41d103…` 23:49:42Z). Then the fatal read-back FAILED: PyPI reports the publisher's
`environment` as `null` (the Trusted Publisher is registered without one), and the check
required `"pypi"`. Fixed in `63e4e7a` (identity = repository + workflow must match; an environment
only when PyPI reports one). That run stays red, because a re-run uses the tag's own check.
**Read back (2026-11-10):** PyPI serves both files. Each has a PEP 740 provenance (integrity API
200, `{kind: GitHub, repository: synapticforge1/universalWasmLoader-py, workflow: publish.yml}`,
also linked from the simple index). The fixed read-back, run locally against the real PyPI, exits
0, and exits 1 for a wrong repository. Page `v2.0.5` by `github-actions[bot]`, made before the
upload (`releases.atom`; the public API's hourly limit was spent). **U10, as a user:** a fresh
venv, `pip install universal-wasm-loader==2.0.5` from PyPI (site-packages): `add(3, 4)` = 7,
`greet('World')` = "Hello, World!", `add(2.7, 1)` refused, `imports_50` without callbacks
refused, naming both.

### 2.0.4 — 2026-11-10 · patch · TAGGED, page made, NEVER PUBLISHED (superseded by 2.0.5)

**What it was:** the first release in the owner's order (H33): the release tooling and CI only (no
library change). **What happened:** `bump to v2.0.4` (`179c405`); `release.py` pushed `main` only,
with no tag. The push run **42922433222**: `checks` ✓ → `tag` ✓ (CI's annotated `v2.0.4`, object
`6a6fb45`, peels to `179c405`) → `release` ✓ (page by `github-actions[bot]`, 23:20:31Z) →
`dispatch` (started the publish on the tag, then timed out waiting for PyPI, as designed). The
dispatched run **42922568285**: `build` ✓ → `publish` FAILED at "Publish to PyPI". The order
check, the plan, the install and the Sigstore signing all passed; PyPI got nothing.
**Cause (mine, measured with the real twine 7.0.0):** `twine upload --attestations` does not look
for attestations beside the dists. It sorts the files it is GIVEN, and the step passed the dists
only: "Upload with attestations requested, but … has no associated attestations". Fixed in
`a8c950d`: `pypi_attest.py` prints twine's argument list (each dist, then its attestation), and a
regression test runs the real twine. **Why not a re-run:** the dispatched run uses the TAG's
workflow and scripts, which hold the bug, and a published tag never moves. So the fix ships as
2.0.5. **Owner, 2026-11-10:** "Release 2.0.5 now"; leave the `v2.0.4` page and record why. The
tag `v2.0.4` and its page stay; PyPI never has 2.0.4, and its page's PyPI link answers 404.

### 2.0.3 — 2026-11-09 · patch · time limits in the CI scripts

**What changed:** no library change. `52c754d`: every request in `scripts/github_release.py` and
`scripts/pypi_files.py` has ONE total time limit, request to last byte (workspace H32 / 7.21),
with the socket timeout as a looser backstop (equal values raced).
**Out:** `bump patch` → `4fd83c6`; local tag `v2.0.3`; `compat --release` (v2.0.2's 117 tests
green on the new src); `release.py` read back `main = v2.0.3^{} = 4fd83c6`. Publish run
**42682719743** (tag push): `checks` / `publish` / `release` green. **Read back:** PyPI
`…-2.0.3-py3-none-any.whl` sha256 `a0631a93…`, `…-2.0.3.tar.gz` sha256 `be919f54…`; Release
`v2.0.3` by `github-actions[bot]`, `releases/latest`; tag unmoved. No reviewer pause.

### 2.0.2 — 2026-11-09 · patch · the GitHub Release page from CI

**What changed:** no library change. `a3bc61e`: `publish.yml`'s third job `release` makes the
GitHub Release page by REST (`scripts/github_release.py`; owner: "can we add the github release
page when we release it via the github actions?"), in the order later made workspace letter H32.
**Out:** `bump patch` → `a89b91a`; `compat --release` (v2.0.1's 108 tests green). Publish run
**42644832218**. **Read back:** PyPI `…whl` `8096e9e0…`, `…tar.gz` `178076ea…`; Release `v2.0.2`
by `github-actions[bot]` — the first CI-made page; tag unmoved.

### 2.0.1 — 2026-11-09 · patch · no GitHub CLI; CI + publish on tag

**What changed:** no library change. `ecd736a`: `release.py` reads the push back with
`ls-remote` and no longer calls the GitHub CLI (workspace H30). `eff40fa`: per-file upload (only
the files PyPI lacks). `4548c34`: `ci.yml` on every push / PR; `publish.yml` on a tag push;
pixi-locked tools. `05131e6` + `4403cc1`: bump-hint wording.
**Out:** `bump patch` → `0bd7f14`; `compat --release` (v2.0.0's 92 tests green). Publish run
**42642679890** — the first tag-triggered run. **Read back:** PyPI `…whl` `87648e85…`, `…tar.gz`
`4b12cb29…`. Measured here first: the `pypi` environment does NOT pause for a reviewer (owner,
2026-11-09: keep it so).

### 2.0.0 — 2026-11-08 · MAJOR · SPEC 4.0.0

**What changed:** SPEC 4.0.0 — loud failures (`568f7f3` + `bb7feb6`; details in
[overview.md](overview.md) § SPEC 4.0.0): only an absent `.wit` is raw; a strict WIT parser;
every WIT import needs a callback; typed calls and callback results checked, never coerced.
`InstancePool` default size 4 (`93cc2f3`). The two-job publish workflow (`ae51e95`, C30). The
compat Rule 4 fix (`238afa0`).
**Out:** `bump major` → `13f125a`; `compat --release` on that tag REFUSED (the Rule 4 bug) → fixed;
on the owner's word `v2.0.0` was MOVED to `21e680a` before anything consumed it. Published by the
owner's dispatched run **42517168769**. **Read back:** PyPI `…whl` `75f53723…`, `…tar.gz`
`81a03f99…`; a local build of the same commit differs — the build is not byte-reproducible.

### 1.1.1 — 2026-10-26 · patch · the workspace floor

**What changed:** the stamped -js reference fixtures (H7) and the fixed `.wat` harness (L8); the
real gate (`pixi run gate` = CI, no `|| true`); a nameless import raises; the toolchain on pixi
Python (H15); the compatibility gate (H6); README Versioning + Breaking Changes.
**Out:** `bump patch` → `e92e2dd` (the gate's first real use: floor patch, 0 regressions);
`release` tagged + pushed; the owner's dispatched publish. **Read back:** PyPI serves 1.1.1 (2
files, 2026-10-26 20:23 UTC).

### 1.1.0 — 2026-10-21 · minor · SPEC §10; first release from `synapticforge1`

**What changed:** `a51c8da` — SPEC §10 loader capabilities (`_initialize` + built-in WASI); the
org-transfer edits; the first committed `pixi.lock`.
**Out:** `bump-version.sh minor` → `fc847fa`; `release.sh`; the owner dispatched `Publish`.
**Read back:** PyPI latest 1.1.0 (22:55 UTC). Since removed from PyPI (owner, 2026-11-09).

### 1.0.1 — 2026-06-19 · patch · a user-facing README

**What changed:** README trimmed to a user-facing PyPI page + a clearer usage example.
**Out:** tag `v1.0.1` (`d6b2b17`), published by the OIDC workflow. Since removed from PyPI.

### 1.0.0 — 2026-06-19 · the first release

**What changed:** the Python port, published. Two CI fixes found live: the `workflow_dispatch`
`ref` input ("Use workflow from: Tag v1.0.0", for the environment's `v*` rule) and the twine ≥ 6.1
/ packaging ≥ 24.2 pin (older twine rejected hatchling's PEP 639 `License-File`). The `v1.0.0` tag
was force-moved twice while unpublished (`38b44a5`). Since removed from PyPI.

## How the release workflow got here (decisions and lessons, oldest first)

- **2026-06-19:** PyPI Trusted Publishing over OIDC, done by hand in `run:` steps (mint at
  `https://pypi.org/_/oidc/mint-token`, `twine upload`) — no stored token (owner: "so that we are
  not hacked"); the protected `pypi` environment; publishing made a manual `workflow_dispatch`.
  A token was once pasted into a script's help text and scrubbed before any commit, then rotated:
  never edit a script to hold a credential.
- **2026-10-26 (H15):** the `.sh` / `.nu` scripts ported to pixi Python after a 24-case
  equivalence run; `publish` proceeded only on an HTTP 404 (the masked-HTTP-error class).
- **2026-11-08:** C30 — the credential job split from the package-code job; hash-pinned artifact
  actions (the org accepts them; the old "never `uses:`" rule was the previous owner's policy);
  per-file upload (`pypi_files.py`); `ci.yml`; publish on a tag push; pixi-locked CI tools.
- **2026-11-09:** H30 — no GitHub CLI anywhere; H32 — the Release page from CI in a fixed order;
  7.21 — a total time limit per request (in Python NOT `urlopen(timeout=)`); the `pypi`
  environment's missing reviewer found and KEPT (owner: "no").
- **2026-11-10:** H33 — the owner's order (above): the local publish path deleted
  (`scripts/publish.py`, `pixi run publish`), CI tags, the publish dispatched on the tag, PEP 740
  attestations signed and read back. H34 — the owner's three words.
