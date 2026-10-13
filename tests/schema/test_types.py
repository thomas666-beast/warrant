"""Tests for the type-expression parser."""

from __future__ import annotations

import pytest

from warrant.schema.types import (
    DictType,
    ListType,
    OpaqueType,
    OptionalType,
    PrimitiveType,
    parse_type,
)


@pytest.mark.parametrize("name", ["int", "str", "bool", "float", "bytes", "None"])
def test_primitives(name: str) -> None:
    assert parse_type(name) == PrimitiveType(name=name)


def test_list_of_int() -> None:
    assert parse_type("List[int]") == ListType(element=PrimitiveType(name="int"))


def test_nested_list() -> None:
    assert parse_type("List[List[int]]") == ListType(
        element=ListType(element=PrimitiveType(name="int"))
    )


def test_optional() -> None:
    assert parse_type("Optional[str]") == OptionalType(inner=PrimitiveType(name="str"))


def test_dict() -> None:
    assert parse_type("Dict[str, int]") == DictType(
        key=PrimitiveType(name="str"), value=PrimitiveType(name="int")
    )


def test_dict_with_nested() -> None:
    assert parse_type("Dict[str, List[int]]") == DictType(
        key=PrimitiveType(name="str"),
        value=ListType(element=PrimitiveType(name="int")),
    )


def test_unknown_type_is_opaque_not_error() -> None:
    result = parse_type("MyCustomThing")
    assert isinstance(result, OpaqueType)
    assert result.text == "MyCustomThing"


def test_malformed_dict_is_opaque_not_error() -> None:
    # Only one type arg — should not raise
    result = parse_type("Dict[str]")
    assert isinstance(result, OpaqueType)
    assert result.text == "Dict[str]"


def test_whitespace_is_stripped() -> None:
    assert parse_type("  int  ") == PrimitiveType(name="int")


def test_empty_becomes_opaque() -> None:
    result = parse_type("")
    assert isinstance(result, OpaqueType)
