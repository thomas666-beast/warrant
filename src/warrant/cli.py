"""Warrant command-line interface."""

from __future__ import annotations

import typer
from rich.console import Console

from warrant import __version__

app = typer.Typer(
    name="warrant",
    help="Specs you can check. Code you can trust.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"warrant [bold cyan]{__version__}[/bold cyan]")
        raise typer.Exit()


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
    level: int = typer.Option(1, "--level", "-l", min=1, max=3, help="Verification rigor level (1-3)."),
) -> None:
    """Verify an implementation against a spec."""
    # Task 4 will wire this to the loader + levels.
    console.print(f"[yellow]TODO[/yellow] verify spec={spec} impl={impl} level={level}")
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
