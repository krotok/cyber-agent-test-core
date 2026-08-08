"""Strict internal backend request configuration and typed responses."""

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Self

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

from cyber_agent_test_core.config import CredentialsReference

Name = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")]


class StrictBackendModel(BaseModel):
    """Immutable backend model that rejects unknown wire fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class TLSConfiguration(StrictBackendModel):
    """TLS verification and optional mTLS references."""

    verify_certificate: bool = True
    ca_bundle: Path | None = None
    client_certificate: CredentialsReference | None = None
    client_private_key: CredentialsReference | None = None

    @model_validator(mode="after")
    def validate_mtls_pair(self) -> Self:
        """Require both certificate and private-key references for mTLS."""
        if (self.client_certificate is None) != (self.client_private_key is None):
            raise ValueError("mTLS requires certificate and private-key references")
        return self


class ProxyConfiguration(StrictBackendModel):
    """Proxy endpoint and optional external credential reference."""

    url: AnyHttpUrl
    credentials: CredentialsReference | None = None


class BackendClientSettings(StrictBackendModel):
    """Runtime HTTP behavior without embedded secret values."""

    base_url: AnyHttpUrl
    environment: Name
    authentication: CredentialsReference
    request_timeout_seconds: Annotated[float, Field(gt=0, le=300)] = 30
    max_safe_attempts: Annotated[int, Field(ge=1, le=10)] = 2
    tls: TLSConfiguration = TLSConfiguration()
    proxy: ProxyConfiguration | None = None
    max_attachment_body_bytes: Annotated[int, Field(ge=0, le=1_048_576)] = 16_384
    allow_production_body_attachments: bool = False

    @model_validator(mode="after")
    def require_production_certificate_validation(self) -> Self:
        """Forbid disabling certificate validation against production."""
        if self.environment.casefold() == "prod" and not self.tls.verify_certificate:
            raise ValueError("certificate validation is mandatory in prod")
        return self


class BackendAgentState(StrEnum):
    """Normalized backend view of Agent state."""

    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class RegistrationResult(StrictBackendModel):
    """Typed Agent registration result."""

    agent_id: Name
    registered_at: datetime
    correlation_id: str


class BackendAgentStatus(StrictBackendModel):
    """Typed control-plane Agent status."""

    agent_id: Name
    state: BackendAgentState
    last_seen_at: datetime | None = None
    policy_id: Name | None = None


class PolicyAssignmentResult(StrictBackendModel):
    """Typed policy assignment acknowledgement."""

    agent_id: Name
    policy_id: Name
    accepted: bool
    correlation_id: str


class FeatureFlagState(StrictBackendModel):
    """Resolved backend feature flags and revision."""

    flags: dict[Name, bool]
    revision: str


class PackageMetadata(StrictBackendModel):
    """Typed Agent package metadata without package credentials."""

    version: str
    operating_system: Name
    architecture: Name
    download_url: AnyHttpUrl
    sha256: Annotated[str, Field(pattern=r"^[0-9a-fA-F]{64}$")]
    size_bytes: Annotated[int, Field(ge=0)]
