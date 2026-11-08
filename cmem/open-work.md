# Open work — items waiting on the owner (or on a later session)

Each item: what was found, how (measured / read / reasoned), and what is proposed. Nothing here
is changed without the owner. Close an item by moving its outcome into the topic file it belongs
to and deleting it here.

**No open items (2026-11-08).** Closed that day, outcomes in [overview.md](overview.md):

- C30 workflow split — `ae51e95` (owner: "yes C30 applies here"); first run 42517168769 green.
- PyPI serving only 1.1.1 — intended (owner).
- `InstancePool` default size 4 — `93cc2f3` (owner).
- A half-finished upload (C34's PyPI analogue) — `eff40fa`: both publish paths upload only the
  files PyPI still needs (`scripts/pypi_files.py`); owner: "fix the last minor items".
- Unpinned CI tools — `4548c34`: CI and the publish `checks` job install `pixi.lock` through
  pixi 0.84.1 pinned by sha256; the build uses the locked hatchling.
