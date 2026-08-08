"""Generic distributed resource lease tests."""

from datetime import timedelta

import pytest

from cyber_agent_test_core.execution import (
    FakeLockProvider,
    ResourceKind,
    ResourceLeaseLostError,
    ResourceLeaseManager,
    ResourceRequest,
    ResourceType,
    ResourceUnavailableError,
)


def test_acquires_all_resource_types_and_ignores_immutable() -> None:
    provider = FakeLockProvider()
    manager = ResourceLeaseManager(provider)
    requests = (
        ResourceRequest(ResourceType.HOST, "lab-a/host-1", ResourceKind.EXCLUSIVE),
        ResourceRequest(ResourceType.TENANT, "tenant-a", ResourceKind.SHARED, 2),
        ResourceRequest(ResourceType.LICENSE, "license-a", ResourceKind.STATEFUL),
        ResourceRequest(
            ResourceType.BACKEND_CONFIGURATION, "policy-a", ResourceKind.EXCLUSIVE
        ),
        ResourceRequest(ResourceType.NETWORK_NAMESPACE, "ns-a", ResourceKind.EXCLUSIVE),
        ResourceRequest(ResourceType.TEST_USER, "user-a", ResourceKind.EXCLUSIVE),
        ResourceRequest(ResourceType.LICENSE, "catalog", ResourceKind.IMMUTABLE),
    )

    lease = manager.acquire(requests, owner="job/worker", ttl=timedelta(minutes=1))

    assert len(lease.handles) == 6
    assert lease.immutable == (requests[-1],)
    manager.release(lease)
    assert all(not provider.is_locked(handle.key) for handle in lease.handles)


def test_partial_acquisition_is_unwound() -> None:
    provider = FakeLockProvider()
    manager = ResourceLeaseManager(provider)
    blocked = provider.acquire(
        "cyber-agent-test-core:tenant:t:0", "other", timedelta(minutes=1)
    )
    assert blocked is not None
    requests = (
        ResourceRequest(ResourceType.HOST, "h", ResourceKind.EXCLUSIVE),
        ResourceRequest(ResourceType.TENANT, "t", ResourceKind.EXCLUSIVE),
    )

    with pytest.raises(ResourceUnavailableError):
        manager.acquire(requests, owner="job", ttl=timedelta(minutes=1))

    assert not provider.is_locked("cyber-agent-test-core:host:h:0")


def test_refreshes_all_mutable_resource_fencing_tokens() -> None:
    provider = FakeLockProvider()
    manager = ResourceLeaseManager(provider)
    lease = manager.acquire(
        (
            ResourceRequest(ResourceType.TENANT, "tenant", ResourceKind.EXCLUSIVE),
            ResourceRequest(ResourceType.LICENSE, "license", ResourceKind.STATEFUL),
        ),
        owner="job",
        ttl=timedelta(minutes=1),
    )

    refreshed = manager.refresh(lease, ttl=timedelta(minutes=2))

    assert [handle.token for handle in refreshed.handles] == [
        handle.token for handle in lease.handles
    ]
    assert all(
        refreshed_handle.expires_at > original.expires_at
        for refreshed_handle, original in zip(
            refreshed.handles, lease.handles, strict=True
        )
    )


def test_refresh_reports_lost_resource_ownership() -> None:
    provider = FakeLockProvider()
    manager = ResourceLeaseManager(provider)
    lease = manager.acquire(
        (ResourceRequest(ResourceType.TEST_USER, "user", ResourceKind.EXCLUSIVE),),
        owner="job",
        ttl=timedelta(minutes=1),
    )
    provider.force_loss(lease.handles[0].key)

    with pytest.raises(ResourceLeaseLostError):
        manager.refresh(lease, ttl=timedelta(minutes=1))
