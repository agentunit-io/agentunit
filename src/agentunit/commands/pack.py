"""`au pack` command — pack an Agent Unit into a Docker image."""

from __future__ import annotations

import subprocess
from pathlib import Path  # noqa: TC003

import typer
from rich.console import Console
from rich.table import Table

from agentunit.adapters.registry import get as get_adapter
from agentunit.core.spec import load_spec, validate_spec

console = Console()


def handle(
    tag: str = typer.Option(..., "--tag", "-t", help="Docker image tag (e.g. my-unit:1.0.0)"),
    spec_file: Path = typer.Option("agentunit.yaml", "--spec", "-s", help="Path to agentunit.yaml"),  # noqa: B008
) -> None:
    """Pack an Agent Unit into a Docker image."""
    if not spec_file.exists():
        console.print(f"[red]Error:[/red] {spec_file} not found")
        raise typer.Exit(1)

    spec = load_spec(spec_file)
    console.print(f"[bold]Packing:[/bold] {spec.metadata.name} v{spec.metadata.version}")

    warnings = validate_spec(spec, spec_file.parent)
    file_warnings = [w for w in warnings if "not found" in w]
    if file_warnings:
        for w in file_warnings:
            console.print(f"[red]Error:[/red] {w}")
        raise typer.Exit(1)

    adapter = get_adapter(spec.runtime.framework)
    context_dir = spec_file.parent

    # Generate Dockerfile
    dockerfile_content = adapter.generate_dockerfile(spec, context_dir)

    # Write Dockerfile to context
    dockerfile_path = context_dir / "Dockerfile"
    dockerfile_path.write_text(dockerfile_content, encoding="utf-8")

    console.print("[dim]Generated Dockerfile[/dim]")

    # Generate .dockerignore if not present
    dockerignore_path = context_dir / ".dockerignore"
    if not dockerignore_path.exists():
        dockerignore_path.write_text(_DOCKERIGNORE, encoding="utf-8")
        console.print("[dim]Generated .dockerignore[/dim]")

    # Build Docker image
    console.print(f"[bold]Building Docker image:[/bold] {tag}")
    cmd = ["docker", "build", "-t", tag, "-f", str(dockerfile_path), str(context_dir)]

    try:
        subprocess.run(cmd, capture_output=False, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Docker build failed (exit code {e.returncode})[/red]")
        raise typer.Exit(1) from None
    except FileNotFoundError:
        console.print("[red]Error:[/red] Docker not found. Install Docker to use `au pack`.")
        raise typer.Exit(1) from None

    # Summary
    table = Table(title="Agent Unit Image")
    table.add_column("Property", style="bold")
    table.add_column("Value")
    table.add_row("Name", spec.metadata.name)
    table.add_row("Version", spec.metadata.version)
    table.add_row("Image", tag)
    table.add_row("Framework", spec.runtime.framework)
    table.add_row("Skills", ", ".join(s.name for s in spec.runtime.components.skills) or "(none)")
    table.add_row("Tools", ", ".join(t.name for t in spec.runtime.components.tools) or "(none)")
    table.add_row(
        "Knowledge", ", ".join(k.name for k in spec.runtime.components.knowledge) or "(none)"
    )
    console.print(table)

    console.print(f"\n[green]Successfully packed {tag}[/green]")
    console.print(f"Run with: [bold]au run {tag} --input input.json[/bold]")


_DOCKERIGNORE = """\
.git
.gitignore
__pycache__/
*.pyc
*.pyo
.env
.venv/
venv/
.DS_Store
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
.ruff_cache/
"""
