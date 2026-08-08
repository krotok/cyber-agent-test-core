"""Declarative YAML and JSON compatibility loading tests."""

import json
from pathlib import Path

import pytest

from cyber_agent_test_core.capabilities import (
    CompatibilityDataError,
    load_capability_context,
    load_compatibility_matrix,
)
from cyber_agent_test_core.models import Capability


def test_loads_yaml_matrix(tmp_path: Path) -> None:
    path = tmp_path / "matrix.yaml"
    path.write_text(
        """\
schema_version: 1
rules:
  - rule_id: synthetic-rule
    agent_version: ">=1,<2"
    grants: [offline_scan]
""",
        encoding="utf-8",
    )

    matrix = load_compatibility_matrix(path)

    assert matrix.rules[0].grants == frozenset({Capability.OFFLINE_SCAN})


def test_loads_json_context(tmp_path: Path) -> None:
    path = tmp_path / "context.json"
    path.write_text(
        json.dumps(
            {
                "agent_version": "1.0.0",
                "backend_version": "2.0.0",
                "operating_system": "macos",
                "os_version": "15.0",
                "kernel_build": "24.0",
                "architecture": "arm64",
                "environment": "synthetic-dev",
            }
        ),
        encoding="utf-8",
    )

    context = load_capability_context(path)

    assert context.operating_system.value == "macos"


def test_invalid_data_is_a_configuration_error(tmp_path: Path) -> None:
    path = tmp_path / "matrix.json"
    path.write_text("not-json", encoding="utf-8")

    with pytest.raises(CompatibilityDataError, match="invalid compatibility data"):
        load_compatibility_matrix(path)
