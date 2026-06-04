"""Agent Unit Spec parser and validator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml
from pydantic import BaseModel, Field


class Metadata(BaseModel):
    name: str
    version: str
    description: str
    author: str = ""
    license: str = "Apache-2.0"
    tags: list[str] = Field(default_factory=list)
    domain: list[str] = Field(default_factory=list)


class Contract(BaseModel):
    inputs: dict[str, Any]
    outputs: dict[str, Any]


class Governance(BaseModel):
    responsible_human: str = ""
    require_human_approval: bool = True
    max_token_per_task: int = 0
    audit_enabled: bool = True


class ModelConfig(BaseModel):
    provider: str = "openai"
    name: str = "gpt-4o"


class ComponentRef(BaseModel):
    name: str
    path: str
    type: str = "embedded"


class Components(BaseModel):
    skills: list[ComponentRef] = Field(default_factory=list)
    tools: list[ComponentRef] = Field(default_factory=list)
    knowledge: list[ComponentRef] = Field(default_factory=list)


class Dependencies(BaseModel):
    file: str = "requirements.txt"


class Runtime(BaseModel):
    framework: str = "generic-python"
    language: str = "python"
    entry: str = "app.py"
    model: ModelConfig = Field(default_factory=ModelConfig)
    components: Components = Field(default_factory=Components)
    framework_config: dict[str, Any] = Field(default_factory=dict)
    dependencies: Dependencies = Field(default_factory=Dependencies)


class Build(BaseModel):
    base_image: str = "python:3.11-slim"
    port: int = 8091
    health_check: str = "/health"
    env: dict[str, str] = Field(default_factory=dict)


class AgentUnitSpec(BaseModel):
    api_version: str = Field(alias="apiVersion", default="agentunit.io/v1alpha1")
    kind: str = "AgentUnit"
    metadata: Metadata
    contract: Contract
    governance: Governance = Field(default_factory=Governance)
    runtime: Runtime = Field(default_factory=Runtime)
    build: Build = Field(default_factory=Build)

    model_config = {"populate_by_name": True}

    @property
    def docker_labels(self) -> dict[str, str]:
        return {
            "agentunit.name": self.metadata.name,
            "agentunit.version": self.metadata.version,
            "agentunit.description": self.metadata.description,
            "agentunit.framework": self.runtime.framework,
            "agentunit.spec": json.dumps(self.to_yaml_dict(), ensure_ascii=False),
        }

    def to_yaml_dict(self) -> dict[str, Any]:
        return _spec_to_yaml_dict(self)


def _spec_to_yaml_dict(spec: AgentUnitSpec) -> dict[str, Any]:
    """Convert spec back to the original YAML-compatible dict."""
    d: dict[str, Any] = spec.model_dump(by_alias=True)
    d["apiVersion"] = spec.api_version
    d["kind"] = spec.kind
    return d


def load_spec(path: Path) -> AgentUnitSpec:
    """Load and parse agentunit.yaml."""
    text = path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text)
    return AgentUnitSpec(**raw)


def validate_spec(spec: AgentUnitSpec, base_dir: Path) -> list[str]:
    """Validate spec for structural and file-reference errors. Returns warning messages."""
    warnings: list[str] = []

    # Validate against JSON Schema
    schema_path = (
        Path(__file__).parent.parent.parent.parent / "spec" / "schemas" / "agentunit-schema.json"
    )
    if schema_path.exists():
        schema = json.loads(schema_path.read_text())
        yaml_dict = _spec_to_yaml_dict(spec)
        try:
            jsonschema.validate(yaml_dict, schema)
        except jsonschema.ValidationError as e:
            warnings.append(f"Schema validation error: {e.message}")

    # Check file references
    if not (base_dir / spec.runtime.entry).exists():
        warnings.append(f"Entry file not found: {spec.runtime.entry}")

    if not (base_dir / spec.runtime.dependencies.file).exists():
        warnings.append(f"Dependencies file not found: {spec.runtime.dependencies.file}")

    for comp_list_name in ("skills", "tools", "knowledge"):
        for comp in getattr(spec.runtime.components, comp_list_name, []):
            if not (base_dir / comp.path).exists():
                warnings.append(
                    f"{comp_list_name.rstrip('s')} not found: {comp.path} ({comp.name})"
                )

    return warnings
