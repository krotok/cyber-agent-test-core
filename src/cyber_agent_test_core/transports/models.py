"""Private transport command and result models."""

from dataclasses import dataclass
from enum import StrEnum


class TransportType(StrEnum):
    """Supported transport implementations."""

    LOCAL = "local"
    SSH = "ssh"
    WINRM = "winrm"
    FAKE = "fake"


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """OS-controller-owned command with a safe diagnostic representation."""

    argv: tuple[str, ...]
    redacted_command: str

    def __post_init__(self) -> None:
        """Reject empty commands and empty diagnostic representations."""
        if not self.argv:
            raise ValueError("command argv must not be empty")
        if not self.redacted_command:
            raise ValueError("redacted_command must not be empty")


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Normalized command result returned by every transport."""

    exit_code: int
    stdout: str
    stderr: str
    duration: float
    host: str
    redacted_command: str
    transport_type: TransportType

    def __post_init__(self) -> None:
        """Reject impossible negative durations."""
        if self.duration < 0:
            raise ValueError("duration must be non-negative")


@dataclass(frozen=True, slots=True)
class RawCommandResult:
    """Client-adapter result before transport metadata is attached."""

    exit_code: int
    stdout: str
    stderr: str
    duration: float
