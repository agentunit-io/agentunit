"""pm-agent adapter — for the self-developed AI-Platform framework."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from agentunit.adapters.base import AgentAdapter

if TYPE_CHECKING:
    from agentunit.core.spec import AgentUnitSpec


class PmAgentAdapter(AgentAdapter):
    @property
    def name(self) -> str:
        return "pm-agent"

    @property
    def display_name(self) -> str:
        return "pm-agent"

    @property
    def description(self) -> str:
        return "For the self-developed pm-agent framework (Skill = Markdown + YAML frontmatter)"

    def get_init_templates(self) -> dict[str, str]:
        return {
            "agentunit.yaml": _PM_AGENT_YAML,
            "skills/example.md": _PM_SKILL_MD,
            "knowledge/example.md": _PM_KNOWLEDGE_MD,
            "config/default.yaml": _PM_CONFIG,
            "requirements.txt": _PM_REQUIREMENTS,
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
        lines.append(
            f"HEALTHCHECK CMD curl -f http://localhost:{spec.build.port}{spec.build.health_check} || exit 1"
        )
        lines.append("")
        lines.append('CMD ["python", "-m", "pm_agent.main"]')
        return "\n".join(lines) + "\n"

    def get_run_command(self, spec: AgentUnitSpec, image: str, input_file: str) -> list[str]:
        cmd = ["docker", "run", "--rm"]
        cmd += ["-p", f"{spec.build.port}:{spec.build.port}"]
        cmd += ["-e", f"PMAGENT_PORT={spec.build.port}"]
        cmd += ["-e", "PMAGENT_LLM_BASE_URL=${MODEL_BASE_URL}"]
        cmd += ["-e", "PMAGENT_LLM_API_KEY=${MODEL_API_KEY}"]
        for key, val in spec.build.env.items():
            if val:
                cmd += ["-e", f"{key}={val}"]
        cmd += ["-v", f"{Path(input_file).resolve()}:/agent/input.json:ro"]
        cmd += [image]
        return cmd

    def validate_framework_config(self, config: dict[str, Any]) -> list[str]:
        warnings: list[str] = []
        known_keys = {
            "mcp_server_url",
            "model_tier",
            "session_backend",
            "skills_path",
            "knowledge_path",
        }
        for key in config:
            if key not in known_keys:
                warnings.append(f"Unknown pm-agent framework_config key: '{key}'")
        return warnings


_PM_AGENT_YAML = """\
apiVersion: agentunit.io/v1alpha1
kind: AgentUnit

metadata:
  name: "{{NAME}}"
  version: "0.1.0"
  description: "pm-agent based Agent Unit"
  tags: []
  domain: []

contract:
  inputs:
    type: object
    properties:
      prompt:
        type: string
        description: "User request"
    required: [prompt]
  outputs:
    type: object
    properties:
      result:
        type: string
        description: "Agent response"

governance:
  require_human_approval: true
  audit_enabled: true

runtime:
  framework: "pm-agent"
  language: "python"
  entry: "pm_agent.main"
  model:
    provider: "openai"
    name: "gpt-4o"
  components:
    skills:
      - name: example
        path: skills/example.md
    knowledge:
      - name: example
        path: knowledge/example.md
  framework_config:
    model_tier: "standard"
    session_backend: "sqlite"
  dependencies:
    file: requirements.txt

build:
  base_image: "python:3.11-slim"
  port: 8091
  health_check: "/health"
  env:
    MODEL_API_KEY: ""
    MODEL_BASE_URL: ""
"""

_PM_SKILL_MD = """\
---
id: example-skill
name: Example Skill
description: A sample pm-agent skill
version: "1.0"
max_steps: 10
timeout: 120
tools: []
trigger:
  type: chat
  keywords: [example]
  example_queries: ["示例请求"]
  priority: 0
model_tier: standard
streaming: true
input_schema: {}
---

你是一个有用的 AI 助手，请根据用户的需求提供帮助。
"""

_PM_KNOWLEDGE_MD = """\
# Example Knowledge

This is a sample knowledge file for pm-agent. Replace with domain-specific reference material.
"""

_PM_CONFIG = """\
server:
  host: "0.0.0.0"
  port: 8091
llm:
  base_url: "${MODEL_BASE_URL}"
  api_key: "${MODEL_API_KEY}"
  model: "gpt-4o"
  temperature: 0.1
  max_tokens: 4096
skills:
  paths:
    - "./skills"
knowledge:
  path: "./knowledge"
session:
  backend: "sqlite"
"""

_PM_REQUIREMENTS = """\
# pm-agent and its dependencies
# Install from local path or PyPI when available
openai>=1.0
starlette>=0.37
uvicorn>=0.29
pyyaml>=6.0
httpx>=0.27
pydantic>=2.0
"""
