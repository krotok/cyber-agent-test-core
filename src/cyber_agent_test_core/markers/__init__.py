"""Stable pytest marker names for product tests."""

FRAMEWORK_CONTRACT: str = "framework_contract"
REQUIRES_CAPABILITY: str = "requires_capability"
REQUIRES_FEATURE: str = "requires_feature"
INCOMPATIBLE_FEATURE: str = "incompatible_feature"
SUPPORTED_OS: str = "supported_os"
MIN_AGENT_VERSION: str = "min_agent_version"
MAX_AGENT_VERSION: str = "max_agent_version"

__all__ = [
    "FRAMEWORK_CONTRACT",
    "INCOMPATIBLE_FEATURE",
    "MAX_AGENT_VERSION",
    "MIN_AGENT_VERSION",
    "REQUIRES_CAPABILITY",
    "REQUIRES_FEATURE",
    "SUPPORTED_OS",
]
