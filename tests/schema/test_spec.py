"""Tests for the top-level spec models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from warrant.schema.spec import (
    Complexity,
    ComplexityClass,
    Effect,
    Expression,
    FunctionSpec,
    Property,
    PropertyKind,
    Signature,
    Spec,
)


def _minimal_function() -> FunctionSpec:
    return FunctionSpec(signature=Signature.parse("f(x: int) -> int"))


def test_minimal_spec() -> None:
    spec = Spec(module="m", functions={"f": _minimal_function()})
    assert spec.module == "m"
    assert set(spec.functions) == {"f"}


def test_spec_requires_matching_key_and_signature_name() -> None:
    with pytest.raises(ValidationError, match="does not match signature name"):
        Spec(
            module="m",
            functions={"g": _minimal_function()},  # key "g", sig name "f"
        )


def test_spec_requires_at_least_one_function() -> None:
    with pytest.raises(ValidationError, match="no functions"):
        Spec(module="m", functions={})


def test_function_spec_effects_roundtrip() -> None:
    fn = FunctionSpec(
        signature=Signature.parse("read(p: str) -> str"),
        effects=frozenset({Effect.READ_FS}),
    )
    assert Effect.READ_FS in fn.effects


def test_unknown_effect_rejected() -> None:
    with pytest.raises(ValidationError):
        FunctionSpec(
            signature=Signature.parse("f(x: int) -> int"),
            effects=frozenset({"teleport"}),  # type: ignore[arg-type]
        )


def test_property_names_must_be_unique() -> None:
    with pytest.raises(ValidationError, match="duplicate property names"):
        FunctionSpec(
            signature=Signature.parse("f(x: int) -> int"),
            properties=(
                Property(name="idem", kind=PropertyKind.IDEMPOTENT),
                Property(name="idem", kind=PropertyKind.IDEMPOTENT),
            ),
        )


def test_property_example_requires_text() -> None:
    with pytest.raises(ValidationError, match="requires `text`"):
        Property(name="ex", kind=PropertyKind.EXAMPLE)


def test_property_idempotent_does_not_require_text() -> None:
    p = Property(name="idem", kind=PropertyKind.IDEMPOTENT)
    assert p.text is None


def test_property_name_rejects_bad_identifier() -> None:
    with pytest.raises(ValidationError):
        Property(name="1bad", kind=PropertyKind.IDEMPOTENT)


def test_expression_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        Expression(text="   ")


def test_expression_strips_text() -> None:
    e = Expression(text="  x > 0  ")
    assert e.text == "x > 0"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("O(1)", ComplexityClass.O_1),
        ("o(1)", ComplexityClass.O_1),
        ("O(n)", ComplexityClass.O_N),
        ("O(n log n)", ComplexityClass.O_N_LOG_N),
        ("O(nlogn)", ComplexityClass.O_N_LOG_N),
        ("O(n^2)", ComplexityClass.O_N_SQUARED),
        ("O(n**2)", ComplexityClass.O_N_SQUARED),
        ("O(2^n)", ComplexityClass.O_2_N),
    ],
)
def test_complexity_mapping(text: str, expected: ComplexityClass) -> None:
    c = Complexity.from_text(text)
    assert c.klass == expected


def test_unknown_complexity_is_carried_but_unclassified() -> None:
    c = Complexity.from_text("O(n log log n)")
    assert c.raw == "O(n log log n)"
    assert c.klass is None


def test_full_example_spec() -> None:
    spec = Spec(
        module="max",
        functions={
            "max_of": FunctionSpec(
                signature=Signature.parse("max_of(xs: List[int]) -> int"),
                requires=(Expression(text="len(xs) > 0"),),
                ensures=(
                    Expression(text="result in xs"),
                    Expression(text="forall y in xs: result >= y"),
                ),
                complexity=Complexity.from_text("O(n)"),
                properties=(
                    Property(
                        name="idempotent",
                        kind=PropertyKind.EXAMPLE,
                        text="max_of([x]) == x",
                    ),
                ),
            )
        },
    )
    fn = spec.functions["max_of"]
    assert len(fn.requires) == 1
    assert fn.complexity is not None
    assert fn.complexity.klass == ComplexityClass.O_N
