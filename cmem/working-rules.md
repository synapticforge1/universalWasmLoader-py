# Working rules — the checklist (rules, not lessons; lessons are in best-practices.md)

The workspace floor is `../../cmem/working-rules.md`; these are what bite in this repo.

## Git and release

- **Nothing is pushed, tagged or published unless the owner says so.** A published PyPI version is
  immutable ([overview.md](overview.md) § release toolchain).
- Commit messages go through a file: `git commit -F <file>`. Never a heredoc.
- Nothing is written into a sibling repo from here (workspace ★ 8.1). Read `-js` freely.

## Tooling hard rules (workspace, 🔒 owner 2026-10-22, letter H15)

- **Committed scripts are pixi's Python** (`pixi run python <file>.py`), never the host `python3`
  (a Store stub on this machine). No committed shell scripts; Nushell counts as a shell.
  **Open (H15, 2026-10-26):** `scripts/{bump-version,release,publish}.{sh,nu}` are still the six
  shell / Nushell files; each port replaces its original only after an output diff proves them
  equivalent (same inputs, files + stdout + exit code, one input that must fail).
- No heredocs for any content. When the exit code is the measurement, do not pipe it.

## Privacy 🔒 (owner, 2026-10-22 / 2026-10-23 / 2026-10-26; workspace letters H18, H22, H28)

- **No secrets and no personal information in any committed file, commit message, package or
  issue.** The workspace text is `../../cmem/working-rules.md` § Records.
- **The path test is "is it machine-specific?", not "is it absolute?"** NOT public: any path that
  records the owner's machine layout (a user profile, the project tree on a drive, other drives,
  scoop / AppData installs, scratchpad or session ids). Fine: repo- or sibling-relative paths,
  env vars, placeholders (`<repo-root>`), and a CONVENTION path that names nothing about one
  machine (e.g. `~/.pypirc`). A scan hit is a CANDIDATE judged by this test; do not scrub
  convention paths.
- **The one email exception:** the maintainer contact address in the manifest field a registry
  reads, as the git commit author / committer address, and in ONE committed `cmem/` contact note
  (owner, 2026-10-26, H28). Nowhere else; not repeated. This repo keeps it in `pyproject.toml`
  `[project] authors` (PyPI reads it) and on commits; there is no contact note.
- Private facts go in a gitignored `cmem/local/` (machine notes; any private backup).
- **Scan before committing, binaries included** (`-a`: a compiler's debug output embeds the build
  machine's paths): `git grep -n -a -i -E '[A-Za-z]:[\\/]+(Programs|Users|scoop|tools)[\\/]'`.
  2026-10-26: 0 hits at HEAD; no history purge needed (workspace H25 §3(a), measured over every ref).

## Memory

- `cmem/` is the single home of project memory; [INDEX.md](INDEX.md) has one line per file.
- Never run a formatter on `cmem/`. Absolute dates; every number carries its date.
- At session start, read `../../cmem/workspace-correspondence.md` (rows addressed to this repo, and
  rows touching the work at hand), then the letter it points to in `../../cmem/handoffs.md`.
- **A sibling's commit id is looked up in its history map before it is quoted** (workspace H21).
