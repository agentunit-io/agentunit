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

    def _include_healthcheck(self, spec: AgentUnitSpec) -> bool:
        return False

    def get_init_templates(self) -> dict[str, str]:
        return {
            "agentunit.yaml": _LANGCHAIN_YAML,
            "app.py": _LANGCHAIN_APP,
            "requirements.txt": _LANGCHAIN_REQS,
        }

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

governance:
  require_human_approval: true
  audit_enabled: true

protocol:
  mode: "request-response"
  streaming_type: "none"
  compatible_with: []
  supports_function_calling: false

runtime:
  framework: "langchain"
  language: "python"
  entry: "app.py"
  model:
    provider: "openai"
    name: "gpt-4o"
  routing:
    default: hybrid
  framework_config:
    agent_type: "ReAct"
    memory: "ConversationBufferMemory"
  dependencies:
    file: requirements.txt

resources:
  cpu: "1"
  memory: "512Mi"
  gpu: false
  timeout_seconds: 300
  concurrency: 10

services:
  outbound_network: true
  domains: ["api.openai.com"]

observability:
  metrics_endpoint: ""

build:
  base_image: "python:3.11-slim"
  port: 8091
  health_check: "/health"
  env:
    MODEL_API_KEY: ""
    MODEL_BASE_URL: ""
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
