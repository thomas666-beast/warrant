"""The core spec schema.

Everything downstream (loader, adapters, levels, reporter) reads these models.
They are frozen: once a spec is loaded, it never mutates.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from warrant.schema.types import (
    TypeExpr,
    parse_type,
)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Effect(StrEnum):
    """Effects a function may have on the world.

    Closed set for the MVP. Unknown effects are rejected at parse time so
    that L1 static analysis has a tractable, well-defined target. We'll add
    a `custom:` escape hatch once we have a real user asking for it.
    """

    READ_FS = "read_fs"
    WRITE_FS = "write_fs"
    NETWORK = "network"
    READ_DB = "read_db"
    WRITE_DB = "write_db"
    EMIT_EVENT = "emit_event"
    CLOCK = "clock"
    RANDOM = "random"
    SPAWN = "spawn"


class PropertyKind(StrEnum):
    """How the verifier should check a property."""

    EXAMPLE = "example"  # A concrete example: f([1,2,3]) == 3
    INVARIANT = "invariant"  # A predicate that must hold: max_of(shuffle(xs)) == max_of(xs)
    IDEMPOTENT = "idempotent"  # f(f(x)) == f(x)
    COMMUTATIVE = "commutative"  # f(a, b) == f(b, a)


class ComplexityClass(StrEnum):
    """Big-O classes we understand well enough to reason about."""

    O_1 = "O(1)"
    O_LOG_N = "O(log n)"
    O_N = "O(n)"
    O_N_LOG_N = "O(n log n)"
    O_N_SQUARED = "O(n^2)"
    O_2_N = "O(2^n)"
    O_N_FACTORIAL = "O(n!)"


# ---------------------------------------------------------------------------
# Signature
# ---------------------------------------------------------------------------

_SIGNATURE_RE = re.compile(
    r"""
    ^\s*
    (?P<name>[A-Za-z_][A-Za-z0-9_]*)
    \s*\(\s*
    (?P<params>.*?)
    \s*\)\s*
    ->\s*
    (?P<returns>.+?)
    \s*$
    """,
    re.VERBOSE | re.DOTALL,
)


class Parameter(BaseModel):
    """A single parameter: `name: TypeExpr`, optionally with a default."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    type: TypeExpr
    has_default: bool = False

    @field_validator("name")
    @classmethod
    def _name_is_identifier(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError(f"parameter name {v!r} is not a valid identifier")
        return v


class Signature(BaseModel):
    """A parsed function signature.

    We store the original text so error messages can quote it exactly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    raw: str
    name: str
    parameters: tuple[Parameter, ...]
    returns: TypeExpr

    @classmethod
    def parse(cls, text: str) -> Signature:
        """Parse `name(a: T, b: U) -> R`. Raises ValueError with a helpful
        message on malformed input."""
        match = _SIGNATURE_RE.match(text)
        if not match:
            raise ValueError(
                f"invalid signature: {text!r}. Expected 'name(param: Type, ...) -> ReturnType'."
            )

        name = match.group("name")
        params_text = match.group("params").strip()
        returns_text = match.group("returns").strip()

        parameters = _parse_parameters(params_text)
        returns = parse_type(returns_text)

        return cls(raw=text.strip(), name=name, parameters=parameters, returns=returns)


def _parse_parameters(text: str) -> tuple[Parameter, ...]:
    """Parse a comma-separated parameter list, respecting nested brackets
    and treating `= default` as a suffix."""
    if not text:
        return ()

    parts = _split_top_level_params(text)
    params: list[Parameter] = []
    seen: set[str] = set()

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Split off default value: `x: int = 5`
        has_default = False
        if "=" in part:
            part, _default = part.split("=", 1)
            part = part.strip()
            has_default = True

        if ":" not in part:
            raise ValueError(f"parameter {part!r} is missing a type annotation")

        pname, ptype = part.split(":", 1)
        pname = pname.strip()
        ptype = ptype.strip()

        if not pname:
            raise ValueError(f"parameter in {part!r} has no name")

        if pname in seen:
            raise ValueError(f"duplicate parameter name {pname!r}")
        seen.add(pname)

        params.append(Parameter(name=pname, type=parse_type(ptype), has_default=has_default))

    return tuple(params)


def _split_top_level_params(text: str) -> list[str]:
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
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


# ---------------------------------------------------------------------------
# Expression (carried as text for now)
# ---------------------------------------------------------------------------


class Expression(BaseModel):
    """A predicate written in the spec language.

    Stored as text with optional source location for error reporting.
    Parsed downstream (Tasks 7, 9, 11). The schema only carries it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    line: int | None = None

    @field_validator("text")
    @classmethod
    def _not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("expression text is empty")
        return v


# ---------------------------------------------------------------------------
# Property
# ---------------------------------------------------------------------------


class Property(BaseModel):
    """A named, checkable claim about a function's behavior."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    kind: PropertyKind
    text: str | None = None
    # For EXAMPLE: expression giving the expected value
    # For INVARIANT: an expression that must be True
    # For IDEMPOTENT / COMMUTATIVE: unused

    @field_validator("name")
    @classmethod
    def _name_ok(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("property name is empty")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v):
            raise ValueError(
                f"property name {v!r} must be a valid identifier "
                f"(letters, digits, underscores; not starting with a digit)"
            )
        return v

    @model_validator(mode="after")
    def _check_text_for_kind(self) -> Property:
        if self.kind in (PropertyKind.EXAMPLE, PropertyKind.INVARIANT) and not self.text:
            raise ValueError(f"property {self.name!r} of kind {self.kind.value!r} requires `text`")
        return self


# ---------------------------------------------------------------------------
# Complexity
# ---------------------------------------------------------------------------


class Complexity(BaseModel):
    """A complexity claim. `raw` is what the user wrote; `klass` is our
    best structured guess (None if we didn't recognize it)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    raw: str
    klass: ComplexityClass | None = None

    @field_validator("raw")
    @classmethod
    def _normalize(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("complexity string is empty")
        return v

    @classmethod
    def from_text(cls, text: str) -> Complexity:
        raw = text.strip()
        # Normalize whitespace and casing for matching
        canonical = re.sub(r"\s+", " ", raw.lower().replace(" ", ""))
        # Try to map to a known class; unknown → klass=None
        mapping = {
            "o(1)": ComplexityClass.O_1,
            "o(logn)": ComplexityClass.O_LOG_N,
            "o(n)": ComplexityClass.O_N,
            "o(nlogn)": ComplexityClass.O_N_LOG_N,
            "o(n^2)": ComplexityClass.O_N_SQUARED,
            "o(n**2)": ComplexityClass.O_N_SQUARED,
            "o(2^n)": ComplexityClass.O_2_N,
            "o(2**n)": ComplexityClass.O_2_N,
            "o(n!)": ComplexityClass.O_N_FACTORIAL,
        }
        return cls(raw=raw, klass=mapping.get(canonical))


# ---------------------------------------------------------------------------
# FunctionSpec
# ---------------------------------------------------------------------------


class FunctionSpec(BaseModel):
    """Everything we know about one function under verification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    signature: Signature
    requires: tuple[Expression, ...] = ()
    ensures: tuple[Expression, ...] = ()
    invariants: tuple[Expression, ...] = ()
    effects: frozenset[Effect] = frozenset()
    complexity: Complexity | None = None
    properties: tuple[Property, ...] = ()

    @model_validator(mode="after")
    def _property_names_unique(self) -> FunctionSpec:
        names = [p.name for p in self.properties]
        if len(names) != len(set(names)):
            dupes = sorted({n for n in names if names.count(n) > 1})
            raise ValueError(f"duplicate property names: {dupes}")
        return self


# ---------------------------------------------------------------------------
# Spec (top-level)
# ---------------------------------------------------------------------------


class Spec(BaseModel):
    """A warrant spec file: a module name and the functions it declares."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    module: str
    functions: dict[str, FunctionSpec]

    @field_validator("module")
    @classmethod
    def _module_ok(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("module name is empty")
        return v

    @field_validator("functions")
    @classmethod
    def _functions_nonempty(cls, v: dict[str, FunctionSpec]) -> dict[str, FunctionSpec]:
        if not v:
            raise ValueError("spec declares no functions")
        return v

    @model_validator(mode="after")
    def _keys_match_signature_names(self) -> Spec:
        for key, fn in self.functions.items():
            if key != fn.signature.name:
                raise ValueError(
                    f"function key {key!r} does not match signature name {fn.signature.name!r}"
                )
        return self
