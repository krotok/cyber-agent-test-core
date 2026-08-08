"""Fully in-memory cross-platform lifecycle composition root."""

from dataclasses import dataclass
from datetime import UTC, datetime

from cyber_agent_test_core.backend import (
    BackendAgentState,
    BackendAgentStatus,
    FakeBackendClient,
)
from cyber_agent_test_core.backend import RegistrationResult as BackendRegistration
from cyber_agent_test_core.config import (
    BackendConfig,
    CredentialsReference,
    EnvironmentConfig,
    HostConfig,
    LaboratoryConfig,
    OperatingSystemConfig,
    TestRunConfig,
)
from cyber_agent_test_core.controllers import OperatingSystemController
from cyber_agent_test_core.internal.waiting import Waiter
from cyber_agent_test_core.inventory import ConnectionType, Host, HostState
from cyber_agent_test_core.models import (
    AgentHandle,
    AgentHealth,
    Architecture,
    Capability,
    CapabilitySet,
    DiagnosticDetail,
    HostPreparation,
    OperatingSystemFamily,
    RegistrationResult,
)
from cyber_agent_test_core.platforms.linux import LinuxController
from cyber_agent_test_core.platforms.macos import MacOSController
from cyber_agent_test_core.platforms.windows import WindowsController
from cyber_agent_test_core.transports import FakeTransport


class FakeSSHTransport(FakeTransport):
    """Named SSH fake; records commands and performs no network I/O."""


class FakeWinRMTransport(FakeTransport):
    """Named WinRM fake; records commands and performs no network I/O."""


class FakeInventory:
    """Deterministic three-OS inventory with mutable availability state."""

    def __init__(self) -> None:
        credential = CredentialsReference(reference="vault:fake/hosts")
        self.hosts = (
            Host(
                logical_name="fake-linux",
                operating_system=OperatingSystemFamily.LINUX,
                os_version="24.04",
                architecture=Architecture.X86_64,
                connection_type=ConnectionType.SSH,
                credentials_reference=credential,
                snapshot_supported=True,
            ),
            Host(
                logical_name="fake-windows",
                operating_system=OperatingSystemFamily.WINDOWS,
                os_version="2022",
                architecture=Architecture.X86_64,
                connection_type=ConnectionType.WINRM,
                credentials_reference=credential,
                snapshot_supported=True,
            ),
            Host(
                logical_name="fake-macos",
                operating_system=OperatingSystemFamily.MACOS,
                os_version="15.0",
                architecture=Architecture.X86_64,
                connection_type=ConnectionType.SSH,
                credentials_reference=credential,
                snapshot_supported=True,
            ),
        )

    def select(self, operating_system: OperatingSystemFamily) -> Host:
        """Select the first available host for the requested OS."""
        for host in self.hosts:
            if (
                host.operating_system is operating_system
                and host.state is HostState.AVAILABLE
            ):
                return host
        raise RuntimeError(f"no fake host available for {operating_system.value}")


@dataclass(frozen=True, slots=True)
class FakeHostLease:
    """Opaque fake ownership token."""

    lease_id: str
    host: Host


class FakeHostLeaseManager:
    """In-memory exclusive lease manager with observable release."""

    def __init__(self, inventory: FakeInventory, events: list[str]) -> None:
        self._inventory = inventory
        self._events = events
        self._active: set[str] = set()

    def acquire(self, operating_system: OperatingSystemFamily) -> FakeHostLease:
        """Acquire one exclusive host or fail without overbooking it."""
        host = self._inventory.select(operating_system)
        if host.logical_name in self._active:
            raise RuntimeError(f"fake host already leased: {host.logical_name}")
        self._active.add(host.logical_name)
        self._events.append(f"lease:{host.logical_name}")
        return FakeHostLease(f"lease-{host.logical_name}", host)

    def release(self, lease: FakeHostLease) -> None:
        """Release idempotently and record the lifecycle boundary."""
        if lease.host.logical_name in self._active:
            self._active.remove(lease.host.logical_name)
            self._events.append(f"release:{lease.host.logical_name}")

    def is_leased(self, logical_name: str) -> bool:
        """Return whether a fake host currently has an owner."""
        return logical_name in self._active


