"""Turn a YAML document into a `Spec`, with errors that point at the source.

The flow:
  1. Load YAML into a `Source` (preserves line/col).
  2. Walk the raw tree, extracting known keys and rejecting unknown ones
     with a helpful message that names the offending key and its line.
  3. Hand a clean dict to pydantic's `Spec.model_validate`.
  4. Translate any `ValidationError` back into a `SpecLoadError` with the
     YAML location of the offending path.

The loader never raises on user input. It returns `Spec | SpecLoadError`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from warrant.parser.errors import SpecLoadError
from warrant.parser.source import Source, lookup_path, node_col, node_line
from warrant.schema.spec import Spec

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_spec(path: str | Path) -> Spec | SpecLoadError:
    """Load a `.warrant.yaml` file into a `Spec`, or return a structured error."""
    p = Path(path)
    source = Source.from_file(p)
    if isinstance(source, SpecLoadError):
        return source
    return load_spec_from_source(source)


def load_spec_from_string(
    text: str, *, file: str | Path = "<string>"
) -> Spec | SpecLoadError:
    """Load a spec from a string. Useful for tests and programmatic use."""
    source = Source.from_string(text, file=Path(file))
    if isinstance(source, SpecLoadError):
        return source
    return load_spec_from_source(source)


def load_spec_from_source(source: Source) -> Spec | SpecLoadError:
    """Load a spec from an already-parsed `Source`."""
    raw = _extract_raw_dict(source)
    if isinstance(raw, SpecLoadError):
        return raw

    try:
        return Spec.model_validate(raw)
    except ValidationError as e:
        return _translate_validation_error(e, source)


# ---------------------------------------------------------------------------
# Raw tree extraction: walk YAML, reject unknown keys, build a plain dict
# ---------------------------------------------------------------------------

_TOP_LEVEL_KEYS = {"module", "functions"}

_FUNCTION_KEYS = {
    "signature",
    "requires",
    "ensures",
    "invariants",
    "effects",
    "complexity",
    "properties",
}

_PROPERTY_KEYS = {"name", "kind", "text"}


def _extract_raw_dict(source: Source) -> dict[str, Any] | SpecLoadError:
    root = source.root
    assert isinstance(root, dict)  # guaranteed by Source.from_string

    # Reject unknown top-level keys
    for key in root:
        if not isinstance(key, str):
            return SpecLoadError(
                message=f"top-level key must be a string, got {type(key).__name__}",
                file=source.file,
                line=node_line(root),
                column=node_col(root),
            )
        if key not in _TOP_LEVEL_KEYS:
            _, line, col = lookup_path(root, (key,))
            return SpecLoadError(
                message=f"unknown top-level key {key!r}",
                file=source.file,
                line=line,
                column=col,
                path=(key,),
                hint=f"allowed keys: {sorted(_TOP_LEVEL_KEYS)}",
            )

    if "module" not in root:
        return SpecLoadError(
            message="missing required key 'module'",
            file=source.file,
            line=node_line(root),
            column=node_col(root),
            hint="every spec declares the module it describes, e.g. `module: max`",
        )

    if "functions" not in root:
        return SpecLoadError(
            message="missing required key 'functions'",
            file=source.file,
            line=node_line(root),
            column=node_col(root),
            hint="a spec must declare at least one function",
        )

    functions_raw = root["functions"]
    if not isinstance(functions_raw, dict):
        _, line, col = lookup_path(root, ("functions",))
        return SpecLoadError(
            message="'functions' must be a mapping of name → function spec",
            file=source.file,
            line=line,
            column=col,
            path=("functions",),
        )

    functions: dict[str, Any] = {}
    for fname, fraw in functions_raw.items():
        if not isinstance(fname, str):
            return SpecLoadError(
                message=f"function name must be a string, got {type(fname).__name__}",
                file=source.file,
                line=node_line(functions_raw),
                column=node_col(functions_raw),
                path=("functions",),
            )
        if not isinstance(fraw, dict):
            _, line, col = lookup_path(root, ("functions", fname))
            return SpecLoadError(
                message=f"function {fname!r} must be a mapping",
                file=source.file,
                line=line,
                column=col,
                path=("functions", fname),
            )

        # Reject unknown function keys
        for key in fraw:
            if key not in _FUNCTION_KEYS:
                _, line, col = lookup_path(root, ("functions", fname, str(key)))
                return SpecLoadError(
                    message=f"unknown key {key!r} in function {fname!r}",
                    file=source.file,
                    line=line,
                    column=col,
                    path=("functions", fname, str(key)),
                    hint=f"allowed keys: {sorted(_FUNCTION_KEYS)}",
                )

        normalized = _normalize_function(fname, fraw, source)
        if isinstance(normalized, SpecLoadError):
            return normalized
        functions[fname] = normalized

    return {"module": root["module"], "functions": functions}


def _normalize_function(
    fname: str, fraw: dict[str, Any], source: Source
) -> dict[str, Any] | SpecLoadError:
    """Normalize one function's raw YAML into the shape pydantic expects."""
    from warrant.schema.spec import Signature

    out: dict[str, Any] = {}

    # signature: required, and must parse
    sig = fraw.get("signature")
    if sig is None:
        _, line, col = lookup_path(source.root, ("functions", fname))
        return SpecLoadError(
            message=f"function {fname!r} is missing required key 'signature'",
            file=source.file,
            line=line,
            column=col,
            path=("functions", fname, "signature"),
            hint='e.g. signature: "f(x: int) -> int"',
        )
    if not isinstance(sig, str):
        _, line, col = lookup_path(source.root, ("functions", fname, "signature"))
        return SpecLoadError(
            message=f"signature must be a string, got {type(sig).__name__}",
            file=source.file,
            line=line,
            column=col,
            path=("functions", fname, "signature"),
        )

    try:
        parsed_sig = Signature.parse(sig)
    except ValueError as e:
        _, line, col = lookup_path(source.root, ("functions", fname, "signature"))
        return SpecLoadError(
            message=f"invalid signature: {e}",
            file=source.file,
            line=line,
            column=col,
            path=("functions", fname, "signature"),
        )

    out["signature"] = parsed_sig

    # requires / ensures / invariants: list of strings → list of dicts
    for key in ("requires", "ensures", "invariants"):
        if key in fraw:
            value = fraw[key]
            if value is None:
                out[key] = []
            elif isinstance(value, list):
                out[key] = [
                    {"text": str(v), "line": _expr_line(source, fname, key, i)}
                    for i, v in enumerate(value)
                ]
            else:
                out[key] = value
        else:
            out[key] = []

    # effects
    if "effects" in fraw:
        value = fraw["effects"]
        out["effects"] = [] if value is None else value
    else:
        out["effects"] = []

    # complexity
    if "complexity" in fraw and fraw["complexity"] is not None:
        from warrant.schema.spec import Complexity

        out["complexity"] = Complexity.from_text(str(fraw["complexity"]))
    else:
        out["complexity"] = None

    # properties
    if "properties" in fraw and fraw["properties"] is not None:
        props = fraw["properties"]
        if isinstance(props, list):
            out["properties"] = [
                dict(prop) if isinstance(prop, dict) else prop for prop in props
            ]
        else:
            out["properties"] = props
    else:
        out["properties"] = []

    return out


