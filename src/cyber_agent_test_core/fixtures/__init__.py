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
from cyber_agent_test_core.fixtures.lifecycle import (
    agent_controller,
    backend_client,
    capability_set,
    clean_host,
    diagnostics_collector,
    environment_config,
    execution_context,
    healthy_agent,
    host,
    host_lease,
    installed_agent,
    lab_inventory,
    os_controller,
    registered_agent,
    running_agent,
    test_run_config,
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
from cyber_agent_test_core.models import AgentHandle


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
    "agent_controller",
    "agent_handle",
    "agent_operations",
    "agent_version",
    "backend_checks",
    "backend_client",
    "capability_set",
    "clean_host",
    "diagnostics_collector",
    "downgrade_flow",
    "environment_config",
    "event_checks",
    "execution_context",
    "health_flow",
    "healthy_agent",
    "host",
    "host_lease",
    "installation_flow",
    "installed_agent",
    "lab_inventory",
    "log_checks",
    "log_upload_flow",
    "network_isolation_flow",
    "os_controller",
    "process_checks",
    "registered_agent",
    "registration_flow",
    "rollback_flow",
    "running_agent",
    "service_checks",
    "test_run_config",
    "threat_detection_flow",
    "uninstall_flow",
    "upgrade_flow",
    "version_checks",
]
