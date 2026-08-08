"""Distributed leasing for non-host execution resources."""

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from cyber_agent_test_core.execution.locks import DistributedLockProvider, LockHandle


class ResourceKind(StrEnum):
    """Concurrency and mutation semantics of an execution resource."""

    IMMUTABLE = "immutable"
    SHARED = "shared"
    EXCLUSIVE = "exclusive"
    STATEFUL = "stateful"


class ResourceType(StrEnum):
    """Lockable resources known to the core execution layer."""

    HOST = "host"
    TENANT = "tenant"
    LICENSE = "license"
    BACKEND_CONFIGURATION = "backend-configuration"
    NETWORK_NAMESPACE = "network-namespace"
    TEST_USER = "test-user"


@dataclass(frozen=True, slots=True)
class ResourceRequest:
    """One globally named resource requirement."""

    resource_type: ResourceType
    identifier: str
    kind: ResourceKind
    capacity: int = 1

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("resource identifier must not be empty")
        if self.capacity < 1:
            raise ValueError("resource capacity must be positive")
        if self.kind is not ResourceKind.SHARED and self.capacity != 1:
            raise ValueError("only shared resources may have capacity > 1")


@dataclass(frozen=True, slots=True)
class ResourceLease:
    """Fenced ownership of all mutable resources requested by one test."""

    owner: str
    handles: tuple[LockHandle, ...]
    immutable: tuple[ResourceRequest, ...]


class ResourceUnavailableError(RuntimeError):
    """At least one atomic resource lock could not be acquired."""


class ResourceLeaseLostError(RuntimeError):
    """A resource fencing token could not be renewed."""


class ResourceLeaseManager:
    """Acquire heterogeneous locks in stable order and unwind atomically."""

    def __init__(self, provider: DistributedLockProvider) -> None:
        self._provider = provider

    @staticmethod
    def _prefix(request: ResourceRequest) -> str:
        return (
            f"cyber-agent-test-core:{request.resource_type.value}:{request.identifier}"
        )

    def _acquire_one(
        self,
        request: ResourceRequest,
        owner: str,
        ttl: timedelta,
    ) -> LockHandle | None:
        prefix = self._prefix(request)
        slots = (
            range(request.capacity) if request.kind is ResourceKind.SHARED else range(1)
        )
        for slot in slots:
            handle = self._provider.acquire(f"{prefix}:{slot}", owner, ttl)
            if handle is not None:
                return handle
        return None

    def acquire(
        self,
        requests: tuple[ResourceRequest, ...],
        *,
        owner: str,
        ttl: timedelta,
    ) -> ResourceLease:
        """Acquire all mutable resources or release the partial acquisition."""
        immutable = tuple(
            request for request in requests if request.kind is ResourceKind.IMMUTABLE
        )
        mutable = sorted(
            (
                request
                for request in requests
                if request.kind is not ResourceKind.IMMUTABLE
            ),
            key=lambda request: self._prefix(request),
        )
        handles: list[LockHandle] = []
        try:
            for request in mutable:
                handle = self._acquire_one(request, owner, ttl)
                if handle is None:
                    raise ResourceUnavailableError(
                        f"resource is unavailable: {request.resource_type.value}/"
                        f"{request.identifier}"
                    )
                handles.append(handle)
        except Exception:
            for handle in reversed(handles):
                self._provider.release(handle)
            raise
        return ResourceLease(owner, tuple(handles), immutable)

    def release(self, lease: ResourceLease) -> None:
        """Release in reverse acquisition order using fencing tokens."""
        for handle in reversed(lease.handles):
            self._provider.release(handle)

    def refresh(self, lease: ResourceLease, *, ttl: timedelta) -> ResourceLease:
        """Renew every fencing token or report that aggregate ownership was lost."""
        if ttl <= timedelta(0):
            raise ValueError("lock ttl must be positive")
        refreshed: list[LockHandle] = []
        for handle in lease.handles:
            renewed = self._provider.refresh(handle, ttl)
            if renewed is None:
                raise ResourceLeaseLostError(
                    f"resource lease ownership lost: {handle.key}"
                )
            refreshed.append(renewed)
        return ResourceLease(lease.owner, tuple(refreshed), lease.immutable)
