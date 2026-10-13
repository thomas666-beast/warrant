"""Tests for the YAML spec loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from warrant.parser import SpecLoadError, load_spec, load_spec_from_string
from warrant.schema.spec import ComplexityClass, Effect, PropertyKind

# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

MINIMAL = """
module: m
functions:
  f:
    signature: "f(x: int) -> int"
"""


def test_minimal_spec_loads() -> None:
    result = load_spec_from_string(MINIMAL)
    assert not isinstance(result, SpecLoadError), result
    assert result.module == "m"
    assert set(result.functions) == {"f"}
    assert result.functions["f"].signature.name == "f"


FULL = """
module: max
functions:
  max_of:
    signature: "max_of(xs: List[int]) -> int"
    requires:
      - "len(xs) > 0"
    ensures:
      - "result in xs"
      - "forall y in xs: result >= y"
    effects: []
    complexity: "O(n)"
    properties:
      - name: idempotent
        kind: example
        text: "max_of([x]) == x"
"""


def test_full_spec_loads() -> None:
    result = load_spec_from_string(FULL)
    assert not isinstance(result, SpecLoadError), result
    fn = result.functions["max_of"]
    assert len(fn.requires) == 1
    assert fn.requires[0].text == "len(xs) > 0"
    assert len(fn.ensures) == 2
    assert fn.complexity is not None
    assert fn.complexity.klass == ComplexityClass.O_N
    assert len(fn.properties) == 1
    assert fn.properties[0].kind == PropertyKind.EXAMPLE


def test_effects_are_loaded() -> None:
    text = """
module: m
functions:
  read:
    signature: "read(p: str) -> str"
    effects:
      - read_fs
      - network
"""
    result = load_spec_from_string(text)
    assert not isinstance(result, SpecLoadError), result
    assert result.functions["read"].effects == frozenset({Effect.READ_FS, Effect.NETWORK})


# ---------------------------------------------------------------------------
# File-level errors
# ---------------------------------------------------------------------------


def test_missing_file() -> None:
    result = load_spec("/nonexistent/path.warrant.yaml")
    assert isinstance(result, SpecLoadError)
    assert "not found" in result.message


def test_empty_file() -> None:
    result = load_spec_from_string("")
    assert isinstance(result, SpecLoadError)
    assert "empty" in result.message


def test_yaml_syntax_error_has_line() -> None:
    text = """
module: m
functions:
  f:
    signature: "f(x: int) -> int"
  bad_indent_here
"""
    result = load_spec_from_string(text)
    assert isinstance(result, SpecLoadError)
    assert "YAML syntax error" in result.message
    assert result.line is not None
    assert result.line > 1


def test_root_must_be_mapping() -> None:
    result = load_spec_from_string("- just\n- a\n- list\n")
    assert isinstance(result, SpecLoadError)
    assert "mapping" in result.message


# ---------------------------------------------------------------------------
# Structural errors — with line numbers
# ---------------------------------------------------------------------------


def test_unknown_top_level_key() -> None:
    text = """
module: m
funcs:
  f:
    signature: "f(x: int) -> int"
"""
    result = load_spec_from_string(text)
    assert isinstance(result, SpecLoadError)
    assert "unknown top-level key" in result.message
    assert "funcs" in result.message
    assert result.path == ("funcs",)
    assert result.line is not None


def test_missing_module() -> None:
    text = """
functions:
  f:
    signature: "f(x: int) -> int"
"""
    result = load_spec_from_string(text)
    assert isinstance(result, SpecLoadError)
    assert "module" in result.message


def test_missing_functions() -> None:
    text = "module: m\n"
    result = load_spec_from_string(text)
    assert isinstance(result, SpecLoadError)
    assert "functions" in result.message


def test_unknown_function_key() -> None:
    text = """
module: m
functions:
  f:
    signature: "f(x: int) -> int"
    reqiures:
      - "x > 0"
"""
    result = load_spec_from_string(text)
    assert isinstance(result, SpecLoadError)
    assert "reqiures" in result.message
    assert result.path == ("functions", "f", "reqiures")


def test_functions_must_be_mapping() -> None:
    text = """
module: m
functions:
  - f
"""
    result = load_spec_from_string(text)
    assert isinstance(result, SpecLoadError)
    assert "mapping" in result.message


# ---------------------------------------------------------------------------
# Pydantic errors, translated
# ---------------------------------------------------------------------------


def test_invalid_signature_reports_line() -> None:
    text = """
module: m
functions:
  f:
    signature: "not a valid signature"
"""
    result = load_spec_from_string(text)
    assert isinstance(result, SpecLoadError)
    assert result.line is not None
    assert result.path == ("functions", "f", "signature")


def test_unknown_effect_reports_line() -> None:
    text = """
module: m
functions:
  f:
    signature: "f(x: int) -> int"
    effects:
      - teleport
"""
    result = load_spec_from_string(text)
    assert isinstance(result, SpecLoadError)
    assert "teleport" in result.message or "Input should be" in result.message


def test_property_name_mismatch_reports_path() -> None:
    text = """
module: m
functions:
  f:
    signature: "f(x: int) -> int"
    properties:
      - name: idem
        kind: idempotent
      - name: idem
        kind: idempotent
"""
    result = load_spec_from_string(text)
    assert isinstance(result, SpecLoadError)
    assert "duplicate" in result.message.lower()


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------


def test_round_trip_via_file(tmp_path: Path) -> None:
    spec_file = tmp_path / "test.warrant.yaml"
    spec_file.write_text(MINIMAL)
    result = load_spec(spec_file)
    assert not isinstance(result, SpecLoadError), result
    assert result.module == "m"


def test_source_provides_line_text() -> None:
    from warrant.parser.source import Source

    source = Source.from_string(MINIMAL, file=Path("test.yaml"))
    assert isinstance(source, Source)
    # Line 2 is `module: m`
    assert "module" in source.line_at(2)


# ---------------------------------------------------------------------------
# Error rendering
# ---------------------------------------------------------------------------


def test_error_render_includes_location() -> None:
    text = """
module: m
functions:
  f:
    signature: "f(x: int) -> int"
    reqiures:
      - "x > 0"
"""
    result = load_spec_from_string(text)
    assert isinstance(result, SpecLoadError)
    rendered = result.render()
    assert "<string>" in rendered
    assert "reqiures" in rendered
