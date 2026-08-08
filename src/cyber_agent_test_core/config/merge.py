"""Deterministic configuration merge operations."""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

ConfigMapping = Mapping[str, Any]


def _merge_into(target: dict[str, Any], source: ConfigMapping) -> None:
    """Recursively merge one source into a mutable target."""
    for key, value in source.items():
        current = target.get(key)
        if isinstance(current, dict) and isinstance(value, Mapping):
            _merge_into(current, value)
        else:
            target[key] = deepcopy(value)


def merge_config_sources(*sources: ConfigMapping) -> dict[str, Any]:
    """Merge sources left-to-right, with every later source taking priority."""
    merged: dict[str, Any] = {}
    for source in sources:
        _merge_into(merged, source)
    return merged
