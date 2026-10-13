"""The verify runner: load spec + impl, dispatch to a level, return result."""

from __future__ import annotations

from pathlib import Path

from warrant.ir import ReadError, read_module
from warrant.levels import check_level1
from warrant.schema.spec import Spec
from warrant.verify.result import Finding, Severity, VerifyResult


def verify_spec(spec: Spec, impl_path: Path, level: int) -> VerifyResult:
    """Run verification at the given level. Never raises on user input."""
    try:
        module = read_module(impl_path)
    except ReadError as e:
        return VerifyResult(
            spec=spec,
            impl_path=impl_path,
            level=level,
            findings=(
                Finding(
                    severity=Severity.ERROR,
                    function="<module>",
                    message=e.message,
                    location=(e.file, e.line, None) if e.line else None,
                ),
            ),
        )

    findings: list[Finding] = []

    if level >= 1:
        findings.extend(check_level1(spec, module))

    # Tasks 9 and 11 fill in levels 2 and 3.

    return VerifyResult(
        spec=spec,
        impl_path=impl_path,
        level=level,
        findings=tuple(findings),
    )
