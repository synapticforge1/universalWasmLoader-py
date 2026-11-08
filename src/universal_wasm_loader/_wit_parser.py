"""Strict parser for the companion `.wit` (SPEC 4.0.0 §2 "Parsing").

A port of universalWasmLoader-js `wit-parser.js` 2.0.0: same grammar, same messages. The accepted
form is the subset wasmtk writes: an optional `package` line and one `world` holding only
`import` / `export` function statements, with `//` comments. Anything else raises `ValueError`
naming it; a `.wit` is never read loosely.
"""

from __future__ import annotations

import re

# The WIT types this loader translates (SPEC §4); any other type is an error. Order = the message.
_WIT_TYPES = ("s32", "s64", "f32", "f64", "bool", "string")

# A WIT identifier: kebab-case words of letters and digits.
_IDENT = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*")

# One `import` / `export` statement of a world body, without its `;`.
_FUNC_STMT = re.compile(r"(import|export)\s+([^\s:]+)\s*:\s*func\s*\(([^()]*)\)\s*(?:->\s*(\S+))?")

_PARAM = re.compile(r"([^:\s]+)\s*:\s*(\S+)")
_PACKAGE = re.compile(r"package\s+([^\s;]+)\s*;")
_WORLD = re.compile(r"world\s+([^\s{]+)\s*\{([^{}]*)\}")
_COMMENT = re.compile(r"//[^\n]*")


def kebab_to_camel(name: str) -> str:
    """`is-positive` -> `isPositive` (exactly -js's `kebabToCamel`: `-` + [a-z0-9])."""
    return re.sub(r"-([a-z0-9])", lambda m: m.group(1).upper(), name)


def kebab_to_wasm_key(name: str) -> str:
    """`env-mul` -> `env_mul`, the WASM import / export key."""
    return name.replace("-", "_")


def parse_wit_type(raw: str, where: str) -> str:
    t = raw.strip()
    if t not in _WIT_TYPES:
        raise ValueError(
            f'unsupported WIT type "{t}" in {where} (supported: {", ".join(_WIT_TYPES)})'
        )
    return t


def parse_wit_params(raw: str, fn_label: str) -> list[dict[str, str]]:
    # A trailing comma is valid WIT: `func(a: s32,)`.
    parts = [p.strip() for p in raw.split(",")]
    if parts and parts[-1] == "":
        parts.pop()
    params: list[dict[str, str]] = []
    seen: set[str] = set()
    for part in parts:
        m = _PARAM.fullmatch(part)
        if m is None or _IDENT.fullmatch(m.group(1)) is None:
            raise ValueError(f'malformed parameter "{part}" in {fn_label} (expected "name: type")')
        raw_name = m.group(1)
        if raw_name in seen:
            raise ValueError(f'duplicate parameter "{raw_name}" in {fn_label}')
        seen.add(raw_name)
        ptype = parse_wit_type(m.group(2), f"{fn_label}, parameter {raw_name}")
        params.append({"name": kebab_to_camel(raw_name), "type": ptype})
    return params


def parse_wit(src: str) -> dict:  # type: ignore[type-arg]
    """Parse a `.wit` source. Returns `{package, world, imports, exports}`; each function is
    `{name, camel_name, wasm_key, params, return_type}` (`return_type` None for no result).
    Raises `ValueError` on anything outside the grammar (SPEC 4.0.0 §2)."""
    code = _COMMENT.sub("", src.removeprefix("﻿"))

    rest = code.strip()
    package = ""
    pkg = _PACKAGE.match(rest)
    if pkg is not None:
        package = pkg.group(1)
        rest = rest[pkg.end() :].strip()

    world = _WORLD.fullmatch(rest)
    if world is None:
        what = (
            "it is empty"
            if rest == ""
            else f'expected one "world <name> {{ ... }}" block, found: {rest[:60]}'
        )
        raise ValueError(f"not a WIT world: {what}")
    world_name = world.group(1)
    if _IDENT.fullmatch(world_name) is None:
        raise ValueError(f'malformed world name "{world_name}"')

    imports: list[dict] = []  # type: ignore[type-arg]
    exports: list[dict] = []  # type: ignore[type-arg]
    statements = [s.strip() for s in world.group(2).split(";")]
    last = statements.pop()
    if last != "":
        raise ValueError(f'unterminated WIT statement (missing ";"): {last}')
    for stmt in statements:
        m = _FUNC_STMT.fullmatch(stmt)
        if m is None:
            flat = re.sub(r"\s+", " ", stmt)
            raise ValueError(f"unsupported or malformed WIT statement: {flat}")
        keyword, name = m.group(1), m.group(2)
        fn_label = f"{keyword} {name}"
        if _IDENT.fullmatch(name) is None:
            raise ValueError(f"malformed function name in {fn_label}")
        funcs = imports if keyword == "import" else exports
        if any(f["name"] == name for f in funcs):
            raise ValueError(f"duplicate {fn_label}")
        params = parse_wit_params(m.group(3), fn_label)
        result = parse_wit_type(m.group(4), f"{fn_label}, result") if m.group(4) else None
        funcs.append(
            {
                "name": name,
                "camel_name": kebab_to_camel(name),
                "wasm_key": kebab_to_wasm_key(name),
                "params": params,
                "return_type": result,
            }
        )

    return {"package": package, "world": world_name, "imports": imports, "exports": exports}
