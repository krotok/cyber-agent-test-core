"""Concurrent, timeout, heartbeat, and release host leasing tests."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest

from cyber_agent_test_core.execution import (
    FakeLockProvider,
    HostLeaseManager,
    LeaseLostError,
    LeaseState,
    NoHostAvailableError,
)
from cyber_agent_test_core.inventory import (
    Host,
    HostAccessMode,
    HostInventory,
    HostQuarantineManager,
    HostRequirement,
    HostSelector,
    HostState,
)

from .conftest import MutableClock


def _manager(
    inventory: HostInventory,
    provider: FakeLockProvider,
    clock: MutableClock,
) -> HostLeaseManager:
    return HostLeaseManager(
        inventory,
        HostSelector(),
        provider,
        HostQuarantineManager(inventory),
        clock=clock,
    )


def test_concurrent_workers_cannot_lease_same_exclusive_host(
    host_factory: Callable[..., Host],
    clock: MutableClock,
) -> None:
    inventory = HostInventory([host_factory()])
    provider = FakeLockProvider(clock=clock)
    managers = [
        _manager(inventory, provider, clock),
        _manager(inventory, provider, clock),
    ]

    def acquire(index: int) -> str:
        try:
            return managers[index].acquire(
                HostRequirement(),
                owner=f"ci-job-{index}",
                lease_timeout=timedelta(minutes=1),
            ).owner
        except NoHostAvailableError:
            return "unavailable"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(acquire, (0, 1)))

    assert outcomes.count("unavailable") == 1
    assert len([value for value in outcomes if value.startswith("ci-job-")]) == 1


def test_shared_host_uses_distributed_capacity_slots(
    host_factory: Callable[..., Host],
    clock: MutableClock,
) -> None:
    host = host_factory(access_mode=HostAccessMode.SHARED, shared_capacity=2)
    inventory = HostInventory([host])
    provider = FakeLockProvider(clock=clock)
    managers = [_manager(inventory, provider, clock) for _ in range(3)]
    requirement = HostRequirement(access_mode=HostAccessMode.SHARED)

    first = managers[0].acquire(
        requirement, owner="worker-1", lease_timeout=timedelta(minutes=1)
    )
    second = managers[1].acquire(
        requirement, owner="worker-2", lease_timeout=timedelta(minutes=1)
    )

    assert {first.slot, second.slot} == {0, 1}
    with pytest.raises(NoHostAvailableError):
        managers[2].acquire(
            requirement,
            owner="worker-3",
            lease_timeout=timedelta(minutes=1),
        )
    managers[0].release(first)
    assert inventory.get(host.logical_name).state is HostState.RESERVED
    managers[1].release(second)
    assert inventory.get(host.logical_name).state is HostState.AVAILABLE


def test_lease_timeout_releases_host_for_reuse(
    host_factory: Callable[..., Host],
    clock: MutableClock,
) -> None:
    inventory = HostInventory([host_factory()])
    provider = FakeLockProvider(clock=clock)
    manager = _manager(inventory, provider, clock)
    lease = manager.acquire(
        HostRequirement(), owner="worker-1", lease_timeout=timedelta(seconds=5)
    )

    clock.advance(timedelta(seconds=6))
    expired = manager.reap_expired()
    replacement = manager.acquire(
        HostRequirement(), owner="worker-2", lease_timeout=timedelta(seconds=5)
    )

    assert expired[0].state is LeaseState.EXPIRED
    assert replacement.owner == "worker-2"
    assert replacement.lock_handle.token != lease.lock_handle.token


def test_heartbeat_loss_quarantines_host(
    host_factory: Callable[..., Host],
    clock: MutableClock,
) -> None:
    inventory = HostInventory([host_factory()])
    provider = FakeLockProvider(clock=clock)
    quarantine = HostQuarantineManager(inventory)
    manager = HostLeaseManager(
        inventory,
        HostSelector(),
        provider,
        quarantine,
        clock=clock,
    )
    lease = manager.acquire(
        HostRequirement(), owner="worker", lease_timeout=timedelta(seconds=5)
    )
    provider.force_loss(lease.lock_handle.key)

    with pytest.raises(LeaseLostError, match="heartbeat lost"):
        manager.heartbeat(lease)

    assert inventory.get(lease.host.logical_name).state is HostState.QUARANTINED


def test_context_releases_after_failed_test(
    host_factory: Callable[..., Host],
    clock: MutableClock,
) -> None:
    inventory = HostInventory([host_factory()])
    provider = FakeLockProvider(clock=clock)
    manager = _manager(inventory, provider, clock)

    with pytest.raises(RuntimeError, match="synthetic test failure"):
        with manager.lease(
            HostRequirement(),
            owner="worker",
            lease_timeout=timedelta(minutes=1),
        ):
            raise RuntimeError("synthetic test failure")

    assert inventory.list_hosts()[0].state is HostState.AVAILABLE
    replacement = manager.acquire(
        HostRequirement(), owner="next-worker", lease_timeout=timedelta(minutes=1)
    )
    assert replacement.owner == "next-worker"


def test_unavailable_host_cannot_be_leased(
    host_factory: Callable[..., Host],
    clock: MutableClock,
) -> None:
    inventory = HostInventory([host_factory(state=HostState.UNAVAILABLE)])
    manager = _manager(inventory, FakeLockProvider(clock=clock), clock)

    with pytest.raises(NoHostAvailableError):
        manager.acquire(
            HostRequirement(),
            owner="worker",
            lease_timeout=timedelta(minutes=1),
        )
