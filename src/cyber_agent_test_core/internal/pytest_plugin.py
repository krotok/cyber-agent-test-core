"""Private pytest integration exposed through the ``pytest11`` entry point."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from packaging.version import InvalidVersion, Version

from cyber_agent_test_core.api import CORE_VERSION
from cyber_agent_test_core.capabilities import (
    CapabilityResolver,
    CompatibilityDataError,
    load_capability_context,
    load_compatibility_matrix,
)
from cyber_agent_test_core.markers import (
    FRAMEWORK_CONTRACT,
    INCOMPATIBLE_FEATURE,
    MAX_AGENT_VERSION,
    MIN_AGENT_VERSION,
    REQUIRES_CAPABILITY,
    REQUIRES_FEATURE,
    SUPPORTED_OS,
)
from cyber_agent_test_core.models import (
    Capability,
    CompatibilityResult,
    OperatingSystemFamily,
)
from cyber_agent_test_core.reporting.allure import attach_skip_reason

pytest_plugins = ("cyber_agent_test_core.fixtures",)

_COMPATIBILITY_RESULT = pytest.StashKey[CompatibilityResult]()
_CAPABILITY_MARKERS = (
    REQUIRES_CAPABILITY,
    REQUIRES_FEATURE,
    INCOMPATIBLE_FEATURE,
    SUPPORTED_OS,
    MIN_AGENT_VERSION,
    MAX_AGENT_VERSION,
)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register command-line options owned by the core plugin."""
    group = parser.getgroup("cyber-agent-test-core")
    group.addoption(
        "--core-info",
        action="store_true",
        default=False,
        help="show Cyber Agent Test Core information in the pytest header",
    )
    group.addoption(
        "--core-compatibility-matrix",
        type=Path,
        help="path to a declarative YAML or JSON compatibility matrix",
    )
    group.addoption(
        "--core-capability-context",
        type=Path,
        help="path to the selected target capability context",
    )


def _load_compatibility_result(config: pytest.Config) -> None:
    """Resolve optional CLI compatibility data and preserve configuration errors."""
    matrix_path = config.getoption("--core-compatibility-matrix")
    context_path = config.getoption("--core-capability-context")
    if matrix_path is None and context_path is None:
        return
    if matrix_path is None or context_path is None:
        raise pytest.UsageError(
            "--core-compatibility-matrix and --core-capability-context "
            "must be supplied together"
        )
    try:
        matrix = load_compatibility_matrix(matrix_path)
        context = load_capability_context(context_path)
        config.stash[_COMPATIBILITY_RESULT] = CapabilityResolver(matrix).resolve(
            context
        )
    except CompatibilityDataError as error:
        raise pytest.UsageError(str(error)) from error


def pytest_configure(config: pytest.Config) -> None:
    """Register markers and resolve compatibility before collection."""
    marker_descriptions = {
        FRAMEWORK_CONTRACT: "marks tests that validate framework contracts",
        REQUIRES_CAPABILITY: "requires one or more resolved capabilities",
        REQUIRES_FEATURE: "requires one or more enabled feature flags",
        INCOMPATIBLE_FEATURE: "cannot run when a feature flag is enabled",
        SUPPORTED_OS: "lists supported operating-system families",
        MIN_AGENT_VERSION: "requires at least the specified Agent version",
        MAX_AGENT_VERSION: "requires at most the specified Agent version",
    }
    for name, description in marker_descriptions.items():
        config.addinivalue_line("markers", f"{name}(*values): {description}")
    _load_compatibility_result(config)


def _marker_strings(marker: pytest.Mark, marker_name: str) -> tuple[str, ...]:
    """Validate marker arguments as one or more positional strings."""
    valid_arguments = marker.args and all(
        isinstance(arg, str) for arg in marker.args
    )
    if marker.kwargs or not valid_arguments:
        raise pytest.UsageError(f"{marker_name} requires positional string arguments")
    return tuple(marker.args)


