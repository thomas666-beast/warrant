"""Tests for VerifyResult and Finding."""

from __future__ import annotations

from pathlib import Path

from warrant.schema.spec import FunctionSpec, Signature, Spec
from warrant.verify.result import Finding, Severity, VerifyResult


def _spec() -> Spec:
    return Spec(
        module="m",
        functions={"f": FunctionSpec(signature=Signature.parse("f(x: int) -> int"))},
    )


def test_empty_result_is_ok() -> None:
    r = VerifyResult(spec=_spec(), impl_path=Path("m.py"), level=1)
    assert r.ok
    assert r.errors == ()
    assert r.warnings == ()


def test_error_result_is_not_ok() -> None:
    r = VerifyResult(
        spec=_spec(),
        impl_path=Path("m.py"),
        level=1,
        findings=(
            Finding(severity=Severity.ERROR, function="f", message="bad"),
        ),
    )
    assert not r.ok
    assert len(r.errors) == 1


def test_warning_does_not_fail() -> None:
    r = VerifyResult(
        spec=_spec(),
        impl_path=Path("m.py"),
        level=1,
        findings=(
            Finding(severity=Severity.WARNING, function="f", message="meh"),
        ),
    )
    assert r.ok
    assert len(r.warnings) == 1


def test_info_does_not_fail() -> None:
    r = VerifyResult(
        spec=_spec(),
        impl_path=Path("m.py"),
        level=1,
        findings=(Finding(severity=Severity.INFO, function="f", message="fyi"),),
    )
    assert r.ok
