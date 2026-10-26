# The compatibility gate (workspace letter H6, built 2026-10-26)

🔒 Binding (owner, 2026-09-20; workspace `../../cmem/layout-and-packaging.md` § "The compatibility
gate"): "backward compatible" is a gate result, never a judgment made at bump time. Design follows
loader-dart's `cmem/compat-gate.md` (itself from -js), in pixi Python.

## What runs where

| Rule | File | Runs in |
| --- | --- | --- |
| 1, the SURFACE | `scripts/compat.py` → `api-surface.json` (committed) | `compat.py --write` writes it; staleness is checked by every gate run |
| 2, the FLOOR | `compat.py` `floor_of` | `bump_version.py` (refuses below it), `compat.py` (report), `compat.py --release` on the tag (CI, blocking) |
| 3, BEHAVIOUR | `compat.py` `previous_tag_tests` | same places; required green for a patch or minor |
| 4, deprecate first | README `### ⚠️ Breaking Changes` | a major needs a `\| _next release_ \|` row; `bump_version.py` stamps the version into it |
| 5, re-baseline alone | the stale-snapshot refusal | an intended surface change is its own commit (`--write`), with the reason |
| 6, pre-1.0 | — | n/a: the package is ≥ 1.0.0 |

**The surface:** the `SPEC.md` version README declares once (`` `SPEC.md` **vX.Y.Z** ``), plus every
name in `universal_wasm_loader.__all__`: functions and classes, and each class's public methods
(+ `__init__`) and properties, valued by `inspect.signature` (annotations stay strings, from
`from __future__ import annotations`). A public name of any other kind THROWS. It is computed in a
child interpreter that must import the package from the given `src/` (asserted). 7 keys on
2026-10-26. The other half of a loader's surface, the reference fixture suite unmodified, is
`tests/test_fixtures.py` (H7).

**The floor:** removed or changed → major; added → minor; nothing → patch; the SPEC version moves it
by its own level (lowered → major). ⚠️ It errs high on purpose: a changed default value or a renamed
parameter counts as "changed", because the signature string includes them.

**The baseline** is the previous tag's committed `api-surface.json`. A tag older than the gate
(v1.0.0 – v1.1.0) has none, so its surface is computed from its own `src/` in a `git worktree`, and
its SPEC version — which its README never declared — is DERIVED: the submodule commit the tag
pinned (`git ls-tree <tag> upstream/universalwasmloader-js`) → that commit's `SPEC.md` `Version:`
line. Never typed by hand. Needs the submodule initialised (CI runs `git submodule update --init`).

**Previous-tag tests, per test, not by exit code:** a `git worktree` of the tag in the system temp
dir; its `tests/` (files AND fixtures) untouched; run once on the tag's own `src/` and once with
`src/` replaced by the current one; `pytest --junitxml`, `PYTHONPATH=<worktree>/src` (a probe
proves the import resolves there and not to this checkout's editable install). A test that passed
on the tag and does not pass now is a REGRESSION and refuses the bump; tests already failing on the
tag itself are reported, not blocking. Why per test: v1.1.0's own suite is 13 / 26 on its own code
(the L8 `.wat` harness bug), so "the previous tag's tests must pass" read as an exit code would
refuse every bump forever. Green also needs at least one pass on the new src. The worktree is
always removed.

**CI:** `publish.yml` clones with full history (it was `--depth=1`) and the submodule, runs the
lint → typecheck → test gate, then `compat.py --release`: HEAD must be tag `v<manifest version>`;
the step from the previous tag (by semver) is checked like a bump of that level.

**First run, 2026-10-26** (against v1.1.0): floor patch (the API surface is unchanged since v1.1.0);
v1.1.0's tests 13 passed / 13 not on v1.1.0's src and the same on the new src — 0 regressions.

**Consumers (Rule 3, second half):** no known PyPI package depends on this one; nothing to run.
