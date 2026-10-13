"""Smoke tests: package imports, version is set, CLI is wired."""

from __future__ import annotations

from typer.testing import CliRunner

from warrant import __version__
from warrant.cli import app

runner = CliRunner()


def test_version_is_set() -> None:
    assert __version__
    assert isinstance(__version__, str)


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Specs you can check" in result.stdout


def test_cli_verify_stub() -> None:
    result = runner.invoke(
        app,
        ["verify", "some/spec.warrant.yaml", "--impl", "some/impl.py", "--level", "1"],
    )
    assert result.exit_code == 0
    assert "TODO" in result.stdout
