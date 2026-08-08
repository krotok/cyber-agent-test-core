"""Contract tests for the registered pytest plugin."""

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
    result = pytester.runpytest(
        "--shared-ci", "--cleanup-policy=never", "--no-cov"
    )
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(
        ["*--cleanup-policy=never is forbidden in shared CI*"]
    )
