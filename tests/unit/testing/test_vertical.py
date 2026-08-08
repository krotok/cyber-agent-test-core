"""Unit tests for deterministic fake vertical-slice components."""

import pytest

from cyber_agent_test_core.controllers import OperatingSystemController
from cyber_agent_test_core.models import OperatingSystemFamily
from cyber_agent_test_core.testing import (
    FakeAgentController,
    FakeHostLeaseManager,
    FakeInventory,
    FakeSSHTransport,
    FakeVerticalSliceRuntime,
    FakeWinRMTransport,
)


def test_fake_lease_is_exclusive_and_releasable() -> None:
    events: list[str] = []
    manager = FakeHostLeaseManager(FakeInventory(), events)
    lease = manager.acquire(OperatingSystemFamily.LINUX)

    with pytest.raises(RuntimeError, match="already leased"):
        manager.acquire(OperatingSystemFamily.LINUX)

    manager.release(lease)
    assert not manager.is_leased("fake-linux")
    assert events == ["lease:fake-linux", "release:fake-linux"]


@pytest.mark.parametrize(
    ("family", "transport_type"),
    [
        (OperatingSystemFamily.LINUX, FakeSSHTransport),
        (OperatingSystemFamily.WINDOWS, FakeWinRMTransport),
        (OperatingSystemFamily.MACOS, FakeSSHTransport),
    ],
)
def test_builds_real_os_controller_over_expected_fake_transport(
    family: OperatingSystemFamily,
    transport_type: type[FakeSSHTransport] | type[FakeWinRMTransport],
) -> None:
    runtime = FakeVerticalSliceRuntime(family)
    lease = runtime.acquire_host(runtime.test_run_config())

    controller = runtime.os_controller(runtime.host(lease))

    assert isinstance(controller, OperatingSystemController)
    assert isinstance(controller._transport, transport_type)


@pytest.mark.parametrize("family", list(OperatingSystemFamily))
def test_fake_agent_completes_lifecycle_for_every_os(
    family: OperatingSystemFamily,
) -> None:
    runtime = FakeVerticalSliceRuntime(family)
    lease = runtime.acquire_host(runtime.test_run_config())
    host = runtime.host(lease)
    os_controller = runtime.os_controller(host)
    controller = runtime.agent_controller(host, os_controller)
    assert isinstance(controller, FakeAgentController)
    agent = runtime.agent_handle(host)

    runtime.install_agent(agent, "4.8.1")
    runtime.start_agent(agent)
    registration = runtime.register_agent(agent)
    health = runtime.wait_for_health(agent)

    assert registration.registered
    assert registration.backend_reference == f"backend-{host.logical_name}"
    assert health.healthy
    assert runtime.observed_agent_version(agent) == "4.8.1"
    runtime.uninstall_agent(agent)
    runtime.cleanup_host(host)
    assert runtime.verify_cleanup(host)
    runtime.release_host(lease)
    assert runtime.events[-1] == f"release:{host.logical_name}"
    event_actions = [event.split(":", 1)[0] for event in runtime.events]
    assert event_actions.index("install") < event_actions.index("start")
    assert event_actions.index("start") < event_actions.index("register")
    assert event_actions.index("register") < event_actions.index("status")
    assert event_actions.index("uninstall") < event_actions.index("cleanup")
    assert event_actions.index("cleanup") < event_actions.index("release")

