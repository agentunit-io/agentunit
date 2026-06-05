"""Adapter base class — every framework adapter implements this interface."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from agentunit.core.spec import AgentUnitSpec


class AgentAdapter(ABC):
    """Base class for framework adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Adapter identifier (e.g. 'generic-python', 'langchain')."""

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def description(self) -> str:
        return ""

    @abstractmethod
    def get_init_templates(self) -> dict[str, str]:
        """Return files to generate during `au init`. {relative_path: template_content}."""

    def generate_dockerfile(self, spec: AgentUnitSpec, context_dir: Path) -> str:
        """Generate a Dockerfile for the given spec. Override for full customization."""
        lines = [
            f"FROM {spec.build.base_image}",
            "",
            "WORKDIR /agent",
            "",
            f"COPY {spec.runtime.dependencies.file} ./",
            f"RUN pip install --no-cache-dir -r {spec.runtime.dependencies.file}",
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

        if self._include_healthcheck(spec):
            hc_url = f"http://localhost:{spec.build.port}{spec.build.health_check}"
            hc_python = (
                f"import urllib.request,sys; sys.exit(0"
                f" if urllib.request.urlopen('{hc_url}',timeout=2).status==200 else 1)"
            )
            lines.append(f'HEALTHCHECK CMD python -c "{hc_python}" || exit 1')
            lines.append("")

        entry_args = self._entrypoint_args(spec)
        lines.append(f"ENTRYPOINT {json.dumps(entry_args)}")
        return "\n".join(lines) + "\n"

    def _entrypoint_args(self, spec: AgentUnitSpec) -> list[str]:
        """Return ENTRYPOINT command args. Override for custom entry behavior."""
        entry = spec.runtime.entry
        if entry.endswith(".py"):
            return ["python", entry]
        return ["python", "-m", entry]

    def _include_healthcheck(self, spec: AgentUnitSpec) -> bool:
        """Whether to include HEALTHCHECK in the generated Dockerfile."""
        return True

    @abstractmethod
    def get_run_command(self, spec: AgentUnitSpec, image: str, input_file: str) -> list[str]:
        """Build the `docker run` command for `au run`."""

    def validate_framework_config(self, config: dict[str, Any]) -> list[str]:
        """Validate framework_config. Return warning strings (empty = OK)."""
        return []
