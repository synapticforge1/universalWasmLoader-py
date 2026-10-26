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
| [overview.md](overview.md) | What this loader port is (Python/wasmtime), its home (**GitHub org `synapticforge1`**, transferred from `jrmarcum` 2026-10-21; in-repo URLs updated + PyPI Trusted Publisher re-registered and proven), the 2026-10-21 test baseline + dev-host tooling,, API surface, ABI/SPEC 3.0.0 conformance, tests, the release toolchain (`bump-version`/`release`/`publish` in paired `.sh`+`.nu`), the token-free OIDC publish workflow, and the **PyPI release history — `1.0.0` + `1.0.1` published 2026-06-19; `1.1.0` (SPEC §10) published 2026-10-21** (latest `1.1.0`) |
| [working-rules.md](working-rules.md) | The checklist: git/release, tooling (pixi Python; H15 port open), **privacy** (path test "machine-specific?", the one email exception, `-a` scans; H18/H22/H28), memory (read the workspace ledger at session start) |
| [best-practices.md](best-practices.md) | The workspace's 28 ★ convergent rules, a verbatim COPY stamped `Copied from synapticforge1/cmem/best-practices.md on 2026-10-26` (H6/H24/H27/C8); text-checked 28 = 28, 0 differences, inverted |
