"""Common lifecycle fixtures composed over an environment-owned runtime."""

from collections.abc import Iterator
from typing import Protocol

import pytest

from cyber_agent_test_core.api import CORE_VERSION
from cyber_agent_test_core.config import (
    EnvironmentConfig,
    LaboratoryConfig,
    TestRunConfig,
)
from cyber_agent_test_core.diagnostics.artifacts import make_attachment
from cyber_agent_test_core.models import (
    AgentHandle,
    AgentHealth,
    CapabilitySet,
    CleanupMode,
    DiagnosticDetail,
    ExecutionContext,
    HostPreparation,
    RegistrationResult,
)
from cyber_agent_test_core.reporting.allure import (
    apply_test_metadata,
    attach_diagnostic,
)
from cyber_agent_test_core.reporting.context import (
    LoggingContext,
    bind_logging_context,
    reset_logging_context,
)


class LifecycleRuntime(Protocol):
    """Composition-root operations supplied by a lab integration plugin."""

    def test_run_config(self) -> TestRunConfig: ...
    def environment_config(self, name: str) -> EnvironmentConfig: ...
    def lab_inventory(self, name: str) -> LaboratoryConfig: ...
    def acquire_host(self, config: TestRunConfig) -> object: ...
    def release_host(self, lease: object) -> None: ...
    def host(self, lease: object) -> object: ...
    def prepare_host(self, host: object, mode: HostPreparation) -> None: ...
    def cleanup_host(self, host: object) -> None: ...
    def verify_cleanup(self, host: object) -> bool: ...
    def os_controller(self, host: object) -> object: ...
    def agent_controller(self, host: object, os_controller: object) -> object: ...
    def backend_client(self, environment: EnvironmentConfig) -> object: ...
    def agent_handle(self, host: object) -> AgentHandle: ...
    def install_agent(self, agent: AgentHandle, version: str) -> None: ...
    def rollback_agent(self, agent: AgentHandle) -> None: ...
    def uninstall_agent(self, agent: AgentHandle) -> None: ...
    def start_agent(self, agent: AgentHandle) -> None: ...
    def register_agent(self, agent: AgentHandle) -> RegistrationResult: ...
    def wait_for_health(self, agent: AgentHandle) -> AgentHealth: ...
    def capabilities(self, agent: AgentHandle) -> CapabilitySet: ...
    def collect_diagnostics(self, host: object, level: DiagnosticDetail) -> None: ...

    def diagnostic_attachments(self, host: object) -> dict[str, object]: ...


class DiagnosticsCollector:
    """Idempotent per-test diagnostic collection facade."""

    def __init__(
        self,
        runtime: LifecycleRuntime,
        host: object,
        level: DiagnosticDetail,
        test_config: TestRunConfig,
        max_attachment_bytes: int,
    ) -> None:
        self._runtime = runtime
        self._host = host
        self._level = level
        self._test_config = test_config
        self._max_attachment_bytes = max_attachment_bytes
        self._collected = False

    def collect(self) -> None:
        """Collect at most once, including when several finalizers observe failure."""
        if not self._collected:
            self._runtime.collect_diagnostics(self._host, self._level)
            provider = getattr(self._runtime, "diagnostic_attachments", None)
            values: dict[str, object] = {} if provider is None else provider(self._host)
            values["test config"] = self._test_config.model_dump(mode="json")
            required = (
                "Agent logs",
                "installer logs",
                "service status",
                "process list",
                "OS info",
                "backend response",
                "redacted command",
                "Agent events",
                "network diagnostics",
            )
            for name in required:
                values.setdefault(name, "not available from lifecycle runtime")
            for name, value in values.items():
                attach_diagnostic(
                    make_attachment(name, value, max_bytes=self._max_attachment_bytes)
                )
            self._collected = True


_LIFECYCLE_FIXTURES = frozenset(
    {
        "host_lease",
        "host",
        "clean_host",
        "os_controller",
        "agent_controller",
        "backend_client",
        "installed_agent",
        "running_agent",
        "registered_agent",
        "healthy_agent",
        "capability_set",
        "diagnostics_collector",
    }
)


@pytest.fixture(autouse=True)
def _core_lifecycle_safety_guard(
    request: pytest.FixtureRequest,
    execution_context: ExecutionContext,
) -> None:
    """Enforce safety policy before any lifecycle fixture mutates a target."""
    requested = _LIFECYCLE_FIXTURES.intersection(request.fixturenames)
    if not requested:
        return
    destructive = request.node.get_closest_marker("destructive") is not None
    if (
        destructive
        and execution_context.host_preparation is HostPreparation.REUSE
        and not execution_context.allow_destructive_reuse
    ):
        pytest.fail(
            "destructive tests on reused hosts require --allow-destructive-reuse",
            pytrace=False,
        )
    environment = request.getfixturevalue("environment_config")
    if not environment.is_production:
        return
    if request.node.get_closest_marker("prod_safe") is None:
        pytest.fail(
            "production permits only tests explicitly marked prod_safe",
            pytrace=False,
        )
    if (
        execution_context.diagnostics_level is DiagnosticDetail.FULL
        and not execution_context.allow_full_diagnostics_in_prod
    ):
        pytest.fail(
            "full diagnostics in production require --allow-full-diagnostics-in-prod",
            pytrace=False,
        )


