"""Tests for framework adapters."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentunit.adapters.registry import framework_names, get, list_frameworks
from agentunit.core.spec import (
    AgentUnitSpec,
    Contract,
    Metadata,
    Runtime,
    load_spec,
)

FIXTURES_DIR = Path(__file__).parent.parent / "examples" / "prd-writer-generic"


class TestAdapterRegistry:
    def test_builtin_adapters_registered(self) -> None:
        names = framework_names()
        assert "generic-python" in names
        assert "langchain" in names
        assert "pm-agent" in names

    def test_get_existing_adapter(self) -> None:
        adapter = get("generic-python")
        assert adapter.name == "generic-python"

    def test_get_unknown_adapter_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown framework"):
            get("nonexistent-framework")

    def test_list_frameworks_returns_all(self) -> None:
        adapters = list_frameworks()
        assert len(adapters) >= 3


class TestGenericPythonAdapter:
    def test_init_templates(self) -> None:
        adapter = get("generic-python")
        templates = adapter.get_init_templates()
        assert "agentunit.yaml" in templates
        assert "app.py" in templates
        assert "requirements.txt" in templates
        assert "skills/example.md" in templates

    def test_generate_dockerfile(self) -> None:
        adapter = get("generic-python")
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        dockerfile = adapter.generate_dockerfile(spec, FIXTURES_DIR)
        assert "FROM python:3.11-slim" in dockerfile
        assert "EXPOSE 8091" in dockerfile
        assert "agentunit.name" in dockerfile
        assert "prd-writer" in dockerfile
        assert 'ENTRYPOINT ["python", "app.py"]' in dockerfile
        assert "HEALTHCHECK" in dockerfile

    def test_run_command(self) -> None:
        adapter = get("generic-python")
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        cmd = adapter.get_run_command(spec, "prd-writer:1.0.0", "/tmp/input.json")
        assert cmd[0] == "docker"
        assert "run" in cmd
        assert "prd-writer:1.0.0" in cmd


class TestLangChainAdapter:
    def test_init_templates(self) -> None:
        adapter = get("langchain")
        templates = adapter.get_init_templates()
        assert "agentunit.yaml" in templates
        assert "app.py" in templates

    def test_name(self) -> None:
        adapter = get("langchain")
        assert adapter.name == "langchain"

    def test_generate_dockerfile_no_healthcheck(self) -> None:
        adapter = get("langchain")
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        dockerfile = adapter.generate_dockerfile(spec, FIXTURES_DIR)
        assert "HEALTHCHECK" not in dockerfile
        assert "ENTRYPOINT" in dockerfile


class TestPmAgentAdapter:
    def test_init_templates(self) -> None:
        adapter = get("pm-agent")
        templates = adapter.get_init_templates()
        assert "agentunit.yaml" in templates
        assert "config/default.yaml" in templates

    def test_framework_config_validation(self) -> None:
        adapter = get("pm-agent")
        warnings = adapter.validate_framework_config({"model_tier": "standard"})
        assert len(warnings) == 0

    def test_framework_config_unknown_key(self) -> None:
        adapter = get("pm-agent")
        warnings = adapter.validate_framework_config({"unknown_key": "value"})
        assert len(warnings) == 1
        assert "unknown_key" in warnings[0]

    def test_generate_dockerfile_module_entry(self) -> None:
        adapter = get("pm-agent")
        spec = AgentUnitSpec(
            metadata=Metadata(name="test-pm", version="1.0.0", description="test"),
            contract=Contract(inputs={}, outputs={}),
            runtime=Runtime(framework="pm-agent", entry="pm_agent.main"),
        )
        dockerfile = adapter.generate_dockerfile(spec, Path("/tmp"))
        assert 'ENTRYPOINT ["python", "-m", "pm_agent.main"]' in dockerfile
        assert "HEALTHCHECK" in dockerfile


class TestEntrypointArgs:
    def test_file_entry(self) -> None:
        adapter = get("generic-python")
        spec = AgentUnitSpec(
            metadata=Metadata(name="test", version="1.0.0", description="test"),
            contract=Contract(inputs={}, outputs={}),
            runtime=Runtime(entry="app.py"),
        )
        assert adapter._entrypoint_args(spec) == ["python", "app.py"]

    def test_module_entry(self) -> None:
        adapter = get("pm-agent")
        spec = AgentUnitSpec(
            metadata=Metadata(name="test", version="1.0.0", description="test"),
            contract=Contract(inputs={}, outputs={}),
            runtime=Runtime(entry="pm_agent.main"),
        )
        assert adapter._entrypoint_args(spec) == ["python", "-m", "pm_agent.main"]


class TestDockerignoreGeneration:
    def test_dockerignore_constant_exists(self) -> None:
        from agentunit.commands.pack import _DOCKERIGNORE

        assert ".git" in _DOCKERIGNORE
        assert "__pycache__" in _DOCKERIGNORE
        assert ".env" in _DOCKERIGNORE
        assert ".DS_Store" in _DOCKERIGNORE

    def test_dockerignore_not_overwritten(self, tmp_path: Path) -> None:
        existing = tmp_path / ".dockerignore"
        existing.write_text("custom-content\n")
        from agentunit.commands.pack import _DOCKERIGNORE

        if not (tmp_path / ".dockerignore").exists():
            (tmp_path / ".dockerignore").write_text(_DOCKERIGNORE)
        assert (tmp_path / ".dockerignore").read_text() == "custom-content\n"
