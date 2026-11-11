# cmem — Portable Project Memory for universalWasmLoader-py

This folder is the **authoritative, portable project memory** for `universalWasmLoader-py`. It lives
inside the project tree, so it travels with the repo and is committed to git. Keep files small and
single-topic.

## Policy

- **`cmem/` is the single home for ALL project memory.** When the owner says "**update the project
  memory**," update the matching `cmem/` topic file with the latest decisions, found bugs, design
  changes, and current state — then add/refresh its one-line pointer in the table below. Convert
  relative dates to absolute; update existing entries rather than duplicating.
- **`README` and `SPEC.md` are NOT project memory.** They are the public, user-facing docs. Keep
  internal decision logs / bug post-mortems out of them — those live here in `cmem/`.

### The "update the project memory" trigger (binding on every agent)
When the owner says **"update the project memory"** (or a synonym — "update memory", "record this"),
do BOTH: (1) revise all relevant `cmem/` files and refresh the Files-table pointers (absolute dates;
update, don't duplicate); and (2) sync the user-facing README / SPEC.md only where the change is
user-relevant — never copy internal decision logs into them.

### The "look for code issues" trigger (binding on every agent)
When the owner says **"look for code issues"** (or "code audit" / "audit the code"), perform a
comprehensive audit across tested AND untested paths for: (1) workarounds / temporary hacks;
(2) dead code; (3) bugs (wrong ABI marshalling, off-by-one pointer/length math, endianness, missing
`cabi_post` calls); and (4) silent fall-throughs (returning a default instead of erroring). Report
`file:line` + severity, fix the safe ones, and keep the test suite green (`pixi run test`).

## Files

| File | What it holds |
| --- | --- |
| [overview.md](overview.md) | What this loader port is (Python/wasmtime), its home (**GitHub org `synapticforge1`**), API surface, ABI; **SPEC 4.0.0 implemented 2026-11-08 (C29: `568f7f3` + `bb7feb6`); SPEC 4.0.1 claimed 2026-11-10 (`fdca3d9`, no behaviour change)**; tests (the stamped -js fixture set, H7; **144 passed 2026-11-10**), the gate (`pixi run gate` = CI), layout; latest **2.0.6** on PyPI with PEP 740, SPEC 4.0.1 (2.0.4 never published; 1.0.0 / 1.0.1 / 1.1.0 removed, owner) |
| [release.md](release.md) | 🔒 **How a release runs** (H33, the owner's order: `bump <level>` → `release` pushes `main` only → CI checks → CI tags → the page → the PyPI publish dispatched on the tag, PEP 740 attestations, a fatal read-back; `9c6d3bd`, 2026-11-10; MEASURED by 2.0.5; 2.0.6 green on its first attempt) and the **Release History, newest first** (2.0.6 → 1.0.0, a summary each; moved from overview.md 2026-11-10), plus how the workflow got here |
| [compat-gate.md](compat-gate.md) | The compatibility gate (H6): `api-surface.json`, the floor, per-test previous-tag tests, the Breaking Changes row, CI's `compat.py --release`; how a pre-gate tag's baseline is derived; the 4.0.0 run (floor major); the Rule 4 `--release` bug fixed `238afa0`; the lesson that Rule 3 is all-or-nothing on a collection error |
| [open-work.md](open-work.md) | **No open items (2026-11-11).** PyPI's Trusted Publisher environment: fixed by the owner, verified on 2.0.6. Closed: 2.0.4's failed publish, the read-back's environment check, no `pypi` reviewer (owner "no"), old tags' pages, C30 split, pool size 4, per-file upload, pixi-locked CI |
| [working-rules.md](working-rules.md) | The checklist: git/release (**the version line ARMS a release: a push of `main` with an untagged version IS one** — H33, 2026-11-10; the owner's words "commit" / "push" / "release", H34; read runs back via the public API), tooling (pixi Python; H15 ported; **no GitHub CLI, H30**; **Bun notations = latest installed, H31**; **CI-made Release pages in H32's order, total time limit per request**), **privacy** (path test "machine-specific?", the one email exception, `-a` scans; H18/H22/H28), memory (read the workspace ledger at session start) |
| [best-practices.md](best-practices.md) | The workspace's 28 ★ convergent rules, a verbatim COPY stamped `Copied from synapticforge1/cmem/best-practices.md on 2026-10-26` (H6/H24/H27/C8); text-checked 28 = 28, 0 differences, inverted |
