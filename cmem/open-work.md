# Open work — items waiting on the owner (or on a later session)

Each item: what was found, how (measured / read / reasoned), and what is proposed. Nothing here
was changed without the owner. Close an item by moving its outcome into the topic file it belongs
to and deleting it here.

Closed 2026-11-08 on the owner's answers ("yes C30 applies here. yes 1.1.1 is the only one on
pypi. yes change the instance pool"): the workflow split (C30, `ae51e95`), the PyPI 404s
(intended), `InstancePool` size 4 (`93cc2f3`) — outcomes in [overview.md](overview.md).

## 1. A failed upload can strand a version (C34 (1), PyPI analogue)

**Read 2026-11-08 (record-only, reasoned).** `twine upload dist/*` sends the sdist and the wheel
one file at a time; a failure after the first leaves a half-published version, and PyPI never
accepts a removed file name again. The upload is the workflow's last step, so no later job is
skipped, but a re-run fails on the file already there. A re-run that should finish the job needs
`twine upload --skip-existing`; deliberately NOT the default (it would also hide a re-run of a
version already fully published). Owner's call if it ever happens.

## 2. The checks job installs its tools unpinned (recorded 2026-10-26, narrowed 2026-11-08)

`checks` installs ruff / mypy / pytest / build / twine from pip without pins, while local runs use
`pixi.lock`; a newer ruff could fail on the runner what passes here. Since the C30 split that job
holds no credential, so this is reproducibility only, not exposure. (The `publish` job pins
`twine==7.0.0`, wheels only; twine's own dependencies float.)
