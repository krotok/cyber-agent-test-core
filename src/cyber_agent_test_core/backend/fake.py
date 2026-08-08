"""Deterministic backend fake for unit and flow tests."""

from dataclasses import dataclass

from cyber_agent_test_core.backend.models import (
    BackendAgentStatus,
    FeatureFlagState,
    PackageMetadata,
    PolicyAssignmentResult,
    RegistrationResult,
)


@dataclass(frozen=True, slots=True)
class BackendCall:
    """Recorded semantic call without credentials."""

    operation: str
    arguments: tuple[str, ...]
    idempotency_key: str | None = None


class FakeBackendClient:
    """In-memory typed fake that performs no HTTP requests."""

    def __init__(self) -> None:
        self.registrations: dict[str, RegistrationResult] = {}
        self.statuses: dict[str, BackendAgentStatus] = {}
        self.policy_assignments: dict[tuple[str, str], PolicyAssignmentResult] = {}
        self.feature_flags: dict[str, FeatureFlagState] = {}
        self.packages: dict[tuple[str, str, str], PackageMetadata] = {}
        self.calls: list[BackendCall] = []

    def register_agent(
        self, logical_name: str, *, idempotency_key: str | None = None
    ) -> RegistrationResult:
        self.calls.append(
            BackendCall("register_agent", (logical_name,), idempotency_key)
        )
        return self.registrations[logical_name]

    def get_agent_status(self, agent_id: str) -> BackendAgentStatus:
        self.calls.append(BackendCall("get_agent_status", (agent_id,)))
        return self.statuses[agent_id]

    def assign_policy(
        self,
        agent_id: str,
        policy_id: str,
        *,
        idempotency_key: str | None = None,
    ) -> PolicyAssignmentResult:
        self.calls.append(
            BackendCall("assign_policy", (agent_id, policy_id), idempotency_key)
        )
        return self.policy_assignments[(agent_id, policy_id)]

    def get_feature_flags(self, tenant_reference: str) -> FeatureFlagState:
        self.calls.append(BackendCall("get_feature_flags", (tenant_reference,)))
        return self.feature_flags[tenant_reference]

    def get_package_metadata(
        self, version: str, operating_system: str, architecture: str
    ) -> PackageMetadata:
        self.calls.append(
            BackendCall(
                "get_package_metadata", (version, operating_system, architecture)
            )
        )
        return self.packages[(version, operating_system, architecture)]
