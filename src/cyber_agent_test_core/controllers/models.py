"""Internal normalized operating-system controller models."""

from dataclasses import dataclass
from enum import StrEnum

from cyber_agent_test_core.models import Architecture, OperatingSystemFamily


class ServiceStatus(StrEnum):
    """Normalized cross-platform service state."""

    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class OperatingSystemInfo:
    """Normalized OS facts discovered by an OS controller."""

    family: OperatingSystemFamily
    version: str
    kernel_build: str
    architecture: Architecture
