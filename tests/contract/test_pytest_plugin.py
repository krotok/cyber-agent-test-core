"""Contract tests for the registered pytest plugin."""

import json

import pytest

from cyber_agent_test_core.checks import AgentChecks


@pytest.mark.framework_contract
def test_core_version_fixture(core_version: str) -> None:
    assert core_version == "0.2.0"


def test_beginner_check_fixture_is_registered(agent_checks: AgentChecks) -> None:
    assert isinstance(agent_checks, AgentChecks)


def test_core_info_option(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        def test_minimal(core_version: str) -> None:
            assert core_version == "0.2.0"
        """
    )

    result = pytester.runpytest("--core-info", "-v", "--no-cov")

    result.stdout.fnmatch_lines(["*cyber-agent-test-core: 0.2.0*"])
    result.assert_outcomes(passed=1)


def test_lifecycle_options_are_registered(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        def test_policy(execution_context) -> None:
            assert execution_context.host_preparation == "snapshot"
            assert execution_context.cleanup_policy == "on-success"
            assert execution_context.diagnostics_level == "extended"
        """
    )
    result = pytester.runpytest(
        "--host-preparation=snapshot",
        "--cleanup-policy=on-success",
        "--diagnostics-level=extended",
        "--no-cov",
    )
    result.assert_outcomes(passed=1)


def test_cleanup_never_is_rejected_in_shared_ci(pytester: pytest.Pytester) -> None:
    pytester.makepyfile("def test_not_run() -> None: pass")
    result = pytester.runpytest("--shared-ci", "--cleanup-policy=never", "--no-cov")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(["*--cleanup-policy=never is forbidden in shared CI*"])


def test_writes_and_applies_execution_plan_shard(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.estimated_duration(10)
        def test_long() -> None: pass

        @pytest.mark.estimated_duration(1)
        def test_short() -> None: pass
        """
    )
    plan_path = pytester.path / "plan.json"

    result = pytester.runpytest(
        "--core-shard-count=2",
        "--core-shard-index=1",
        f"--core-execution-plan={plan_path}",
        "--no-cov",
    )

    result.assert_outcomes(passed=1)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["shard_count"] == 2
    assert len(plan["selected_tests"]) == 2
    assert {test["required_hosts"] for test in plan["selected_tests"]} == {1}


def test_production_guard_runs_before_host_acquisition(
    pytester: pytest.Pytester,
) -> None:
    acquired = pytester.path / "acquired"
    pytester.makeconftest(
        f"""
        import pytest
        from cyber_agent_test_core.models import OperatingSystemFamily
        from cyber_agent_test_core.testing import FakeVerticalSliceRuntime

        class ProdRuntime(FakeVerticalSliceRuntime):
            def __init__(self):
                super().__init__(OperatingSystemFamily.LINUX)
                self._environment = self._environment.model_copy(
                    update={{"is_production": True}}
                )

            def acquire_host(self, config):
                open({str(acquired)!r}, "w", encoding="utf-8").write("unsafe")
                return super().acquire_host(config)

        @pytest.fixture(scope="session")
        def lifecycle_runtime():
            return ProdRuntime()
        """
    )
    pytester.makepyfile("def test_prod(host): pass")

    result = pytester.runpytest("--no-cov")

    result.assert_outcomes(errors=1)
    assert not acquired.exists()
    result.stdout.fnmatch_lines(
        ["*production execution requires production_approved=true*"]
    )


def test_private_composition_fixture_is_not_publicly_exported() -> None:
    from cyber_agent_test_core import fixtures

    assert "lifecycle_runtime" not in fixtures.__all__


def test_host_lease_is_renewed_during_test(pytester: pytest.Pytester) -> None:
    heartbeat = pytester.path / "heartbeat"
    pytester.makeconftest(
        f"""
        import pytest
        from cyber_agent_test_core.models import OperatingSystemFamily
        from cyber_agent_test_core.testing import FakeVerticalSliceRuntime

        class ObservableRuntime(FakeVerticalSliceRuntime):
            def heartbeat_host(self, lease):
                super().heartbeat_host(lease)
                open({str(heartbeat)!r}, "w", encoding="utf-8").write("renewed")

        @pytest.fixture(scope="session")
        def lifecycle_runtime():
            return ObservableRuntime(OperatingSystemFamily.LINUX)
        """
    )
    pytester.makepyfile(
        """
        from threading import Event

        def test_lease(host):
            assert Event().wait(0.05) is False
        """
    )

    result = pytester.runpytest(
        "--host-lease-heartbeat-seconds=0.01",
        "--no-cov",
    )

    result.assert_outcomes(passed=1)
    assert heartbeat.read_text(encoding="utf-8") == "renewed"


def test_failed_upgrade_preserves_primary_error_when_rollback_fails(
    pytester: pytest.Pytester,
) -> None:
    pytester.makeconftest(
        """
        import pytest
        from cyber_agent_test_core.models import OperatingSystemFamily
        from cyber_agent_test_core.testing import FakeVerticalSliceRuntime

        class BrokenUpgradeRuntime(FakeVerticalSliceRuntime):
            def __init__(self):
                super().__init__(OperatingSystemFamily.LINUX)
                self._config = self._config.model_copy(
                    update={"upgrade_from_version": "4.7.0", "install_mode": "upgrade"}
                )

            def install_agent(self, agent, version):
                raise ValueError("primary install failure")

            def rollback_agent(self, agent):
                raise RuntimeError("secondary rollback failure")

        @pytest.fixture(scope="session")
        def lifecycle_runtime():
            return BrokenUpgradeRuntime()
        """
    )
    pytester.makepyfile("def test_upgrade(installed_agent): pass")

    result = pytester.runpytest("--no-cov")

    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*primary install failure*"])
