import pytest

from universal_wasm_loader._wit_parser import (
    kebab_to_camel,
    kebab_to_wasm_key,
    parse_wit,
    parse_wit_params,
    parse_wit_type,
)


def test_kebab_to_camel() -> None:
    assert kebab_to_camel("my-func") == "myFunc"
    assert kebab_to_camel("calculate") == "calculate"
    assert kebab_to_camel("is-positive") == "isPositive"
    assert kebab_to_camel("env-mul") == "envMul"
    assert kebab_to_camel("math-50") == "math50"


def test_kebab_to_wasm_key() -> None:
    assert kebab_to_wasm_key("my-func") == "my_func"
    assert kebab_to_wasm_key("env-add") == "env_add"
    assert kebab_to_wasm_key("calculate") == "calculate"


def test_parse_wit_type() -> None:
    for t in ("s32", "s64", "f32", "f64", "bool", "string"):
        assert parse_wit_type(t, "here") == t
    assert parse_wit_type("  f64  ", "here") == "f64"


@pytest.mark.parametrize("t", ["u32", "list<u8>", "unknown", ""])
def test_parse_wit_type_refuses_anything_else(t: str) -> None:
    # SPEC 4.0.0 §2: never read as another type (3.0.0 read every unknown type as s32).
    with pytest.raises(ValueError, match=r"unsupported WIT type .* in export f, result"):
        parse_wit_type(t, "export f, result")


def test_parse_wit_params() -> None:
    assert parse_wit_params("a: s32, b: s32", "export f") == [
        {"name": "a", "type": "s32"},
        {"name": "b", "type": "s32"},
    ]
    assert parse_wit_params("x: bool", "export f") == [{"name": "x", "type": "bool"}]
    kebab = parse_wit_params("my-name: string", "export f")
    assert kebab == [{"name": "myName", "type": "string"}]
    assert parse_wit_params("a: s32,", "export f") == [{"name": "a", "type": "s32"}]
    assert parse_wit_params("", "export f") == []


@pytest.mark.parametrize(
    ("raw", "fault"),
    [
        ("a: s32 b: s32", "malformed parameter"),
        ("a", "malformed parameter"),
        ("a: s32,,", "malformed parameter"),
        ("1a: s32", "malformed parameter"),
        ("a: s32, a: f64", 'duplicate parameter "a"'),
    ],
)
def test_parse_wit_params_refuses(raw: str, fault: str) -> None:
    with pytest.raises(ValueError, match=fault):
        parse_wit_params(raw, "export f")


def test_parse_wit_full() -> None:
    src = """
    // a comment
    package example:math@1.0.0;

    world math-world {
      export calculate: func(a: s32, b: s32) -> s32;  // trailing comment
      export is-positive: func(n: s32) -> bool;
      import env-mul: func(a: f32, b: f32) -> f32;
      import log: func(msg: string);
    }
    """
    result = parse_wit(src)
    assert result["package"] == "example:math@1.0.0"
    assert result["world"] == "math-world"
    assert [f["camel_name"] for f in result["exports"]] == ["calculate", "isPositive"]
    assert result["exports"][1]["wasm_key"] == "is_positive"
    assert result["exports"][1]["return_type"] == "bool"
    assert result["imports"][0] == {
        "name": "env-mul",
        "camel_name": "envMul",
        "wasm_key": "env_mul",
        "params": [{"name": "a", "type": "f32"}, {"name": "b", "type": "f32"}],
        "return_type": "f32",
    }
    assert result["imports"][1]["return_type"] is None


def test_parse_wit_bom_and_no_package() -> None:
    result = parse_wit("﻿world w { export f: func(); }")
    assert result["package"] == ""
    assert result["exports"][0]["params"] == []


@pytest.mark.parametrize(
    ("src", "fault"),
    [
        ("", "it is empty"),
        ("// only a comment", "it is empty"),
        ("package p;", "it is empty"),
        ("world w { export f: func() }", 'missing ";"'),
        ("world w { export f: func(); } world v { }", "expected one"),
        ("world w { export f: func(); } trailing", "expected one"),
        ("world w { type t = s32; }", "unsupported or malformed"),
        ("world w { export f: func(); export f: func(); }", "duplicate export f"),
        ("world w { import f: func(); import f: func(); }", "duplicate import f"),
        ("world w { export f-: func(); }", "malformed function name"),
        ("world bad_name { }", 'malformed world name "bad_name"'),
        ("world w { export f: func() -> u32; }", 'unsupported WIT type "u32" in export f, result'),
    ],
)
def test_parse_wit_refuses(src: str, fault: str) -> None:
    with pytest.raises(ValueError, match=fault):
        parse_wit(src)


def test_parse_wit_import_and_export_may_share_a_name() -> None:
    result = parse_wit("world w { import f: func(); export f: func(); }")
    assert len(result["imports"]) == len(result["exports"]) == 1
