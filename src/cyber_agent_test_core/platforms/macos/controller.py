"""macOS command construction and result parsing."""

from cyber_agent_test_core.controllers import (
    OperatingSystemController,
    OperatingSystemInfo,
    ServiceStatus,
)
from cyber_agent_test_core.models import Architecture, OperatingSystemFamily
from cyber_agent_test_core.platforms.common import encoded_text, parse_os_info_json
from cyber_agent_test_core.transports import CommandResult, CommandSpec


class MacOSController(OperatingSystemController):
    """Implement macOS operations without owning SSH/local mechanics."""

    def _file_exists_command(self, path: str) -> CommandSpec:
        return CommandSpec(("test", "-e", path), f"test -e {path}")

    def _read_file_command(self, path: str) -> CommandSpec:
        return CommandSpec(("cat", path), f"cat {path}")

    def _write_file_command(self, path: str, content: str) -> CommandSpec:
        script = (
            "import base64,pathlib,sys;"
            "pathlib.Path(sys.argv[1]).write_bytes(base64.b64decode(sys.argv[2]))"
        )
        return CommandSpec(
            ("python3", "-c", script, path, encoded_text(content)),
            f"write-file {path} <redacted-content>",
        )

    def _delete_file_command(self, path: str) -> CommandSpec:
        return CommandSpec(("rm", "-f", path), f"rm -f {path}")

    def _process_exists_command(self, process_name: str) -> CommandSpec:
        return CommandSpec(("pgrep", "-x", process_name), f"pgrep -x {process_name}")

    def _start_service_command(self, service_name: str) -> CommandSpec:
        return CommandSpec(
            ("launchctl", "kickstart", f"system/{service_name}"),
            f"launchctl kickstart system/{service_name}",
        )

    def _stop_service_command(self, service_name: str) -> CommandSpec:
        return CommandSpec(
            ("launchctl", "kill", "SIGTERM", f"system/{service_name}"),
            f"launchctl kill SIGTERM system/{service_name}",
        )

    def _restart_service_command(self, service_name: str) -> CommandSpec:
        return CommandSpec(
            ("launchctl", "kickstart", "-k", f"system/{service_name}"),
            f"launchctl kickstart -k system/{service_name}",
        )

    def _service_status_command(self, service_name: str) -> CommandSpec:
        return CommandSpec(
            ("launchctl", "print", f"system/{service_name}"),
            f"launchctl print system/{service_name}",
        )

    def _parse_service_status(self, result: CommandResult) -> ServiceStatus:
        if result.exit_code != 0:
            return ServiceStatus.STOPPED
        if "state = running" in result.stdout.lower():
            return ServiceStatus.RUNNING
        return ServiceStatus.UNKNOWN

    def _install_package_command(self, package_path: str) -> CommandSpec:
        return CommandSpec(
            ("installer", "-pkg", package_path, "-target", "/"),
            f"installer -pkg {package_path} -target /",
        )

    def _uninstall_package_command(self, package_name: str) -> CommandSpec:
        return CommandSpec(
            ("pkgutil", "--forget", package_name),
            f"pkgutil --forget {package_name}",
        )

    def _os_info_command(self) -> CommandSpec:
        script = (
            "import json,platform;print(json.dumps({'version':platform.mac_ver()[0],"
            "'kernel_build':platform.release(),'architecture':platform.machine()}))"
        )
        return CommandSpec(("python3", "-c", script), "collect-macos-os-info")

    def _parse_os_info(self, output: str) -> OperatingSystemInfo:
        version, kernel, architecture = parse_os_info_json(output)
        return OperatingSystemInfo(
            family=OperatingSystemFamily.MACOS,
            version=version,
            kernel_build=kernel,
            architecture=Architecture(architecture),
        )

    def _reboot_command(self) -> CommandSpec:
        return CommandSpec(("shutdown", "-r", "now"), "shutdown -r now")

    def _collect_system_logs_command(self) -> CommandSpec:
        return CommandSpec(
            ("log", "show", "--last", "10m", "--style", "compact"),
            "log show --last 10m --style compact",
        )
