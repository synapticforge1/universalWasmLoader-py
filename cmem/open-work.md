# Open work — items waiting on the owner (or on a later session)

Each item: what was found, how (measured / read / reasoned), and what is proposed. Nothing here
is changed without the owner. Close an item by moving its outcome into the topic file it belongs
to and deleting it here.

## OWNER (PyPI web UI, optional): the Trusted Publisher has no environment

**Measured 2026-11-10** (PyPI's integrity API for 2.0.5): the publisher PyPI recorded is
`{kind: GitHub, repository: synapticforge1/universalWasmLoader-py, workflow: publish.yml,
environment: null}`. So the Trusted Publisher on PyPI is registered WITHOUT the `pypi`
environment, although this memory (from 2026-06-19 / 2026-10-21) said "Environment: pypi". PyPI
therefore accepts a token minted by `publish.yml` from ANY job of that workflow, not only from the
`publish` job in the `pypi` environment. The GitHub side still holds: only `publish` has
`id-token: write`, and the environment admits only `v*` refs. **If wanted:** pypi.org →
universal-wasm-loader → Publishing → edit the GitHub publisher → Environment `pypi`. After that,
PyPI would report `environment: pypi`, and the read-back accepts either answer.

Closed (outcomes in [overview.md](overview.md), [release.md](release.md) and
[working-rules.md](working-rules.md)): 2026-11-10 — 2.0.4's failed publish (fixed `a8c950d`,
shipped as 2.0.5; its page stays, owner); the read-back's environment check (`63e4e7a`).
2026-11-09 — no `pypi` reviewer (owner: "no"); Release pages for the old tags (owner, H32).
2026-11-08 — the C30 split, PyPI 1.1.1-only, `InstancePool` size 4, per-file upload, pixi-locked CI.
