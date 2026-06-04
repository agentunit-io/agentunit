"""Generic Python Agent adapter."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from agentunit.adapters.base import AgentAdapter

if TYPE_CHECKING:
    from agentunit.core.spec import AgentUnitSpec


class GenericPythonAdapter(AgentAdapter):
    @property
    def name(self) -> str:
        return "generic-python"

    @property
    def display_name(self) -> str:
        return "Generic Python"

    @property
    def description(self) -> str:
        return "For any Python-based Agent — bring your own entry script"

    def get_init_templates(self) -> dict[str, str]:
        return {
            "agentunit.yaml": _AGENTUNIT_YAML,
            "app.py": _APP_PY,
            "skills/example.md": _SKILL_MD,
            "knowledge/example.md": _KNOWLEDGE_MD,
            "tools/example.py": _TOOL_PY,
            "requirements.txt": _REQUIREMENTS,
        }

    def generate_dockerfile(self, spec: AgentUnitSpec, context_dir: Path) -> str:
        deps_file = spec.runtime.dependencies.file
        lines = [
            f"FROM {spec.build.base_image}",
            "",
            "WORKDIR /agent",
            "",
            f"COPY {deps_file} ./",
            "RUN pip install --no-cache-dir -r requirements.txt",
            "",
            "COPY . .",
            "",
            f"EXPOSE {spec.build.port}",
            "",
        ]
        # Add labels
        for key, val in spec.docker_labels.items():
            escaped = val.replace('"', '\\"')
            lines.append(f'LABEL "{key}"="{escaped}"')
        lines.append("")
        lines.append(
            f"HEALTHCHECK CMD curl -f http://localhost:{spec.build.port}{spec.build.health_check} || exit 1"
        )
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


_AGENTUNIT_YAML = """\
apiVersion: agentunit.io/v1alpha1
kind: AgentUnit

metadata:
  name: "{{NAME}}"
  version: "0.1.0"
  description: "Describe what this Agent Unit does"
  tags: []
  domain: []

contract:
  inputs:
    type: object
    properties:
      prompt:
        type: string
        description: "Input prompt"
    required: [prompt]
  outputs:
    type: object
    properties:
      result:
        type: string
        description: "Agent output"

governance:
  require_human_approval: true
  audit_enabled: true

runtime:
  framework: "generic-python"
  language: "python"
  entry: "app.py"
  model:
    provider: "openai"
    name: "gpt-4o"
  components:
    skills:
      - name: example
        path: skills/example.md
    tools:
      - name: example
        path: tools/example.py
    knowledge:
      - name: example
        path: knowledge/example.md
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

_APP_PY = """\
\"\"\"Agent Unit entry point — generic-python template.\"\"\"

import json
import os
import sys
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


async def spec(request: Request) -> JSONResponse:
    spec_path = Path(__file__).parent / "agentunit.yaml"
    if spec_path.exists():
        import yaml
        data = yaml.safe_load(spec_path.read_text())
        return JSONResponse(data)
    return JSONResponse({"error": "spec not found"}, status_code=404)


async def run(request: Request) -> JSONResponse:
    body = await request.json()
    # TODO: Implement your agent logic here
    # - Load skills from skills/ directory
    # - Call LLM with model config
    # - Use tools from tools/ directory
    # - Reference knowledge from knowledge/ directory
    result = {"result": f"Agent received: {body}"}
    return JSONResponse(result)


app = Starlette(routes=[
    Route("/health", health),
    Route("/spec", spec),
    Route("/run", run, methods=["POST"]),
])

if __name__ == "__main__":
    # CLI mode: read input file and print result
    if "--input" in sys.argv:
        idx = sys.argv.index("--input")
        input_path = sys.argv[idx + 1]
        data = json.loads(Path(input_path).read_text())
        print(json.dumps({"result": f"Agent received: {data}"}))
    else:
        uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8091")))
"""

_SKILL_MD = """\
---
id: example-skill
name: Example Skill
description: A sample skill definition
version: "1.0"
---

You are a helpful AI assistant. Follow the instructions provided by the user.
"""

_KNOWLEDGE_MD = """\
# Example Knowledge

This is a sample knowledge file. Replace with your domain-specific reference material.
"""

_TOOL_PY = """\
\"\"\"Example tool — replace with your actual tool implementation.\"\"\"


def example_tool(query: str) -> str:
    \"\"\"A simple example tool.\"\"\"
    return f"Tool result for: {query}"
"""

_REQUIREMENTS = """\
openai>=1.0
starlette>=0.37
uvicorn>=0.29
pyyaml>=6.0
"""