class FakeAgentController:
    """Stateful Agent fake implemented through a real OS controller boundary."""

    def __init__(
        self,
        agent: AgentHandle,
        operating_system: OperatingSystemController,
        backend: FakeBackendClient,
        events: list[str],
    ) -> None:
        self.agent = agent
        self.operating_system = operating_system
        self.backend = backend
        self.events = events
        self.version: str | None = None
        self.running = False
        self.backend_id: str | None = None

    def install(self, version: str) -> None:
        """Install through the OS adapter and expose the requested version."""
        self.operating_system.install_package(f"fake-agent-{version}.package")
        self.version = version
        self.events.append(f"install:{self.agent.logical_name}:{version}")

    def start(self) -> None:
        """Start the fake service through the OS adapter."""
        if self.version is None:
            raise RuntimeError("cannot start an uninstalled fake Agent")
        self.operating_system.start_service("cyber-agent")
        self.running = True
        self.events.append(f"start:{self.agent.logical_name}")

    def register(self) -> RegistrationResult:
        """Register through FakeBackendClient and make status immediately online."""
        if not self.running:
            raise RuntimeError("cannot register a stopped fake Agent")
        backend_id = f"backend-{self.agent.logical_name}"
        now = datetime(2026, 1, 1, tzinfo=UTC)
        self.backend.registrations[self.agent.logical_name] = BackendRegistration(
            agent_id=backend_id,
            registered_at=now,
            correlation_id=f"correlation-{self.agent.logical_name}",
        )
        self.backend.statuses[backend_id] = BackendAgentStatus(
            agent_id=backend_id,
            state=BackendAgentState.ONLINE,
            last_seen_at=now,
        )
        result = self.backend.register_agent(
            self.agent.logical_name,
            idempotency_key=f"register-{self.agent.logical_name}",
        )
        self.backend_id = result.agent_id
        self.events.append(f"register:{self.agent.logical_name}")
        return RegistrationResult(self.agent, True, result.agent_id)

    def health(self) -> AgentHealth:
        """Read backend status and return a public health observation."""
        if self.backend_id is None:
            return AgentHealth(self.agent, False, "unregistered")
        status = self.backend.get_agent_status(self.backend_id)
        healthy = status.state is BackendAgentState.ONLINE
        self.events.append(f"status:{self.agent.logical_name}:{status.state.value}")
        return AgentHealth(self.agent, healthy, status.state.value)

    def uninstall(self) -> None:
        """Remove the package and all mutable fake Agent state."""
        self.operating_system.uninstall_package("cyber-agent")
        self.version = None
        self.running = False
        self.backend_id = None
        self.events.append(f"uninstall:{self.agent.logical_name}")

    def is_healthy(self) -> bool:
        """Satisfy the private AgentController behavior contract."""
        return self.health().healthy


