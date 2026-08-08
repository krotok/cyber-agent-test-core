"""Feature flag provider contracts used by capability resolution."""

from collections.abc import Mapping
from typing import Protocol

from cyber_agent_test_core.models import CapabilityContext


class FeatureFlagProvider(Protocol):
    """Resolve enabled feature flags without exposing a backend client."""

    def get_enabled_flags(self, context: CapabilityContext) -> frozenset[str]:
        """Return enabled flags for the supplied target context."""
        ...


class EnvironmentFeatureFlagProvider:
    """Deterministic provider backed by an environment-to-flags mapping."""

    def __init__(self, flags_by_environment: Mapping[str, frozenset[str]]) -> None:
        self._flags_by_environment = dict(flags_by_environment)

    def get_enabled_flags(self, context: CapabilityContext) -> frozenset[str]:
        """Return flags configured for the context environment."""
        return self._flags_by_environment.get(context.environment, frozenset())
