"""Public OS-neutral operation ports composed by reusable flows."""

from typing import Protocol

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


class AgentOperations(Protocol):
    """Product operation boundary implemented above OS controllers."""

    def lifecycle(
        self, agent: AgentHandle, action: LifecycleAction, version: str | None
    ) -> LifecycleResult: ...

    def request_registration(self, agent: AgentHandle) -> None: ...

    def registration(self, agent: AgentHandle) -> RegistrationResult: ...

    def health(self, agent: AgentHandle) -> AgentHealth: ...

    def submit_threat(self, agent: AgentHandle, sample_reference: str) -> None: ...

    def threat_detection(
        self, agent: AgentHandle, sample_reference: str
    ) -> ThreatDetectionResult: ...

    def request_network_isolation(
        self, agent: AgentHandle, *, isolated: bool
    ) -> None: ...

    def network_isolation(self, agent: AgentHandle) -> NetworkIsolationResult: ...

    def request_log_upload(self, agent: AgentHandle) -> None: ...

    def log_upload(self, agent: AgentHandle) -> LogUploadResult: ...

    def process_state(self, agent: AgentHandle, name: str) -> ProcessState: ...

    def service_state(self, agent: AgentHandle, name: str) -> ServiceState: ...

    def events(self, agent: AgentHandle) -> tuple[EventRecord, ...]: ...

    def logs(self, agent: AgentHandle) -> tuple[str, ...]: ...

    def version(self, agent: AgentHandle) -> str | None: ...
