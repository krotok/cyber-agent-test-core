"""Beginner-friendly assertions with product-level failure messages."""

from cyber_agent_test_core.models import (
    AgentHealth,
    EventRecord,
    LifecycleResult,
    LogUploadResult,
    ProcessState,
    RegistrationResult,
    ServiceState,
)


class AgentChecks:
    """Assertions for Agent lifecycle, registration, and health."""

    def is_healthy(self, health: AgentHealth) -> None:
        assert health.healthy, (
            f"Agent {health.agent.logical_name!r} is not healthy: "
            f"state={health.state!r}; {health.diagnostic}"
        )

    def is_registered(self, result: RegistrationResult) -> None:
        assert result.registered, (
            f"Agent {result.agent.logical_name!r} is not registered; "
            f"{result.diagnostic}"
        )

    def lifecycle_succeeded(self, result: LifecycleResult) -> None:
        assert result.successful, (
            f"Agent {result.agent.logical_name!r} {result.action.value} failed; "
            f"{result.diagnostic}"
        )


class BackendChecks:
    """Assertions for backend-visible Agent outcomes."""

    def has_backend_reference(self, result: RegistrationResult) -> None:
        assert result.backend_reference, (
            f"registered Agent {result.agent.logical_name!r} has no backend reference"
        )


class ProcessChecks:
    """Assertions for normalized process observations."""

    def is_running(self, process: ProcessState) -> None:
        assert process.running, f"process {process.name!r} is not running"

    def is_stopped(self, process: ProcessState) -> None:
        assert not process.running, f"process {process.name!r} is still running"


class ServiceChecks:
    """Assertions for normalized service observations."""

    def is_running(self, service: ServiceState) -> None:
        assert service.running, f"service {service.name!r} is not running"

    def is_stopped(self, service: ServiceState) -> None:
        assert not service.running, f"service {service.name!r} is still running"


class EventChecks:
    """Assertions over sanitized product events."""

    def contains(self, events: tuple[EventRecord, ...], event_type: str) -> None:
        observed = sorted(event.event_type for event in events)
        assert any(event.event_type == event_type for event in events), (
            f"event {event_type!r} was not found; observed event types: {observed}"
        )


class LogChecks:
    """Assertions over sanitized log lines and upload outcomes."""

    def contains(self, lines: tuple[str, ...], expected: str) -> None:
        assert any(expected in line for line in lines), (
            f"log text {expected!r} was not found in {len(lines)} sanitized lines"
        )

    def upload_succeeded(self, result: LogUploadResult) -> None:
        assert result.uploaded, f"log upload failed; {result.diagnostic}"


class VersionChecks:
    """Assertions for normalized semantic version strings."""

    def equals(self, actual: str | None, expected: str) -> None:
        assert actual == expected, (
            f"unexpected Agent version: expected {expected!r}, observed {actual!r}"
        )

    def is_uninstalled(self, actual: str | None) -> None:
        assert actual is None, f"Agent is still installed with version {actual!r}"
