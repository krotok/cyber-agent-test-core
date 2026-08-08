"""OS-neutral public models used by flows, checks, and fixtures."""

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class AgentHandle:
    """Stable reference to an Agent managed by the framework."""

    logical_name: str


class LifecycleAction(StrEnum):
    """Supported Agent lifecycle transitions."""

    INSTALL = "install"
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    ROLLBACK = "rollback"
    UNINSTALL = "uninstall"


@dataclass(frozen=True, slots=True)
class LifecycleResult:
    """Observable lifecycle outcome."""

    agent: AgentHandle
    action: LifecycleAction
    version: str | None
    successful: bool
    diagnostic: str = ""


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    """Public registration outcome independent of backend wire schemas."""

    agent: AgentHandle
    registered: bool
    backend_reference: str | None = None
    diagnostic: str = ""


@dataclass(frozen=True, slots=True)
class AgentHealth:
    """Normalized Agent health observation."""

    agent: AgentHandle
    healthy: bool
    state: str
    diagnostic: str = ""


@dataclass(frozen=True, slots=True)
class ThreatDetectionResult:
    """Threat detection observation."""

    detected: bool
    event_reference: str | None = None
    diagnostic: str = ""


@dataclass(frozen=True, slots=True)
class NetworkIsolationResult:
    """Network isolation observation."""

    agent: AgentHandle
    isolated: bool
    diagnostic: str = ""


@dataclass(frozen=True, slots=True)
class LogUploadResult:
    """Log upload observation."""

    agent: AgentHandle
    uploaded: bool
    upload_reference: str | None = None
    diagnostic: str = ""


@dataclass(frozen=True, slots=True)
class EventRecord:
    """Sanitized product event."""

    event_type: str
    message: str


@dataclass(frozen=True, slots=True)
class ProcessState:
    """Normalized process observation."""

    name: str
    running: bool


@dataclass(frozen=True, slots=True)
class ServiceState:
    """Normalized service observation."""

    name: str
    running: bool

