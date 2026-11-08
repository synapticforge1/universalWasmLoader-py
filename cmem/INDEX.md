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
| [overview.md](overview.md) | What this loader port is (Python/wasmtime), its home (**GitHub org `synapticforge1`**), API surface, ABI; **SPEC 4.0.0 implemented 2026-11-08 (C29: `568f7f3` + `bb7feb6`); 2.0.0 tagged + pushed 2026-11-08 (tag moved once onto the compat fix, owner), not yet on PyPI**; tests (the stamped -js fixture set, H7; **92 passed 2026-11-08**), the gate (`pixi run gate` = CI), the release toolchain (`scripts/*.py` on pixi Python, H15), the token-free OIDC publish workflow, and the PyPI release history (**PyPI serves only `1.1.1`, measured 2026-11-08**; 1.0.0 / 1.0.1 / 1.1.0 answer 404) |
| [compat-gate.md](compat-gate.md) | The compatibility gate (H6): `api-surface.json`, the floor, per-test previous-tag tests, the Breaking Changes row, CI's `compat.py --release`; how a pre-gate tag's baseline is derived; the 4.0.0 run (floor major); the Rule 4 `--release` bug fixed `238afa0`; the lesson that Rule 3 is all-or-nothing on a collection error |
| [open-work.md](open-work.md) | Open (2026-11-08): C34's PyPI analogue (a half-finished upload), the `checks` job's unpinned tools. Closed the same day on the owner's word: C30 split (`ae51e95`), PyPI 1.1.1-only (intended), `InstancePool` size 4 (`93cc2f3`) |
| [working-rules.md](working-rules.md) | The checklist: git/release, tooling (pixi Python; H15 port open), **privacy** (path test "machine-specific?", the one email exception, `-a` scans; H18/H22/H28), memory (read the workspace ledger at session start) |
| [best-practices.md](best-practices.md) | The workspace's 28 ★ convergent rules, a verbatim COPY stamped `Copied from synapticforge1/cmem/best-practices.md on 2026-10-26` (H6/H24/H27/C8); text-checked 28 = 28, 0 differences, inverted |
