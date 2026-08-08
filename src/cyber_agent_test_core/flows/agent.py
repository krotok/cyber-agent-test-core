"""Reusable intent-level Agent flows."""

from cyber_agent_test_core.api import AgentOperations
from cyber_agent_test_core.internal.waiting import Waiter
from cyber_agent_test_core.models import (
    AgentHandle,
    AgentHealth,
    LifecycleAction,
    LifecycleResult,
    LogUploadResult,
    NetworkIsolationResult,
    RegistrationResult,
    ThreatDetectionResult,
)


class _LifecycleFlow:
    def __init__(
        self, operations: AgentOperations, waiter: Waiter | None = None
    ) -> None:
        self._operations = operations
        self._waiter = waiter or Waiter()

    def _run(
        self, agent: AgentHandle, action: LifecycleAction, version: str | None
    ) -> LifecycleResult:
        result = self._operations.lifecycle(agent, action, version)
        if not result.successful:
            return result
        if action is LifecycleAction.UNINSTALL:
            self._waiter.until(
                lambda: self._operations.version(agent),
                lambda observed: observed is None,
                description="Agent removal",
            )
        elif version is not None:
            self._waiter.until(
                lambda: self._operations.version(agent),
                lambda observed: observed == version,
                description=f"Agent version {version}",
            )
        return result


class AgentInstallationFlow(_LifecycleFlow):
    """Install an Agent and wait until its requested version is observable."""

    def install(self, agent: AgentHandle, version: str) -> LifecycleResult:
        return self._run(agent, LifecycleAction.INSTALL, version)


class AgentUpgradeFlow(_LifecycleFlow):
    """Upgrade an Agent and wait for the target version."""

    def upgrade(self, agent: AgentHandle, version: str) -> LifecycleResult:
        return self._run(agent, LifecycleAction.UPGRADE, version)


class AgentDowngradeFlow(_LifecycleFlow):
    """Downgrade an Agent and wait for the target version."""

    def downgrade(self, agent: AgentHandle, version: str) -> LifecycleResult:
        return self._run(agent, LifecycleAction.DOWNGRADE, version)


class AgentRollbackFlow(_LifecycleFlow):
    """Rollback an Agent and wait for the restored version."""

    def rollback(self, agent: AgentHandle, version: str) -> LifecycleResult:
        return self._run(agent, LifecycleAction.ROLLBACK, version)


class AgentUninstallFlow(_LifecycleFlow):
    """Uninstall an Agent and wait until no installed version is observable."""

    def uninstall(self, agent: AgentHandle) -> LifecycleResult:
        return self._run(agent, LifecycleAction.UNINSTALL, None)


class AgentRegistrationFlow:
    """Register an installed Agent and wait for backend acknowledgement."""

    def __init__(
        self, operations: AgentOperations, waiter: Waiter | None = None
    ) -> None:
        self._operations = operations
        self._waiter = waiter or Waiter()

    def register(self, agent: AgentHandle) -> RegistrationResult:
        self._operations.request_registration(agent)
        return self._waiter.until(
            lambda: self._operations.registration(agent),
            lambda result: result.registered,
            description="Agent registration",
            diagnose=lambda result: result.diagnostic or "not registered",
        )


class AgentHealthFlow:
    """Wait for a normalized healthy Agent observation."""

    def __init__(
        self, operations: AgentOperations, waiter: Waiter | None = None
    ) -> None:
        self._operations = operations
        self._waiter = waiter or Waiter()

    def wait_until_healthy(self, agent: AgentHandle) -> AgentHealth:
        return self._waiter.until(
            lambda: self._operations.health(agent),
            lambda health: health.healthy,
            description="healthy Agent",
            diagnose=lambda health: health.diagnostic or health.state,
        )


class ThreatDetectionFlow:
    """Submit a safe sample reference once and wait for its detection."""

    def __init__(
        self, operations: AgentOperations, waiter: Waiter | None = None
    ) -> None:
        self._operations = operations
        self._waiter = waiter or Waiter()

    def detect(
        self, agent: AgentHandle, sample_reference: str
    ) -> ThreatDetectionResult:
        self._operations.submit_threat(agent, sample_reference)
        return self._waiter.until(
            lambda: self._operations.threat_detection(agent, sample_reference),
            lambda result: result.detected,
            description="threat detection event",
            diagnose=lambda result: result.diagnostic or "not detected",
        )


class NetworkIsolationFlow:
    """Request and observe Agent network-isolation state."""

    def __init__(
        self, operations: AgentOperations, waiter: Waiter | None = None
    ) -> None:
        self._operations = operations
        self._waiter = waiter or Waiter()

    def isolate(self, agent: AgentHandle) -> NetworkIsolationResult:
        return self._set(agent, isolated=True)

    def restore(self, agent: AgentHandle) -> NetworkIsolationResult:
        return self._set(agent, isolated=False)

    def _set(self, agent: AgentHandle, *, isolated: bool) -> NetworkIsolationResult:
        self._operations.request_network_isolation(agent, isolated=isolated)
        return self._waiter.until(
            lambda: self._operations.network_isolation(agent),
            lambda result: result.isolated is isolated,
            description=f"network isolation={isolated}",
            diagnose=lambda result: result.diagnostic,
        )


class LogUploadFlow:
    """Request bounded log upload and wait for its acknowledgement."""

    def __init__(
        self, operations: AgentOperations, waiter: Waiter | None = None
    ) -> None:
        self._operations = operations
        self._waiter = waiter or Waiter()

    def upload(self, agent: AgentHandle) -> LogUploadResult:
        self._operations.request_log_upload(agent)
        return self._waiter.until(
            lambda: self._operations.log_upload(agent),
            lambda result: result.uploaded,
            description="Agent log upload",
            diagnose=lambda result: result.diagnostic or "not uploaded",
        )
