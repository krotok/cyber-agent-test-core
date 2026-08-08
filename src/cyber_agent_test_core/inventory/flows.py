"""Host preparation and cleanup orchestration over injected maintenance."""

from typing import Protocol

from cyber_agent_test_core.inventory.health import HostHealthChecker, HostProbe
from cyber_agent_test_core.inventory.models import Host
from cyber_agent_test_core.inventory.quarantine import HostQuarantineManager


class HostMaintenance(Protocol):
    """Lab-specific maintenance actions hidden from product tests."""

    def restore_snapshot(self, host: Host) -> None: ...

    def prepare(self, host: Host) -> None: ...

    def cleanup(self, host: Host) -> None: ...

    def verify_cleanup(self, host: Host) -> bool: ...


class HostPreparationError(RuntimeError):
    """Host preparation failed and the host was quarantined."""


class HostCleanupError(RuntimeError):
    """Host cleanup verification failed and the host was quarantined."""


class HostPreparationFlow:
    """Prepare or restore a host, then prove it is reachable."""

    def __init__(
        self,
        health_checker: HostHealthChecker,
        quarantine_manager: HostQuarantineManager,
    ) -> None:
        self._health_checker = health_checker
        self._quarantine_manager = quarantine_manager

    def run(
        self,
        host: Host,
        maintenance: HostMaintenance,
        probe: HostProbe,
        *,
        restore_snapshot: bool = False,
    ) -> None:
        """Prepare a host and quarantine every unverified outcome."""
        try:
            if restore_snapshot:
                if not host.snapshot_supported:
                    raise HostPreparationError("host does not support snapshot restore")
                maintenance.restore_snapshot(host)
            else:
                maintenance.prepare(host)
            if not self._health_checker.check(host, probe):
                raise HostPreparationError("host is unavailable after preparation")
        except Exception as error:
            reason = f"host preparation failed: {error}"
            self._quarantine_manager.quarantine(host.logical_name, reason)
            if isinstance(error, HostPreparationError):
                raise
            raise HostPreparationError(reason) from error


class HostCleanupFlow:
    """Clean a host and require explicit verification before reuse."""

    def __init__(self, quarantine_manager: HostQuarantineManager) -> None:
        self._quarantine_manager = quarantine_manager

    def run(self, host: Host, maintenance: HostMaintenance) -> None:
        """Quarantine a host when cleanup or verification fails."""
        try:
            maintenance.cleanup(host)
            if not maintenance.verify_cleanup(host):
                raise HostCleanupError("cleanup verification returned false")
        except Exception as error:
            reason = f"host cleanup failed: {error}"
            self._quarantine_manager.quarantine(host.logical_name, reason)
            if isinstance(error, HostCleanupError):
                raise
            raise HostCleanupError(reason) from error
