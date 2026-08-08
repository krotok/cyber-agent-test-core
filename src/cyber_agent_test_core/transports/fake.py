"""Deterministic in-memory transport for controller and flow unit tests."""

from collections import deque
from pathlib import Path

from cyber_agent_test_core.transports.base import Transport
from cyber_agent_test_core.transports.exceptions import HostUnavailableError
from cyber_agent_test_core.transports.models import (
    CommandResult,
    CommandSpec,
    RawCommandResult,
    TransportType,
)


class FakeTransport(Transport):
    """Scriptable transport that never connects to a real machine."""

    def __init__(self, host: str = "synthetic-host") -> None:
        self.host = host
        self.connected = False
        self.commands: list[CommandSpec] = []
        self.uploads: list[tuple[Path, str]] = []
        self.downloads: list[tuple[str, Path]] = []
        self._outcomes: deque[RawCommandResult | Exception] = deque()
        self._availability: deque[bool] = deque()

    def queue_result(
        self,
        *,
        exit_code: int = 0,
        stdout: str = "",
        stderr: str = "",
        duration: float = 0,
    ) -> None:
        """Queue one normalized successful or non-zero command outcome."""
        self._outcomes.append(
            RawCommandResult(exit_code, stdout, stderr, duration)
        )

    def queue_error(self, error: Exception) -> None:
        """Queue an exception for the next command."""
        self._outcomes.append(error)

    def queue_availability(self, *values: bool) -> None:
        """Queue endpoint availability probe results."""
        self._availability.extend(values)

    def connect(self) -> None:
        """Connect the fake endpoint."""
        self.connected = True

    def disconnect(self) -> None:
        """Disconnect the fake endpoint."""
        self.connected = False

    def execute(
        self,
        command: CommandSpec,
        *,
        timeout_seconds: float | None = None,
    ) -> CommandResult:
        """Return the next scripted outcome and record the opaque command."""
        del timeout_seconds
        if not self.connected:
            raise HostUnavailableError(f"fake host is unavailable: {self.host}")
        self.commands.append(command)
        outcome = (
            self._outcomes.popleft()
            if self._outcomes
            else RawCommandResult(0, "", "", 0)
        )
        if isinstance(outcome, Exception):
            raise outcome
        return CommandResult(
            exit_code=outcome.exit_code,
            stdout=outcome.stdout,
            stderr=outcome.stderr,
            duration=outcome.duration,
            host=self.host,
            redacted_command=command.redacted_command,
            transport_type=TransportType.FAKE,
        )

    def upload(self, local_path: Path, remote_path: str) -> None:
        """Record an upload without reading either filesystem."""
        if not self.connected:
            raise HostUnavailableError(f"fake host is unavailable: {self.host}")
        self.uploads.append((local_path, remote_path))

    def download(self, remote_path: str, local_path: Path) -> None:
        """Record a download without reading either filesystem."""
        if not self.connected:
            raise HostUnavailableError(f"fake host is unavailable: {self.host}")
        self.downloads.append((remote_path, local_path))

    def is_available(self) -> bool:
        """Return scripted availability, then fall back to connection state."""
        if self._availability:
            return self._availability.popleft()
        return self.connected