def _version_reason(
    marker: pytest.Mark,
    marker_name: str,
    actual: str,
) -> str | None:
    """Evaluate one min/max Agent version marker with inclusive boundaries."""
    values = _marker_strings(marker, marker_name)
    if len(values) != 1:
        raise pytest.UsageError(f"{marker_name} requires exactly one version")
    try:
        actual_version = Version(actual)
        boundary = Version(values[0])
    except InvalidVersion as error:
        raise pytest.UsageError(
            f"invalid Agent version in {marker_name}: {error}"
        ) from error
    if marker_name == MIN_AGENT_VERSION and actual_version < boundary:
        return f"requires Agent >= {boundary}; resolved Agent is {actual_version}"
    if marker_name == MAX_AGENT_VERSION and actual_version > boundary:
        return f"requires Agent <= {boundary}; resolved Agent is {actual_version}"
    return None


def _marker_reasons(item: pytest.Item, result: CompatibilityResult) -> list[str]:
    """Evaluate declarative test requirements against one resolved result."""
    reasons: list[str] = []
    for marker in item.iter_markers(REQUIRES_CAPABILITY):
        requested = _marker_strings(marker, REQUIRES_CAPABILITY)
        try:
            missing = [
                value
                for value in requested
                if not result.capabilities.supports(Capability(value))
            ]
        except ValueError as error:
            raise pytest.UsageError(f"unknown capability in marker: {error}") from error
        if missing:
            reasons.append("missing capabilities: " + ", ".join(missing))
    for marker in item.iter_markers(REQUIRES_FEATURE):
        missing_features = (
            set(_marker_strings(marker, REQUIRES_FEATURE))
            - result.context.feature_flags
        )
        if missing_features:
            reasons.append(
                "disabled feature flags: " + ", ".join(sorted(missing_features))
            )
    for marker in item.iter_markers(INCOMPATIBLE_FEATURE):
        enabled = (
            set(_marker_strings(marker, INCOMPATIBLE_FEATURE))
            & result.context.feature_flags
        )
        if enabled:
            reasons.append(
                "incompatible enabled feature flags: " + ", ".join(sorted(enabled))
            )
    for marker in item.iter_markers(SUPPORTED_OS):
        values = _marker_strings(marker, SUPPORTED_OS)
        try:
            supported = {OperatingSystemFamily(value) for value in values}
        except ValueError as error:
            raise pytest.UsageError(f"unknown OS in supported_os: {error}") from error
        if result.context.operating_system not in supported:
            reasons.append(
                "unsupported OS: "
                f"resolved {result.context.operating_system.value}; "
                f"allowed {sorted(values)}"
            )
    for marker_name in (MIN_AGENT_VERSION, MAX_AGENT_VERSION):
        for marker in item.iter_markers(marker_name):
            reason = _version_reason(marker, marker_name, result.context.agent_version)
            if reason is not None:
                reasons.append(reason)
    return reasons


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Skip only valid but unsupported test/target combinations."""
    result = config.stash.get(_COMPATIBILITY_RESULT, None)
    marked_items = [
        item
        for item in items
        if any(
            item.get_closest_marker(name) is not None for name in _CAPABILITY_MARKERS
        )
    ]
    if result is None:
        if marked_items:
            raise pytest.UsageError(
                "capability markers require resolved compatibility matrix and context"
            )
        return
    for item in items:
        reasons = list(result.reasons) if not result.supported else []
        reasons.extend(_marker_reasons(item, result))
        if reasons:
            reason = "; ".join(dict.fromkeys(reasons))
            item.user_properties.append(("core_skip_reason", reason))
            item.add_marker(pytest.mark.skip(reason=reason))


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Attach a capability skip reason through the optional Allure adapter."""
    if not report.skipped:
        return
    for name, value in report.user_properties:
        if name == "core_skip_reason":
            attach_skip_reason(str(value))
            return


def pytest_report_header(config: pytest.Config) -> str | None:
    """Return version information when explicitly requested by the user."""
    if config.getoption("--core-info"):
        return f"cyber-agent-test-core: {CORE_VERSION}"
    return None


@pytest.fixture
def core_version() -> Iterator[str]:
    """Provide the installed core package version."""
    yield CORE_VERSION
