"""Flows and checks use fake product controllers and an injected clock."""

from collections import deque

import pytest

from cyber_agent_test_core.checks import (
    AgentChecks,
    BackendChecks,
    EventChecks,
    LogChecks,
    ProcessChecks,
    ServiceChecks,
    VersionChecks,
)
from cyber_agent_test_core.flows import (
    AgentDowngradeFlow,
    AgentHealthFlow,
    AgentInstallationFlow,
    AgentRegistrationFlow,
    AgentRollbackFlow,
    AgentUninstallFlow,
    AgentUpgradeFlow,
    LogUploadFlow,
    NetworkIsolationFlow,
    ThreatDetectionFlow,
)
from cyber_agent_test_core.internal.waiting import (
    Waiter,
    WaitPolicy,
    WaitTimeoutError,
)
from cyber_agent_test_core.models import (
    AgentHandle,
    AgentHealth,
    EventRecord,
    LifecycleAction,
    LifecycleResult,
    LogUploadResult,
    NetworkIsolationResult,
    ProcessState,
    RegistrationResult,
    ServiceState,
    ThreatDetectionResult,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0
        self.intervals: list[float] = []

    def now(self) -> float:
        return self.value

    def wait(self, seconds: float) -> None:
        self.intervals.append(seconds)
        self.value += seconds


class FakeAgentOperations:
    """OS-independent fake representing a controller composition."""

    def __init__(self, agent: AgentHandle) -> None:
        self.agent = agent
        self.current_version: str | None = None
        self.health_values = deque([AgentHealth(agent, True, "healthy")])
        self.registration_values = deque([RegistrationResult(agent, True, "backend-1")])
        self.threat_values = deque([ThreatDetectionResult(True, "event-1")])
        self.isolation_values = deque([NetworkIsolationResult(agent, True)])
        self.upload_values = deque([LogUploadResult(agent, True, "upload-1")])
        self.actions: list[str] = []

    def lifecycle(
        self, agent: AgentHandle, action: LifecycleAction, version: str | None
    ) -> LifecycleResult:
        self.actions.append(action.value)
        self.current_version = None if action is LifecycleAction.UNINSTALL else version
        return LifecycleResult(agent, action, self.current_version, True)

    def request_registration(self, agent: AgentHandle) -> None:
        self.actions.append(f"register:{agent.logical_name}")

    def registration(self, agent: AgentHandle) -> RegistrationResult:
        return self.registration_values.popleft()

    def health(self, agent: AgentHandle) -> AgentHealth:
        return self.health_values.popleft()

    def submit_threat(self, agent: AgentHandle, sample_reference: str) -> None:
        self.actions.append(f"threat:{sample_reference}")

    def threat_detection(
        self, agent: AgentHandle, sample_reference: str
    ) -> ThreatDetectionResult:
        return self.threat_values.popleft()

    def request_network_isolation(self, agent: AgentHandle, *, isolated: bool) -> None:
        self.actions.append(f"isolation:{isolated}")

    def network_isolation(self, agent: AgentHandle) -> NetworkIsolationResult:
        return self.isolation_values.popleft()

    def request_log_upload(self, agent: AgentHandle) -> None:
        self.actions.append("upload")

    def log_upload(self, agent: AgentHandle) -> LogUploadResult:
        return self.upload_values.popleft()

    def process_state(self, agent: AgentHandle, name: str) -> ProcessState:
        return ProcessState(name, True)

    def service_state(self, agent: AgentHandle, name: str) -> ServiceState:
        return ServiceState(name, True)

    def events(self, agent: AgentHandle) -> tuple[EventRecord, ...]:
        return (EventRecord("healthy", "ready"),)

    def logs(self, agent: AgentHandle) -> tuple[str, ...]:
        return ("Agent ready",)

    def version(self, agent: AgentHandle) -> str | None:
        return self.current_version


@pytest.fixture
def agent() -> AgentHandle:
    return AgentHandle("host-1")


@pytest.fixture
def operations(agent: AgentHandle) -> FakeAgentOperations:
    return FakeAgentOperations(agent)


@pytest.fixture
def waiter() -> Waiter:
    return Waiter(WaitPolicy(timeout_seconds=2, interval_seconds=1), FakeClock())


def test_lifecycle_flows(
    agent: AgentHandle, operations: FakeAgentOperations, waiter: Waiter
) -> None:
    assert AgentInstallationFlow(operations, waiter).install(agent, "1.0").successful
    assert AgentUpgradeFlow(operations, waiter).upgrade(agent, "2.0").version == "2.0"
    assert AgentDowngradeFlow(operations, waiter).downgrade(agent, "1.5").successful
    assert AgentRollbackFlow(operations, waiter).rollback(agent, "1.0").successful
    assert AgentUninstallFlow(operations, waiter).uninstall(agent).version is None
    assert operations.actions == [
        "install",
        "upgrade",
        "downgrade",
        "rollback",
        "uninstall",
    ]


def test_observation_flows_trigger_each_action_once(
    agent: AgentHandle, operations: FakeAgentOperations, waiter: Waiter
) -> None:
    operations.registration_values = deque(
        [RegistrationResult(agent, False), RegistrationResult(agent, True, "backend-1")]
    )
    assert AgentRegistrationFlow(operations, waiter).register(agent).registered
    assert AgentHealthFlow(operations, waiter).wait_until_healthy(agent).healthy
    assert ThreatDetectionFlow(operations, waiter).detect(agent, "safe-sample").detected
    assert NetworkIsolationFlow(operations, waiter).isolate(agent).isolated
    assert LogUploadFlow(operations, waiter).upload(agent).uploaded
    assert operations.actions == [
        "register:host-1",
        "threat:safe-sample",
        "isolation:True",
        "upload",
    ]


def test_waiter_reports_last_observation_without_sleep() -> None:
    clock = FakeClock()
    waiter = Waiter(WaitPolicy(timeout_seconds=2, interval_seconds=1), clock)
    with pytest.raises(WaitTimeoutError, match="last observation: unhealthy"):
        waiter.until(
            lambda: "unhealthy",
            lambda value: value == "healthy",
            description="healthy Agent",
            diagnose=str,
        )
    assert clock.intervals == [1, 1]


def test_wait_policy_rejects_unbounded_parameters() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        WaitPolicy(timeout_seconds=-1)
    with pytest.raises(ValueError, match="positive"):
        WaitPolicy(interval_seconds=0)


def test_checks_have_intent_level_messages(agent: AgentHandle) -> None:
    AgentChecks().is_healthy(AgentHealth(agent, True, "healthy"))
    AgentChecks().is_registered(RegistrationResult(agent, True, "backend-1"))
    AgentChecks().lifecycle_succeeded(
        LifecycleResult(agent, LifecycleAction.INSTALL, "1.0", True)
    )
    BackendChecks().has_backend_reference(RegistrationResult(agent, True, "ref"))
    ProcessChecks().is_running(ProcessState("agent", True))
    ProcessChecks().is_stopped(ProcessState("agent", False))
    ServiceChecks().is_running(ServiceState("agent", True))
    ServiceChecks().is_stopped(ServiceState("agent", False))
    EventChecks().contains((EventRecord("detection", "found"),), "detection")
    LogChecks().contains(("Agent ready",), "ready")
    LogChecks().upload_succeeded(LogUploadResult(agent, True, "upload"))
    VersionChecks().equals("1.0", "1.0")
    VersionChecks().is_uninstalled(None)


def test_check_failure_is_clear(agent: AgentHandle) -> None:
    with pytest.raises(AssertionError, match=r"is not healthy.*disconnected"):
        AgentChecks().is_healthy(
            AgentHealth(agent, False, "offline", "disconnected from backend")
        )
