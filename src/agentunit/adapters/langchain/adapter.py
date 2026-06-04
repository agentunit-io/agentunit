"""LangChain adapter — skeleton implementation for extensibility validation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from agentunit.adapters.base import AgentAdapter

if TYPE_CHECKING:
    from agentunit.core.spec import AgentUnitSpec


class LangChainAdapter(AgentAdapter):
    @property
    def name(self) -> str:
        return "langchain"

    @property
    def display_name(self) -> str:
        return "LangChain"

    @property
    def description(self) -> str:
        return "For LangChain / LangGraph agents (experimental)"

    def get_init_templates(self) -> dict[str, str]:
        return {
            "agentunit.yaml": _LANGCHAIN_YAML,
            "app.py": _LANGCHAIN_APP,
            "requirements.txt": _LANGCHAIN_REQS,
        }

    def generate_dockerfile(self, spec: AgentUnitSpec, context_dir: Path) -> str:
        lines = [
            f"FROM {spec.build.base_image}",
            "",
            "WORKDIR /agent",
            "",
            f"COPY {spec.runtime.dependencies.file} ./",
            "RUN pip install --no-cache-dir -r requirements.txt",
            "",
            "COPY . .",
            "",
            f"EXPOSE {spec.build.port}",
            "",
        ]
        for key, val in spec.docker_labels.items():
            escaped = val.replace('"', '\\"')
            lines.append(f'LABEL "{key}"="{escaped}"')
        lines.append("")
        lines.append(f'CMD ["python", "{spec.runtime.entry}"]')
        return "\n".join(lines) + "\n"

    def get_run_command(self, spec: AgentUnitSpec, image: str, input_file: str) -> list[str]:
        cmd = ["docker", "run", "--rm"]
        cmd += ["-p", f"{spec.build.port}:{spec.build.port}"]
        for key, val in spec.build.env.items():
            if val:
                cmd += ["-e", f"{key}={val}"]
        cmd += ["-v", f"{Path(input_file).resolve()}:/agent/input.json:ro"]
        cmd += [image, "--input", "/agent/input.json"]
        return cmd


_LANGCHAIN_YAML = """\
apiVersion: agentunit.io/v1alpha1
kind: AgentUnit

metadata:
  name: "{{NAME}}"
  version: "0.1.0"
  description: "LangChain-based Agent Unit"
  tags: [langchain]
  domain: []

contract:
  inputs:
    type: object
    properties:
      prompt:
        type: string
    required: [prompt]
  outputs:
    type: object
    properties:
      result:
        type: string

runtime:
  framework: "langchain"
  language: "python"
  entry: "app.py"
  model:
    provider: "openai"
    name: "gpt-4o"
  framework_config:
    agent_type: "ReAct"
    memory: "ConversationBufferMemory"
  dependencies:
    file: requirements.txt

build:
  base_image: "python:3.11-slim"
  port: 8091
"""

_LANGCHAIN_APP = """\
\"\"\"LangChain Agent Unit entry point (skeleton).\"\"\"

# TODO: Implement your LangChain agent here
# from langchain_openai import ChatOpenAI
# from langchain.agents import AgentExecutor, create_react_agent
print("LangChain Agent Unit — implement me!")
"""

_LANGCHAIN_REQS = """\
langchain>=0.2
langchain-openai>=0.1
langchain-community>=0.2
"""
