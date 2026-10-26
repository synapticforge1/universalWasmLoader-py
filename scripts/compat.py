"""The compatibility gate (workspace letter H6; layout-and-packaging.md, same heading).

"Backward compatible" is a gate result, never a judgment made at bump time.

  Rule 1  the SURFACE: api-surface.json (committed) = the SPEC.md version README declares + every
          public symbol of `universal_wasm_loader` with its signature. The reference fixture suite,
          the other half of a loader's surface, is pinned by tests/test_fixtures.py.
  Rule 2  the FLOOR: removed or changed -> major; added -> minor; nothing -> patch; the SPEC
          version moves it by its own level (lowered -> major). A bump below it is refused.
  Rule 3  BEHAVIOUR: the previous tag's tests/ run against its own src/ and then against the new
          src/, per test; a test that passed before and does not pass now is a regression.
  Rule 4  a major needs a `| _next release_ |` row under README's "### ⚠️ Breaking Changes".
  Rule 5  an intended surface change re-baselines in its OWN commit (`--write`).

Usage: pixi run python scripts/compat.py [--write | --release]
  (no flag)  report: snapshot fresh?, floor vs the last tag, previous-tag tests.
  --write    regenerate api-surface.json (a re-baseline: commit it alone, with the reason).
  --release  CI on the tagged commit: HEAD = tag v<manifest version>, and the step from the
             previous tag is at or above the floor with the tests green. Exit 1 blocks the publish.
"""
from __future__ import annotations

import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from _common import ROOT, git, read_version

SNAPSHOT = ROOT / "api-surface.json"
LEVELS = ("patch", "minor", "major")
SPEC_DECLARATION = re.compile(r"`SPEC\.md` \*\*v(\d+\.\d+\.\d+)\*\*")
BREAKING_HEADING = "### ⚠️ Breaking Changes"
NEXT_RELEASE_ROW = "| _next release_ |"


# ── Rule 1: the surface ────────────────────────────────────────────────────────

def _surface_here(src: Path, readme: Path, spec: str | None = None) -> dict[str, Any]:
    """Runs in a child process (see surface_of), so the package imported is the one under src."""
    sys.path.insert(0, str(src))
    import universal_wasm_loader as pkg

    origin = Path(pkg.__file__).resolve()
    if not origin.is_relative_to(src.resolve()):
        raise RuntimeError(f"imported {origin}, not the package under {src}")
    symbols: dict[str, str] = {}
    for name in pkg.__all__:
        obj = getattr(pkg, name)
        if inspect.isclass(obj):
            symbols[name] = "class"
            for member, value in vars(obj).items():
                if member.startswith("_") and member != "__init__":
                    continue
                if inspect.isfunction(value):
                    kind = "async method" if inspect.iscoroutinefunction(value) else "method"
                    symbols[f"{name}.{member}"] = f"{kind} {inspect.signature(value)}"
                elif isinstance(value, property):
                    symbols[f"{name}.{member}"] = "property"
        elif inspect.isfunction(obj):
            kind = "async function" if inspect.iscoroutinefunction(obj) else "function"
            symbols[name] = f"{kind} {inspect.signature(obj)}"
        else:
            raise RuntimeError(f"cannot key public name {name!r} ({type(obj).__name__})")
    if spec is None:
        m = SPEC_DECLARATION.search(readme.read_text(encoding="utf-8"))
        if not m:
            raise RuntimeError(f"{readme} declares no `SPEC.md` **vX.Y.Z**")
        spec = m.group(1)
    return {"spec": spec, "symbols": dict(sorted(symbols.items()))}


def surface_of(src: Path, readme: Path, spec: str | None = None) -> dict[str, Any]:
    """The surface of the package under `src`, computed in a fresh interpreter."""
    cmd = [sys.executable, __file__, "--emit-surface", str(src), str(readme)]
    r = subprocess.run(cmd + ([spec] if spec else []), capture_output=True, text=True,
                       encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"surface of {src} failed:\n{r.stderr}")
    result: dict[str, Any] = json.loads(r.stdout)
    return result


def render(surface: dict[str, Any]) -> str:
    return json.dumps(surface, indent=2, ensure_ascii=False) + "\n"


# ── Rule 2: the floor ──────────────────────────────────────────────────────────

def _semver(v: str) -> tuple[int, int, int]:
    a, b, c = (int(x) for x in v.split("."))
    return a, b, c


def level_between(old: str, new: str) -> str:
    o, n = _semver(old), _semver(new)
    if n <= o:
        return "lowered"
    return "major" if n[0] != o[0] else "minor" if n[1] != o[1] else "patch"


