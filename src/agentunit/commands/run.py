"""`au run` command — run a packed Agent Unit."""

from __future__ import annotations

import json
import os
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
            [
                "docker",
                "inspect",
                "--format",
                '{{index .Config.Labels "agentunit.spec"}}',
                image,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout.strip():
            return json.loads(result.stdout.strip())  # type: ignore[no-any-return]
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        pass
    return None


def _inject_env_vars(cmd: list[str], spec_data: dict[str, Any] | None) -> None:
    """Inject build.env vars from the current shell environment into the docker command."""
    if not spec_data:
        return
    build_env = spec_data.get("build", {}).get("env", {})
    missing_env: list[str] = []
    for key in build_env:
        val = os.environ.get(key)
        if val:
            cmd += ["-e", f"{key}={val}"]
        else:
            missing_env.append(key)
    if missing_env:
        console.print(
            f"[yellow]Warning:[/yellow] Environment variables not set: {', '.join(missing_env)}"
        )


def _resolve_ports(spec_data: dict[str, Any] | None, port: int | None) -> tuple[int, int]:
    """Return (host_port, container_port)."""
    container_port = 8091
    if spec_data:
        container_port = spec_data.get("build", {}).get("port", 8091)
    host_port = port or container_port
    return host_port, container_port


def handle(
    image: str = typer.Argument(..., help="Docker image tag"),
    input_file: Path | None = typer.Option(  # noqa: B008
        None, "--input", "-i", help="Input JSON file (one-shot mode)"
    ),
    port: int | None = typer.Option(None, "--port", "-p", help="Host port (default: auto)"),
    serve: bool = typer.Option(False, "--serve", help="Run as HTTP server (foreground)"),
) -> None:
    """Run a packed Agent Unit."""
    if not serve and input_file is None:
        console.print(
            "[red]Error:[/red] Provide --input for one-shot mode or --serve for server mode."
        )
        raise typer.Exit(1)

    if serve and input_file is not None:
        console.print("[red]Error:[/red] --serve and --input are mutually exclusive.")
        raise typer.Exit(1)

    if input_file is not None and not input_file.exists():
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

    # Build docker run command
    cmd: list[str] = ["docker", "run", "--rm"]

    host_port, container_port = _resolve_ports(spec_data, port)
    cmd += ["-p", f"{host_port}:{container_port}"]
    _inject_env_vars(cmd, spec_data)

    if serve:
        cmd += [image]
        console.print(f"[dim]Serving on http://localhost:{host_port} (Ctrl+C to stop)[/dim]\n")
    else:
        # Validate input against contract if spec available
        input_data = json.loads(input_file.read_text())  # type: ignore[union-attr]
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

        cmd += ["-v", f"{input_file.resolve()}:/agent/input.json:ro"]  # type: ignore[union-attr]
        cmd += [image, "--input", "/agent/input.json"]
        console.print("[dim]Starting one-shot execution...[/dim]\n")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Container exited with code {e.returncode}[/red]")
        raise typer.Exit(1) from None
    except FileNotFoundError:
        console.print("[red]Error:[/red] Docker not found.")
        raise typer.Exit(1) from None
