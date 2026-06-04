"""`au list-frameworks` command."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from agentunit.adapters.registry import list_frameworks

console = Console()


def handle() -> None:
    """List available framework adapters."""
    adapters = list_frameworks()

    table = Table(title="Available Framework Adapters")
    table.add_column("Name", style="bold")
    table.add_column("Display Name")
    table.add_column("Description")

    for adapter in adapters:
        table.add_row(adapter.name, adapter.display_name, adapter.description)

    console.print(table)
    console.print("\n[dim]Use with: au init <name> --framework <name>[/dim]")
