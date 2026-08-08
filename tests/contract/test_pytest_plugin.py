"""Contract tests for the registered pytest plugin."""

import pytest


@pytest.mark.framework_contract
def test_core_version_fixture(core_version: str) -> None:
    assert core_version == "0.2.0"


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
