"""Configuration source parsing and priority tests."""

from argparse import Namespace
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cyber_agent_test_core.config import (
    load_environment_variables,
    load_named_yaml_entry,
    load_test_run_config,
    merge_config_sources,
    normalize_cli_overrides,
)


def test_recursive_merge_replaces_sequences() -> None:
    merged = merge_config_sources(
        {"nested": {"keep": 1, "replace": 1}, "items": ["default"]},
        {"nested": {"replace": 2}, "items": ["override"]},
    )

    assert merged == {
        "nested": {"keep": 1, "replace": 2},
        "items": ["override"],
    }


def test_five_source_priority(run_data: Callable[..., dict[str, Any]]) -> None:
    config = load_test_run_config(
        defaults=run_data(parallelism=1, suite="defaults"),
        environment_yaml={"parallelism": 2, "suite": "environment"},
        laboratory_inventory={"parallelism": 3, "suite": "laboratory"},
        environ={
            "CYBER_AGENT_CORE_PARALLELISM": "4",
            "CYBER_AGENT_CORE_SUITE": "environment-variable",
        },
        cli_arguments={"parallelism": 5, "suite": "cli"},
    )

    assert config.parallelism == 5
    assert config.suite == "cli"


def test_environment_values_support_typed_yaml_scalars() -> None:
    values = load_environment_variables(
        {
            "CYBER_AGENT_CORE_PARALLELISM": "8",
            "CYBER_AGENT_CORE_ENABLED_FEATURES": "[feature-a, feature-b]",
            "UNRELATED": "ignored",
        }
    )

    assert values == {
        "parallelism": 8,
        "enabled_features": ["feature-a", "feature-b"],
    }


def test_cli_none_does_not_override() -> None:
    assert normalize_cli_overrides(Namespace(suite=None, parallelism=3)) == {
        "parallelism": 3
    }


def test_loads_named_yaml_entry(tmp_path: Path) -> None:
    path = tmp_path / "configuration.yaml"
    path.write_text(
        "environments:\n  synthetic-stage:\n    suite: smoke\n",
        encoding="utf-8",
    )

    assert load_named_yaml_entry(path, "environments", "synthetic-stage") == {
        "suite": "smoke"
    }