class FakeVerticalSliceRuntime:
    """Composition root used by public lifecycle fixtures in fake mode."""

    def __init__(self, operating_system: OperatingSystemFamily) -> None:
        self.operating_system = operating_system
        self.events: list[str] = []
        self.inventory = FakeInventory()
        self.lease_manager = FakeHostLeaseManager(self.inventory, self.events)
        self.backend = FakeBackendClient()
        self._os_controllers: dict[str, OperatingSystemController] = {}
        self._agents: dict[str, FakeAgentController] = {}
        self._config = self._build_test_run_config()
        self._environment = self._build_environment()
        self._laboratory = self._build_laboratory()

    @staticmethod
    def _backend_config() -> BackendConfig:
        return BackendConfig.model_validate(
            {
                "version": "12.5",
                "base_url": "https://fake-backend.invalid",
                "credentials": {"reference": "vault:fake/backend"},
            }
        )

    def _build_test_run_config(self) -> TestRunConfig:
        return TestRunConfig.model_validate(
            {
                "agent_version": "4.8.1",
                "backend_version": "12.5",
                "environment": "fake-stage",
                "lab": "fake-lab",
                "suite": "smoke",
                "enabled_features": ["registration"],
                "target_hosts": [f"fake-{self.operating_system.value}"],
                "tenant": {"reference": "vault:fake/tenant"},
                "build_id": "fake-package-build",
                "git_commit": "abcdef1234567",
                "execution_id": f"fake-{self.operating_system.value}",
                "architecture": "x86_64",
                "ci_context": {"job_id": "fake-ci-build"},
            }
        )

    def _build_environment(self) -> EnvironmentConfig:
        return EnvironmentConfig(
            name="fake-stage",
            backend=self._backend_config(),
            allowed_suites=frozenset({"smoke"}),
        )

    def _build_laboratory(self) -> LaboratoryConfig:
        hosts = tuple(
            HostConfig(
                host_id=host.logical_name,
                operating_system=OperatingSystemConfig(
                    family=host.operating_system,
                    version=host.os_version,
                    architecture=host.architecture,
                ),
                capabilities=frozenset(capability.value for capability in Capability),
            )
            for host in self.inventory.hosts
        )
        return LaboratoryConfig(
            name="fake-lab",
            allowed_environments=frozenset({"fake-stage"}),
            allowed_suites=frozenset({"smoke"}),
            hosts=hosts,
        )

    def test_run_config(self) -> TestRunConfig:
        return self._config

    def environment_config(self, name: str) -> EnvironmentConfig:
        if name != self._environment.name:
            raise KeyError(name)
        return self._environment

    def lab_inventory(self, name: str) -> LaboratoryConfig:
        if name != self._laboratory.name:
            raise KeyError(name)
        return self._laboratory

    def acquire_host(self, config: TestRunConfig) -> FakeHostLease:
        del config
        return self.lease_manager.acquire(self.operating_system)

    def release_host(self, lease: object) -> None:
        if not isinstance(lease, FakeHostLease):
            raise TypeError("expected FakeHostLease")
        self.lease_manager.release(lease)

    def heartbeat_host(self, lease: object) -> None:
        if not isinstance(lease, FakeHostLease):
            raise TypeError("expected FakeHostLease")
        if not self.lease_manager.is_leased(lease.host.logical_name):
            raise RuntimeError("fake host lease was lost")

    def host(self, lease: object) -> Host:
        if not isinstance(lease, FakeHostLease):
            raise TypeError("expected FakeHostLease")
        return lease.host

    def prepare_host(self, host: object, mode: HostPreparation) -> None:
        selected = self._require_host(host)
        self.events.append(f"prepare:{selected.logical_name}:{mode.value}")

    def cleanup_host(self, host: object) -> None:
        selected = self._require_host(host)
        self.events.append(f"cleanup:{selected.logical_name}")

    def verify_cleanup(self, host: object) -> bool:
        selected = self._require_host(host)
        agent = self._agents.get(selected.logical_name)
        clean = agent is None or (agent.version is None and not agent.running)
        self.events.append(f"verify-cleanup:{selected.logical_name}:{clean}")
        return clean

    @staticmethod
    def _require_host(value: object) -> Host:
        if not isinstance(value, Host):
            raise TypeError("expected fake Host")
        return value

    def os_controller(self, host: object) -> OperatingSystemController:
        selected = self._require_host(host)
        existing = self._os_controllers.get(selected.logical_name)
        if existing is not None:
            return existing
        transport: FakeTransport
        if selected.connection_type is ConnectionType.WINRM:
            transport = FakeWinRMTransport(selected.logical_name)
            controller: OperatingSystemController = WindowsController(transport)
        else:
            transport = FakeSSHTransport(selected.logical_name)
            controller = (
                LinuxController(transport)
                if selected.operating_system is OperatingSystemFamily.LINUX
                else MacOSController(transport)
            )
        transport.connect()
        self._os_controllers[selected.logical_name] = controller
        self.events.append(f"controller:{selected.logical_name}")
        return controller

    def agent_controller(
        self, host: object, os_controller: object
    ) -> FakeAgentController:
        selected = self._require_host(host)
        if not isinstance(os_controller, OperatingSystemController):
            raise TypeError("expected OperatingSystemController")
        return self._agent(selected, os_controller)

    def backend_client(self, environment: EnvironmentConfig) -> FakeBackendClient:
        if environment.name != self._environment.name:
            raise KeyError(environment.name)
        return self.backend

    def agent_handle(self, host: object) -> AgentHandle:
        return AgentHandle(self._require_host(host).logical_name)

    def _agent(
        self,
        host: Host,
        controller: OperatingSystemController | None = None,
    ) -> FakeAgentController:
        existing = self._agents.get(host.logical_name)
        if existing is not None:
            return existing
        agent = FakeAgentController(
            AgentHandle(host.logical_name),
            controller or self.os_controller(host),
            self.backend,
            self.events,
        )
        self._agents[host.logical_name] = agent
        return agent

    def _by_handle(self, agent: AgentHandle) -> FakeAgentController:
        host = next(
            host
            for host in self.inventory.hosts
            if host.logical_name == agent.logical_name
        )
        return self._agent(host)

    def install_agent(self, agent: AgentHandle, version: str) -> None:
        self._by_handle(agent).install(version)

    def rollback_agent(self, agent: AgentHandle) -> None:
        self.events.append(f"rollback:{agent.logical_name}")

    def uninstall_agent(self, agent: AgentHandle) -> None:
        self._by_handle(agent).uninstall()

    def start_agent(self, agent: AgentHandle) -> None:
        self._by_handle(agent).start()

    def register_agent(self, agent: AgentHandle) -> RegistrationResult:
        return self._by_handle(agent).register()

    def wait_for_health(self, agent: AgentHandle) -> AgentHealth:
        return Waiter().until(
            self._by_handle(agent).health,
            lambda health: health.healthy,
            description="fake backend Agent status online",
            diagnose=lambda health: health.state,
        )

    def observed_agent_version(self, agent: AgentHandle) -> str | None:
        return self._by_handle(agent).version

    def capabilities(self, agent: AgentHandle) -> CapabilitySet:
        del agent
        return CapabilitySet(values=frozenset(Capability))

    def collect_diagnostics(self, host: object, level: DiagnosticDetail) -> None:
        selected = self._require_host(host)
        self.events.append(f"diagnostics:{selected.logical_name}:{level.value}")

    def diagnostic_attachments(self, host: object) -> dict[str, object]:
        selected = self._require_host(host)
        return {
            "Agent logs": "fake Agent log",
            "installer logs": "fake installer log",
            "service status": {"running": self._agent(selected).running},
            "process list": ["cyber-agent"],
            "OS info": {
                "family": selected.operating_system.value,
                "version": selected.os_version,
            },
            "backend response": {"status": "online"},
            "redacted command": "fake-command <redacted>",
            "Agent events": tuple(self.events),
            "network diagnostics": "fake network reachable",
        }
