"""`au run` command — run a packed Agent Unit."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path  # noqa: TC003
from typing import Any

import typer
from rich.console import Console

console = Console()


def _extract_spec_from_image(image: str) -> dict[str, Any] | None:
    """Extract agentunit spec from Docker image labels."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", '{{index .Config.Labels "agentunit.spec"}}', image],
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout.strip():
            return json.loads(result.stdout.strip())  # type: ignore[no-any-return]
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        pass
    return None


def handle(
    image: str = typer.Argument(..., help="Docker image tag"),
    input_file: Path = typer.Option(..., "--input", "-i", help="Input JSON file"),  # noqa: B008
    port: int | None = typer.Option(None, "--port", "-p", help="Host port (default: auto)"),
) -> None:
    """Run a packed Agent Unit."""
    if not input_file.exists():
        console.print(f"[red]Error:[/red] Input file not found: {input_file}")
        raise typer.Exit(1)

    # Read image metadata
    spec_data = _extract_spec_from_image(image)

    if spec_data:
        name = spec_data.get("metadata", {}).get("name", image)
        version = spec_data.get("metadata", {}).get("version", "?")
        console.print(f"[bold]Running:[/bold] {name} v{version}")
    else:
        console.print(f"[bold]Running:[/bold] {image} (no Agent Unit metadata found)")

    # Validate input against contract if spec available
    input_data = json.loads(input_file.read_text())

    if spec_data:
        contract = spec_data.get("contract", {})
        inputs_schema = contract.get("inputs", {})
        if inputs_schema:
            import jsonschema

            try:
                jsonschema.validate(input_data, inputs_schema)
            except jsonschema.ValidationError as e:
                console.print(f"[red]Input validation error:[/red] {e.message}")
                raise typer.Exit(1) from None

    # Determine port
    container_port = 8091
    if spec_data:
        container_port = spec_data.get("build", {}).get("port", 8091)
    host_port = port or container_port

    # Run container
    cmd = [
        "docker",
        "run",
        "--rm",
        "-p",
        f"{host_port}:{container_port}",
        "-v",
        f"{input_file.resolve()}:/agent/input.json:ro",
        "-e",
        "INPUT_FILE=/agent/input.json",
        image,
    ]

    console.print(f"[dim]Starting container on port {host_port}...[/dim]")
    console.print(f"[dim]API: http://localhost:{host_port}/run[/dim]")
    console.print(f"[dim]Health: http://localhost:{host_port}/health[/dim]\n")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Container exited with code {e.returncode}[/red]")
        raise typer.Exit(1) from None
    except FileNotFoundError:
        console.print("[red]Error:[/red] Docker not found.")
        raise typer.Exit(1) from None
