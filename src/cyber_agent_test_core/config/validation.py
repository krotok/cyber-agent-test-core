"""Early contextual validation performed before any host is leased."""

from collections.abc import Collection, Mapping, Set

from cyber_agent_test_core.config.schemas import (
    EnvironmentConfig,
    HostConfig,
    LaboratoryConfig,
    TestRunConfig,
)


class ConfigurationValidationError(ValueError):
    """Aggregate configuration errors that must stop test execution."""

    def __init__(self, issues: Collection[str]) -> None:
        self.issues = tuple(issues)
        super().__init__("invalid test run configuration: " + "; ".join(self.issues))


def _eligible_hosts(
    config: TestRunConfig,
    laboratory: LaboratoryConfig,
    required_capabilities: Set[str],
) -> list[HostConfig]:
    """Return available hosts satisfying explicit run constraints."""
    targets = set(config.target_hosts)
    return [
        host
        for host in laboratory.hosts
        if host.available
        and host.operating_system.architecture is config.architecture
        and config.network.mode in host.network_modes
        and required_capabilities <= host.capabilities
        and (not targets or host.host_id in targets)
    ]


def validate_test_run(
    config: TestRunConfig,
    *,
    environments: Mapping[str, EnvironmentConfig],
    laboratories: Mapping[str, LaboratoryConfig],
    compatible_versions: Collection[tuple[str, str]],
    required_capabilities: Set[str] = frozenset(),
) -> None:
    """Validate runtime policy before transport creation or host acquisition."""
    issues: list[str] = []
    environment = environments.get(config.environment)
    laboratory = laboratories.get(config.lab)

    if environment is None:
        issues.append(f"environment does not exist: {config.environment}")
    if laboratory is None:
        issues.append(f"laboratory does not exist: {config.lab}")
    if environment is not None:
        if config.suite not in environment.allowed_suites:
            issues.append(f"suite is not allowed in environment: {config.suite}")
        if not environment.test_execution_enabled:
            issues.append(
                f"test execution is disabled in environment: {config.environment}"
            )
        if environment.is_production and not config.production_approved:
            issues.append("production execution requires explicit approval")
        if environment.is_production and config.destructive_test:
            issues.append("destructive tests are forbidden in production")
        missing_environment = required_capabilities - environment.capabilities
        if missing_environment:
            issues.append(
                "environment capabilities are unavailable: "
                + ", ".join(sorted(missing_environment))
            )
    if laboratory is not None:
        if config.environment not in laboratory.allowed_environments:
            issues.append(
                f"environment is not allowed in laboratory: {config.environment}"
            )
        if config.suite not in laboratory.allowed_suites:
            issues.append(f"suite is not allowed in laboratory: {config.suite}")
        missing_laboratory = required_capabilities - laboratory.capabilities
        if missing_laboratory:
            issues.append(
                "laboratory capabilities are unavailable: "
                + ", ".join(sorted(missing_laboratory))
            )
        known_hosts = {host.host_id for host in laboratory.hosts}
        missing_hosts = set(config.target_hosts) - known_hosts
        if missing_hosts:
            issues.append(
                "target hosts do not exist: " + ", ".join(sorted(missing_hosts))
            )
        eligible = _eligible_hosts(config, laboratory, required_capabilities)
        if len(eligible) < config.parallelism:
            issues.append(
                f"insufficient eligible hosts: need {config.parallelism}, "
                f"found {len(eligible)}"
            )
    pair = (config.agent_version, config.backend_version)
    if pair not in compatible_versions:
        issues.append(
            "Agent/backend versions are incompatible: "
            f"{config.agent_version}/{config.backend_version}"
        )
    if issues:
        raise ConfigurationValidationError(issues)
