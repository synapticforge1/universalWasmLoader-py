# Open work — items waiting on the owner (or on a later session)

Each item: what was found, how (measured / read / reasoned), and what is proposed. Nothing here
is changed without the owner. Close an item by moving its outcome into the topic file it belongs
to and deleting it here.

## To verify at the next release: PyPI's Trusted Publisher environment

**Measured 2026-11-10** (PyPI's integrity API for 2.0.5): PyPI recorded the publisher as
`{kind: GitHub, repository: synapticforge1/universalWasmLoader-py, workflow: publish.yml,
environment: null}`, i.e. a PyPI-side Trusted Publisher entry without the environment (the GitHub
environment `pypi` already existed and the job ran in it). **Owner, 2026-11-10: "fixed"** on
PyPI's Publishing page. 2.0.5's provenance stays as recorded. **Check at the next release:** its
files' provenance should report `environment: "pypi"`
(`GET https://pypi.org/integrity/universal-wasm-loader/<v>/<file>/provenance`); then close this
item. The read-back accepts either answer, so nothing blocks on it.

Closed (outcomes in [overview.md](overview.md), [release.md](release.md) and
[working-rules.md](working-rules.md)): 2026-11-10 — 2.0.4's failed publish (fixed `a8c950d`,
shipped as 2.0.5; its page stays, owner); the read-back's environment check (`63e4e7a`).
2026-11-09 — no `pypi` reviewer (owner: "no"); Release pages for the old tags (owner, H32).
2026-11-08 — the C30 split, PyPI 1.1.1-only, `InstancePool` size 4, per-file upload, pixi-locked CI.
