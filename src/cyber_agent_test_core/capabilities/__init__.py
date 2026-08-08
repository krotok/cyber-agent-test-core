"""Internal centralized capability resolution."""

from cyber_agent_test_core.capabilities.matrix import (
    CompatibilityDataError,
    CompatibilityMatrix,
    CompatibilityRule,
    load_capability_context,
    load_compatibility_matrix,
)
from cyber_agent_test_core.capabilities.providers import (
    EnvironmentFeatureFlagProvider,
    FeatureFlagProvider,
)
from cyber_agent_test_core.capabilities.resolver import CapabilityResolver
from cyber_agent_test_core.models import (
    Capability,
    CapabilitySet,
    CompatibilityResult,
    UnsupportedConfigurationError,
)

__all__ = [
    "Capability",
    "CapabilityResolver",
    "CapabilitySet",
    "CompatibilityDataError",
    "CompatibilityMatrix",
    "CompatibilityResult",
    "CompatibilityRule",
    "EnvironmentFeatureFlagProvider",
    "FeatureFlagProvider",
    "UnsupportedConfigurationError",
    "load_capability_context",
    "load_compatibility_matrix",
]
