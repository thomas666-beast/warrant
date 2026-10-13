"""Tests for the Python adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from warrant.ir import ReadError, read_module


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content)
    return p


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_reads_simple_function(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "m.py",
        "def f(x: int) -> int:\n    return x\n",
    )
    mod = read_module(p)
    assert set(mod.functions) == {"f"}
    fn = mod.functions["f"]
    assert fn.name == "f"
    assert fn.return_annotation == "int"
    assert len(fn.parameters) == 1
    assert fn.parameters[0].name == "x"
    assert fn.parameters[0].annotation == "int"
    assert fn.parameters[0].has_default is False
    assert fn.line == 1
    assert fn.end_line == 2
    assert "return x" in fn.source


def test_reads_multiple_functions(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "m.py",
        "def a() -> int:\n    return 1\n\ndef b() -> str:\n    return 'x'\n",
    )
    mod = read_module(p)
    assert set(mod.functions) == {"a", "b"}
    assert mod.functions["a"].line == 1
    assert mod.functions["b"].line == 4


def test_reads_function_with_defaults(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "m.py",
        "def greet(name: str, greeting: str = 'hi') -> str:\n    return greeting\n",
    )
    mod = read_module(p)
    fn = mod.functions["greet"]
    assert fn.parameters[0].has_default is False
    assert fn.parameters[1].has_default is True


def test_reads_kwonly_args(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "m.py",
        "def f(*, x: int, y: int = 0) -> int:\n    return x + y\n",
    )
    mod = read_module(p)
    fn = mod.functions["f"]
    names = [p.name for p in fn.parameters]
    assert names == ["x", "y"]
    assert fn.parameters[0].has_default is False
    assert fn.parameters[1].has_default is True


def test_reads_varargs(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "m.py",
        "def f(*args: int, **kwargs: str) -> None:\n    pass\n",
    )
    mod = read_module(p)
    fn = mod.functions["f"]
    names = [p.name for p in fn.parameters]
    assert names == ["*args", "**kwargs"]


def test_reads_async_functions(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "m.py",
        "async def fetch(url: str) -> bytes:\n    return b''\n",
    )
    mod = read_module(p)
    assert "fetch" in mod.functions
    assert mod.functions["fetch"].return_annotation == "bytes"


def test_no_annotation_gives_none(tmp_path: Path) -> None:
    p = _write(tmp_path, "m.py", "def f(x):\n    return x\n")
    mod = read_module(p)
    fn = mod.functions["f"]
    assert fn.parameters[0].annotation is None
    assert fn.return_annotation is None


def test_decorators_recorded(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "m.py",
        "import functools\n\n@functools.cache\ndef f(x: int) -> int:\n    return x\n",
    )
    mod = read_module(p)
    fn = mod.functions["f"]
    assert "functools.cache" in fn.decorators


def test_function_with_no_functions(tmp_path: Path) -> None:
    p = _write(tmp_path, "m.py", "x = 1\n")
    mod = read_module(p)
    assert mod.functions == {}


def test_nested_function_not_collected(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "m.py",
        "def outer():\n    def inner():\n        pass\n    return inner\n",
    )
    mod = read_module(p)
    assert set(mod.functions) == {"outer"}


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ReadError) as exc_info:
        read_module(tmp_path / "nope.py")
    assert "not found" in exc_info.value.message
    assert exc_info.value.file == tmp_path / "nope.py"


def test_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(ReadError) as exc_info:
        read_module(tmp_path)
    assert "not a file" in exc_info.value.message


def test_syntax_error_reports_line(tmp_path: Path) -> None:
    p = _write(tmp_path, "m.py", "def f(:\n    pass\n")
    with pytest.raises(ReadError) as exc_info:
        read_module(p)
    assert "syntax error" in exc_info.value.message
    assert exc_info.value.line == 1


# ---------------------------------------------------------------------------
# The real example
# ---------------------------------------------------------------------------


def test_read_example_max() -> None:
    root = Path(__file__).resolve().parents[2]
    impl = root / "examples" / "max" / "src" / "max.py"
    assert impl.exists()
    mod = read_module(impl)
    assert "max_of" in mod.functions
    fn = mod.functions["max_of"]
    assert fn.return_annotation == "int"
    assert [p.name for p in fn.parameters] == ["xs"]
    assert "for x in xs[1:]" in fn.source
