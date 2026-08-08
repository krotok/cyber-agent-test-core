"""Schema parsing and local validation tests."""

from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError

from cyber_agent_test_core.config import (
    Architecture,
    CredentialsReference,
    InstallMode,
    RetryPolicy,
)
from cyber_agent_test_core.config import TestRunConfig as RunConfig


def test_parses_complete_test_run(
    run_data: Callable[..., dict[str, Any]],
) -> None:
    config = RunConfig.model_validate(
        run_data(
            enabled_features=["feature-a"],
            target_hosts=["synthetic-host-1"],
            retry_policy={"max_attempts": 3, "max_delay_seconds": 5},
        )
    )

    assert config.architecture is Architecture.X86_64
    assert config.enabled_features == frozenset({"feature-a"})
    assert config.retry_policy == RetryPolicy(max_attempts=3, max_delay_seconds=5)


def test_rejects_unknown_fields(run_data: Callable[..., dict[str, Any]]) -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        RunConfig.model_validate(run_data(unknown_setting=True))


def test_transition_requires_source_version(
    run_data: Callable[..., dict[str, Any]],
) -> None:
    with pytest.raises(ValidationError, match="upgrade_from_version is required"):
        RunConfig.model_validate(run_data(install_mode=InstallMode.UPGRADE))


def test_credentials_accept_references_not_secret_values() -> None:
    assert CredentialsReference(reference="vault:path/to/item").reference.startswith(
        "vault:"
    )
    with pytest.raises(ValidationError):
        CredentialsReference(reference="literal-secret-without-provider")
