"""Internal local and remote transport boundary."""

from cyber_agent_test_core.transports.base import Transport, retry_transport_failure
from cyber_agent_test_core.transports.exceptions import (
    AuthenticationError,
    CommandTimeoutError,
    HostUnavailableError,
    TransportError,
    UnsupportedOperationError,
)
from cyber_agent_test_core.transports.fake import FakeTransport
from cyber_agent_test_core.transports.local import LocalTransport
from cyber_agent_test_core.transports.models import (
    CommandResult,
    CommandSpec,
    RawCommandResult,
    TransportType,
)
from cyber_agent_test_core.transports.remote import (
    RemoteTransportClient,
    SSHTransport,
    WinRMTransport,
)

__all__ = [
    "AuthenticationError",
    "CommandResult",
    "CommandSpec",
    "CommandTimeoutError",
    "FakeTransport",
    "HostUnavailableError",
    "LocalTransport",
    "RawCommandResult",
    "RemoteTransportClient",
    "SSHTransport",
    "Transport",
    "TransportError",
    "TransportType",
    "UnsupportedOperationError",
    "WinRMTransport",
    "retry_transport_failure",
]
