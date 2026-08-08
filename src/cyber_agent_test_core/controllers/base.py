"""OS-neutral controller contract and shared operation semantics."""

from abc import ABC, abstractmethod

from cyber_agent_test_core.controllers.models import OperatingSystemInfo, ServiceStatus
from cyber_agent_test_core.transports import (
    CommandResult,
    CommandSpec,
    HostUnavailableError,
    Transport,
    TransportError,
)


class OperatingSystemController(ABC):
    """Know OS operations and commands while delegating all I/O to a transport."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def execute(
        self,
        command: CommandSpec,
        *,
        timeout_seconds: float | None = None,
    ) -> CommandResult:
        """Execute an OS-controller-owned command through the transport."""
        return self._transport.execute(command, timeout_seconds=timeout_seconds)

    @staticmethod
    def _require_success(result: CommandResult, operation: str) -> CommandResult:
        """Normalize a non-zero OS command into a non-retryable operation failure."""
        if result.exit_code != 0:
            raise TransportError(
                f"{operation} failed on {result.host}: {result.stderr.strip()}"
            )
        return result

    def file_exists(self, path: str) -> bool:
        """Return whether a path exists."""
        return self.execute(self._file_exists_command(path)).exit_code == 0

    def read_file(self, path: str) -> str:
        """Read text from a target path."""
        result = self._require_success(
            self.execute(self._read_file_command(path)),
            "read file",
        )
        return result.stdout

    def write_file(self, path: str, content: str) -> None:
        """Write text to a target path."""
        self._require_success(
            self.execute(self._write_file_command(path, content)),
            "write file",
        )

    def delete_file(self, path: str) -> None:
        """Delete a target path if present."""
        self._require_success(
            self.execute(self._delete_file_command(path)),
            "delete file",
        )

    def process_exists(self, process_name: str) -> bool:
        """Return whether a named process exists."""
        return self.execute(self._process_exists_command(process_name)).exit_code == 0

    def start_service(self, service_name: str) -> None:
        """Start an OS service."""
        self._require_success(
            self.execute(self._start_service_command(service_name)),
            "start service",
        )

    def stop_service(self, service_name: str) -> None:
        """Stop an OS service."""
        self._require_success(
            self.execute(self._stop_service_command(service_name)),
            "stop service",
        )

    def restart_service(self, service_name: str) -> None:
        """Restart an OS service."""
        self._require_success(
            self.execute(self._restart_service_command(service_name)),
            "restart service",
        )

    def service_status(self, service_name: str) -> ServiceStatus:
        """Return normalized service state."""
        result = self.execute(self._service_status_command(service_name))
        return self._parse_service_status(result)

    def install_package(self, package_path: str) -> None:
        """Install a package using the OS package mechanism."""
        self._require_success(
            self.execute(self._install_package_command(package_path)),
            "install package",
        )

    def uninstall_package(self, package_name: str) -> None:
        """Uninstall a package using the OS package mechanism."""
        self._require_success(
            self.execute(self._uninstall_package_command(package_name)),
            "uninstall package",
        )

    def get_os_info(self) -> OperatingSystemInfo:
        """Discover normalized OS information."""
        result = self._require_success(
            self.execute(self._os_info_command()),
            "get OS info",
        )
        return self._parse_os_info(result.stdout)

    def reboot(self) -> None:
        """Initiate reboot, then close the now-stale transport session."""
        self._require_success(self.execute(self._reboot_command()), "reboot")
        self._transport.disconnect()

    def wait_until_online(self, *, max_attempts: int) -> None:
        """Probe availability without sleeping or hiding the final failure."""
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        for _ in range(max_attempts):
            if self._transport.is_available():
                return
        raise HostUnavailableError(
            f"host did not become available after {max_attempts} probes"
        )

    def collect_system_logs(self) -> str:
        """Collect bounded OS-owned diagnostic logs."""
        result = self._require_success(
            self.execute(self._collect_system_logs_command()),
            "collect system logs",
        )
        return result.stdout

    @abstractmethod
    def _file_exists_command(self, path: str) -> CommandSpec: ...

    @abstractmethod
    def _read_file_command(self, path: str) -> CommandSpec: ...

    @abstractmethod
    def _write_file_command(self, path: str, content: str) -> CommandSpec: ...

    @abstractmethod
    def _delete_file_command(self, path: str) -> CommandSpec: ...

    @abstractmethod
    def _process_exists_command(self, process_name: str) -> CommandSpec: ...

    @abstractmethod
    def _start_service_command(self, service_name: str) -> CommandSpec: ...

    @abstractmethod
    def _stop_service_command(self, service_name: str) -> CommandSpec: ...

    @abstractmethod
    def _restart_service_command(self, service_name: str) -> CommandSpec: ...

    @abstractmethod
    def _service_status_command(self, service_name: str) -> CommandSpec: ...

    @abstractmethod
    def _parse_service_status(self, result: CommandResult) -> ServiceStatus: ...

    @abstractmethod
    def _install_package_command(self, package_path: str) -> CommandSpec: ...

    @abstractmethod
    def _uninstall_package_command(self, package_name: str) -> CommandSpec: ...

    @abstractmethod
    def _os_info_command(self) -> CommandSpec: ...

    @abstractmethod
    def _parse_os_info(self, output: str) -> OperatingSystemInfo: ...

    @abstractmethod
    def _reboot_command(self) -> CommandSpec: ...

    @abstractmethod
    def _collect_system_logs_command(self) -> CommandSpec: ...
