# Open work — items waiting on the owner (or on a later session)

Each item: what was found, how (measured / read / reasoned), and what is proposed. Nothing here
is changed without the owner. Close an item by moving its outcome into the topic file it belongs
to and deleting it here.

## OWNER (web UI, optional): GitHub Release pages

**Measured 2026-11-09** (public REST API `GET /repos/…/releases`): **0 Release pages**, for the five
tags `v1.0.0`, `v1.0.1`, `v1.1.0`, `v1.1.1`, `v2.0.0`. Nothing depends on them: the tag is the
release, and PyPI is fed by `publish.yml`. Since 2026-11-09 `scripts/release.py` prints a
pre-filled page link for each new tag (workspace H30: no GitHub CLI). If wanted, the two versions
PyPI serves:

- `v2.0.0`: `https://github.com/synapticforge1/universalWasmLoader-py/releases/new?tag=v2.0.0&title=v2.0.0`
- `v1.1.1`: `https://github.com/synapticforge1/universalWasmLoader-py/releases/new?tag=v1.1.1&title=v1.1.1`

Closed 2026-11-08 (outcomes in [overview.md](overview.md)): the C30 workflow split, PyPI 1.1.1-only
(intended), `InstancePool` size 4, per-file upload (C34 analogue), pixi-locked CI tools.
