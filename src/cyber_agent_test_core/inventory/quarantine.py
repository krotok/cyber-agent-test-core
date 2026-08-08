"""Quarantine state and reason management."""

from cyber_agent_test_core.inventory.catalog import HostInventory
from cyber_agent_test_core.inventory.models import Host, HostState


class HostQuarantineManager:
    """Remove unsafe hosts from selection while preserving an exact reason."""

    def __init__(self, inventory: HostInventory) -> None:
        self._inventory = inventory
        self._reasons: dict[str, str] = {}

    def quarantine(self, logical_name: str, reason: str) -> Host:
        """Mark a host quarantined with a non-empty diagnostic reason."""
        if not reason.strip():
            raise ValueError("quarantine reason must not be empty")
        self._reasons[logical_name] = reason
        return self._inventory.update_state(logical_name, HostState.QUARANTINED)

    def clear(self, logical_name: str) -> Host:
        """Return a manually repaired host to available state."""
        self._reasons.pop(logical_name, None)
        return self._inventory.update_state(logical_name, HostState.AVAILABLE)

    def reason(self, logical_name: str) -> str | None:
        """Return the recorded quarantine reason."""
        return self._reasons.get(logical_name)
