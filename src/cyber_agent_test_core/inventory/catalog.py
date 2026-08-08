"""Thread-safe logical inventory and declarative host selection."""

from collections.abc import Iterable
from threading import RLock

from cyber_agent_test_core.inventory.models import (
    Host,
    HostRequirement,
    HostState,
)


class HostInventory:
    """Mutable logical view; distributed locks remain the ownership authority."""

    def __init__(self, hosts: Iterable[Host]) -> None:
        host_values = tuple(hosts)
        host_map = {host.logical_name: host for host in host_values}
        if len(host_map) != len(host_values):
            raise ValueError("inventory host logical_name values must be unique")
        self._hosts = host_map
        self._lock = RLock()

    def list_hosts(self) -> tuple[Host, ...]:
        """Return a stable inventory snapshot sorted by logical name."""
        with self._lock:
            return tuple(self._hosts[name] for name in sorted(self._hosts))

    def get(self, logical_name: str) -> Host:
        """Return one logical host or raise a configuration error."""
        with self._lock:
            try:
                return self._hosts[logical_name]
            except KeyError as error:
                raise KeyError(f"host does not exist: {logical_name}") from error

    def update_state(self, logical_name: str, state: HostState) -> Host:
        """Atomically update only the mutable inventory state field."""
        with self._lock:
            updated = self.get(logical_name).model_copy(update={"state": state})
            self._hosts[logical_name] = updated
            return updated


class HostSelector:
    """Filter inventory by typed requirements without reserving hosts."""

    @staticmethod
    def _matches(host: Host, requirement: HostRequirement) -> bool:
        """Evaluate generic placement constraints against one host record."""
        selectable_state = host.state in {HostState.AVAILABLE, HostState.RESERVED}
        return (
            selectable_state
            and (
                not requirement.operating_systems
                or host.operating_system in requirement.operating_systems
            )
            and (
                not requirement.os_versions
                or host.os_version in requirement.os_versions
            )
            and (
                not requirement.architectures
                or host.architecture in requirement.architectures
            )
            and (
                not requirement.connection_types
                or host.connection_type in requirement.connection_types
            )
            and requirement.required_labels <= host.labels
            and requirement.required_software <= host.installed_software.keys()
            and requirement.required_capabilities <= host.capabilities
            and (
                not requirement.network_profiles
                or host.network_profile in requirement.network_profiles
            )
            and (
                requirement.access_mode is None
                or host.access_mode is requirement.access_mode
            )
            and (not requirement.require_snapshot or host.snapshot_supported)
            and (not requirement.require_reboot or host.reboot_supported)
            and (
                not requirement.logical_names
                or host.logical_name in requirement.logical_names
            )
        )

    def select(
        self,
        inventory: HostInventory,
        requirement: HostRequirement,
    ) -> tuple[Host, ...]:
        """Return all matching hosts in deterministic order."""
        return tuple(
            host for host in inventory.list_hosts() if self._matches(host, requirement)
        )
