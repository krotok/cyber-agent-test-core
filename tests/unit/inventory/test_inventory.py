"""Host inventory, selection, health, and quarantine tests."""

from collections.abc import Callable

import pytest
from pydantic import ValidationError

from cyber_agent_test_core.inventory import (
    Host,
    HostHealthChecker,
    HostInventory,
    HostQuarantineManager,
    HostRequirement,
    HostSelector,
    HostState,
)


class SyntheticProbe:
    def __init__(self, available: bool) -> None:
        self._available = available

    def is_available(self) -> bool:
        return self._available


def test_host_describes_required_inventory_dimensions(
    host_factory: Callable[..., Host],
) -> None:
    host = host_factory()

    assert host.logical_name == "synthetic-host-1"
    assert host.operating_system.value == "linux"
    assert host.connection_type.value == "ssh"
    assert host.credentials_reference.reference.startswith("vault:")
    assert host.labels == frozenset({"ephemeral"})
    assert host.installed_software == {"python": "synthetic-version"}
    assert host.snapshot_supported
    assert host.reboot_supported
    assert host.network_profile.value == "restricted"
    assert {capability.value for capability in host.capabilities} == {"offline_scan"}


def test_inventory_rejects_embedded_credentials(
    host_factory: Callable[..., Host],
) -> None:
    data = host_factory().model_dump()
    data["credentials"] = {"username": "forbidden", "password": "forbidden"}

    with pytest.raises(ValidationError, match="extra_forbidden"):
        Host.model_validate(data)


def test_selector_filters_unavailable_host(
    host_factory: Callable[..., Host],
) -> None:
    host = host_factory(state=HostState.UNAVAILABLE)
    inventory = HostInventory([host])

    selected = HostSelector().select(inventory, HostRequirement())

    assert selected == ()


def test_selector_matches_all_generic_requirements(
    host_factory: Callable[..., Host],
) -> None:
    host = host_factory()
    inventory = HostInventory([host])
    requirement = HostRequirement(
        operating_systems=frozenset({"linux"}),
        architectures=frozenset({"x86_64"}),
        connection_types=frozenset({"ssh"}),
        required_labels=frozenset({"ephemeral"}),
        required_software=frozenset({"python"}),
        required_capabilities=frozenset({"offline_scan"}),
        network_profiles=frozenset({"restricted"}),
        require_snapshot=True,
        require_reboot=True,
    )

    assert HostSelector().select(inventory, requirement) == (host,)


def test_health_failure_marks_host_broken(
    host_factory: Callable[..., Host],
) -> None:
    host = host_factory()
    inventory = HostInventory([host])

    healthy = HostHealthChecker(inventory).check(host, SyntheticProbe(False))

    assert not healthy
    assert inventory.get(host.logical_name).state is HostState.BROKEN


def test_quarantine_records_reason_and_blocks_selection(
    host_factory: Callable[..., Host],
) -> None:
    host = host_factory()
    inventory = HostInventory([host])
    quarantine = HostQuarantineManager(inventory)

    quarantine.quarantine(host.logical_name, "synthetic cleanup failure")

    assert inventory.get(host.logical_name).state is HostState.QUARANTINED
    assert quarantine.reason(host.logical_name) == "synthetic cleanup failure"
    assert HostSelector().select(inventory, HostRequirement()) == ()
