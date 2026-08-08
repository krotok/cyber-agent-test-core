"""Shared OS controller contract tests using only FakeTransport."""

import json
from collections.abc import Callable

import pytest

from cyber_agent_test_core.controllers import (
    OperatingSystemController,
    ServiceStatus,
)
from cyber_agent_test_core.models import OperatingSystemFamily
from cyber_agent_test_core.platforms.linux import LinuxController
from cyber_agent_test_core.platforms.macos import MacOSController
from cyber_agent_test_core.platforms.windows import WindowsController
from cyber_agent_test_core.transports import (
    CommandSpec,
    FakeTransport,
    HostUnavailableError,
    TransportError,
)

ControllerFactory = Callable[[FakeTransport], OperatingSystemController]


@pytest.mark.parametrize(
    ("controller_factory", "family", "running_output"),
    [
        (LinuxController, OperatingSystemFamily.LINUX, "active"),
        (WindowsController, OperatingSystemFamily.WINDOWS, "Running"),
        (MacOSController, OperatingSystemFamily.MACOS, "state = running"),
    ],
)
def test_controller_operations_delegate_os_commands(
    controller_factory: ControllerFactory,
    family: OperatingSystemFamily,
    running_output: str,
) -> None:
    transport = FakeTransport()
    transport.connect()
    controller = controller_factory(transport)
    transport.queue_result()
    transport.queue_result(stdout="file content")
    transport.queue_result()
    transport.queue_result()
    transport.queue_result()
    transport.queue_result()
    transport.queue_result()
    transport.queue_result()
    transport.queue_result(stdout=running_output)
    transport.queue_result()
    transport.queue_result()
    transport.queue_result(
        stdout=json.dumps(
            {
                "version": "synthetic-version",
                "kernel_build": "synthetic-kernel",
                "architecture": "x86_64",
            }
        )
    )
    transport.queue_result(stdout="system logs")
    transport.queue_result()

    assert controller.file_exists("synthetic-path")
    assert controller.read_file("synthetic-path") == "file content"
    controller.write_file("synthetic-path", "sensitive-content-placeholder")
    controller.delete_file("synthetic-path")
    assert controller.process_exists("synthetic-process")
    controller.start_service("synthetic-service")
    controller.stop_service("synthetic-service")
    controller.restart_service("synthetic-service")
    assert controller.service_status("synthetic-service") is ServiceStatus.RUNNING
    controller.install_package("synthetic-package")
    controller.uninstall_package("synthetic-package")
    info = controller.get_os_info()
    assert info.family is family
    assert info.version == "synthetic-version"
    assert controller.collect_system_logs() == "system logs"
    controller.reboot()

    assert len(transport.commands) == 14
    assert "sensitive-content-placeholder" not in transport.commands[2].redacted_command
    assert not transport.connected


@pytest.mark.parametrize(
    "controller_factory",
    [LinuxController, WindowsController, MacOSController],
)
def test_controller_execute_preserves_command_result(
    controller_factory: ControllerFactory,
) -> None:
    transport = FakeTransport()
    transport.connect()
    transport.queue_result(exit_code=3, stderr="synthetic failure")
    controller = controller_factory(transport)

    result = controller.execute(CommandSpec(("opaque",), "opaque"))

    assert result.exit_code == 3


def test_wait_until_online_uses_bounded_probes_without_sleep() -> None:
    transport = FakeTransport()
    transport.queue_availability(False, False, True)
    controller = LinuxController(transport)

    controller.wait_until_online(max_attempts=3)


def test_wait_until_online_reports_unavailable_host() -> None:
    transport = FakeTransport()
    transport.queue_availability(False, False)
    controller = LinuxController(transport)

    with pytest.raises(HostUnavailableError, match="after 2 probes"):
        controller.wait_until_online(max_attempts=2)


def test_failed_mutation_is_not_retryable_product_behavior() -> None:
    transport = FakeTransport()
    transport.connect()
    transport.queue_result(exit_code=1, stderr="synthetic OS error")
    controller = LinuxController(transport)

    with pytest.raises(TransportError) as captured:
        controller.start_service("synthetic-service")

    assert not captured.value.retryable


def test_windows_controller_escapes_powershell_literals() -> None:
    transport = FakeTransport()
    transport.connect()
    controller = WindowsController(transport)

    controller.file_exists("synthetic'path")

    script = transport.commands[0].argv[-1]
    assert "'synthetic''path'" in script
