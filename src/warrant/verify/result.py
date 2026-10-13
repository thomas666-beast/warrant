"""Result types produced by verification.

Every level (L1 static, L2 property, L3 SMT) returns findings with the
same shape. The CLI renders them; nothing else prints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from warrant.schema.spec import Spec


class Severity(StrEnum):
    """How seriously to take a finding."""

    ERROR = "error"  # verification failed; exit 1
    WARNING = "warning"  # something suspicious; exit 0
    INFO = "info"  # informational; exit 0


@dataclass(frozen=True, slots=True)
class Finding:
    """A single problem (or note) about the implementation.

    `function` is the name of the spec function this finding is about.
    `location` is an optional (file, line, column) tuple pointing at the
    implementation. `hint` is an optional suggestion for fixing it.
    """

    severity: Severity
    function: str
    message: str
    location: tuple[Path, int, int | None] | None = None
    hint: str | None = None


@dataclass(frozen=True, slots=True)
class VerifyResult:
    """The outcome of running verification on one spec/impl pair."""

    spec: Spec
    impl_path: Path
    level: int
    findings: tuple[Finding, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        """True iff no ERROR-level findings."""
        return not any(f.severity is Severity.ERROR for f in self.findings)

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.ERROR)

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.WARNING)
