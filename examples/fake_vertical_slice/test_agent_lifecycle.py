"""Thin product-style test backed entirely by packaged core fakes."""

from cyber_agent_test_core.checks import AgentChecks, VersionChecks
from cyber_agent_test_core.models import AgentHealth, RegistrationResult


def test_agent_lifecycle(
    registered_agent: RegistrationResult,
    healthy_agent: AgentHealth,
    observed_agent_version: str | None,
    agent_checks: AgentChecks,
    version_checks: VersionChecks,
) -> None:
    agent_checks.is_registered(registered_agent)
    agent_checks.is_healthy(healthy_agent)
    version_checks.equals(observed_agent_version, "4.8.1")

