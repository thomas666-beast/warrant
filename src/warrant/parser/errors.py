"""Structured errors for spec loading.

The loader never raises on user input — it returns `Spec | SpecLoadError`.
This module defines the error type and its rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SpecLoadError:
    """A failure to load a spec file, with location info for reporting.

    `path` is a dotted key path into the YAML tree, e.g.
    `("functions", "max_of", "signature")`. Empty tuple means the error
    applies to the whole file.
    """

    message: str
    file: Path
    line: int | None = None
    column: int | None = None
    path: tuple[str, ...] = field(default_factory=tuple)
    hint: str | None = None

    def location(self) -> str:
        """Human-readable location string: `spec.yaml:12:5`."""
        parts = [str(self.file)]
        if self.line is not None:
            parts.append(str(self.line))
            if self.column is not None:
                parts.append(str(self.column))
        return ":".join(parts)

    def path_str(self) -> str:
        """Dotted path string, or empty if the error is top-level."""
        if not self.path:
            return ""
        return ".".join(self.path)

    def render(self) -> str:
        """A plain-text rendering. Task 8 will produce a rich version."""
        lines = [f"{self.location()}: {self.message}"]
        if self.path:
            lines.append(f"  at: {self.path_str()}")
        if self.hint:
            lines.append(f"  hint: {self.hint}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.render()