def floor_of(old: dict[str, Any], new: dict[str, Any]) -> tuple[str, list[str]]:
    """The minimum bump from `old` to `new`, with the reasons that set it."""
    reasons: list[str] = []
    level = 0
    os_, ns = old["symbols"], new["symbols"]
    for key in sorted(set(os_) | set(ns)):
        if key not in ns:
            reasons.append(f"major: removed {key}")
            level = 2
        elif key not in os_:
            reasons.append(f"minor: added {key}")
            level = max(level, 1)
        elif os_[key] != ns[key]:
            reasons.append(f"major: changed {key}: {os_[key]}  ->  {ns[key]}")
            level = 2
    if old["spec"] != new["spec"]:
        step = level_between(old["spec"], new["spec"])
        spec_level = 2 if step == "lowered" else LEVELS.index(step)
        reasons.append(f"{LEVELS[spec_level]}: SPEC.md v{old['spec']} -> v{new['spec']}")
        level = max(level, spec_level)
    return LEVELS[level], reasons


# ── Rule 3: the previous tag's tests ──────────────────────────────────────────

def tags() -> list[str]:
    """Release tags, lowest first."""
    listed = git("tag", "--list", "v*").stdout.split()
    found = [t for t in listed if re.fullmatch(r"v\d+\.\d+\.\d+", t)]
    return sorted(found, key=lambda t: _semver(t[1:]))


def _run_suite(tree: Path, out: Path) -> dict[str, str]:
    env = dict(os.environ, PYTHONPATH=str(tree / "src"))
    # The env's editable install points at this checkout; PYTHONPATH must win, so prove it does.
    probe = subprocess.run(
        [sys.executable, __file__, "--where", str(tree / "src")],
        capture_output=True, text=True, env=env, cwd=tree,
    )
    if probe.returncode != 0:
        raise RuntimeError(f"the suite in {tree} would not import its own src/:\n{probe.stderr}")
    subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider",
         f"--junitxml={out}"],
        capture_output=True, text=True, env=env, cwd=tree,
    )
    results: dict[str, str] = {}
    for case in ET.parse(out).getroot().iter("testcase"):
        verdict = "passed"
        for child in case:
            if child.tag in ("failure", "error", "skipped"):
                verdict = child.tag
        results[f"{case.get('classname')}::{case.get('name')}"] = verdict
    return results


def previous_tag_tests(tag: str) -> tuple[bool, list[str]]:
    """Run `tag`'s tests/ on its own src/ and on the current src/; green = no regression."""
    lines: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="uwl-compat-"))
    tree = tmp / "tree"
    try:
        r = git("worktree", "add", "--detach", str(tree), tag)
        if r.returncode != 0:
            raise RuntimeError(f"git worktree add {tag} failed: {r.stderr}")
        before = _run_suite(tree, tmp / "before.xml")
        shutil.rmtree(tree / "src")
        shutil.copytree(ROOT / "src", tree / "src")
        after = _run_suite(tree, tmp / "after.xml")
    finally:
        git("worktree", "remove", "--force", str(tree))
        shutil.rmtree(tmp, ignore_errors=True)

    def count(res: dict[str, str]) -> str:
        p = sum(v == "passed" for v in res.values())
        return f"{p} passed / {len(res) - p} not"

    regressions = [t for t, v in before.items() if v == "passed" and after.get(t) != "passed"]
    known = [t for t, v in before.items() if v != "passed"]
    lines.append(f"{tag}'s tests on {tag}'s src: {count(before)}; on the new src: {count(after)}")
    if known:
        lines.append(f"  {len(known)} already not passing on {tag} itself (not regressions)")
    for t in regressions:
        lines.append(f"  REGRESSION: {t} passed on {tag}, {after.get(t, 'missing')} now")
    green = not regressions and any(v == "passed" for v in after.values())
    return green, lines


# ── the gate ───────────────────────────────────────────────────────────────────

SUBMODULE = "upstream/universalwasmloader-js"
SPEC_VERSION_LINE = re.compile(r"^Version:\s*(\d+\.\d+\.\d+)", re.MULTILINE)


def spec_at(tag: str) -> str:
    """For a tag older than the gate (its README declares no version): the SPEC.md version of
    the reference-implementation commit that tag pinned as its submodule. Derived, never typed."""
    entry = git("ls-tree", tag, SUBMODULE).stdout.split()
    if len(entry) < 3 or entry[1] != "commit":
        raise RuntimeError(f"{tag} pins no {SUBMODULE} submodule")
    shown = subprocess.run(["git", "-C", str(ROOT / SUBMODULE), "show", f"{entry[2]}:SPEC.md"],
                           capture_output=True, text=True, encoding="utf-8")
    m = SPEC_VERSION_LINE.search(shown.stdout) if shown.returncode == 0 else None
    if not m:
        raise RuntimeError(f"cannot read SPEC.md at {SUBMODULE}@{entry[2][:10]} for {tag} "
                           "(is the submodule initialised? `git submodule update --init`)")
    return m.group(1)


