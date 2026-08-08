"""Load and normalize configuration sources without resolving secrets."""

import os
from argparse import Namespace
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from cyber_agent_test_core.config.merge import ConfigMapping, merge_config_sources
from cyber_agent_test_core.config.schemas import TestRunConfig

ENV_PREFIX = "CYBER_AGENT_CORE_"


class ConfigSourceError(ValueError):
    """Raised when an external configuration source is missing or malformed."""


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a YAML document and require a mapping at its root."""
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ConfigSourceError(f"cannot load configuration file: {path}") from error
    if loaded is None:
        return {}
    if not isinstance(loaded, dict) or not all(isinstance(key, str) for key in loaded):
        raise ConfigSourceError(
            f"configuration root must be a string-keyed mapping: {path}"
        )
    return loaded


def load_named_yaml_entry(path: Path, section: str, name: str) -> dict[str, Any]:
    """Load one named environment or laboratory entry from YAML."""
    document = load_yaml_mapping(path)
    entries = document.get(section)
    if not isinstance(entries, dict) or name not in entries:
        raise ConfigSourceError(f"{section} entry does not exist: {name}")
    entry = entries[name]
    if not isinstance(entry, dict):
        raise ConfigSourceError(f"{section}.{name} must be a mapping")
    return dict(entry)


def _parse_scalar(value: str) -> object:
    """Parse an environment value using YAML scalar/list syntax."""
    try:
        parsed = yaml.safe_load(value)
    except yaml.YAMLError as error:
        raise ConfigSourceError("invalid environment variable value") from error
    return parsed


def load_environment_variables(
    environ: Mapping[str, str] | None = None,
    *,
    prefix: str = ENV_PREFIX,
) -> dict[str, Any]:
    """Load prefixed environment variables as lower-case configuration keys."""
    source = os.environ if environ is None else environ
    return {
        key.removeprefix(prefix).lower(): _parse_scalar(value)
        for key, value in source.items()
        if key.startswith(prefix)
    }


def normalize_cli_overrides(
    arguments: Namespace | Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Convert argparse or mapping values into non-null highest-priority overrides."""
    if arguments is None:
        return {}
    values = vars(arguments) if isinstance(arguments, Namespace) else arguments
    return {key: value for key, value in values.items() if value is not None}


def load_test_run_config(
    *,
    defaults: ConfigMapping,
    environment_yaml: ConfigMapping,
    laboratory_inventory: ConfigMapping,
    environ: Mapping[str, str] | None = None,
    cli_arguments: Namespace | Mapping[str, Any] | None = None,
) -> TestRunConfig:
    """Merge all five sources in documented priority and parse the final schema."""
    merged = merge_config_sources(
        defaults,
        environment_yaml,
        laboratory_inventory,
        load_environment_variables(environ),
        normalize_cli_overrides(cli_arguments),
    )
    return TestRunConfig.model_validate(merged)
