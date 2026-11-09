# Open work — items waiting on the owner (or on a later session)

Each item: what was found, how (measured / read / reasoned), and what is proposed. Nothing here
is changed without the owner. Close an item by moving its outcome into the topic file it belongs
to and deleting it here.

## ⚠️ OWNER (web UI): the `pypi` environment has no required reviewer

**Measured 2026-11-09** (public Actions API, run 42642679890, 2.0.1; again on 2.0.2, run
42644832218): the `publish` job was created at the moment `checks` completed and started seconds
later, so it did not wait for a person. Since `publish.yml` runs on every `v*` tag push (owner's
choice, 2026-11-08), **pushing a tag uploads to PyPI with no approval step**. The memory (from
2026-06-19) and the workflow comments said every publish paused for the owner's approval; they are
corrected. What still holds: the PyPI Trusted Publisher accepts only this repo + `publish.yml` +
environment `pypi`, and the run refuses a moved tag. **If an approval step is wanted:** GitHub →
Settings → Environments → `pypi` → Required reviewers (and check its deployment-tag rule, `v*`).
The environments API needs auth, so its settings cannot be read from here; the next tag run shows
the effect (a `waiting` status).

Closed (outcomes in [overview.md](overview.md)): 2026-11-09 — Release pages for the old tags
(owner, letter H32: "only new tags will get release pages"; every new tag gets one from CI,
measured on v2.0.2). 2026-11-08 — the C30 workflow split, PyPI 1.1.1-only (intended),
`InstancePool` size 4, per-file upload (C34 analogue), pixi-locked CI tools.
