"""AgentUnit CLI — `au` command."""

from __future__ import annotations

import typer

from agentunit.commands import init as init_cmd
from agentunit.commands import list_frameworks as list_cmd
from agentunit.commands import pack as pack_cmd
from agentunit.commands import run as run_cmd
from agentunit.commands import validate as validate_cmd

app = typer.Typer(
    name="au",
    help="AgentUnit — The Docker for AI Agent Packaging",
    no_args_is_help=True,
)

app.command(name="init")(init_cmd.handle)
app.command(name="validate")(validate_cmd.handle)
app.command(name="pack")(pack_cmd.handle)
app.command(name="run")(run_cmd.handle)
app.command(name="list-frameworks", help="List available framework adapters")(list_cmd.handle)


if __name__ == "__main__":
    app()
