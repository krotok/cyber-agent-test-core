"""Host preparation, snapshot restore, and cleanup verification tests."""

from collections.abc import Callable

import pytest

from cyber_agent_test_core.inventory import (
    Host,
    HostCleanupError,
    HostCleanupFlow,
    HostHealthChecker,
    HostInventory,
    HostPreparationFlow,
    HostQuarantineManager,
    HostState,
)


class SyntheticMaintenance:
    def __init__(self, *, verified: bool = True, fail_cleanup: bool = False) -> None:
        self.verified = verified
        self.fail_cleanup = fail_cleanup
        self.actions: list[str] = []

    def restore_snapshot(self, host: Host) -> None:
        self.actions.append(f"restore:{host.logical_name}")

    def prepare(self, host: Host) -> None:
        self.actions.append(f"prepare:{host.logical_name}")

    def cleanup(self, host: Host) -> None:
        self.actions.append(f"cleanup:{host.logical_name}")
        if self.fail_cleanup:
            raise RuntimeError("synthetic cleanup operation failed")

    def verify_cleanup(self, host: Host) -> bool:
        self.actions.append(f"verify:{host.logical_name}")
        return self.verified


class SyntheticProbe:
    def __init__(self, available: bool) -> None:
        self.available = available

    def is_available(self) -> bool:
        return self.available


def test_preparation_supports_snapshot_restore(
    host_factory: Callable[..., Host],
) -> None:
    host = host_factory()
    inventory = HostInventory([host])
    quarantine = HostQuarantineManager(inventory)
    flow = HostPreparationFlow(HostHealthChecker(inventory), quarantine)
    maintenance = SyntheticMaintenance()

    flow.run(host, maintenance, SyntheticProbe(True), restore_snapshot=True)

    assert maintenance.actions == [f"restore:{host.logical_name}"]
    assert quarantine.reason(host.logical_name) is None


@pytest.mark.parametrize(
    ("verified", "fail_cleanup"),
    [(False, False), (True, True)],
)
def test_cleanup_failure_quarantines_host(
    host_factory: Callable[..., Host],
    verified: bool,
    fail_cleanup: bool,
) -> None:
    host = host_factory()
    inventory = HostInventory([host])
    quarantine = HostQuarantineManager(inventory)
    maintenance = SyntheticMaintenance(
        verified=verified,
        fail_cleanup=fail_cleanup,
    )

    with pytest.raises(HostCleanupError):
        HostCleanupFlow(quarantine).run(host, maintenance)

    assert inventory.get(host.logical_name).state is HostState.QUARANTINED
    assert quarantine.reason(host.logical_name) is not None
