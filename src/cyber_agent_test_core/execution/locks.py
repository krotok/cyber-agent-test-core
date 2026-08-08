"""Distributed lock contracts and local/fake provider implementations."""

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Protocol
from uuid import uuid4


def utc_now() -> datetime:
    """Return an aware UTC timestamp for lock expiry."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class LockHandle:
    """Ownership token and fencing identity for a distributed lock."""

    key: str
    owner: str
    token: str
    expires_at: datetime


class DistributedLockProvider(Protocol):
    """Atomic cross-worker lock provider contract."""

    def acquire(self, key: str, owner: str, ttl: timedelta) -> LockHandle | None: ...

    def refresh(self, handle: LockHandle, ttl: timedelta) -> LockHandle | None: ...

    def release(self, handle: LockHandle) -> bool: ...

    def is_locked(self, key: str) -> bool: ...


class RedisLockProvider(DistributedLockProvider, Protocol):
    """Interface for a Redis SET-NX/compare-token lock implementation."""


class FileLockProvider:
    """Cross-process lock provider backed by atomic exclusive file creation."""

    def __init__(
        self,
        directory: Path,
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._directory = directory
        self._directory.mkdir(parents=True, exist_ok=True)
        self._clock = clock

    def _path(self, key: str) -> Path:
        """Map an arbitrary lock key to a safe deterministic file name."""
        return self._directory / f"{sha256(key.encode()).hexdigest()}.lock"

    @staticmethod
    def _payload(handle: LockHandle) -> str:
        """Serialize only lock metadata, never credentials or inventory data."""
        return json.dumps(
            {
                "key": handle.key,
                "owner": handle.owner,
                "token": handle.token,
                "expires_at": handle.expires_at.timestamp(),
            }
        )

    @staticmethod
    def _read(path: Path) -> LockHandle | None:
        """Read lock metadata; malformed files are treated as held."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return LockHandle(
                key=str(data["key"]),
                owner=str(data["owner"]),
                token=str(data["token"]),
                expires_at=datetime.fromtimestamp(float(data["expires_at"]), UTC),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def acquire(self, key: str, owner: str, ttl: timedelta) -> LockHandle | None:
        """Acquire atomically, reclaiming only a proven expired lock."""
        if ttl <= timedelta(0):
            raise ValueError("lock ttl must be positive")
        path = self._path(key)
        for _ in range(2):
            handle = LockHandle(key, owner, uuid4().hex, self._clock() + ttl)
            try:
                descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                existing = self._read(path)
                if existing is None or existing.expires_at > self._clock():
                    return None
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                continue
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(self._payload(handle))
            return handle
        return None

    def refresh(self, handle: LockHandle, ttl: timedelta) -> LockHandle | None:
        """Extend a lock only when its ownership token still matches."""
        path = self._path(handle.key)
        current = self._read(path)
        if current is None or current.token != handle.token:
            return None
        refreshed = LockHandle(
            handle.key,
            handle.owner,
            handle.token,
            self._clock() + ttl,
        )
        path.write_text(self._payload(refreshed), encoding="utf-8")
        return refreshed

    def release(self, handle: LockHandle) -> bool:
        """Release only the lock identified by the caller's ownership token."""
        path = self._path(handle.key)
        current = self._read(path)
        if current is None or current.token != handle.token:
            return False
        try:
            path.unlink()
        except FileNotFoundError:
            return False
        return True

    def is_locked(self, key: str) -> bool:
        """Return whether a non-expired lock currently owns the key."""
        current = self._read(self._path(key))
        return current is not None and current.expires_at > self._clock()


class FakeLockProvider:
    """Thread-safe deterministic lock provider for unit tests."""

    def __init__(self, *, clock: Callable[[], datetime] = utc_now) -> None:
        self._clock = clock
        self._handles: dict[str, LockHandle] = {}
        self._lock = RLock()

    def acquire(self, key: str, owner: str, ttl: timedelta) -> LockHandle | None:
        """Acquire an unheld or expired key atomically."""
        if ttl <= timedelta(0):
            raise ValueError("lock ttl must be positive")
        with self._lock:
            existing = self._handles.get(key)
            if existing is not None and existing.expires_at > self._clock():
                return None
            handle = LockHandle(key, owner, uuid4().hex, self._clock() + ttl)
            self._handles[key] = handle
            return handle

    def refresh(self, handle: LockHandle, ttl: timedelta) -> LockHandle | None:
        """Refresh only a live matching token."""
        with self._lock:
            current = self._handles.get(handle.key)
            if (
                current is None
                or current.token != handle.token
                or current.expires_at <= self._clock()
            ):
                return None
            refreshed = LockHandle(
                handle.key,
                handle.owner,
                handle.token,
                self._clock() + ttl,
            )
            self._handles[handle.key] = refreshed
            return refreshed

    def release(self, handle: LockHandle) -> bool:
        """Release only a matching token."""
        with self._lock:
            current = self._handles.get(handle.key)
            if current is None or current.token != handle.token:
                return False
            del self._handles[handle.key]
            return True

    def is_locked(self, key: str) -> bool:
        """Return whether a non-expired fake lock currently owns the key."""
        with self._lock:
            current = self._handles.get(key)
            return current is not None and current.expires_at > self._clock()

    def force_loss(self, key: str) -> None:
        """Simulate external lock loss for heartbeat tests."""
        with self._lock:
            self._handles.pop(key, None)
