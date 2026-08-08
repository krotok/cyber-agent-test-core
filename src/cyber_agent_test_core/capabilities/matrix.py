"""Declarative compatibility matrix schema and file loading."""

import json
from pathlib import Path
from typing import Annotated, Self

import yaml
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from pydantic import BaseModel, ConfigDict, Field, model_validator

from cyber_agent_test_core.models import (
    Architecture,
    Capability,
    CapabilityContext,
    OperatingSystemFamily,
)

RuleId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")]


class CompatibilityDataError(ValueError):
    """Raised when compatibility data cannot be loaded or validated."""


class CompatibilityRule(BaseModel):
    """One declarative rule over any capability context dimension."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: RuleId
    agent_version: str = ""
    backend_version: str = ""
    operating_systems: frozenset[OperatingSystemFamily] = frozenset()
    os_version: str = ""
    kernel_build: str = ""
    architectures: frozenset[Architecture] = frozenset()
    required_features: frozenset[str] = frozenset()
    forbidden_features: frozenset[str] = frozenset()
    licenses: frozenset[str] = frozenset()
    environments: frozenset[str] = frozenset()
    grants: frozenset[Capability] = frozenset()
    removes: frozenset[Capability] = frozenset()
    supported: bool = True
    reason: str | None = None

    @model_validator(mode="after")
    def validate_rule(self) -> Self:
        """Validate version specifiers and unsupported-rule explanations."""
        for value in (
            self.agent_version,
            self.backend_version,
            self.os_version,
            self.kernel_build,
        ):
            try:
                SpecifierSet(value)
            except InvalidSpecifier as error:
                raise ValueError(f"invalid version specifier: {value}") from error
        if not self.supported and not self.reason:
            raise ValueError("unsupported compatibility rule requires a reason")
        overlap = self.grants & self.removes
        if overlap:
            raise ValueError(f"rule cannot grant and remove: {sorted(overlap)}")
        return self


class CompatibilityMatrix(BaseModel):
    """Versioned declarative capability data owned outside resolver code."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Annotated[int, Field(ge=1)] = 1
    default_capabilities: frozenset[Capability] = frozenset()
    require_matching_rule: bool = True
    rules: tuple[CompatibilityRule, ...]

    @model_validator(mode="after")
    def validate_unique_rule_ids(self) -> Self:
        """Reject ambiguous duplicate rule identifiers."""
        identifiers = [rule.rule_id for rule in self.rules]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("compatibility rule_id values must be unique")
        return self


def load_compatibility_matrix(path: Path) -> CompatibilityMatrix:
    """Load a strict compatibility matrix from YAML or JSON."""
    try:
        text = path.read_text(encoding="utf-8")
        data = (
            json.loads(text)
            if path.suffix.lower() == ".json"
            else yaml.safe_load(text)
        )
        return CompatibilityMatrix.model_validate(data)
    except (OSError, json.JSONDecodeError, yaml.YAMLError, ValueError) as error:
        raise CompatibilityDataError(f"invalid compatibility data: {path}") from error


def load_capability_context(path: Path) -> CapabilityContext:
    """Load the selected target context from strict YAML or JSON."""
    try:
        text = path.read_text(encoding="utf-8")
        data = (
            json.loads(text)
            if path.suffix.lower() == ".json"
            else yaml.safe_load(text)
        )
        return CapabilityContext.model_validate(data)
    except (OSError, json.JSONDecodeError, yaml.YAMLError, ValueError) as error:
        raise CompatibilityDataError(f"invalid capability context: {path}") from error
