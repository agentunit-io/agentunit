"""Tests for Agent Unit Spec parser and validator."""

from __future__ import annotations

import json
from pathlib import Path

from agentunit.core.spec import (
    AgentUnitSpec,
    Build,
    ComponentRef,
    Components,
    Contract,
    EvaluationBaselines,
    EvaluationIndicator,
    Metadata,
    Observability,
    Protocol,
    Resources,
    Routing,
    Runtime,
    ServiceDependency,
    load_spec,
    validate_spec,
)

FIXTURES_DIR = Path(__file__).parent.parent / "examples" / "prd-writer-generic"


class TestSpecParsing:
    def test_load_valid_spec(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        assert spec.metadata.name == "prd-writer"
        assert spec.metadata.version == "1.0.0"
        assert spec.runtime.framework == "generic-python"
        assert spec.runtime.language == "python"
        assert spec.runtime.entry == "app.py"

    def test_metadata_fields(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        assert "requirements" in spec.metadata.tags
        assert "product-management" in spec.metadata.domain

    def test_contract_schema(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        assert "requirement_notes" in spec.contract.inputs["properties"]
        assert "prd_document" in spec.contract.outputs["properties"]

    def test_components(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        assert len(spec.runtime.components.skills) == 1
        assert spec.runtime.components.skills[0].name == "prd_writer"
        assert spec.runtime.components.skills[0].id == "prd_writer"
        assert spec.runtime.components.skills[0].description != ""
        assert len(spec.runtime.components.tools) == 1
        assert len(spec.runtime.components.knowledge) == 1

    def test_routing(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        assert spec.runtime.routing.default == "hybrid"

    def test_governance_defaults(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        assert spec.governance.require_human_approval is True
        assert spec.governance.audit_enabled is True
        assert spec.governance.max_token_per_task == 8000

    def test_protocol(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        assert spec.protocol.mode == "request-response"
        assert spec.protocol.streaming_type == "none"
        assert spec.protocol.supports_function_calling is False

    def test_resources(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        assert spec.resources.cpu == "1"
        assert spec.resources.memory == "512Mi"
        assert spec.resources.gpu is False
        assert spec.resources.timeout_seconds == 300
        assert spec.resources.concurrency == 10

    def test_services(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        assert spec.services.outbound_network is True
        assert "api.openai.com" in spec.services.domains

    def test_build_config(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        assert spec.build.port == 8091
        assert "python:3.11-slim" in spec.build.base_image


class TestSpecValidation:
    def test_valid_spec_no_warnings(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        warnings = validate_spec(spec, FIXTURES_DIR)
        assert len(warnings) == 0

    def test_missing_entry_file(self, tmp_path: Path) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        warnings = validate_spec(spec, tmp_path)
        assert any("Entry file not found" in w for w in warnings)

    def test_missing_skill_file(self, tmp_path: Path) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        warnings = validate_spec(spec, tmp_path)
        assert any("not found" in w for w in warnings)

    def test_invalid_routing_mode(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="literal_error"):
            Routing(default="invalid")  # type: ignore[arg-type]

    def test_duplicate_skill_ids(self, tmp_path: Path) -> None:
        spec = AgentUnitSpec(
            metadata=Metadata(name="test", version="1.0.0", description="test"),
            contract=Contract(inputs={}, outputs={}),
            runtime=Runtime(
                components=Components(
                    skills=[
                        ComponentRef(name="a", id="same-id", path="skills/a.md"),
                        ComponentRef(name="b", id="same-id", path="skills/b.md"),
                    ],
                ),
            ),
        )
        warnings = validate_spec(spec, tmp_path)
        assert any("Duplicate skill id" in w for w in warnings)

    def test_skill_without_id_falls_back_to_name(self, tmp_path: Path) -> None:
        spec = AgentUnitSpec(
            metadata=Metadata(name="test", version="1.0.0", description="test"),
            contract=Contract(inputs={}, outputs={}),
            runtime=Runtime(
                components=Components(
                    skills=[
                        ComponentRef(name="alpha", path="skills/a.md"),
                        ComponentRef(name="alpha", path="skills/b.md"),
                    ],
                ),
            ),
        )
        warnings = validate_spec(spec, tmp_path)
        assert any("Duplicate skill id" in w for w in warnings)

    def test_skill_without_id_no_spurious_schema_error(self, tmp_path: Path) -> None:
        spec = AgentUnitSpec(
            metadata=Metadata(name="test", version="1.0.0", description="test"),
            contract=Contract(inputs={}, outputs={}),
            runtime=Runtime(
                components=Components(
                    skills=[ComponentRef(name="my_skill", path="skills/my_skill.md")],
                ),
            ),
        )
        warnings = validate_spec(spec, tmp_path)
        assert not any("Schema validation" in w and "id" in w for w in warnings)


class TestDockerLabels:
    def test_labels_contain_required_keys(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        labels = spec.docker_labels
        assert "agentunit.name" in labels
        assert labels["agentunit.name"] == "prd-writer"
        assert "agentunit.version" in labels
        assert labels["agentunit.version"] == "1.0.0"
        assert "agentunit.framework" in labels
        assert "agentunit.spec" in labels

    def test_spec_label_is_valid_json(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        labels = spec.docker_labels
        spec_json = json.loads(labels["agentunit.spec"])
        assert spec_json["metadata"]["name"] == "prd-writer"


class TestSpecSerialization:
    def test_to_yaml_dict_roundtrip(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        d = spec.to_yaml_dict()
        assert d["apiVersion"] == "agentunit.io/v1alpha1"
        assert d["kind"] == "AgentUnit"
        assert d["metadata"]["name"] == "prd-writer"
        assert d["runtime"]["framework"] == "generic-python"
        assert d["runtime"]["routing"]["default"] == "hybrid"
        assert d["runtime"]["components"]["skills"][0]["id"] == "prd_writer"
        assert d["runtime"]["components"]["skills"][0]["description"] != ""
        assert d["protocol"]["mode"] == "request-response"
        assert d["resources"]["cpu"] == "1"
        assert d["services"]["outbound_network"] is True
        assert "observability" in d
        obs = d["observability"]
        assert obs["baselines"]["latency_p95_ms"] == 10000
        assert obs["baselines"]["success_rate"] == 0.95
        assert len(obs["evaluation_indicators"]) == 1
        assert obs["evaluation_indicators"][0]["field"] == "quality_score"


class TestProtocol:
    def test_defaults(self) -> None:
        p = Protocol()
        assert p.mode == "request-response"
        assert p.streaming_type == "none"
        assert p.compatible_with == []
        assert p.supports_function_calling is False

    def test_streaming(self) -> None:
        p = Protocol(
            mode="streaming", streaming_type="sse", compatible_with=["openai-chat-completions"]
        )
        assert p.mode == "streaming"
        assert p.streaming_type == "sse"
        assert "openai-chat-completions" in p.compatible_with

    def test_invalid_mode(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Protocol(mode="invalid")  # type: ignore[arg-type]

    def test_request_response_with_sse_invalid(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Protocol(mode="request-response", streaming_type="sse")

    def test_streaming_with_sse_valid(self) -> None:
        p = Protocol(mode="streaming", streaming_type="sse")
        assert p.mode == "streaming"
        assert p.streaming_type == "sse"

    def test_request_response_with_none_valid(self) -> None:
        p = Protocol(mode="request-response", streaming_type="none")
        assert p.streaming_type == "none"


class TestResources:
    def test_defaults(self) -> None:
        r = Resources()
        assert r.cpu == "1"
        assert r.memory == "512Mi"
        assert r.gpu is False
        assert r.timeout_seconds == 300
        assert r.concurrency == 10


class TestServiceDependency:
    def test_defaults(self) -> None:
        s = ServiceDependency()
        assert s.outbound_network is True
        assert s.domains == []

    def test_custom_domains(self) -> None:
        s = ServiceDependency(domains=["api.openai.com", "api.anthropic.com"])
        assert len(s.domains) == 2


class TestSkillContract:
    def test_skill_without_contract(self) -> None:
        skill = ComponentRef(name="test", path="skills/test.md")
        assert skill.contract is None

    def test_skill_with_contract(self) -> None:
        skill = ComponentRef(
            name="test",
            path="skills/test.md",
            contract=Contract(
                inputs={"type": "object", "properties": {"query": {"type": "string"}}},
                outputs={"type": "object", "properties": {"result": {"type": "string"}}},
            ),
        )
        assert skill.contract is not None
        assert "query" in skill.contract.inputs["properties"]

    def test_skill_contract_in_spec(self, tmp_path: Path) -> None:
        spec = AgentUnitSpec(
            metadata=Metadata(name="test", version="1.0.0", description="test"),
            contract=Contract(inputs={}, outputs={}),
            runtime=Runtime(
                components=Components(
                    skills=[
                        ComponentRef(
                            name="writer",
                            id="writer",
                            path="skills/writer.md",
                            contract=Contract(
                                inputs={
                                    "type": "object",
                                    "properties": {"text": {"type": "string"}},
                                },
                                outputs={
                                    "type": "object",
                                    "properties": {"doc": {"type": "string"}},
                                },
                            ),
                        ),
                        ComponentRef(name="reviewer", id="reviewer", path="skills/reviewer.md"),
                    ],
                ),
            ),
        )
        writer = spec.runtime.components.skills[0]
        reviewer = spec.runtime.components.skills[1]
        assert writer.contract is not None
        assert reviewer.contract is None


class TestGovernanceTokenBudget:
    def test_default_is_none(self) -> None:
        from agentunit.core.spec import Governance

        g = Governance()
        assert g.max_token_per_task is None

    def test_set_value(self) -> None:
        from agentunit.core.spec import Governance

        g = Governance(max_token_per_task=8000)
        assert g.max_token_per_task == 8000


class TestObservability:
    def test_defaults(self) -> None:
        o = Observability()
        assert o.metrics_endpoint == ""
        assert o.evaluation_indicators == []
        assert o.baselines.latency_p95_ms is None
        assert o.baselines.success_rate is None

    def test_with_indicators(self) -> None:
        o = Observability(
            evaluation_indicators=[
                EvaluationIndicator(field="quality_score", range=[0, 1], higher_is_better=True),
                EvaluationIndicator(field="error_rate", range=[0, 1], higher_is_better=False),
            ],
        )
        assert len(o.evaluation_indicators) == 2
        assert o.evaluation_indicators[1].higher_is_better is False

    def test_with_baselines(self) -> None:
        o = Observability(
            baselines=EvaluationBaselines(latency_p95_ms=5000, success_rate=0.95),
        )
        assert o.baselines.latency_p95_ms == 5000
        assert o.baselines.success_rate == 0.95

    def test_loaded_from_fixture(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        obs = spec.observability
        assert obs.baselines.latency_p95_ms == 10000
        assert obs.baselines.success_rate == 0.95
        assert len(obs.evaluation_indicators) == 1
        assert obs.evaluation_indicators[0].field == "quality_score"
        assert obs.evaluation_indicators[0].range == [0, 1]


class TestEvaluationIndicator:
    def test_defaults(self) -> None:
        i = EvaluationIndicator(field="score")
        assert i.field == "score"
        assert i.description == ""
        assert i.range is None
        assert i.higher_is_better is True

    def test_full_spec(self) -> None:
        i = EvaluationIndicator(
            field="accuracy",
            description="Classification accuracy",
            range=[0.8, 1.0],
            higher_is_better=True,
        )
        assert i.range == [0.8, 1.0]


class TestMetadataConstraints:
    def test_valid_kebab_name(self) -> None:
        m = Metadata(name="my-agent", version="1.0.0", description="test")
        assert m.name == "my-agent"

    def test_invalid_name_with_spaces(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Metadata(name="my agent", version="1.0.0", description="test")

    def test_invalid_name_uppercase(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Metadata(name="MyAgent", version="1.0.0", description="test")

    def test_valid_semver(self) -> None:
        m = Metadata(name="test", version="1.2.3", description="test")
        assert m.version == "1.2.3"

    def test_valid_semver_prerelease(self) -> None:
        m = Metadata(name="test", version="1.0.0-alpha.1", description="test")
        assert m.version == "1.0.0-alpha.1"

    def test_invalid_version(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Metadata(name="test", version="v1.0", description="test")

    def test_description_min_length(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Metadata(name="test", version="1.0.0", description="")


class TestRuntimeConstraints:
    def test_valid_languages(self) -> None:
        for lang in ("python", "nodejs", "go"):
            r = Runtime(language=lang)
            assert r.language == lang

    def test_invalid_language(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Runtime(language="rust")  # type: ignore[arg-type]


class TestBuildConstraints:
    def test_valid_port_range(self) -> None:
        b = Build(port=1)
        assert b.port == 1
        b = Build(port=65535)
        assert b.port == 65535

    def test_port_zero_invalid(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Build(port=0)

    def test_port_too_large(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Build(port=70000)


class TestResourcesConstraints:
    def test_timeout_minimum(self) -> None:
        r = Resources(timeout_seconds=1)
        assert r.timeout_seconds == 1

    def test_timeout_zero_invalid(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Resources(timeout_seconds=0)

    def test_concurrency_minimum(self) -> None:
        r = Resources(concurrency=1)
        assert r.concurrency == 1

    def test_concurrency_zero_invalid(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Resources(concurrency=0)


class TestBaselineConstraints:
    def test_latency_minimum(self) -> None:
        b = EvaluationBaselines(latency_p95_ms=1)
        assert b.latency_p95_ms == 1

    def test_latency_zero_invalid(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            EvaluationBaselines(latency_p95_ms=0)

    def test_success_rate_valid_range(self) -> None:
        b = EvaluationBaselines(success_rate=0.5)
        assert b.success_rate == 0.5
        b = EvaluationBaselines(success_rate=0.0)
        assert b.success_rate == 0.0
        b = EvaluationBaselines(success_rate=1.0)
        assert b.success_rate == 1.0

    def test_success_rate_above_one_invalid(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            EvaluationBaselines(success_rate=1.5)

    def test_success_rate_negative_invalid(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            EvaluationBaselines(success_rate=-0.1)


class TestApiVersionKindConstraints:
    def test_invalid_api_version(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AgentUnitSpec(
                apiVersion="invalid",  # type: ignore[arg-type]
                metadata=Metadata(name="test", version="1.0.0", description="test"),
                contract=Contract(inputs={}, outputs={}),
            )

    def test_invalid_kind(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AgentUnitSpec(
                kind="Invalid",  # type: ignore[arg-type]
                metadata=Metadata(name="test", version="1.0.0", description="test"),
                contract=Contract(inputs={}, outputs={}),
            )
