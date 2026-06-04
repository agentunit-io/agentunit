"""Tests for Agent Unit Spec parser and validator."""

from __future__ import annotations

import json
from pathlib import Path

from agentunit.core.spec import load_spec, validate_spec

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
        assert len(spec.runtime.components.tools) == 1
        assert len(spec.runtime.components.knowledge) == 1

    def test_governance_defaults(self) -> None:
        spec = load_spec(FIXTURES_DIR / "agentunit.yaml")
        assert spec.governance.require_human_approval is True
        assert spec.governance.audit_enabled is True

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
