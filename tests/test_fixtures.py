"""The fixtures in tests/fixtures/ are exactly the stamped reference set from
universalWasmLoader-js (workspace letter H7 / S4; SPEC §7: "without modification").

Same rule as -js's scripts/check-fixtures.ts: fails when a stamped file is missing or its bytes
differ from tests/fixtures/fixtures.json, or when the folder holds a .wasm / .wit / .wat the stamp
does not list. To update: re-copy every *.wasm, *.wit, *.wat and fixtures.json from -js's tests/;
never edit a fixture by hand. Python-only fixtures live in tests/py_fixtures/.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_problems(directory: Path) -> list[str]:
    stamp = json.loads((directory / "fixtures.json").read_text(encoding="utf-8"))
    files: dict[str, str] = stamp["files"]
    problems: list[str] = []
    for name, digest in files.items():
        path = directory / name
        if not path.exists():
            problems.append(f"{name}: missing")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            problems.append(f"{name}: bytes differ from the stamp")
    for path in sorted(directory.iterdir()):
        if path.suffix in (".wasm", ".wit", ".wat") and path.name not in files:
            problems.append(f"{path.name}: not in the stamp")
    return problems


def test_fixtures_match_stamp() -> None:
    assert fixture_problems(FIXTURES) == []


def test_stamp_lists_the_reference_set() -> None:
    stamp = json.loads((FIXTURES / "fixtures.json").read_text(encoding="utf-8"))
    assert stamp["generator"]["commit"] == "4a5c3cf668da2c5c6e2cde444851773b5d4f4a08"
    assert len(stamp["files"]) == 12
