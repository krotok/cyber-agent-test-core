"""Installed-plugin style vertical slice with a genuinely thin product test."""

import pytest


@pytest.mark.parametrize("operating_system", ["linux", "windows", "macos"])
def test_thin_test_runs_without_remote_machine(
    pytester: pytest.Pytester,
    operating_system: str,
) -> None:
    pytester.makepyfile(
        """
        def test_agent_lifecycle(
            registered_agent,
            healthy_agent,
            observed_agent_version,
            agent_checks,
            version_checks,
        ) -> None:
            agent_checks.is_registered(registered_agent)
            agent_checks.is_healthy(healthy_agent)
            version_checks.equals(observed_agent_version, "4.8.1")
        """
    )

    result = pytester.runpytest(
        "--fake-vertical-slice",
        f"--fake-os={operating_system}",
        "--no-cov",
    )

    result.assert_outcomes(passed=1)

