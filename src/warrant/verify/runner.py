"""The verify runner: load spec + impl, dispatch to a level, return result.

For Task 4, all three levels return an empty result (no findings). Tasks 5–11
will replace these stubs with real checks.
"""

from __future__ import annotations

from pathlib import Path

from warrant.schema.spec import Spec
from warrant.verify.result import Finding, VerifyResult


def verify_spec(spec: Spec, impl_path: Path, level: int) -> VerifyResult:
    """Run verification at the given level. Never raises on user input."""
    # Tasks 5–11 fill this in. For now, return an empty (passing) result.
    findings: tuple[Finding, ...] = ()
    return VerifyResult(spec=spec, impl_path=impl_path, level=level, findings=findings)
