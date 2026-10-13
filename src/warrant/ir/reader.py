"""The Python adapter: read a .py file into an IR.

This is pure parsing. We never import or execute the module under test.
"""

from __future__ import annotations

import ast
from pathlib import Path

from warrant.ir.module import FunctionIR, ModuleIR, ParameterIR


class ReadError(Exception):
    """Raised when the implementation file cannot be read at all.

    This is distinct from "the function you wanted isn't in here" —
    that's a verification finding, not a read error.
    """

    def __init__(self, message: str, *, file: Path, line: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.file = file
        self.line = line


def read_module(path: str | Path) -> ModuleIR:
    """Parse a Python file into a `ModuleIR`. Raises `ReadError` on failure.

    The only reasons `ReadError` is raised:
      - file doesn't exist
      - file isn't valid UTF-8
      - file isn't valid Python (SyntaxError)
    Everything else (missing functions, wrong arity) is a finding downstream.
    """
    p = Path(path)
    if not p.exists():
        raise ReadError("file not found", file=p)
    if not p.is_file():
        raise ReadError("not a file", file=p)

    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ReadError(f"file is not valid UTF-8: {e.reason}", file=p) from e
    except OSError as e:
        raise ReadError(f"could not read file: {e.strerror}", file=p) from e

    try:
        tree = ast.parse(text, filename=str(p))
    except SyntaxError as e:
        raise ReadError(
            f"syntax error: {e.msg}",
            file=p,
            line=e.lineno,
        ) from e

    lines = text.splitlines(keepends=True)
    functions = _collect_functions(tree, lines)
    return ModuleIR(path=p, functions=functions, source=text)


def _collect_functions(
    tree: ast.Module, lines: list[str]
) -> dict[str, FunctionIR]:
    """Walk top-level statements collecting function definitions.

    Nested functions and methods are ignored for now — we'll add class
    and method support in a later task.
    """
    functions: dict[str, FunctionIR] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = _build_function_ir(node, lines, prefix="")
            functions[fn.name] = fn
    return functions


def _build_function_ir(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    lines: list[str],
    prefix: str,
) -> FunctionIR:
    """Convert an ast function node into our IR."""
    name = node.name
    qualified = f"{prefix}{name}" if not prefix else f"{prefix}.{name}"

    # Parameters
    params: list[ParameterIR] = []
    args = node.args

    # Positional-only, then positional-or-keyword, then keyword-only.
    # Defaults apply to the LAST len(defaults) elements of (posonly + args).
    all_pos = list(args.posonlyargs) + list(args.args)
    n_defaults = len(args.defaults)
    first_default_idx = len(all_pos) - n_defaults

    for i, arg in enumerate(all_pos):
        params.append(
            ParameterIR(
                name=arg.arg,
                annotation=_unparse(arg.annotation),
                has_default=i >= first_default_idx,
            )
        )

    if args.vararg is not None:
        params.append(
            ParameterIR(
                name=f"*{args.vararg.arg}",
                annotation=_unparse(args.vararg.annotation),
                has_default=False,
            )
        )

    for i, arg in enumerate(args.kwonlyargs):
        params.append(
            ParameterIR(
                name=arg.arg,
                annotation=_unparse(arg.annotation),
                has_default=args.kw_defaults[i] is not None,
            )
        )

    if args.kwarg is not None:
        params.append(
            ParameterIR(
                name=f"**{args.kwarg.arg}",
                annotation=_unparse(args.kwarg.annotation),
                has_default=False,
            )
        )

    # Return annotation
    return_annotation = _unparse(node.returns)

    # Decorators — record by name
    decorators: list[str] = []
    for dec in node.decorator_list:
        dname = _decorator_name(dec)
        if dname is not None:
            decorators.append(dname)

    # Source range: `lineno` is the `def` keyword line in modern Python.
    # `end_lineno` is the last line of the body.
    start_line = node.lineno
    end_line = node.end_lineno if node.end_lineno is not None else start_line

    # Column: ast uses 0-based columns. We report 1-based.
    column = node.col_offset + 1

    source = "".join(lines[start_line - 1 : end_line])

    return FunctionIR(
        name=name,
        qualified_name=qualified,
        parameters=tuple(params),
        return_annotation=return_annotation,
        line=start_line,
        column=column,
        end_line=end_line,
        source=source,
        decorators=tuple(decorators),
    )


def _unparse(node: ast.AST | None) -> str | None:
    """Convert an annotation node back to source text, or None."""
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _decorator_name(node: ast.AST) -> str | None:
    """Best-effort name for a decorator node.

    Handles: @foo, @foo.bar, @foo(...), @foo.bar(...)
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _decorator_name(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return None
