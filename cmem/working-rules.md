# Working rules — the checklist (rules, not lessons; lessons are in best-practices.md)

The workspace floor is `../../cmem/working-rules.md`; these are what bite in this repo.

## Git and release

- **Nothing is pushed, tagged or published unless the owner says so.** A published PyPI version is
  immutable ([release.md](release.md)). 🔒 **Since the H33 order (`9c6d3bd`, 2026-11-10) the
  `pyproject.toml` version line ARMS a release:** a push of `main` whose version has NO tag yet
  IS a release — CI checks, tags, makes the page and publishes, with no person in between (the
  `pypi` environment has no reviewer; owner, 2026-11-09: "no" to adding one). So the version line
  moves only through `pixi run bump <level>` and is pushed only by `pixi run release`, on the
  owner's word "release". **Nobody makes or pushes a tag by hand any more — CI does** (a published
  tag never moves). A push of `main` with an already-tagged version runs `checks` only (+ `ci.yml`).
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
  can do (a topic, a page CI did not create) is an OWNER item, never "blocked". Since
  2026-11-09 `publish.yml`'s `release` job creates the Release page by REST
  (`scripts/github_release.py`); `release.py` prints a pre-filled `releases/new` link as the
  fallback. `POST /releases` CREATES a missing tag, so the script first requires that the tag
  exists and peels to `github.sha` (loader-rs's hazard) — keep that check FIRST in any change.
  🔒 **Letter H32 (owner, 2026-11-09): every tagged release's page is made BY CI, never by hand;
  only NEW tags get pages (no backfill).** Its order, all kept here: tag exists + peels first;
  an existing page = done, no write; POST with the registry link, read back (not a draft), peel
  again; no checkout beside the write token (C30); **every request has its own total time limit,
  request to last byte** (best-practice 7.21) — in Python that is NOT `urlopen(timeout=)` (per
  socket operation); use the `with_limit()` deadline, with the socket timeout looser than it.
  Re-grep: `git grep -n -w gh -- . ':!cmem' ':!*.md'` → 0 hits.
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

## Owner commands: "commit", "push", "release" (owner, 2026-11-10)

🔒 Written into every project by the workspace session on the owner's direction (2026-11-10:
"please write that into each project"; workspace `cmem/working-rules.md` Tooling rule 12, letter
H34). When the owner says:

- **"commit"** — first run "update the project memory files" (re-derive this repo's `cmem/` from
  its current state), then commit to the branch being worked on. Nothing is pushed.
- **"push"** — perform "commit", then merge the branch into `main`, then push `main` (and the
  working branch) to GitHub (`origin`) and read it back with `git ls-remote`.
- **"release"** — perform "push", then the release process: the workspace's
  `cmem/release-process.md` §§ 5–8 — CI checks first, then CI pushes the tag, then the GitHub
  Release page from the tag, then the publish to the registry — recorded in `cmem/release.md`
  § "Release History" (newest first, a summary of what changed). The level (patch / minor /
  major) is the owner's: ask if it was not given.

Each command includes the one before it, and none goes further than its own word (a "commit"
never pushes, a "push" never releases). This repo's own gate and merge rules apply at each step.
