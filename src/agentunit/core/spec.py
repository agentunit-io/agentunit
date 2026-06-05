"""Agent Unit Spec parser and validator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import jsonschema
import yaml
from pydantic import BaseModel, Field, model_validator


class Metadata(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$")
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$")
    description: str = Field(min_length=1, max_length=500)
    author: str = ""
    license: str = "Apache-2.0"
    tags: list[str] = Field(default_factory=list)
    domain: list[str] = Field(default_factory=list)


class Contract(BaseModel):
    inputs: dict[str, Any]
    outputs: dict[str, Any]


class Governance(BaseModel):
    require_human_approval: bool = True
    max_token_per_task: int | None = Field(default=None, ge=1)
    audit_enabled: bool = True


class Protocol(BaseModel):
    mode: Literal["request-response", "streaming", "both"] = "request-response"
    streaming_type: Literal["sse", "none", "websocket"] = "none"
    compatible_with: list[str] = Field(default_factory=list)
    supports_function_calling: bool = False

    @model_validator(mode="after")
    def check_streaming_consistency(self) -> Protocol:
        if self.mode == "request-response" and self.streaming_type != "none":
            msg = "streaming_type must be 'none' when mode is 'request-response'"
            raise ValueError(msg)
        return self


class ModelConfig(BaseModel):
    provider: str = "openai"
    name: str = "gpt-4o"


class ComponentRef(BaseModel):
    name: str
    id: str | None = None
    path: str
    description: str = ""
    type: Literal["embedded", "external"] = "embedded"
    contract: Contract | None = None


class Components(BaseModel):
    skills: list[ComponentRef] = Field(default_factory=list)
    tools: list[ComponentRef] = Field(default_factory=list)
    knowledge: list[ComponentRef] = Field(default_factory=list)


class Dependencies(BaseModel):
    file: str = "requirements.txt"


class Routing(BaseModel):
    default: Literal["auto", "explicit", "hybrid"] = "hybrid"


class Runtime(BaseModel):
    framework: str = "generic-python"
    language: Literal["python", "nodejs", "go"] = "python"
    entry: str = "app.py"
    model: ModelConfig = Field(default_factory=ModelConfig)
    routing: Routing = Field(default_factory=Routing)
    components: Components = Field(default_factory=Components)
    framework_config: dict[str, Any] = Field(default_factory=dict)
    dependencies: Dependencies = Field(default_factory=Dependencies)


class Resources(BaseModel):
    cpu: str = "1"
    memory: str = "512Mi"
    gpu: bool = False
    timeout_seconds: int = Field(default=300, ge=1)
    concurrency: int = Field(default=10, ge=1)


class ServiceDependency(BaseModel):
    outbound_network: bool = True
    domains: list[str] = Field(default_factory=list)


class EvaluationIndicator(BaseModel):
    field: str
    description: str = ""
    range: list[float] | None = None
    higher_is_better: bool = True


class EvaluationBaselines(BaseModel):
    latency_p95_ms: int | None = Field(default=None, ge=1)
    success_rate: float | None = Field(default=None, ge=0, le=1)


class Observability(BaseModel):
    metrics_endpoint: str = ""
    evaluation_indicators: list[EvaluationIndicator] = Field(default_factory=list)
    baselines: EvaluationBaselines = Field(default_factory=EvaluationBaselines)


class Build(BaseModel):
    base_image: str = "python:3.11-slim"
    port: int = Field(default=8091, ge=1, le=65535)
    health_check: str = "/health"
    env: dict[str, str] = Field(default_factory=dict)


class AgentUnitSpec(BaseModel):
    api_version: Literal["agentunit.io/v1alpha1"] = Field(
        alias="apiVersion", default="agentunit.io/v1alpha1"
    )
    kind: Literal["AgentUnit"] = "AgentUnit"
    metadata: Metadata
    contract: Contract
    governance: Governance = Field(default_factory=Governance)
    protocol: Protocol = Field(default_factory=Protocol)
    runtime: Runtime = Field(default_factory=Runtime)
    resources: Resources = Field(default_factory=Resources)
    services: ServiceDependency = Field(default_factory=ServiceDependency)
    observability: Observability = Field(default_factory=Observability)
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
    return spec.model_dump(by_alias=True, exclude_none=True)


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

    # Validate unique skill IDs
    skill_ids: list[str] = []
    for skill in spec.runtime.components.skills:
        sid = skill.id or skill.name
        if sid in skill_ids:
            warnings.append(f"Duplicate skill id: '{sid}'")
        skill_ids.append(sid)

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
