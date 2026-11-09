# Open work — items waiting on the owner (or on a later session)

Each item: what was found, how (measured / read / reasoned), and what is proposed. Nothing here
is changed without the owner. Close an item by moving its outcome into the topic file it belongs
to and deleting it here.

## ⚠️ OWNER (web UI): the `pypi` environment has no required reviewer

**Measured 2026-11-09** (public Actions API, run 42642679890, 2.0.1): the `publish` job was
created at the moment `checks` completed and started 4 s later, so it did not wait for a person.
Since `publish.yml` runs on every `v*` tag push (owner's choice, 2026-11-08), **pushing a tag
uploads to PyPI with no approval step**. The memory (from 2026-06-19) and the workflow comments
said every publish paused for the owner's approval; they are corrected. What still holds: the PyPI
Trusted Publisher accepts only this repo + `publish.yml` + environment `pypi`, and the run refuses
a moved tag. **If an approval step is wanted:** GitHub → Settings → Environments → `pypi` →
Required reviewers (and check its deployment-tag rule, `v*`). The environments API needs auth, so
its settings cannot be read from here; the next tag run shows the effect (a `waiting` status).

## OWNER (web UI, optional): GitHub Release pages for the EXISTING tags

**Measured 2026-11-09** (public REST API `GET /repos/…/releases`): the only Release page is
**`v2.0.2`**, made by CI's `release` job (run 42644832218); the tags `v1.0.0` … `v2.0.1` have none.
**Every new tag gets its page from CI** (2026-11-09, owner). It cannot backfill: a dispatch from an old tag runs THAT tag's
`publish.yml`, which has no `release` job. Nothing depends on the old pages (the tag is the
release). If wanted, the versions PyPI serves:

- `v2.0.1`: `https://github.com/synapticforge1/universalWasmLoader-py/releases/new?tag=v2.0.1&title=v2.0.1`
- `v2.0.0`: `https://github.com/synapticforge1/universalWasmLoader-py/releases/new?tag=v2.0.0&title=v2.0.0`
- `v1.1.1`: `https://github.com/synapticforge1/universalWasmLoader-py/releases/new?tag=v1.1.1&title=v1.1.1`

Closed 2026-11-08 (outcomes in [overview.md](overview.md)): the C30 workflow split, PyPI 1.1.1-only
(intended), `InstancePool` size 4, per-file upload (C34 analogue), pixi-locked CI tools.
