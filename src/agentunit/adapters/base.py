"""Adapter base class — every framework adapter implements this interface."""

from __future__ import annotations

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

    @abstractmethod
    def generate_dockerfile(self, spec: AgentUnitSpec, context_dir: Path) -> str:
        """Generate a Dockerfile for the given spec."""

    @abstractmethod
    def get_run_command(self, spec: AgentUnitSpec, image: str, input_file: str) -> list[str]:
        """Build the `docker run` command for `au run`."""

    def validate_framework_config(self, config: dict[str, Any]) -> list[str]:
        """Validate framework_config. Return warning strings (empty = OK)."""
        return []
