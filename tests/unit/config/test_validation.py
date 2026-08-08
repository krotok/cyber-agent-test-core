"""Early contextual validation tests."""

from collections.abc import Callable
from typing import Any

import pytest

from cyber_agent_test_core.config import (
    BackendConfig,
    ConfigurationValidationError,
    CredentialsReference,
    EnvironmentConfig,
    HostConfig,
    LaboratoryConfig,
    OperatingSystemConfig,
    validate_test_run,
)
from cyber_agent_test_core.config import TestRunConfig as RunConfig


def _catalogs() -> tuple[dict[str, EnvironmentConfig], dict[str, LaboratoryConfig]]:
    """Create safe synthetic catalogs with no deployable endpoints or hostnames."""
    backend = BackendConfig(
        version="4.5.6",
        base_url="https://backend.invalid",
        credentials=CredentialsReference(reference="vault:backend/synthetic"),
    )
    environment = EnvironmentConfig(
        name="synthetic-stage",
        backend=backend,
        allowed_suites=frozenset({"smoke"}),
        capabilities=frozenset({"reboot"}),
    )
    host = HostConfig(
        host_id="synthetic-host-1",
        operating_system=OperatingSystemConfig(
            family="linux",
            version="1",
            architecture="x86_64",
        ),
        capabilities=frozenset({"reboot"}),
    )
    laboratory = LaboratoryConfig(
        name="synthetic-lab",
        allowed_environments=frozenset({"synthetic-stage"}),
        allowed_suites=frozenset({"smoke"}),
        hosts=(host,),
        capabilities=frozenset({"reboot"}),
    )
    return ({environment.name: environment}, {laboratory.name: laboratory})


def test_valid_runtime_configuration(
    run_data: Callable[..., dict[str, Any]],
) -> None:
    environments, laboratories = _catalogs()
    config = RunConfig.model_validate(run_data())

    validate_test_run(
        config,
        environments=environments,
        laboratories=laboratories,
        compatible_versions={("1.2.3", "4.5.6")},
        required_capabilities=frozenset({"reboot"}),
    )


def test_reports_missing_catalog_and_incompatible_versions(
    run_data: Callable[..., dict[str, Any]],
) -> None:
    config = RunConfig.model_validate(run_data())

    with pytest.raises(ConfigurationValidationError) as captured:
        validate_test_run(
            config,
            environments={},
            laboratories={},
            compatible_versions=set(),
        )

    assert captured.value.issues == (
        "environment does not exist: synthetic-stage",
        "laboratory does not exist: synthetic-lab",
        "Agent/backend versions are incompatible: 1.2.3/4.5.6",
    )


def test_rejects_unsafe_destructive_production_run(
    run_data: Callable[..., dict[str, Any]],
) -> None:
    environments, laboratories = _catalogs()
    stage = environments["synthetic-stage"]
    production = stage.model_copy(
        update={"name": "synthetic-prod", "is_production": True}
    )
    laboratory = laboratories["synthetic-lab"].model_copy(
        update={"allowed_environments": frozenset({"synthetic-prod"})}
    )
    config = RunConfig.model_validate(
        run_data(environment="synthetic-prod", destructive_test=True)
    )

    with pytest.raises(ConfigurationValidationError) as captured:
        validate_test_run(
            config,
            environments={production.name: production},
            laboratories={laboratory.name: laboratory},
            compatible_versions={("1.2.3", "4.5.6")},
        )

    assert "production execution requires explicit approval" in captured.value.issues
    assert "destructive tests are forbidden in production" in captured.value.issues


def test_rejects_missing_capability_and_host_capacity(
    run_data: Callable[..., dict[str, Any]],
) -> None:
    environments, laboratories = _catalogs()
    config = RunConfig.model_validate(run_data(parallelism=2))

    with pytest.raises(ConfigurationValidationError) as captured:
        validate_test_run(
            config,
            environments=environments,
            laboratories=laboratories,
            compatible_versions={("1.2.3", "4.5.6")},
            required_capabilities=frozenset({"offline-install"}),
        )

    message = str(captured.value)
    assert "capabilities are unavailable" in message
    assert "insufficient eligible hosts: need 2, found 0" in message
