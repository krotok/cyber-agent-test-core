"""SSH/WinRM adapter and transport retry tests with fake clients."""

from collections import deque
from pathlib import Path

import pytest

from cyber_agent_test_core.transports import (
    AuthenticationError,
    CommandSpec,
    HostUnavailableError,
    RawCommandResult,
    SSHTransport,
    TransportType,
    WinRMTransport,
    retry_transport_failure,
)


class SyntheticRemoteClient:
    """Protocol-compatible client that never opens a network connection."""

    def __init__(self) -> None:
        self.available = True
        self.connected = False
        self.connect_outcomes: deque[Exception | None] = deque()
        self.executed: list[CommandSpec] = []
        self.transfers: list[tuple[str, str]] = []

    def connect(self) -> None:
        if self.connect_outcomes:
            outcome = self.connect_outcomes.popleft()
            if outcome is not None:
                raise outcome
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def execute(
        self,
        command: CommandSpec,
        timeout_seconds: float | None,
    ) -> RawCommandResult:
        del timeout_seconds
        self.executed.append(command)
        return RawCommandResult(0, "remote output", "", 0.1)

    def upload(self, local_path: Path, remote_path: str) -> None:
        self.transfers.append((str(local_path), remote_path))

    def download(self, remote_path: str, local_path: Path) -> None:
        self.transfers.append((remote_path, str(local_path)))

    def is_available(self) -> bool:
        return self.available


@pytest.mark.parametrize(
    ("transport_class", "transport_type"),
    [(SSHTransport, TransportType.SSH), (WinRMTransport, TransportType.WINRM)],
)
def test_remote_transport_delegates_without_os_logic(
    transport_class: type[SSHTransport] | type[WinRMTransport],
    transport_type: TransportType,
    tmp_path: Path,
) -> None:
    client = SyntheticRemoteClient()
    transport = transport_class("synthetic-host", client)
    command = CommandSpec(("opaque", "arguments"), "opaque <redacted>")

    transport.connect()
    result = transport.execute(command)
    transport.upload(tmp_path / "source", "/remote")
    transport.download("/remote", tmp_path / "target")
    transport.disconnect()

    assert result.transport_type is transport_type
    assert result.redacted_command == "opaque <redacted>"
    assert client.executed == [command]
    assert not client.connected


def test_only_proven_transport_failure_is_retried() -> None:
    client = SyntheticRemoteClient()
    client.connect_outcomes.extend(
        [HostUnavailableError("transient network loss"), None]
    )

    SSHTransport("synthetic-host", client, max_attempts=2).connect()

    assert client.connected
    assert not client.connect_outcomes


def test_authentication_failure_is_not_retried() -> None:
    calls = 0

    def operation() -> None:
        nonlocal calls
        calls += 1
        raise AuthenticationError("synthetic authentication failure")

    with pytest.raises(AuthenticationError):
        retry_transport_failure(operation, max_attempts=3)

    assert calls == 1


def test_retry_requires_positive_attempt_count() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        retry_transport_failure(lambda: None, max_attempts=0)
