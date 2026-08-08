"""Capability resolver tests, including exact version boundaries."""

import pytest

from cyber_agent_test_core.capabilities import (
    CapabilityResolver,
    CompatibilityMatrix,
    CompatibilityRule,
    EnvironmentFeatureFlagProvider,
)
from cyber_agent_test_core.models import (
    Capability,
    CapabilityContext,
    UnsupportedConfigurationError,
)


def _context(**updates: object) -> CapabilityContext:
    """Create a synthetic context with no external infrastructure data."""
    values: dict[str, object] = {
        "agent_version": "2.0.0",
        "backend_version": "5.0.0",
        "operating_system": "linux",
        "os_version": "24.04",
        "kernel_build": "6.8.0",
        "architecture": "arm64",
        "feature_flags": ["flag-a"],
        "licenses": ["license-a"],
        "environment": "synthetic-stage",
    }
    values.update(updates)
    return CapabilityContext.model_validate(values)


def _boundary_matrix() -> CompatibilityMatrix:
    """Create a matrix whose supported interval has inclusive lower bounds."""
    return CompatibilityMatrix(
        rules=(
            CompatibilityRule(
                rule_id="boundary-rule",
                agent_version=">=2.0.0,<3.0.0",
                backend_version=">=5.0.0,<6.0.0",
                operating_systems=frozenset({"linux"}),
                os_version=">=24.04,<25",
                kernel_build=">=6.8,<7",
                architectures=frozenset({"arm64"}),
                required_features=frozenset({"flag-a"}),
                licenses=frozenset({"license-a"}),
                environments=frozenset({"synthetic-stage"}),
                grants=frozenset(
                    {Capability.ARM64_SUPPORT, Capability.KERNEL_EVENTS}
                ),
            ),
        )
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("agent_version", "2.0.0"),
        ("agent_version", "2.999"),
        ("backend_version", "5.0.0"),
        ("os_version", "24.04"),
        ("kernel_build", "6.8.0"),
    ],
)
def test_inclusive_version_boundaries_are_supported(field: str, value: str) -> None:
    result = CapabilityResolver(_boundary_matrix()).resolve(_context(**{field: value}))

    assert result.supported
    assert result.capabilities.supports(Capability.ARM64_SUPPORT)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("agent_version", "1.9.999"),
        ("agent_version", "3.0.0"),
        ("backend_version", "6.0.0"),
        ("os_version", "25.0"),
        ("kernel_build", "7.0.0"),
    ],
)
def test_excluded_version_boundaries_are_unsupported(field: str, value: str) -> None:
    result = CapabilityResolver(_boundary_matrix()).resolve(_context(**{field: value}))

    assert not result.supported
    assert result.reasons == ("no compatibility rule matches the target configuration",)
    with pytest.raises(UnsupportedConfigurationError, match="no compatibility rule"):
        result.require_supported()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("operating_system", "windows"),
        ("architecture", "x86_64"),
        ("feature_flags", []),
        ("licenses", []),
        ("environment", "synthetic-dev"),
    ],
)
def test_every_non_version_dimension_controls_resolution(
    field: str,
    value: object,
) -> None:
    result = CapabilityResolver(_boundary_matrix()).resolve(_context(**{field: value}))

    assert not result.supported


def test_feature_flag_provider_is_applied_centrally() -> None:
    provider = EnvironmentFeatureFlagProvider(
        {"synthetic-stage": frozenset({"flag-a"})}
    )
    context = _context(feature_flags=[])

    result = CapabilityResolver(_boundary_matrix(), provider).resolve(context)

    assert result.supported
    assert result.context.feature_flags == frozenset({"flag-a"})


def test_explicit_unsupported_rule_preserves_exact_reason() -> None:
    matrix = CompatibilityMatrix(
        rules=(
            CompatibilityRule(
                rule_id="blocked-combination",
                supported=False,
                reason="kernel build is blocked by vendor policy",
            ),
        )
    )

    result = CapabilityResolver(matrix).resolve(_context())

    assert result.reasons == ("kernel build is blocked by vendor policy",)
