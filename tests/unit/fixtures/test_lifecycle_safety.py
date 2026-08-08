"""Lifecycle error-preservation tests."""

from cyber_agent_test_core.fixtures.lifecycle import DiagnosticsCollector
from cyber_agent_test_core.models import DiagnosticDetail, OperatingSystemFamily
from cyber_agent_test_core.testing import FakeVerticalSliceRuntime


class BrokenDiagnosticsRuntime(FakeVerticalSliceRuntime):
    def collect_diagnostics(self, host: object, level: DiagnosticDetail) -> None:
        del host, level
        raise RuntimeError("diagnostic provider failed")


def test_diagnostics_failure_never_escapes_or_replaces_primary_failure() -> None:
    runtime = BrokenDiagnosticsRuntime(OperatingSystemFamily.LINUX)
    lease = runtime.acquire_host(runtime.test_run_config())
    collector = DiagnosticsCollector(
        runtime,
        runtime.host(lease),
        DiagnosticDetail.FULL,
        runtime.test_run_config(),
        1024,
    )

    collector.collect()

