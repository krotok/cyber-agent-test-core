"""Stable capability models shared with product-facing APIs."""

from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

VersionText = Annotated[str, Field(min_length=1, max_length=128)]
Name = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")]


class Capability(StrEnum):
    """Product behaviors that tests may require declaratively."""

    REALTIME_PROTECTION = "realtime_protection"
    OFFLINE_SCAN = "offline_scan"
    SELF_PROTECTION = "self_protection"
    PROXY_SUPPORT = "proxy_support"
    REMOTE_COMMANDS = "remote_commands"
    LOG_UPLOAD = "log_upload"
    UPGRADE_WITHOUT_REBOOT = "upgrade_without_reboot"
    ARM64_SUPPORT = "arm64_support"
    KERNEL_EVENTS = "kernel_events"
    NETWORK_ISOLATION = "network_isolation"
    AGENT_HEALTH_API = "agent_health_api"


class Architecture(StrEnum):
    """Supported processor architectures."""

    X86_64 = "x86_64"
    ARM64 = "arm64"


class OperatingSystemFamily(StrEnum):
    """Supported operating-system families."""

    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "macos"


class CapabilitySet(BaseModel):
    """Immutable resolved set with explicit capability queries."""

    model_config = ConfigDict(frozen=True)

    values: frozenset[Capability] = frozenset()

    def supports(self, capability: Capability) -> bool:
        """Return whether a capability is resolved for the target."""
        return capability in self.values

    def with_updates(
        self,
        *,
        grants: frozenset[Capability] = frozenset(),
        removals: frozenset[Capability] = frozenset(),
    ) -> Self:
        """Return a new set after applying one declarative rule."""
        return self.model_copy(update={"values": (self.values | grants) - removals})


class CapabilityContext(BaseModel):
    """All dimensions that may influence capability resolution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_version: VersionText
    backend_version: VersionText
    operating_system: OperatingSystemFamily
    os_version: VersionText
    kernel_build: VersionText | None = None
    architecture: Architecture
    feature_flags: frozenset[Name] = frozenset()
    licenses: frozenset[Name] = frozenset()
    environment: Name


class CompatibilityResult(BaseModel):
    """Explainable result of resolving one complete target context."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    supported: bool
    capabilities: CapabilitySet
    context: CapabilityContext
    reasons: tuple[str, ...] = ()
    matched_rules: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_reasons(self) -> Self:
        """Require an exact reason for every unsupported result."""
        if not self.supported and not self.reasons:
            raise ValueError("unsupported results require at least one reason")
        return self

    def require_supported(self) -> None:
        """Raise a stable public error when the target is unsupported."""
        if not self.supported:
            raise UnsupportedConfigurationError(self.reasons)


class UnsupportedConfigurationError(RuntimeError):
    """Raised when declarative compatibility data rejects a target."""

    def __init__(self, reasons: tuple[str, ...]) -> None:
        self.reasons = reasons
        super().__init__("unsupported configuration: " + "; ".join(reasons))
