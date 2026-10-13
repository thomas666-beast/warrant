"""A minimal type-expression parser.

We do NOT need a full type system here. We need enough structure to:
  - Recognize `List[int]`, `Optional[str]`, `Dict[str, int]`
  - Know whether a type is a primitive (`int`, `str`, `bool`, `float`)
  - Preserve unknown types verbatim so we don't reject valid specs

The parser is deliberately small. Anything we can't parse becomes `OpaqueType`
with the original string preserved — never an error.
"""

from __future__ import annotations

from dataclasses import dataclass

PRIMITIVES: frozenset[str] = frozenset({"int", "str", "bool", "float", "bytes", "None"})


@dataclass(frozen=True, slots=True)
class PrimitiveType:
    name: str  # "int", "str", ...


@dataclass(frozen=True, slots=True)
class ListType:
    element: TypeExpr


@dataclass(frozen=True, slots=True)
class DictType:
    key: TypeExpr
    value: TypeExpr


@dataclass(frozen=True, slots=True)
class OptionalType:
    inner: TypeExpr


@dataclass(frozen=True, slots=True)
class OpaqueType:
    """A type we couldn't parse. Preserved verbatim, never rejected."""

    text: str


TypeExpr = PrimitiveType | ListType | DictType | OptionalType | OpaqueType


class TypeParseError(ValueError):
    """Raised only for internal invariant violations — not for user input."""


def parse_type(text: str) -> TypeExpr:
    """Parse a type expression. Never raises for user input.

    Unknown or malformed types become `OpaqueType` with the original text.
    """
    text = text.strip()
    if not text:
        return OpaqueType(text="")

    if text in PRIMITIVES:
        return PrimitiveType(name=text)

    if text.startswith("Optional[") and text.endswith("]"):
        inner_text = text[len("Optional[") : -1]
        return OptionalType(inner=parse_type(inner_text))

    if text.startswith("List[") and text.endswith("]"):
        inner_text = text[len("List[") : -1]
        return ListType(element=parse_type(inner_text))

    if text.startswith("Dict[") and text.endswith("]"):
        inner_text = text[len("Dict[") : -1]
        key, value = _split_top_level(inner_text, expected=2)
        if key is None or value is None:
            return OpaqueType(text=text)
        return DictType(key=parse_type(key), value=parse_type(value))

    return OpaqueType(text=text)


def _split_top_level(text: str, expected: int) -> tuple[str | None, ...]:
    """Split `a, b` at the top level (ignoring nested brackets). Returns
    a tuple of length `expected`, with `None` for any missing parts."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch in "[(":
            depth += 1
            current.append(ch)
        elif ch in "])":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())

    if len(parts) != expected:
        return tuple([None] * expected)
    return tuple(parts)