def _expr_line(source: Source, fname: str, key: str, index: int) -> int:
    """Best-effort line for the Nth entry in a requires/ensures/invariants list."""
    _, line, _ = lookup_path(source.root, ("functions", fname, key))
    # ruamel gives us the line of the `requires:` key; entries follow.
    # Approximate: add the index (each entry is typically one line).
    return line + index + 1


# ---------------------------------------------------------------------------
# ValidationError → SpecLoadError
# ---------------------------------------------------------------------------


def _translate_validation_error(
    e: ValidationError, source: Source
) -> SpecLoadError:
    """Translate a pydantic ValidationError into the first (most relevant)
    SpecLoadError, with YAML location."""
    errors = e.errors()
    if not errors:
        return SpecLoadError(message="spec validation failed", file=source.file)

    # Prefer errors deeper in the tree — they're usually more specific.
    # Sort by path length descending, then take the first.
    first = max(errors, key=lambda err: len(err.get("loc", ())))

    loc = tuple(str(part) for part in first.get("loc", ()))
    message = first.get("msg", "validation failed")
    hint = _hint_for(first)

    node, line, col = lookup_path(source.root, loc)
    return SpecLoadError(
        message=message,
        file=source.file,
        line=line,
        column=col,
        path=loc,
        hint=hint,
    )


def _hint_for(err: ErrorDetails) -> str | None:
    """Attach a hint for common pydantic errors."""
    err_type = err.get("type", "")
    if err_type == "missing":
        field = err.get("loc", ("?",))[-1]
        return f"required field {field!r} is missing"
    if err_type == "extra_forbidden":
        field = err.get("loc", ("?",))[-1]
        return f"unknown field {field!r}"
    if err_type == "value_error":
        return None
    return None