def _text(value: object) -> str:
    """Normalize enums and optional metadata for reporting."""
    if value is None:
        return "not-set"
    return str(getattr(value, "value", value))


@pytest.fixture(autouse=True)
def _core_reporting_context(
    request: pytest.FixtureRequest,
) -> Iterator[None]:
    """Bind Allure and logging metadata only for host lifecycle tests."""
    if not _LIFECYCLE_FIXTURES.intersection(request.fixturenames):
        yield
        return
    config = request.getfixturevalue("test_run_config")
    host_value = request.getfixturevalue("host")
    ci = config.ci_context
    os_value = getattr(host_value, "operating_system", "unknown")
    os_version = getattr(host_value, "os_version", "unknown")
    host_name = _text(
        getattr(host_value, "logical_name", getattr(host_value, "host_id", "unknown"))
    )
    parameters = {
        "Agent version": config.agent_version,
        "backend version": config.backend_version,
        "environment": config.environment,
        "laboratory": config.lab,
        "host": host_name,
        "OS": _text(os_value),
        "OS version": _text(os_version),
        "architecture": _text(config.architecture),
        "enabled features": ", ".join(sorted(config.enabled_features)) or "none",
        "disabled features": ", ".join(sorted(config.disabled_features)) or "none",
        "suite": config.suite,
        "tenant reference": config.tenant.reference,
        "install mode": _text(config.install_mode),
        "upgrade-from version": _text(config.upgrade_from_version),
        "git commit": config.git_commit,
        "CI build ID": _text(ci.job_id),
        "CI build URL": _text(ci.build_url),
        "package build": config.build_id,
        "execution ID": config.execution_id,
        "core framework version": CORE_VERSION,
    }
    parameters["launch name"] = (
        f"Agent {config.agent_version} | Backend {config.backend_version} | "
        f"{_text(os_value).title()} {_text(os_version)} | "
        f"{config.suite.title()} | {config.environment.title()}"
    )
    feature_marker = request.node.get_closest_marker("allure_feature")
    story_marker = request.node.get_closest_marker("allure_story")
    if feature_marker and feature_marker.args:
        feature = str(feature_marker.args[0])
    elif "registered_agent" in request.fixturenames:
        feature = "Registration"
    else:
        feature = _text(config.install_mode).replace("-", " ").title()
    story = (
        str(story_marker.args[0])
        if story_marker and story_marker.args
        else request.node.name
    )
    apply_test_metadata(parameters, feature=feature, story=story)
    token = bind_logging_context(
        LoggingContext(
            execution_id=config.execution_id,
            test_id=request.node.nodeid,
            host=host_name,
            environment=config.environment,
            lab=config.lab,
            agent_version=config.agent_version,
            backend_version=config.backend_version,
            ci_build_id=ci.job_id,
        )
    )
    try:
        yield
    finally:
        reset_logging_context(token)


@pytest.fixture(scope="session")
def lifecycle_runtime() -> LifecycleRuntime:
    """Lab composition root (session scope because it owns shared adapters)."""
    raise RuntimeError("the test environment must provide lifecycle_runtime")


@pytest.fixture(scope="session")
def test_run_config(lifecycle_runtime: LifecycleRuntime) -> TestRunConfig:
    """Immutable merged run configuration, shared by the entire session."""
    return lifecycle_runtime.test_run_config()


@pytest.fixture(scope="session")
def execution_context(pytestconfig: pytest.Config) -> ExecutionContext:
    """Immutable CLI lifecycle policy, resolved once for the session."""
    return ExecutionContext(
        host_preparation=HostPreparation(pytestconfig.getoption("host_preparation")),
        cleanup_policy=CleanupMode(pytestconfig.getoption("cleanup_policy")),
        diagnostics_level=DiagnosticDetail(pytestconfig.getoption("diagnostics_level")),
        shared_ci=bool(pytestconfig.getoption("shared_ci")),
        allow_destructive_reuse=bool(pytestconfig.getoption("allow_destructive_reuse")),
        allow_full_diagnostics_in_prod=bool(
            pytestconfig.getoption("allow_full_diagnostics_in_prod")
        ),
    )


@pytest.fixture(scope="session")
def environment_config(
    lifecycle_runtime: LifecycleRuntime,
    test_run_config: TestRunConfig,
) -> EnvironmentConfig:
    """Selected immutable environment policy, stable for a test session."""
    return lifecycle_runtime.environment_config(test_run_config.environment)


@pytest.fixture(scope="session")
def lab_inventory(
    lifecycle_runtime: LifecycleRuntime,
    test_run_config: TestRunConfig,
) -> LaboratoryConfig:
    """Inventory snapshot, fixed session-wide to keep placement deterministic."""
    return lifecycle_runtime.lab_inventory(test_run_config.lab)


