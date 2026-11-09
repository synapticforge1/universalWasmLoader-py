# Working rules — the checklist (rules, not lessons; lessons are in best-practices.md)

The workspace floor is `../../cmem/working-rules.md`; these are what bite in this repo.

## Git and release

- **Nothing is pushed, tagged or published unless the owner says so.** A published PyPI version is
  immutable ([overview.md](overview.md) § release toolchain). **Since 2026-11-08 pushing a `v*`
  tag PUBLISHES to PyPI** (`publish.yml`). It does not wait for a person: 2.0.1's run
  42642679890 (2026-11-09) started `publish` 4 s after `checks`, so the `pypi` environment has
  no required reviewer (an owner setting, [open-work.md](open-work.md)). Re-pointing a pushed tag
  re-runs it (the per-file planner then uploads nothing). So a tag push IS a publish. A push to `main` runs
  only `ci.yml`.
- **Read a workflow run back, never assume it:** `api.github.com/repos/synapticforge1/
  universalWasmLoader-py/actions/runs?head_sha=<sha>` (public, no `gh`); a PyPI claim from
  `pypi.org/pypi/universal-wasm-loader/<version>/json` (the project-level JSON lags minutes).
- **A one-time check whose exit code is the measurement is not piped** — measured the hard way
  2026-11-08 (`PIPESTATUS` in a subshell printed `exit=0` for refusals).
- Commit messages go through a file: `git commit -F <file>`. Never a heredoc.
- **Branching = the workspace floor** (this repo had no rule of its own; adopted 2026-10-26):
  branch → `pixi run gate` → `git merge --no-ff` into `main`. Decide commit granularity before
  editing.
- **Never `git checkout <file>` to drop a probe** — copy the file aside and copy it back (broken
  once here on 2026-10-26 restoring a deleted fixture; nothing was lost, but that was luck).
- **Never inline code in a command** (`python -c`, `bun -e`): write a scratch file and run it.
- Nothing is written into a sibling repo from here (workspace ★ 8.1). Read `-js` freely.

## Tooling hard rules (workspace, 🔒 owner 2026-10-22, letter H15)

- **Committed scripts are pixi's Python** (`pixi run python <file>.py`), never the host `python3`
  (a Store stub on this machine). No committed shell scripts; Nushell counts as a shell.
  The six `.sh` / `.nu` were ported 2026-10-26 (H15; proof in [overview.md](overview.md) § "Single
  source of truth"). A future port replaces its original only after an output diff proves them
  equivalent (same inputs, files + stdout + exit code, inputs that must fail).
- No heredocs for any content. When the exit code is the measurement, do not pipe it.
- 🔒 **No GitHub CLI, in CI too** (owner, 2026-11-08; workspace Tooling rule 9, letter H30).
  What GitHub holds is read with `git ls-remote` and the public REST API; a task only the web UI
  can do (a Release page, a topic) is an OWNER item, never "blocked". `release.py` prints the
  Release page as a pre-filled `releases/new` link (`2026-11-09`); no workflow here calls the CLI.
  If a workflow ever creates a Release by REST: `POST /releases` CREATES a missing tag, so the tag
  must first exist and peel to `github.sha` (loader-rs's hazard). Re-grep:
  `git grep -n -w gh -- . ':!cmem' ':!*.md'` → 0 hits.
- 🔒 **Every Bun-version notation is the latest installed Bun** (owner, 2026-11-09; Tooling rule
  10, letter H31): `bun --version` on Windows and in WSL — 1.4.4 on both, measured 2026-11-09.
  This repo pins, installs or requires no Bun (its committed scripts are pixi Python; Bun runs
  only one-time scratch checks), so the only notation is overview.md's dev-host line; it moves at
  the next session after a new Bun is installed. Dated measurements stay as measured.

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
