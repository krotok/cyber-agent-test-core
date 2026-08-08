"""Synthetic inventory fixtures containing no real infrastructure data."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from cyber_agent_test_core.config import CredentialsReference
from cyber_agent_test_core.inventory import Host


class MutableClock:
    """Deterministic aware clock for TTL and heartbeat tests."""

    def __init__(self) -> None:
        self.current = datetime(2026, 1, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


@pytest.fixture
def clock() -> MutableClock:
    return MutableClock()


@pytest.fixture
def host_factory() -> Callable[..., Host]:
    """Create safe logical hosts using only external credential references."""

    def factory(**updates: object) -> Host:
        values: dict[str, object] = {
            "logical_name": "synthetic-host-1",
            "operating_system": "linux",
            "os_version": "synthetic-version",
            "architecture": "x86_64",
            "connection_type": "ssh",
            "credentials_reference": CredentialsReference(
                reference="vault:labs/synthetic-host"
            ),
            "labels": ["ephemeral"],
            "installed_software": {"python": "synthetic-version"},
            "snapshot_supported": True,
            "reboot_supported": True,
            "network_profile": "restricted",
            "capabilities": ["offline_scan"],
        }
        values.update(updates)
        return Host.model_validate(values)

    return factory
