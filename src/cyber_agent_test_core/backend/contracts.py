"""Typed backend/control-plane client protocols."""

from typing import Protocol

from cyber_agent_test_core.backend.models import (
    BackendAgentStatus,
    FeatureFlagState,
    PackageMetadata,
    PolicyAssignmentResult,
    RegistrationResult,
)


class AgentRegistrationAPI(Protocol):
    """Agent registration operations."""

    def register_agent(
        self,
        logical_name: str,
        *,
        idempotency_key: str | None = None,
    ) -> RegistrationResult: ...


class AgentStatusAPI(Protocol):
    """Agent status operations."""

    def get_agent_status(self, agent_id: str) -> BackendAgentStatus: ...


class PolicyAPI(Protocol):
    """Policy control operations."""

    def assign_policy(
        self,
        agent_id: str,
        policy_id: str,
        *,
        idempotency_key: str | None = None,
    ) -> PolicyAssignmentResult: ...


class FeatureFlagsAPI(Protocol):
    """Feature-flag query operations."""

    def get_feature_flags(self, tenant_reference: str) -> FeatureFlagState: ...


class PackageMetadataAPI(Protocol):
    """Package metadata query operations."""

    def get_package_metadata(
        self,
        version: str,
        operating_system: str,
        architecture: str,
    ) -> PackageMetadata: ...


class BackendClient(
    AgentRegistrationAPI,
    AgentStatusAPI,
    PolicyAPI,
    FeatureFlagsAPI,
    PackageMetadataAPI,
    Protocol,
):
    """Complete typed backend client contract."""
