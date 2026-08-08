"""Centralized, explainable capability resolution."""

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

from cyber_agent_test_core.capabilities.matrix import (
    CompatibilityDataError,
    CompatibilityMatrix,
    CompatibilityRule,
)
from cyber_agent_test_core.capabilities.providers import FeatureFlagProvider
from cyber_agent_test_core.models import (
    CapabilityContext,
    CapabilitySet,
    CompatibilityResult,
)


def _version_matches(value: str | None, specifier: str) -> bool:
    """Match a normalized version against an optional PEP 440 specifier."""
    if not specifier:
        return True
    if value is None:
        return False
    try:
        return Version(value) in SpecifierSet(specifier)
    except InvalidVersion as error:
        raise CompatibilityDataError(f"invalid context version: {value}") from error


def _rule_matches(rule: CompatibilityRule, context: CapabilityContext) -> bool:
    """Evaluate every declared dimension of one matrix rule."""
    return (
        _version_matches(context.agent_version, rule.agent_version)
        and _version_matches(context.backend_version, rule.backend_version)
        and (
            not rule.operating_systems
            or context.operating_system in rule.operating_systems
        )
        and _version_matches(context.os_version, rule.os_version)
        and _version_matches(context.kernel_build, rule.kernel_build)
        and (not rule.architectures or context.architecture in rule.architectures)
        and rule.required_features <= context.feature_flags
        and not (rule.forbidden_features & context.feature_flags)
        and rule.licenses <= context.licenses
        and (not rule.environments or context.environment in rule.environments)
    )


class CapabilityResolver:
    """Resolve capabilities only from typed context and declarative matrix data."""

    def __init__(
        self,
        matrix: CompatibilityMatrix,
        feature_flag_provider: FeatureFlagProvider | None = None,
    ) -> None:
        self._matrix = matrix
        self._feature_flag_provider = feature_flag_provider

    def resolve(self, context: CapabilityContext) -> CompatibilityResult:
        """Return capabilities and exact unsupported reasons for one target."""
        if self._feature_flag_provider is not None:
            provider_flags = self._feature_flag_provider.get_enabled_flags(context)
            context = context.model_copy(
                update={"feature_flags": context.feature_flags | provider_flags}
            )

        capabilities = CapabilitySet(values=self._matrix.default_capabilities)
        matched: list[str] = []
        reasons: list[str] = []
        for rule in self._matrix.rules:
            if _rule_matches(rule, context):
                matched.append(rule.rule_id)
                capabilities = capabilities.with_updates(
                    grants=rule.grants,
                    removals=rule.removes,
                )
                if not rule.supported:
                    reasons.append(rule.reason or f"rejected by rule {rule.rule_id}")

        if self._matrix.require_matching_rule and not matched:
            reasons.append("no compatibility rule matches the target configuration")

        return CompatibilityResult(
            supported=not reasons,
            capabilities=capabilities,
            context=context,
            reasons=tuple(reasons),
            matched_rules=tuple(matched),
        )
