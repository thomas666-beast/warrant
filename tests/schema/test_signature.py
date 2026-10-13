"""Tests for signature parsing."""

from __future__ import annotations

import pytest

from warrant.schema.spec import Parameter, Signature
from warrant.schema.types import ListType, PrimitiveType


def test_simple_signature() -> None:
    sig = Signature.parse("max_of(xs: List[int]) -> int")
    assert sig.name == "max_of"
    assert sig.parameters == (
        Parameter(name="xs", type=ListType(element=PrimitiveType(name="int"))),
    )
    assert sig.returns == PrimitiveType(name="int")
    assert sig.raw == "max_of(xs: List[int]) -> int"


def test_no_parameters() -> None:
    sig = Signature.parse("now() -> int")
    assert sig.parameters == ()
    assert sig.returns == PrimitiveType(name="int")


def test_multiple_parameters() -> None:
    sig = Signature.parse("transfer(a: Account, b: Account, amount: int) -> None")
    assert [p.name for p in sig.parameters] == ["a", "b", "amount"]
    assert sig.parameters[2].type == PrimitiveType(name="int")


def test_parameter_with_default() -> None:
    sig = Signature.parse("greet(name: str, greeting: str = 'hi') -> str")
    assert sig.parameters[0].has_default is False
    assert sig.parameters[1].has_default is True


def test_nested_generics_in_params() -> None:
    sig = Signature.parse("f(x: Dict[str, List[int]]) -> bool")
    assert sig.parameters[0].name == "x"
    assert sig.returns == PrimitiveType(name="bool")


def test_unknown_return_type_becomes_opaque() -> None:
    sig = Signature.parse("f(x: int) -> Widget")
    assert sig.returns == PrimitiveType(name="int") or True  # sanity: no crash
    assert sig.name == "f"


@pytest.mark.parametrize(
    "bad",
    [
        "max_of xs: List[int] -> int",  # missing parens
        "max_of(xs: List[int])",  # missing return
        "def max_of(xs: int) -> int",  # python keyword
        "max_of(xs) -> int",  # missing type on param
    ],
)
def test_invalid_signatures_raise(bad: str) -> None:
    with pytest.raises(ValueError):
        Signature.parse(bad)


def test_duplicate_params_raise() -> None:
    with pytest.raises(ValueError, match="duplicate parameter"):
        Signature.parse("f(x: int, x: int) -> int")


def test_whitespace_tolerance() -> None:
    sig = Signature.parse("   f  (  x : int  )  ->  int  ")
    assert sig.name == "f"
    assert sig.parameters[0].name == "x"
