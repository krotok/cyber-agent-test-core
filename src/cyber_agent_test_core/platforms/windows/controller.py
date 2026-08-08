"""Windows command construction and result parsing."""

from cyber_agent_test_core.controllers import (
    OperatingSystemController,
    OperatingSystemInfo,
    ServiceStatus,
)
from cyber_agent_test_core.models import Architecture, OperatingSystemFamily
from cyber_agent_test_core.platforms.common import encoded_text, parse_os_info_json
from cyber_agent_test_core.transports import CommandResult, CommandSpec


def _powershell(script: str, redacted: str) -> CommandSpec:
    """Create a non-interactive PowerShell command."""
    return CommandSpec(
        ("powershell", "-NoProfile", "-NonInteractive", "-Command", script),
        redacted,
    )


def _literal(value: str) -> str:
    """Escape an external value as a single-quoted PowerShell literal."""
    return "'" + value.replace("'", "''") + "'"


class WindowsController(OperatingSystemController):
    """Implement Windows operations without owning WinRM mechanics."""

    def _file_exists_command(self, path: str) -> CommandSpec:
        return _powershell(
            f"if (Test-Path -LiteralPath {_literal(path)}) "
            "{ exit 0 } else { exit 1 }",
            f"Test-Path <{path}>",
        )

    def _read_file_command(self, path: str) -> CommandSpec:
        return _powershell(
            f"Get-Content -Raw -LiteralPath {_literal(path)}",
            f"Get-Content <{path}>",
        )

    def _write_file_command(self, path: str, content: str) -> CommandSpec:
        encoded = encoded_text(content)
        script = (
            f"[IO.File]::WriteAllBytes({_literal(path)},"
            f"[Convert]::FromBase64String({_literal(encoded)}))"
        )
        return _powershell(script, f"WriteAllBytes <{path}> <redacted-content>")

    def _delete_file_command(self, path: str) -> CommandSpec:
        return _powershell(
            "Remove-Item -Force -ErrorAction SilentlyContinue "
            f"-LiteralPath {_literal(path)}",
            f"Remove-Item <{path}>",
        )

    def _process_exists_command(self, process_name: str) -> CommandSpec:
        return _powershell(
            f"if (Get-Process -Name {_literal(process_name)} "
            "-ErrorAction SilentlyContinue) "
            "{ exit 0 } else { exit 1 }",
            f"Get-Process <{process_name}>",
        )

    def _start_service_command(self, service_name: str) -> CommandSpec:
        return _powershell(
            f"Start-Service -Name {_literal(service_name)}",
            f"Start-Service <{service_name}>",
        )

    def _stop_service_command(self, service_name: str) -> CommandSpec:
        return _powershell(
            f"Stop-Service -Name {_literal(service_name)} -Force",
            f"Stop-Service <{service_name}>",
        )

    def _restart_service_command(self, service_name: str) -> CommandSpec:
        return _powershell(
            f"Restart-Service -Name {_literal(service_name)} -Force",
            f"Restart-Service <{service_name}>",
        )

    def _service_status_command(self, service_name: str) -> CommandSpec:
        return _powershell(
            f"(Get-Service -Name {_literal(service_name)}).Status.ToString()",
            f"Get-Service <{service_name}>",
        )

    def _parse_service_status(self, result: CommandResult) -> ServiceStatus:
        state = result.stdout.strip().lower()
        if result.exit_code != 0:
            return ServiceStatus.UNKNOWN
        if state == "running":
            return ServiceStatus.RUNNING
        if state in {"stopped", "stop pending"}:
            return ServiceStatus.STOPPED
        return ServiceStatus.UNKNOWN

    def _install_package_command(self, package_path: str) -> CommandSpec:
        return CommandSpec(
            ("msiexec.exe", "/i", package_path, "/qn", "/norestart"),
            f"msiexec /i {package_path} /qn /norestart",
        )

    def _uninstall_package_command(self, package_name: str) -> CommandSpec:
        return CommandSpec(
            ("msiexec.exe", "/x", package_name, "/qn", "/norestart"),
            f"msiexec /x {package_name} /qn /norestart",
        )

    def _os_info_command(self) -> CommandSpec:
        script = (
            "$os=Get-CimInstance Win32_OperatingSystem;"
            "$cpu=Get-CimInstance Win32_Processor | Select-Object -First 1;"
            "@{version=$os.Version;kernel_build=$os.BuildNumber;"
            "architecture=if($cpu.AddressWidth -eq 64 -and $env:PROCESSOR_ARCHITECTURE "
            "-match 'ARM'){'arm64'}else{'x86_64'}}|ConvertTo-Json -Compress"
        )
        return _powershell(script, "collect-windows-os-info")

    def _parse_os_info(self, output: str) -> OperatingSystemInfo:
        version, kernel, architecture = parse_os_info_json(output)
        return OperatingSystemInfo(
            family=OperatingSystemFamily.WINDOWS,
            version=version,
            kernel_build=kernel,
            architecture=Architecture(architecture),
        )

    def _reboot_command(self) -> CommandSpec:
        return _powershell(
            "Restart-Computer -Force",
            "Restart-Computer -Force",
        )

    def _collect_system_logs_command(self) -> CommandSpec:
        return _powershell(
            "Get-WinEvent -LogName System -MaxEvents 500 | Format-List",
            "Get-WinEvent System -MaxEvents 500",
        )
