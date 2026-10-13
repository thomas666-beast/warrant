"""Tests for call resolution and effect detection."""

from __future__ import annotations

import ast
from pathlib import Path

from warrant.effects import detect_calls, load_default_config, resolve_calls
from warrant.ir.module import FunctionIR, ParameterIR
from warrant.schema.spec import Effect


def _fn(source: str) -> FunctionIR:
    return FunctionIR(
        name="f",
        qualified_name="f",
        parameters=(),
        return_annotation=None,
        line=1,
        column=1,
        end_line=len(source.splitlines()),
        source=source,
    )


def _detect(source: str) -> set[Effect]:
    tree = ast.parse(source)
    fn = _fn(source)
    cfg = load_default_config()
    results = detect_calls(fn, tree, cfg)
    return {effect for effect, _call in results}


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def test_resolve_bare_name() -> None:
    tree = ast.parse("open('x')")
    calls = resolve_calls(tree, [])
    assert calls[0].resolved == "open"


def test_resolve_imported_name() -> None:
    tree = ast.parse("import requests\nrequests.get('x')")
    calls = resolve_calls(tree, [])
    assert calls[0].resolved == "requests.get"


def test_resolve_aliased_import() -> None:
    tree = ast.parse("import requests as rq\nrq.get('x')")
    calls = resolve_calls(tree, [])
    assert calls[0].resolved == "requests.get"


def test_resolve_from_import() -> None:
    tree = ast.parse("from os import path\npath.exists('x')")
    calls = resolve_calls(tree, [])
    assert calls[0].resolved == "os.path.exists"


def test_resolve_nested_attribute_returns_none() -> None:
    tree = ast.parse("import a\na.b.c()")
    calls = resolve_calls(tree, [])
    # We only handle depth 2; `a.b.c` should not appear
    assert all(c.resolved != "a.b.c" for c in calls)


# ---------------------------------------------------------------------------
# Effect detection
# ---------------------------------------------------------------------------


def test_detect_open() -> None:
    assert _detect("def f():\n    open('x')\n") == {Effect.READ_FS}


def test_detect_requests() -> None:
    assert _detect("import requests\ndef f():\n    requests.get('x')\n") == {
        Effect.NETWORK
    }


def test_detect_socket() -> None:
    assert _detect("import socket\ndef f():\n    socket.socket()\n") == {
        Effect.NETWORK
    }


def test_detect_time() -> None:
    assert _detect("import time\ndef f():\n    time.time()\n") == {Effect.CLOCK}


def test_detect_multiple() -> None:
    src = "import requests\nimport time\ndef f():\n    requests.get('x')\n    time.time()\n"
    assert _detect(src) == {Effect.NETWORK, Effect.CLOCK}


def test_unknown_call_ignored() -> None:
    assert _detect("def f():\n    my_func()\n") == set()


def test_shadowed_builtin_ignored() -> None:
    # A user-defined `open` should not trigger read_fs
    src = "from mylib import open\ndef f():\n    open('x')\n"
    # The resolver maps `open` → `mylib.open`, which has no pattern.
    assert _detect(src) == set()


def test_print_not_an_effect() -> None:
    assert _detect("def f():\n    print('hi')\n") == set()
