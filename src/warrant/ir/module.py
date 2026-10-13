"""The IR: what a language adapter produces after reading an implementation.

Downstream code (effect analysis, level checkers, reporters) consumes
these objects and nothing else. The Python-specific AST stops at the
adapter boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ParameterIR:
    """A function parameter as declared in the implementation."""

    name: str
    annotation: str | None
    has_default: bool


@dataclass(frozen=True, slots=True)
class FunctionIR:
    """One function from the implementation module.

    `source` is the full text of the function as it appears in the file,
    including the `def` line and any decorators. This is what the reporter
    draws code frames from.
    """

    name: str
    qualified_name: str
    parameters: tuple[ParameterIR, ...]
    return_annotation: str | None
    # 1-based line, 1-based column of the `def` keyword
    line: int
    column: int
    # Inclusive line range of the entire function body
    end_line: int
    source: str
    # Decorator names, in order, e.g. ["staticmethod", "cached"]
    decorators: tuple[str, ...] = field(default_factory=tuple)
    # Filled in later by the effect analysis (Task 6)
    calls: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ModuleIR:
    """Everything we know about one implementation file."""

    path: Path
    functions: dict[str, FunctionIR]
    # Top-level source text, useful for line lookups
    source: str

    def get(self, name: str) -> FunctionIR | None:
        return self.functions.get(name)

    def function_names(self) -> tuple[str, ...]:
        return tuple(self.functions.keys())
