"""Tests for the `warrant verify` command."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from warrant.cli import EXIT_OK, EXIT_USAGE, app

runner = CliRunner()

MINIMAL_SPEC = """
module: m
functions:
  f:
    signature: "f(x: int) -> int"
"""

MINIMAL_IMPL = """
def f(x: int) -> int:
    return x
"""


@pytest.fixture
def spec_file(tmp_path: Path) -> Path:
    p = tmp_path / "m.warrant.yaml"
    p.write_text(MINIMAL_SPEC)
    return p


@pytest.fixture
def impl_file(tmp_path: Path) -> Path:
    p = tmp_path / "m.py"
    p.write_text(MINIMAL_IMPL)
    return p


# ---------------------------------------------------------------------------
# Happy path — results go to stdout
# ---------------------------------------------------------------------------


def test_verify_happy_path(spec_file: Path, impl_file: Path) -> None:
    result = runner.invoke(
        app,
        ["verify", str(spec_file), "--impl", str(impl_file), "--level", "1"],
    )
    assert result.exit_code == EXIT_OK, result.output
    # Typer's runner merges streams into .output; check that.
    assert "verifying" in result.output
    assert "m" in result.output
    assert "f" in result.output
    assert "all checks passed" in result.output


def test_verify_default_level_is_1(spec_file: Path, impl_file: Path) -> None:
    result = runner.invoke(app, ["verify", str(spec_file), "--impl", str(impl_file)])
    assert result.exit_code == EXIT_OK, result.output
    assert "level 1" in result.output


@pytest.mark.parametrize("level", [1, 2, 3])
def test_verify_accepts_levels_1_to_3(
    spec_file: Path, impl_file: Path, level: int
) -> None:
    result = runner.invoke(
        app,
        ["verify", str(spec_file), "--impl", str(impl_file), "--level", str(level)],
    )
    assert result.exit_code == EXIT_OK, result.output


# ---------------------------------------------------------------------------
# Error paths — exit code 2 (usage), messages on stderr
# ---------------------------------------------------------------------------


def test_missing_spec_file_exits_2(tmp_path: Path, impl_file: Path) -> None:
    result = runner.invoke(
        app,
        ["verify", str(tmp_path / "nope.yaml"), "--impl", str(impl_file)],
    )
    assert result.exit_code == EXIT_USAGE
    assert "not found" in result.output


def test_bad_spec_exits_2(impl_file: Path, tmp_path: Path) -> None:
    bad = tmp_path / "bad.warrant.yaml"
    bad.write_text("module: m\nfunctions:\n  f:\n    reqiures: []\n")
    result = runner.invoke(app, ["verify", str(bad), "--impl", str(impl_file)])
    assert result.exit_code == EXIT_USAGE
    assert "spec error" in result.output


def test_missing_impl_file_exits_2(spec_file: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["verify", str(spec_file), "--impl", str(tmp_path / "nope.py")],
    )
    assert result.exit_code == EXIT_USAGE
    assert "not found" in result.output


def test_impl_path_is_directory_exits_2(spec_file: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["verify", str(spec_file), "--impl", str(tmp_path)],
    )
    assert result.exit_code == EXIT_USAGE
    assert "not a file" in result.output


def test_level_below_range_exits_2(spec_file: Path, impl_file: Path) -> None:
    result = runner.invoke(
        app,
        ["verify", str(spec_file), "--impl", str(impl_file), "--level", "0"],
    )
    assert result.exit_code != EXIT_OK


def test_level_above_range_exits_2(spec_file: Path, impl_file: Path) -> None:
    result = runner.invoke(
        app,
        ["verify", str(spec_file), "--impl", str(impl_file), "--level", "4"],
    )
    assert result.exit_code != EXIT_OK


# ---------------------------------------------------------------------------
# Global options
# ---------------------------------------------------------------------------


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == EXIT_OK
    assert "warrant" in result.output


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == EXIT_OK
    assert "Specs you can check" in result.output


def test_verify_help() -> None:
    result = runner.invoke(app, ["verify", "--help"])
    assert result.exit_code == EXIT_OK
    assert "--impl" in result.output
    assert "--level" in result.output


# ---------------------------------------------------------------------------
# The real example — this is our canary
# ---------------------------------------------------------------------------


def test_example_max_passes() -> None:
    """The reference example must always verify at level 1."""
    root = Path(__file__).resolve().parents[2]
    spec = root / "examples" / "max" / "specs" / "max.warrant.yaml"
    impl = root / "examples" / "max" / "src" / "max.py"
    assert spec.exists(), f"missing {spec}"
    assert impl.exists(), f"missing {impl}"

    result = runner.invoke(
        app,
        ["verify", str(spec), "--impl", str(impl), "--level", "1"],
    )
    assert result.exit_code == EXIT_OK, result.output
    assert "max" in result.output
    assert "max_of" in result.output
