"""`au validate` command."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

import typer
from rich.console import Console

from agentunit.adapters.registry import get as get_adapter
from agentunit.core.spec import load_spec, validate_spec

console = Console()


def handle(
    spec_file: Path = typer.Option("agentunit.yaml", "--spec", "-s", help="Path to agentunit.yaml"),  # noqa: B008
) -> None:
    """Validate an Agent Unit configuration."""
    if not spec_file.exists():
        console.print(f"[red]Error:[/red] {spec_file} not found")
        raise typer.Exit(1)

    try:
        spec = load_spec(spec_file)
    except Exception as e:
        console.print(f"[red]Parse error:[/red] {e}")
        raise typer.Exit(1) from None

    console.print(f"[bold]Agent Unit:[/bold] {spec.metadata.name} v{spec.metadata.version}")
    console.print(f"[bold]Framework:[/bold] {spec.runtime.framework}")
    console.print(f"[bold]Description:[/bold] {spec.metadata.description}")

    warnings = validate_spec(spec, spec_file.parent)

    # Framework-specific validation
    adapter = get_adapter(spec.runtime.framework)
    fw_warnings = adapter.validate_framework_config(spec.runtime.framework_config)
    warnings.extend(fw_warnings)

    if warnings:
        console.print(f"\n[yellow]Warnings ({len(warnings)}):[/yellow]")
        for w in warnings:
            console.print(f"  [yellow]-[/yellow] {w}")
    else:
        console.print("\n[green]All checks passed.[/green]")

    if any("not found" in w for w in warnings):
        raise typer.Exit(1)
