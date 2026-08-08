"""Private pytest integration exposed through the ``pytest11`` entry point."""

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from _pytest.terminal import TerminalReporter
from packaging.version import InvalidVersion, Version

from cyber_agent_test_core.api import CORE_VERSION
from cyber_agent_test_core.capabilities import (
    CapabilityResolver,
    CompatibilityDataError,
    load_capability_context,
    load_compatibility_matrix,
)
from cyber_agent_test_core.diagnostics.artifacts import (
    classify_exception,
    make_attachment,
)
from cyber_agent_test_core.execution.planning import (
    ExecutionPlan,
    ExecutionPlanner,
    LabTarget,
    SkippedCombination,
    TestRequirement,
    stable_shard,
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
from cyber_agent_test_core.reporting.allure import (
    attach_diagnostic,
    attach_failure_category,
    attach_skip_reason,
)
from cyber_agent_test_core.reporting.results import merge_allure_results

pytest_plugins = ("cyber_agent_test_core.fixtures",)

_COMPATIBILITY_RESULT = pytest.StashKey[CompatibilityResult]()
_EXECUTION_PLAN = pytest.StashKey[ExecutionPlan]()
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
    group.addoption(
        "--host-preparation",
        choices=("clean-install", "reuse", "snapshot"),
        default="clean-install",
        dest="host_preparation",
        help="leased-host baseline strategy (default: clean-install)",
    )
    group.addoption(
        "--cleanup-policy",
        choices=("always", "on-success", "never"),
        default="always",
        dest="cleanup_policy",
        help="when framework state cleanup runs (default: always)",
    )
    group.addoption(
        "--diagnostics-level",
        choices=("basic", "extended", "full"),
        default="basic",
        dest="diagnostics_level",
        help="failure diagnostic detail (default: basic)",
    )
    group.addoption(
        "--allow-destructive-reuse",
        action="store_true",
        default=False,
        dest="allow_destructive_reuse",
        help="explicitly allow destructive tests on a reused host",
    )
    group.addoption(
        "--shared-ci",
        action="store_true",
        default=bool(os.environ.get("CI")),
        dest="shared_ci",
        help="declare that hosts are shared by concurrent CI runs",
    )
    group.addoption(
        "--allow-full-diagnostics-in-prod",
        action="store_true",
        default=False,
        dest="allow_full_diagnostics_in_prod",
        help="explicitly permit potentially sensitive full diagnostics in production",
    )
    group.addoption(
        "--diagnostics-max-attachment-bytes",
        type=int,
        default=2 * 1024 * 1024,
        dest="diagnostics_max_attachment_bytes",
        help="maximum bytes per redacted diagnostic attachment",
    )
    group.addoption(
        "--fake-vertical-slice",
        action="store_true",
        default=False,
        dest="fake_vertical_slice",
        help="run lifecycle fixtures against packaged in-memory fakes",
    )
    group.addoption(
        "--fake-os",
        choices=("linux", "windows", "macos"),
        default="linux",
        dest="fake_os",
        help="operating system exposed by the fake vertical slice",
    )
    group.addoption(
        "--core-shard-count",
        type=int,
        default=int(os.environ.get("CI_NODE_TOTAL", "1")),
        dest="core_shard_count",
        help="number of deterministic CI shards",
    )
    group.addoption(
        "--core-shard-index",
        type=int,
        default=int(os.environ.get("CI_NODE_INDEX", "0")),
        dest="core_shard_index",
        help="zero-based CI shard selected by this job",
    )
    group.addoption(
        "--core-plan-labs",
        type=Path,
        dest="core_plan_labs",
        help="JSON file describing labs available to the execution planner",
    )
    group.addoption(
        "--core-execution-plan",
        type=Path,
        dest="core_execution_plan",
        help="optional path for the pre-execution JSON plan",
    )
    group.addoption(
        "--core-allure-results-input",
        action="append",
        type=Path,
        default=[],
        dest="core_allure_results_input",
        help="Allure result directory to merge; may be repeated",
    )
    group.addoption(
        "--core-allure-results-output",
        type=Path,
        dest="core_allure_results_output",
        help="destination for merged Allure results",
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
        "destructive": "changes host state and requires an isolated clean baseline",
        "prod_safe": "audited for execution against a production environment",
        "allure_feature": (
            "Allure Feature label: Installation, Registration, Upgrade, Protection"
        ),
        "allure_story": "Allure Story label describing concrete behavior",
        "estimated_duration": "estimated test duration in seconds for shard balancing",
        "required_hosts": "number of simultaneously required hosts",
        "core_suite": "suite dimension used by execution planning",
    }
    for name, description in marker_descriptions.items():
        config.addinivalue_line("markers", f"{name}(*values): {description}")
    _load_compatibility_result(config)
    if config.getoption("shared_ci") and config.getoption("cleanup_policy") == "never":
        raise pytest.UsageError("--cleanup-policy=never is forbidden in shared CI")
    if config.getoption("diagnostics_max_attachment_bytes") < 128:
        raise pytest.UsageError(
            "--diagnostics-max-attachment-bytes must be at least 128"
        )
    shard_count = int(config.getoption("core_shard_count"))
    shard_index = int(config.getoption("core_shard_index"))
    if shard_count < 1 or not 0 <= shard_index < shard_count:
        raise pytest.UsageError(
            "--core-shard-count must be positive and "
            "--core-shard-index must be in range"
        )
    if (
        config.getoption("core_allure_results_input")
        and config.getoption("core_allure_results_output") is None
    ):
        raise pytest.UsageError(
            "--core-allure-results-output is required when merge inputs are supplied"
        )


def _marker_strings(marker: pytest.Mark, marker_name: str) -> tuple[str, ...]:
    """Validate marker arguments as one or more positional strings."""
    valid_arguments = marker.args and all(isinstance(arg, str) for arg in marker.args)
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


def _single_marker_value(
    item: pytest.Item,
    name: str,
    default: object,
) -> object:
    marker = item.get_closest_marker(name)
    if marker is None:
        return default
    if marker.kwargs or len(marker.args) != 1:
        raise pytest.UsageError(f"{name} requires exactly one positional argument")
    return marker.args[0]


def _load_plan_labs(
    path: Path | None,
    requirements: tuple[TestRequirement, ...],
) -> tuple[LabTarget, ...]:
    """Load non-secret planner capacity or create one permissive logical lab."""
    if path is None:
        operating_systems = frozenset().union(
            *(requirement.operating_systems for requirement in requirements)
        )
        capabilities = frozenset().union(
            *(requirement.required_capabilities for requirement in requirements)
        )
        return (LabTarget("configured", operating_systems, capabilities, 1024),)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("root must be a list")
        return tuple(
            LabTarget(
                name=str(value["name"]),
                operating_systems=frozenset(map(str, value["operating_systems"])),
                capabilities=frozenset(map(str, value.get("capabilities", []))),
                host_count=int(value["host_count"]),
            )
            for value in raw
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise pytest.UsageError(f"invalid --core-plan-labs file: {path}") from error


def _create_execution_plan(
    config: pytest.Config,
    items: list[pytest.Item],
    result: CompatibilityResult | None,
) -> None:
    """Create, optionally persist, and apply the deterministic pre-run plan."""
    requirements: list[TestRequirement] = []
    unsupported: list[SkippedCombination] = []
    unsupported_ids: set[str] = set()
    for item in items:
        skip_reason = next(
            (
                str(value)
                for name, value in item.user_properties
                if name == "core_skip_reason"
            ),
            None,
        )
        if skip_reason is not None:
            unsupported.append(SkippedCombination(item.nodeid, skip_reason))
            unsupported_ids.add(item.nodeid)
            continue
        os_markers = tuple(item.iter_markers(SUPPORTED_OS))
        operating_systems = frozenset(
            value
            for marker in os_markers
            for value in _marker_strings(marker, SUPPORTED_OS)
        )
        if not operating_systems and result is not None:
            operating_systems = frozenset({result.context.operating_system.value})
        capabilities = frozenset(
            value
            for marker in item.iter_markers(REQUIRES_CAPABILITY)
            for value in _marker_strings(marker, REQUIRES_CAPABILITY)
        )
        features = frozenset(
            value
            for marker in item.iter_markers(REQUIRES_FEATURE)
            for value in _marker_strings(marker, REQUIRES_FEATURE)
        )
        raw_duration = _single_marker_value(item, "estimated_duration", 1.0)
        raw_hosts = _single_marker_value(item, "required_hosts", 1)
        if (
            not isinstance(raw_duration, (int, float))
            or isinstance(raw_duration, bool)
            or not isinstance(raw_hosts, int)
            or isinstance(raw_hosts, bool)
        ):
            raise pytest.UsageError(
                "estimated_duration must be numeric and required_hosts must be int"
            )
        duration = float(raw_duration)
        required_hosts = raw_hosts
        if duration <= 0 or required_hosts < 1:
            raise pytest.UsageError(
                "estimated_duration and required_hosts must be positive"
            )
        requirements.append(
            TestRequirement(
                nodeid=item.nodeid,
                operating_systems=operating_systems,
                suite=str(_single_marker_value(item, "core_suite", "default")),
                estimated_duration=duration,
                feature_set=features,
                agent_version=(
                    result.context.agent_version if result is not None else "configured"
                ),
                required_capabilities=capabilities,
                required_hosts=required_hosts,
            )
        )
    requirement_values = tuple(requirements)
    labs = _load_plan_labs(config.getoption("core_plan_labs"), requirement_values)
    planned = ExecutionPlanner().build(
        requirement_values,
        labs,
        shard_count=int(config.getoption("core_shard_count")),
    )
    plan = ExecutionPlan(
        planned.selected_tests,
        tuple(unsupported) + planned.skipped_unsupported,
        planned.shard_count,
    )
    config.stash[_EXECUTION_PLAN] = plan
    output = config.getoption("core_execution_plan")
    if output is not None:
        plan.write_json(output)
    assignments = {test.nodeid: test.shard for test in plan.selected_tests}
    shard_index = int(config.getoption("core_shard_index"))
    shard_count = plan.shard_count
    items[:] = [
        item
        for item in items
        if assignments.get(item.nodeid, stable_shard(item.nodeid, shard_count))
        == shard_index
        or (item.nodeid in unsupported_ids and shard_count == 1)
    ]


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
        _create_execution_plan(config, items, result)
        return
    for item in items:
        reasons = list(result.reasons) if not result.supported else []
        reasons.extend(_marker_reasons(item, result))
        if reasons:
            reason = "; ".join(dict.fromkeys(reasons))
            item.user_properties.append(("core_skip_reason", reason))
            item.add_marker(pytest.mark.skip(reason=reason))
    _create_execution_plan(config, items, result)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Attach a capability skip reason through the optional Allure adapter."""
    if not report.skipped:
        return
    for name, value in report.user_properties:
        if name == "core_skip_reason":
            attach_skip_reason(str(value))
            return


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo[object],
) -> Iterator[None]:
    """Expose the call outcome to fixture finalizers without global state."""
    outcome: Any = yield
    report = outcome.get_result()
    if report.when == "call":
        item.__dict__["_core_call_report"] = report
    if report.when in {"setup", "call"} and report.failed:
        item.__dict__["_core_lifecycle_failed"] = True
    if report.failed and call.excinfo is not None:
        category = classify_exception(call.excinfo.value)
        report.user_properties.append(("failure_category", category.value))
        attach_failure_category(category.value)
        limit = int(item.config.getoption("diagnostics_max_attachment_bytes"))
        for section_name, content in report.sections:
            lowered = section_name.lower()
            if "stdout" in lowered or "stderr" in lowered:
                attach_diagnostic(
                    make_attachment(section_name, content, max_bytes=limit)
                )


def pytest_report_header(config: pytest.Config) -> str | None:
    """Return version information when explicitly requested by the user."""
    if config.getoption("--core-info"):
        return f"cyber-agent-test-core: {CORE_VERSION}"
    return None


def pytest_terminal_summary(
    terminalreporter: TerminalReporter,
    config: pytest.Config,
) -> None:
    """Summarize the immutable plan used by this worker/job."""
    plan = config.stash.get(_EXECUTION_PLAN, None)
    if plan is None:
        return
    selected = sum(
        test.shard == int(config.getoption("core_shard_index"))
        for test in plan.selected_tests
    )
    terminalreporter.write_line(
        "execution plan: "
        f"selected={selected}, shards={plan.shard_count}, "
        f"unsupported={len(plan.skipped_unsupported)}"
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Merge Allure artifacts once in the xdist controller or standalone job."""
    del exitstatus
    if hasattr(session.config, "workerinput"):
        return
    sources = tuple(session.config.getoption("core_allure_results_input"))
    destination = session.config.getoption("core_allure_results_output")
    if destination is not None:
        merge_allure_results(sources, destination)


@pytest.fixture
def core_version() -> Iterator[str]:
    """Provide the installed core package version."""
    yield CORE_VERSION
