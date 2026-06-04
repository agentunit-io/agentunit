"""`au init` command."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

import typer
from rich.console import Console
from rich.tree import Tree

from agentunit.adapters.registry import get as get_adapter

console = Console()


def handle(
    name: str = typer.Argument(..., help="Agent Unit name (kebab-case)"),
    framework: str = typer.Option("generic-python", "--framework", "-f", help="Framework adapter"),
    output: Path = typer.Option(".", "--output", "-o", help="Output directory"),  # noqa: B008
) -> None:
    """Initialize a new Agent Unit project."""
    target = output / name
    if target.exists():
        console.print(f"[red]Error:[/red] Directory '{target}' already exists")
        raise typer.Exit(1)

    adapter = get_adapter(framework)
    templates = adapter.get_init_templates()

    target.mkdir(parents=True, exist_ok=True)

    tree = Tree(f"[bold green]{name}/[/bold green]")
    created: list[Path] = []

    for rel_path, content in templates.items():
        file_path = target / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        rendered = content.replace("{{NAME}}", name)
        file_path.write_text(rendered, encoding="utf-8")
        created.append(file_path)
        tree.add(f"[dim]{rel_path}[/dim]")

    console.print(tree)
    console.print(
        f"\n[green]Created Agent Unit '{name}' with {adapter.display_name} adapter[/green]"
    )
    console.print("\nNext steps:")
    console.print(f"  cd {name}")
    console.print("  au validate")
    console.print(f"  au pack -t {name}:0.1.0")
