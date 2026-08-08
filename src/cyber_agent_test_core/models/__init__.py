"""Stable typed models for product tests."""

from cyber_agent_test_core.models.capabilities import (
    Architecture,
    Capability,
    CapabilityContext,
    CapabilitySet,
    CompatibilityResult,
    OperatingSystemFamily,
    UnsupportedConfigurationError,
)
from cyber_agent_test_core.models.dsl import (
    AgentHandle,
    AgentHealth,
    EventRecord,
    LifecycleAction,
    LifecycleResult,
    LogUploadResult,
    NetworkIsolationResult,
    ProcessState,
    RegistrationResult,
    ServiceState,
    ThreatDetectionResult,
)

__all__ = [
    "AgentHandle",
    "AgentHealth",
    "Architecture",
    "Capability",
    "CapabilityContext",
    "CapabilitySet",
    "CompatibilityResult",
    "EventRecord",
    "LifecycleAction",
    "LifecycleResult",
    "LogUploadResult",
    "NetworkIsolationResult",
    "OperatingSystemFamily",
    "ProcessState",
    "RegistrationResult",
    "ServiceState",
    "ThreatDetectionResult",
    "UnsupportedConfigurationError",
]
