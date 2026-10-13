"""Tests for the Source abstraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from warrant.parser.errors import SpecLoadError
from warrant.parser.source import Source, lookup_path


def test_from_string_ok() -> None:
    source = Source.from_string("module: m\n", file=Path("x.yaml"))
    assert isinstance(source, Source)
    assert source.file == Path("x.yaml")
    assert source.root == {"module": "m"}


def test_from_string_empty_returns_error() -> None:
    result = Source.from_string("", file=Path("x.yaml"))
    assert isinstance(result, SpecLoadError)
    assert "empty" in result.message


def test_line_at_is_1_based() -> None:
    source = Source.from_string("a: 1\nb: 2\nc: 3\n")
    assert isinstance(source, Source)
    assert source.line_at(1) == "a: 1"
    assert source.line_at(3) == "c: 3"
    assert source.line_at(99) == ""


def test_lookup_path_finds_nested() -> None:
    source = Source.from_string(
        "module: m\nfunctions:\n  f:\n    signature: 'f(x: int) -> int'\n"
    )
    assert isinstance(source, Source)
    node, line, _col = lookup_path(source.root, ("functions", "f", "signature"))
    assert node == "f(x: int) -> int"
    assert line >= 4  # signature is on line 4


def test_lookup_path_stops_at_missing() -> None:
    source = Source.from_string("module: m\n")
    assert isinstance(source, Source)
    _node, line, _col = lookup_path(source.root, ("functions", "f", "signature"))
    # Path doesn't exist; we still get a position (near module)
    assert line >= 1
