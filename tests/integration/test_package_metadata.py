"""Framework-only integration checks for package metadata consistency."""

from importlib.metadata import version

from cyber_agent_test_core.api import CORE_VERSION


def test_installed_distribution_matches_public_version() -> None:
    assert version("cyber-agent-test-core") == CORE_VERSION
