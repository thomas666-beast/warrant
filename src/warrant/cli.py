"""Warrant command-line interface."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console

from warrant import __version__
from warrant.parser import SpecLoadError, load_spec
from warrant.verify import VerifyResult
from warrant.verify.result import Finding, Severity
from warrant.verify.runner import verify_spec

app = typer.Typer(
    name="warrant",
    help="Specs you can check. Code you can trust.",
    no_args_is_help=True,
    add_completion=False,
)

# Exit codes — part of the CLI contract.
EXIT_OK = 0
EXIT_VERIFY_FAILED = 1
EXIT_USAGE = 2


def _out() -> Console:
    return Console(file=sys.stdout, highlight=False)


def _err() -> Console:
    return Console(file=sys.stderr, highlight=False)


def _version_callback(value: bool) -> None:
    if value:
        _out().print(f"warrant [bold cyan]{__version__}[/bold cyan]")
        raise typer.Exit(code=EXIT_OK)


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Global options for the warrant CLI."""


@app.command()
def verify(
    spec: str = typer.Argument(..., help="Path to the .warrant.yaml spec file."),
    impl: str = typer.Option(..., "--impl", "-i", help="Path to the implementation file."),
    level: int = typer.Option(
        1,
        "--level",
        "-l",
        min=1,
        max=3,
        help="Verification rigor level (1-3).",
    ),
) -> None:
    """Verify an implementation against a spec."""
    out = _out()
    err = _err()

    spec_path = Path(spec)
    impl_path = Path(impl)

    loaded = load_spec(spec_path)
    if isinstance(loaded, SpecLoadError):
        err.print(f"[red]spec error:[/red] {loaded.render()}")
        raise typer.Exit(code=EXIT_USAGE)

    if not impl_path.exists():
        err.print(f"[red]error:[/red] implementation file not found: {impl_path}")
        raise typer.Exit(code=EXIT_USAGE)
    if not impl_path.is_file():
        err.print(f"[red]error:[/red] not a file: {impl_path}")
        raise typer.Exit(code=EXIT_USAGE)

    out.print(
        f"warrant [bold cyan]{__version__}[/bold cyan] "
        f"— verifying [bold]{loaded.module}[/bold] at level {level}"
    )
    out.print(f"  spec: [dim]{spec_path}[/dim]")
    out.print(f"  impl: [dim]{impl_path}[/dim]")
    out.print(f"  functions: {', '.join(sorted(loaded.functions))}")
    out.print()

    result = verify_spec(loaded, impl_path, level)
    _render_result(result, out)

    raise typer.Exit(code=EXIT_OK if result.ok else EXIT_VERIFY_FAILED)


def _render_result(result: VerifyResult, out: Console) -> None:
    for finding in result.errors:
        _render_finding(finding, "red", "error", out)
    for finding in result.warnings:
        _render_finding(finding, "yellow", "warning", out)
    for finding in result.findings:
        if finding.severity is Severity.INFO:
            _render_finding(finding, "cyan", "info", out)

    if result.ok and not result.findings:
        out.print("[green]✓[/green] all checks passed")
    elif result.ok:
        out.print(f"[green]✓[/green] passed with {len(result.warnings)} warning(s)")
    else:
        out.print(f"[red]✗[/red] {len(result.errors)} error(s)")


def _render_finding(
    finding: Finding, color: str, label: str, out: Console
) -> None:
    location = ""
    if finding.location is not None:
        path, line, col = finding.location
        location = f" [dim]{path}:{line}"
        if col is not None:
            location += f":{col}"
        location += "[/dim]"
    out.print(
        f"[{color}]{label}[/{color}] "
        f"[bold]{finding.function}[/bold]{location}: {finding.message}"
    )
    if finding.hint:
        out.print(f"  [dim]hint:[/dim] {finding.hint}")


if __name__ == "__main__":
    app()
