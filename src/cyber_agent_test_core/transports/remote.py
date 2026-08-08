"""Remote transport adapters with injected protocol clients."""

from pathlib import Path
from typing import Protocol

from cyber_agent_test_core.transports.base import Transport, retry_transport_failure
from cyber_agent_test_core.transports.exceptions import HostUnavailableError
from cyber_agent_test_core.transports.models import (
    CommandResult,
    CommandSpec,
    RawCommandResult,
    TransportType,
)


class RemoteTransportClient(Protocol):
    """Minimal adapter implemented by an SSH or WinRM integration package."""

    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def execute(
        self,
        command: CommandSpec,
        timeout_seconds: float | None,
    ) -> RawCommandResult: ...

    def upload(self, local_path: Path, remote_path: str) -> None: ...

    def download(self, remote_path: str, local_path: Path) -> None: ...

    def is_available(self) -> bool: ...


class ClientTransport(Transport):
    """Common remote transport behavior without OS command knowledge."""

    def __init__(
        self,
        host: str,
        client: RemoteTransportClient,
        transport_type: TransportType,
        *,
        max_attempts: int = 1,
    ) -> None:
        self._host = host
        self._client = client
        self._transport_type = transport_type
        self._max_attempts = max_attempts

    def connect(self) -> None:
        """Connect, retrying only explicitly retryable transport failures."""
        retry_transport_failure(self._client.connect, max_attempts=self._max_attempts)

    def disconnect(self) -> None:
        """Disconnect the underlying client."""
        self._client.disconnect()

    def execute(
        self,
        command: CommandSpec,
        *,
        timeout_seconds: float | None = None,
    ) -> CommandResult:
        """Delegate an opaque command to the remote client."""
        if not self.is_available():
            raise HostUnavailableError(f"host is unavailable: {self._host}")
        raw = retry_transport_failure(
            lambda: self._client.execute(command, timeout_seconds),
            max_attempts=self._max_attempts,
        )
        return CommandResult(
            exit_code=raw.exit_code,
            stdout=raw.stdout,
            stderr=raw.stderr,
            duration=raw.duration,
            host=self._host,
            redacted_command=command.redacted_command,
            transport_type=self._transport_type,
        )

    def upload(self, local_path: Path, remote_path: str) -> None:
        """Upload through the underlying remote client."""
        retry_transport_failure(
            lambda: self._client.upload(local_path, remote_path),
            max_attempts=self._max_attempts,
        )

    def download(self, remote_path: str, local_path: Path) -> None:
        """Download through the underlying remote client."""
        retry_transport_failure(
            lambda: self._client.download(remote_path, local_path),
            max_attempts=self._max_attempts,
        )

    def is_available(self) -> bool:
        """Return client-reported endpoint availability."""
        return self._client.is_available()


class SSHTransport(ClientTransport):
    """Remote transport backed by an injected SSH client adapter."""

    def __init__(
        self,
        host: str,
        client: RemoteTransportClient,
        *,
        max_attempts: int = 1,
    ) -> None:
        super().__init__(host, client, TransportType.SSH, max_attempts=max_attempts)


class WinRMTransport(ClientTransport):
    """Remote transport backed by an injected WinRM client adapter."""

    def __init__(
        self,
        host: str,
        client: RemoteTransportClient,
        *,
        max_attempts: int = 1,
    ) -> None:
        super().__init__(host, client, TransportType.WINRM, max_attempts=max_attempts)
