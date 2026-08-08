"""Host health checks independent of concrete transports."""

from typing import Protocol

from cyber_agent_test_core.inventory.catalog import HostInventory
from cyber_agent_test_core.inventory.models import Host, HostState


class HostProbe(Protocol):
    """Minimal availability probe injected by the composition root."""

    def is_available(self) -> bool: ...


class HostHealthChecker:
    """Normalize a probe result into inventory health state."""

    def __init__(self, inventory: HostInventory) -> None:
        self._inventory = inventory

    def check(self, host: Host, probe: HostProbe) -> bool:
        """Mark unavailable hosts broken before they can be leased."""
        healthy = probe.is_available()
        if not healthy:
            self._inventory.update_state(host.logical_name, HostState.BROKEN)
        return healthy
