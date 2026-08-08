"""OS-agnostic transport contract and retry boundary."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from cyber_agent_test_core.transports.exceptions import TransportError
from cyber_agent_test_core.transports.models import CommandResult, CommandSpec


class Transport(ABC):
    """Connection, command execution, and byte transfer only."""

    @abstractmethod
    def connect(self) -> None:
        """Establish transport connectivity."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close transport connectivity idempotently."""

    @abstractmethod
    def execute(
        self,
        command: CommandSpec,
        *,
        timeout_seconds: float | None = None,
    ) -> CommandResult:
        """Execute a controller-built command without interpreting it."""

    @abstractmethod
    def upload(self, local_path: Path, remote_path: str) -> None:
        """Transfer a local file to the target."""

    @abstractmethod
    def download(self, remote_path: str, local_path: Path) -> None:
        """Transfer a target file to the local filesystem."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return whether the transport endpoint is reachable."""


def retry_transport_failure[T](operation: Callable[[], T], *, max_attempts: int) -> T:
    """Retry only failures carrying explicit transport-level retry evidence."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except TransportError as error:
            if not error.retryable or attempt == max_attempts:
                raise
    raise AssertionError("retry loop exhausted without returning or raising")
