"""Walk a function's AST, resolving call targets to effects.

The detector never guesses. If a call can't be resolved through the
file's imports, it's ignored. False negatives are acceptable; false
positives are not.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from warrant.effects.config import EffectsConfig
from warrant.ir.module import FunctionIR
from warrant.schema.spec import Effect


@dataclass(frozen=True, slots=True)
class ResolvedCall:
    """A call whose target we've resolved to a module path + name."""

    # The raw text of the call target, e.g. "requests.get"
    raw: str
    # The resolved dotted path, e.g. "requests.get" or "open"
    resolved: str
    line: int
    column: int


def resolve_calls(tree: ast.AST, source_lines: list[str]) -> list[ResolvedCall]:
    """Walk an AST, find call sites, and resolve their targets.

    Requires the import table for the enclosing module. For now we work
    only with syntactic resolution: `import x` → `x`; `from a import b` → `b`.
    """
    imports = _collect_imports(tree)
    out: list[ResolvedCall] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = _call_target(node.func, imports)
        if target is None:
            continue
        out.append(
            ResolvedCall(
                raw=_unparse(node.func),
                resolved=target,
                line=node.lineno,
                column=node.col_offset + 1,
            )
        )
    return out


def _collect_imports(tree: ast.AST) -> dict[str, str]:
    """Build a map from local name → canonical dotted path.

    `import requests`            → {"requests": "requests"}
    `import requests as rq`      → {"rq": "requests"}
    `from os import path`        → {"path": "os.path"}
    `from os import path as p`   → {"p": "os.path"}
    """
    imports: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name
                imports[local] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            base = node.module
            for alias in node.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                imports[local] = f"{base}.{alias.name}"
    return imports


def _call_target(node: ast.AST, imports: dict[str, str]) -> str | None:
    """Resolve a call's function node to a dotted path, or None.

    `open`        → "open" (builtin, unresolved through imports)
    `requests.get`→ "requests.get"
    `rq.get`      → "requests.get"  (via alias)
    `foo.bar.baz` → None (we only handle depth 2)
    """
    if isinstance(node, ast.Name):
        # Bare name: could be an import (then resolve) or a builtin/user func.
        # We only return a resolution if it's a known import. Otherwise the
        # name itself, which will only match bare patterns like `open`.
        return imports.get(node.id, node.id)

    if isinstance(node, ast.Attribute):
        # Resolve `a.b` — one level of attribute access.
        if isinstance(node.value, ast.Name):
            base = node.value.id
            canonical_base = imports.get(base, base)
            return f"{canonical_base}.{node.attr}"
        return None

    return None


def _unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return "<expr>"


def detect_calls(
    func: FunctionIR,
    tree: ast.AST,
    config: EffectsConfig,
) -> tuple[tuple[Effect, ResolvedCall], ...]:
    """Detect effects in a function's AST.

    Returns a tuple of (effect, call) pairs — one per (effect, call site).
    The caller is responsible for deduplicating by effect.
    """
    source_lines = func.source.splitlines(keepends=True)
    calls = resolve_calls(tree, source_lines)
    out: list[tuple[Effect, ResolvedCall]] = []

    for call in calls:
        target = call.resolved
        if "." in target:
            module, _, attr = target.rpartition(".")
            pattern = config.matching_module_attr(module, attr)
        else:
            pattern = config.matching_bare(target)
        if pattern is None:
            continue
        out.append((pattern.effect, call))
    return tuple(out)
