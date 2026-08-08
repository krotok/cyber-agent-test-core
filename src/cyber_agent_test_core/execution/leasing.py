"""Distributed host leasing with TTL, heartbeat, release, and fencing."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import StrEnum
from threading import RLock
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from cyber_agent_test_core.execution.locks import (
    DistributedLockProvider,
    LockHandle,
    utc_now,
)
from cyber_agent_test_core.inventory.catalog import HostInventory, HostSelector
from cyber_agent_test_core.inventory.models import (
    Host,
    HostAccessMode,
    HostRequirement,
    HostState,
)
from cyber_agent_test_core.inventory.quarantine import HostQuarantineManager


class LeaseState(StrEnum):
    """Host lease lifecycle state."""

    ACTIVE = "active"
    RELEASED = "released"
    LOST = "lost"
    EXPIRED = "expired"


class HostLease(BaseModel):
    """Immutable lease proof carrying the distributed lock fencing token."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    lease_id: str
    owner: str
    host: Host
    slot: int
    acquired_at: datetime
    expires_at: datetime
    heartbeat_at: datetime
    lease_duration: timedelta
    lock_handle: LockHandle
    state: LeaseState = LeaseState.ACTIVE


class NoHostAvailableError(RuntimeError):
    """No compatible host lock could be acquired."""


class LeaseLostError(RuntimeError):
    """Heartbeat could not prove continued distributed ownership."""


class HostLeaseManager:
    """Coordinate inventory selection with an external distributed lock provider."""

    def __init__(
        self,
        inventory: HostInventory,
        selector: HostSelector,
        lock_provider: DistributedLockProvider,
        quarantine_manager: HostQuarantineManager,
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._inventory = inventory
        self._selector = selector
        self._lock_provider = lock_provider
        self._quarantine_manager = quarantine_manager
        self._clock = clock
        self._active: dict[str, HostLease] = {}
        self._lock = RLock()

    @staticmethod
    def _lock_key(host: Host, slot: int) -> str:
        """Create stable keys shared by xdist workers and independent CI jobs."""
        mode = "exclusive" if host.access_mode is HostAccessMode.EXCLUSIVE else "shared"
        return f"cyber-agent-test-core:host:{host.logical_name}:{mode}:{slot}"

    @staticmethod
    def _slots(host: Host) -> range:
        """Return the fixed distributed lock slots available on a host."""
        return range(host.shared_capacity)

    def acquire(
        self,
        requirement: HostRequirement,
        *,
        owner: str,
        lease_timeout: timedelta,
    ) -> HostLease:
        """Reserve one compatible slot using the distributed lock authority."""
        if lease_timeout <= timedelta(0):
            raise ValueError("lease_timeout must be positive")
        with self._lock:
            for host in self._selector.select(self._inventory, requirement):
                for slot in self._slots(host):
                    handle = self._lock_provider.acquire(
                        self._lock_key(host, slot),
                        owner,
                        lease_timeout,
                    )
                    if handle is None:
                        continue
                    now = self._clock()
                    lease = HostLease(
                        lease_id=uuid4().hex,
                        owner=owner,
                        host=host,
                        slot=slot,
                        acquired_at=now,
                        expires_at=handle.expires_at,
                        heartbeat_at=now,
                        lease_duration=lease_timeout,
                        lock_handle=handle,
                    )
                    self._active[lease.lease_id] = lease
                    self._inventory.update_state(host.logical_name, HostState.RESERVED)
                    return lease
        raise NoHostAvailableError("no compatible host lease is available")

    def heartbeat(self, lease: HostLease) -> HostLease:
        """Renew a live lease or quarantine after ownership loss."""
        with self._lock:
            current = self._active.get(lease.lease_id)
            if current is None or current.state is not LeaseState.ACTIVE:
                raise LeaseLostError(f"lease is not active: {lease.lease_id}")
            refreshed = self._lock_provider.refresh(
                current.lock_handle,
                current.lease_duration,
            )
            if refreshed is None:
                self._active.pop(lease.lease_id, None)
                self._quarantine_manager.quarantine(
                    current.host.logical_name,
                    "distributed lease heartbeat lost",
                )
                raise LeaseLostError(
                    f"distributed lease heartbeat lost: {lease.lease_id}"
                )
            renewed = current.model_copy(
                update={
                    "heartbeat_at": self._clock(),
                    "expires_at": refreshed.expires_at,
                    "lock_handle": refreshed,
                }
            )
            self._active[lease.lease_id] = renewed
            return renewed

    def release(self, lease: HostLease) -> HostLease:
        """Release idempotently and make the host selectable when locally unused."""
        with self._lock:
            current = self._active.pop(lease.lease_id, None)
            if current is None:
                return lease.model_copy(update={"state": LeaseState.RELEASED})
            self._lock_provider.release(current.lock_handle)
            still_used = any(
                self._lock_provider.is_locked(self._lock_key(current.host, slot))
                for slot in self._slots(current.host)
            )
            host_state = self._inventory.get(current.host.logical_name).state
            if not still_used and host_state is HostState.RESERVED:
                self._inventory.update_state(
                    current.host.logical_name,
                    HostState.AVAILABLE,
                )
            return current.model_copy(update={"state": LeaseState.RELEASED})

    def reap_expired(self) -> tuple[HostLease, ...]:
        """Expire locally known leases whose TTL elapsed without heartbeat."""
        with self._lock:
            now = self._clock()
            expired: list[HostLease] = []
            for lease in tuple(self._active.values()):
                if lease.expires_at <= now:
                    self._active.pop(lease.lease_id, None)
                    self._lock_provider.release(lease.lock_handle)
                    expired.append(
                        lease.model_copy(update={"state": LeaseState.EXPIRED})
                    )
                    current_state = self._inventory.get(lease.host.logical_name).state
                    if current_state is HostState.RESERVED:
                        self._inventory.update_state(
                            lease.host.logical_name,
                            HostState.AVAILABLE,
                        )
            return tuple(expired)

    @contextmanager
    def lease(
        self,
        requirement: HostRequirement,
        *,
        owner: str,
        lease_timeout: timedelta,
    ) -> Iterator[HostLease]:
        """Release the lease even when the test or setup body fails."""
        acquired = self.acquire(
            requirement,
            owner=owner,
            lease_timeout=lease_timeout,
        )
        try:
            yield acquired
        finally:
            self.release(acquired)
