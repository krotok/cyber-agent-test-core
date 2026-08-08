"""Distributed lock provider contract tests."""

from datetime import timedelta
from pathlib import Path

from cyber_agent_test_core.execution import FakeLockProvider, FileLockProvider

from .conftest import MutableClock


def test_file_locks_coordinate_independent_provider_instances(
    tmp_path: Path,
    clock: MutableClock,
) -> None:
    first_provider = FileLockProvider(tmp_path, clock=clock)
    second_provider = FileLockProvider(tmp_path, clock=clock)

    first = first_provider.acquire("exclusive-host", "ci-job-1", timedelta(minutes=1))
    second = second_provider.acquire("exclusive-host", "ci-job-2", timedelta(minutes=1))

    assert first is not None
    assert second is None
    assert second_provider.is_locked("exclusive-host")
    assert first_provider.release(first)
    assert second_provider.acquire(
        "exclusive-host", "ci-job-2", timedelta(minutes=1)
    ) is not None


def test_file_lock_reclaims_only_expired_ownership(
    tmp_path: Path,
    clock: MutableClock,
) -> None:
    provider = FileLockProvider(tmp_path, clock=clock)
    first = provider.acquire("host", "worker-1", timedelta(seconds=5))
    assert first is not None

    clock.advance(timedelta(seconds=6))
    second = provider.acquire("host", "worker-2", timedelta(seconds=5))

    assert second is not None
    assert second.token != first.token
    assert not provider.release(first)


def test_fake_lock_heartbeat_requires_live_token(clock: MutableClock) -> None:
    provider = FakeLockProvider(clock=clock)
    handle = provider.acquire("host", "worker", timedelta(seconds=5))
    assert handle is not None

    refreshed = provider.refresh(handle, timedelta(seconds=5))
    provider.force_loss(handle.key)

    assert refreshed is not None
    assert provider.refresh(refreshed, timedelta(seconds=5)) is None
