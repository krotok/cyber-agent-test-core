"""Stable pytest fixtures for product tests and integration adapters."""

import pytest

from cyber_agent_test_core.api import AgentOperations
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
from cyber_agent_test_core.models import AgentHandle, AgentHealth


@pytest.fixture
def agent_operations() -> AgentOperations:
    """Integration extension point supplying OS-neutral Agent operations."""
    raise RuntimeError("the test environment must provide agent_operations")


@pytest.fixture
def agent_handle() -> AgentHandle:
    """Integration extension point supplying a leased Agent target."""
    raise RuntimeError("the test environment must provide agent_handle")


@pytest.fixture
def agent_version() -> str:
    """Integration extension point supplying the configured target version."""
    raise RuntimeError("the test environment must provide agent_version")


@pytest.fixture
def installation_flow(agent_operations: AgentOperations) -> AgentInstallationFlow:
    return AgentInstallationFlow(agent_operations)


@pytest.fixture
def registration_flow(agent_operations: AgentOperations) -> AgentRegistrationFlow:
    return AgentRegistrationFlow(agent_operations)


@pytest.fixture
def health_flow(agent_operations: AgentOperations) -> AgentHealthFlow:
    return AgentHealthFlow(agent_operations)


@pytest.fixture
def upgrade_flow(agent_operations: AgentOperations) -> AgentUpgradeFlow:
    return AgentUpgradeFlow(agent_operations)


@pytest.fixture
def downgrade_flow(agent_operations: AgentOperations) -> AgentDowngradeFlow:
    return AgentDowngradeFlow(agent_operations)


@pytest.fixture
def rollback_flow(agent_operations: AgentOperations) -> AgentRollbackFlow:
    return AgentRollbackFlow(agent_operations)


@pytest.fixture
def uninstall_flow(agent_operations: AgentOperations) -> AgentUninstallFlow:
    return AgentUninstallFlow(agent_operations)


@pytest.fixture
def threat_detection_flow(agent_operations: AgentOperations) -> ThreatDetectionFlow:
    return ThreatDetectionFlow(agent_operations)


@pytest.fixture
def network_isolation_flow(agent_operations: AgentOperations) -> NetworkIsolationFlow:
    return NetworkIsolationFlow(agent_operations)


@pytest.fixture
def log_upload_flow(agent_operations: AgentOperations) -> LogUploadFlow:
    return LogUploadFlow(agent_operations)


@pytest.fixture
def installed_agent(
    agent_handle: AgentHandle,
    agent_version: str,
    installation_flow: AgentInstallationFlow,
) -> AgentHandle:
    """Install the configured Agent version and return its stable handle."""
    result = installation_flow.install(agent_handle, agent_version)
    if not result.successful:
        raise AssertionError(f"Agent installation failed: {result.diagnostic}")
    return agent_handle


@pytest.fixture
def healthy_agent(
    installed_agent: AgentHandle, health_flow: AgentHealthFlow
) -> AgentHealth:
    """Return a ready health observation after bounded framework polling."""
    return health_flow.wait_until_healthy(installed_agent)


@pytest.fixture
def agent_checks() -> AgentChecks:
    return AgentChecks()


@pytest.fixture
def backend_checks() -> BackendChecks:
    return BackendChecks()


@pytest.fixture
def process_checks() -> ProcessChecks:
    return ProcessChecks()


@pytest.fixture
def service_checks() -> ServiceChecks:
    return ServiceChecks()


@pytest.fixture
def event_checks() -> EventChecks:
    return EventChecks()


@pytest.fixture
def log_checks() -> LogChecks:
    return LogChecks()


@pytest.fixture
def version_checks() -> VersionChecks:
    return VersionChecks()


__all__ = [
    "agent_checks",
    "agent_handle",
    "agent_operations",
    "agent_version",
    "backend_checks",
    "downgrade_flow",
    "event_checks",
    "health_flow",
    "healthy_agent",
    "installation_flow",
    "installed_agent",
    "log_checks",
    "log_upload_flow",
    "network_isolation_flow",
    "process_checks",
    "registration_flow",
    "rollback_flow",
    "service_checks",
    "threat_detection_flow",
    "uninstall_flow",
    "upgrade_flow",
    "version_checks",
]
