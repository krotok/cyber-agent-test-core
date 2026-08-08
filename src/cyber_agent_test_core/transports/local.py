"""Local process and file transport."""

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from time import monotonic

from cyber_agent_test_core.transports.base import Transport
from cyber_agent_test_core.transports.exceptions import (
    CommandTimeoutError,
    HostUnavailableError,
)
from cyber_agent_test_core.transports.models import (
    CommandResult,
    CommandSpec,
    TransportType,
)

ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]


class LocalTransport(Transport):
    """Execute argv locally with no shell interpretation."""

    def __init__(
        self,
        *,
        host: str = "local",
        runner: ProcessRunner = subprocess.run,
    ) -> None:
        self._host = host
        self._runner = runner
        self._connected = False

    def connect(self) -> None:
        """Mark the local transport connected."""
        self._connected = True

    def disconnect(self) -> None:
        """Mark the local transport disconnected."""
        self._connected = False

    def _require_connected(self) -> None:
        """Reject operations performed outside the connection lifecycle."""
        if not self._connected:
            raise HostUnavailableError(f"local transport is disconnected: {self._host}")

    def execute(
        self,
        command: CommandSpec,
        *,
        timeout_seconds: float | None = None,
    ) -> CommandResult:
        """Execute argv through subprocess with ``shell=False``."""
        self._require_connected()
        started = monotonic()
        try:
            completed = self._runner(
                command.argv,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as error:
            raise CommandTimeoutError(
                f"local command timed out on {self._host}: {command.redacted_command}"
            ) from error
        return CommandResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration=monotonic() - started,
            host=self._host,
            redacted_command=command.redacted_command,
            transport_type=TransportType.LOCAL,
        )

    def upload(self, local_path: Path, remote_path: str) -> None:
        """Copy a file within the local filesystem."""
        self._require_connected()
        shutil.copy2(local_path, Path(remote_path))

    def download(self, remote_path: str, local_path: Path) -> None:
        """Copy a local target file to the requested destination."""
        self._require_connected()
        shutil.copy2(Path(remote_path), local_path)

    def is_available(self) -> bool:
        """Return the explicit local connection state."""
        return self._connected