def baseline(tag: str) -> dict[str, Any]:
    """The tag's committed snapshot; for a tag older than the gate, its surface from source."""
    shown = git("show", f"{tag}:api-surface.json")
    if shown.returncode == 0:
        result: dict[str, Any] = json.loads(shown.stdout)
        return result
    readme_text = git("show", f"{tag}:README.md").stdout
    spec = None if SPEC_DECLARATION.search(readme_text) else spec_at(tag)
    tmp = Path(tempfile.mkdtemp(prefix="uwl-base-"))
    try:
        r = git("worktree", "add", "--detach", str(tmp / "tree"), tag)
        if r.returncode != 0:
            raise RuntimeError(f"git worktree add {tag} failed: {r.stderr}")
        return surface_of(tmp / "tree" / "src", tmp / "tree" / "README.md", spec)
    finally:
        git("worktree", "remove", "--force", str(tmp / "tree"))
        shutil.rmtree(tmp, ignore_errors=True)


def has_next_release_row() -> bool:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.find(BREAKING_HEADING)
    if start < 0:
        return False
    section = text[start + len(BREAKING_HEADING):]
    nxt = section.find("\n#")
    return NEXT_RELEASE_ROW in (section if nxt < 0 else section[:nxt])


def check(requested: str, since: str | None) -> list[str]:
    """Problems that refuse a `requested` bump from tag `since`; prints the evidence."""
    problems: list[str] = []
    current = surface_of(ROOT / "src", ROOT / "README.md")
    if not SNAPSHOT.is_file() or SNAPSHOT.read_text(encoding="utf-8") != render(current):
        problems.append("api-surface.json is STALE (or missing): re-baseline in its own commit "
                        "with the reason (`pixi run python scripts/compat.py --write`)")
    if since is None:
        print("compat: no previous release tag — nothing to compare against")
        return problems
    floor, reasons = floor_of(baseline(since), current)
    print(f"compat: floor since {since} = {floor}")
    for r in reasons:
        print(f"  {r}")
    if LEVELS.index(requested) < LEVELS.index(floor):
        problems.append(f"a {requested} bump is below the floor ({floor})")
    if floor == "major" and not has_next_release_row():
        problems.append(f"the floor is major: README needs a `{NEXT_RELEASE_ROW}` row under "
                        f'"{BREAKING_HEADING}" (Rule 4)')
    if requested in ("patch", "minor"):
        green, lines = previous_tag_tests(since)
        for line in lines:
            print(f"compat: {line}")
        if not green:
            problems.append(f"{since}'s tests regress on the new src (Rule 3)")
    return problems


def main(argv: list[str]) -> None:
    if argv[:1] == ["--emit-surface"]:
        spec_arg = argv[3] if len(argv) > 3 else None
        print(render(_surface_here(Path(argv[1]), Path(argv[2]), spec_arg)), end="")
        return
    if argv[:1] == ["--where"]:
        import universal_wasm_loader as m

        if not Path(m.__file__).resolve().is_relative_to(Path(argv[1]).resolve()):
            sys.exit(f"imports {m.__file__}")
        return
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__.strip())
        return
    if argv[:1] == ["--write"]:
        SNAPSHOT.write_text(render(surface_of(ROOT / "src", ROOT / "README.md")), encoding="utf-8",
                            newline="\n")
        print(f"wrote {SNAPSHOT.name} — commit it ALONE, with the reason (Rule 5)")
        return

    all_tags = tags()
    if argv[:1] == ["--release"]:
        version = read_version(ROOT / "pyproject.toml")
        head = git("rev-parse", "HEAD").stdout.strip()
        tag = f"v{version}"
        if git("rev-parse", "-q", "--verify", f"{tag}^{{commit}}").stdout.strip() != head:
            sys.exit(f"compat --release: HEAD is not tag {tag} (the manifest version)")
        earlier = [t for t in all_tags if _semver(t[1:]) < _semver(version)]
        since = earlier[-1] if earlier else None
        step = level_between(since[1:], version) if since else "patch"
        problems = check(step, since)
    else:
        since = all_tags[-1] if all_tags else None
        problems = check("patch", since)
    for p in problems:
        print(f"compat: REFUSED: {p}", file=sys.stderr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