@pytest.fixture
def host_lease(
    lifecycle_runtime: LifecycleRuntime,
    test_run_config: TestRunConfig,
) -> Iterator[object]:
    """Function-scoped exclusive ownership; release is unconditional."""
    lease = lifecycle_runtime.acquire_host(test_run_config)
    try:
        yield lease
    finally:
        lifecycle_runtime.release_host(lease)


@pytest.fixture
def host(lifecycle_runtime: LifecycleRuntime, host_lease: object) -> object:
    """Function-scoped host view tied to the live lease."""
    return lifecycle_runtime.host(host_lease)


def _test_succeeded(request: pytest.FixtureRequest) -> bool:
    report = getattr(request.node, "_core_call_report", None)
    return report is not None and bool(report.passed)


@pytest.fixture
def clean_host(
    request: pytest.FixtureRequest,
    lifecycle_runtime: LifecycleRuntime,
    execution_context: ExecutionContext,
    host: object,
) -> Iterator[object]:
    """Per-test baseline with policy cleanup and mandatory verification."""
    lifecycle_runtime.prepare_host(host, execution_context.host_preparation)
    yield host
    cleanup = execution_context.cleanup_policy
    if cleanup is CleanupMode.ALWAYS or (
        cleanup is CleanupMode.ON_SUCCESS and _test_succeeded(request)
    ):
        lifecycle_runtime.cleanup_host(host)
        if not lifecycle_runtime.verify_cleanup(host):
            raise AssertionError("host cleanup verification failed")


@pytest.fixture
def os_controller(lifecycle_runtime: LifecycleRuntime, clean_host: object) -> object:
    """Function-scoped OS adapter; it must never outlive its leased host."""
    return lifecycle_runtime.os_controller(clean_host)


@pytest.fixture
def agent_controller(
    lifecycle_runtime: LifecycleRuntime,
    clean_host: object,
    os_controller: object,
) -> object:
    """Function-scoped Agent controller bound to one OS controller."""
    return lifecycle_runtime.agent_controller(clean_host, os_controller)


@pytest.fixture
def backend_client(
    lifecycle_runtime: LifecycleRuntime,
    environment_config: EnvironmentConfig,
) -> object:
    """Function scope prevents mutable client/session state leaking across tests."""
    return lifecycle_runtime.backend_client(environment_config)


@pytest.fixture
def diagnostics_collector(
    request: pytest.FixtureRequest,
    lifecycle_runtime: LifecycleRuntime,
    execution_context: ExecutionContext,
    test_run_config: TestRunConfig,
    pytestconfig: pytest.Config,
    host: object,
) -> Iterator[DiagnosticsCollector]:
    """Per-test failure diagnostics, collected before host cleanup/release."""
    collector = DiagnosticsCollector(
        lifecycle_runtime,
        host,
        execution_context.diagnostics_level,
        test_run_config,
        int(pytestconfig.getoption("diagnostics_max_attachment_bytes")),
    )
    yield collector
    if bool(getattr(request.node, "_core_lifecycle_failed", False)):
        collector.collect()


@pytest.fixture
def installed_agent(
    request: pytest.FixtureRequest,
    lifecycle_runtime: LifecycleRuntime,
    test_run_config: TestRunConfig,
    clean_host: object,
    diagnostics_collector: DiagnosticsCollector,
) -> Iterator[AgentHandle]:
    """Install per test; rollback failed transitions and uninstall when cleaning."""
    agent = lifecycle_runtime.agent_handle(clean_host)
    try:
        lifecycle_runtime.install_agent(agent, test_run_config.agent_version)
    except Exception:
        if test_run_config.upgrade_from_version is not None:
            lifecycle_runtime.rollback_agent(agent)
        diagnostics_collector.collect()
        raise
    yield agent
    cleanup = request.getfixturevalue("execution_context").cleanup_policy
    if bool(getattr(request.node, "_core_lifecycle_failed", False)):
        diagnostics_collector.collect()
    if cleanup is CleanupMode.ALWAYS or (
        cleanup is CleanupMode.ON_SUCCESS and _test_succeeded(request)
    ):
        lifecycle_runtime.uninstall_agent(agent)


@pytest.fixture
def running_agent(
    lifecycle_runtime: LifecycleRuntime,
    installed_agent: AgentHandle,
) -> AgentHandle:
    """Function-scoped running state built on the installed baseline."""
    lifecycle_runtime.start_agent(installed_agent)
    return installed_agent


@pytest.fixture
def registered_agent(
    lifecycle_runtime: LifecycleRuntime,
    running_agent: AgentHandle,
) -> RegistrationResult:
    """Function-scoped backend registration, isolated with its Agent lifecycle."""
    return lifecycle_runtime.register_agent(running_agent)


@pytest.fixture
def healthy_agent(
    lifecycle_runtime: LifecycleRuntime,
    running_agent: AgentHandle,
) -> AgentHealth:
    """Function-scoped bounded health observation of the running Agent."""
    return lifecycle_runtime.wait_for_health(running_agent)


@pytest.fixture
def capability_set(
    lifecycle_runtime: LifecycleRuntime,
    running_agent: AgentHandle,
) -> CapabilitySet:
    """Capabilities are resolved per leased host and installed Agent version."""
    return lifecycle_runtime.capabilities(running_agent)
