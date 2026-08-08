"""Pydantic schemas for all configuration boundaries."""

from enum import StrEnum
from typing import Annotated, Self

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, model_validator

from cyber_agent_test_core.models import Architecture, OperatingSystemFamily

Version = Annotated[str, Field(min_length=1, max_length=128)]
Name = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")]


class StrictConfigModel(BaseModel):
    """Base class that rejects unknown keys and runtime mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class NetworkMode(StrEnum):
    """Supported host connectivity modes."""

    ONLINE = "online"
    OFFLINE = "offline"
    PROXY = "proxy"
    RESTRICTED = "restricted"


class InstallMode(StrEnum):
    """Requested Agent lifecycle operation."""

    INSTALL = "install"
    UNINSTALL = "uninstall"
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    ROLLBACK = "rollback"
    PREINSTALLED = "preinstalled"


class DiagnosticsLevel(StrEnum):
    """Requested diagnostic collection detail."""

    NONE = "none"
    BASIC = "basic"
    EXTENDED = "extended"
    FULL = "full"


class HostPreparationMode(StrEnum):
    """Host preparation policy before test execution."""

    NONE = "none"
    VERIFY = "verify"
    RESET = "reset"
    CLEAN_INSTALL = "clean-install"
    REUSE = "reuse"
    SNAPSHOT = "snapshot"


class CredentialsReference(StrictConfigModel):
    """Opaque reference resolved by an external secret provider at runtime."""

    reference: Annotated[
        str,
        Field(pattern=r"^[a-z][a-z0-9_-]*:[A-Za-z0-9][A-Za-z0-9_./-]*$"),
    ]


class RetryPolicy(StrictConfigModel):
    """Bounded retry policy for transient infrastructure operations only."""

    max_attempts: Annotated[int, Field(ge=1, le=10)] = 1
    initial_delay_seconds: Annotated[float, Field(ge=0, le=60)] = 0
    max_delay_seconds: Annotated[float, Field(ge=0, le=300)] = 0
    multiplier: Annotated[float, Field(ge=1, le=10)] = 1

    @model_validator(mode="after")
    def validate_delays(self) -> Self:
        """Ensure the retry delay cannot shrink below its initial value."""
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ValueError("max_delay_seconds must be >= initial_delay_seconds")
        return self


class CleanupPolicy(StrictConfigModel):
    """Cleanup behavior applied by framework-owned finalizers."""

    restore_host: bool = True
    uninstall_agent: bool = False
    collect_diagnostics_on_failure: bool = True
    release_host: bool = True


class FeatureSetConfig(StrictConfigModel):
    """Available and forced feature states for an execution target."""

    available: frozenset[Name] = frozenset()
    enabled: frozenset[Name] = frozenset()
    disabled: frozenset[Name] = frozenset()

    @model_validator(mode="after")
    def validate_feature_sets(self) -> Self:
        """Reject contradictory or unavailable feature selections."""
        overlap = self.enabled & self.disabled
        if overlap:
            raise ValueError(
                f"features cannot be enabled and disabled: {sorted(overlap)}"
            )
        unavailable = (self.enabled | self.disabled) - self.available
        if unavailable:
            raise ValueError(
                f"feature state requested for unavailable: {sorted(unavailable)}"
            )
        return self


class NetworkConfig(StrictConfigModel):
    """Network policy without embedded proxy credentials."""

    mode: NetworkMode = NetworkMode.ONLINE
    proxy_url: AnyUrl | None = None
    proxy_credentials: CredentialsReference | None = None
    allowed_endpoints: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_proxy(self) -> Self:
        """Require proxy settings only when proxy networking is selected."""
        if self.mode is NetworkMode.PROXY and self.proxy_url is None:
            raise ValueError("proxy_url is required in proxy mode")
        if self.mode is not NetworkMode.PROXY and self.proxy_credentials is not None:
            raise ValueError("proxy_credentials requires proxy mode")
        return self


class OperatingSystemConfig(StrictConfigModel):
    """Normalized operating-system and processor identity."""

    family: OperatingSystemFamily
    version: Version
    architecture: Architecture


class HostConfig(StrictConfigModel):
    """Normalized inventory host record containing no credentials."""

    host_id: Name
    operating_system: OperatingSystemConfig
    capabilities: frozenset[Name] = frozenset()
    network_modes: frozenset[NetworkMode] = frozenset({NetworkMode.ONLINE})
    available: bool = True
    shared_capacity: Annotated[int, Field(ge=1, le=128)] = 1


class AgentConfig(StrictConfigModel):
    """Agent artifact and version selection."""

    version: Version
    artifact_reference: str | None = None
    credentials: CredentialsReference | None = None


class BackendConfig(StrictConfigModel):
    """Versioned backend endpoint and authentication reference."""

    version: Version
    base_url: AnyUrl
    credentials: CredentialsReference


class ProductConfig(StrictConfigModel):
    """Resolved Agent/backend product pairing and feature state."""

    agent: AgentConfig
    backend: BackendConfig
    features: FeatureSetConfig = FeatureSetConfig()


class EnvironmentConfig(StrictConfigModel):
    """Named deployment environment policy."""

    name: Name
    backend: BackendConfig
    allowed_suites: frozenset[Name]
    capabilities: frozenset[Name] = frozenset()
    is_production: bool = False
    test_execution_enabled: bool = True


class LaboratoryConfig(StrictConfigModel):
    """Normalized laboratory inventory and placement policy."""

    name: Name
    allowed_environments: frozenset[Name]
    allowed_suites: frozenset[Name]
    hosts: tuple[HostConfig, ...]
    capabilities: frozenset[Name] = frozenset()


class CIContext(StrictConfigModel):
    """Optional CI correlation identifiers."""

    provider: Name | None = None
    job_id: str | None = None
    run_id: str | None = None
    worker_id: str | None = None


class TestRunConfig(StrictConfigModel):
    """Fully merged and structurally valid test-run configuration."""

    agent_version: Version
    backend_version: Version
    environment: Name
    lab: Name
    suite: Name
    enabled_features: frozenset[Name] = frozenset()
    disabled_features: frozenset[Name] = frozenset()
    target_hosts: tuple[Name, ...] = ()
    tenant: CredentialsReference
    build_id: str
    git_commit: Annotated[str, Field(pattern=r"^[0-9a-fA-F]{7,64}$")]
    execution_id: Name
    install_mode: InstallMode = InstallMode.INSTALL
    upgrade_from_version: Version | None = None
    architecture: Architecture
    parallelism: Annotated[int, Field(ge=1, le=1024)] = 1
    retry_policy: RetryPolicy = RetryPolicy()
    cleanup_policy: CleanupPolicy = CleanupPolicy()
    diagnostics_level: DiagnosticsLevel = DiagnosticsLevel.BASIC
    host_preparation_mode: HostPreparationMode = HostPreparationMode.VERIFY
    network: NetworkConfig = NetworkConfig()
    ci_context: CIContext = CIContext()
    production_approved: bool = False
    destructive_test: bool = False

    @model_validator(mode="after")
    def validate_run_invariants(self) -> Self:
        """Reject contradictory features and incomplete upgrade requests."""
        overlap = self.enabled_features & self.disabled_features
        if overlap:
            raise ValueError(
                f"features cannot be enabled and disabled: {sorted(overlap)}"
            )
        requires_source = self.install_mode in {
            InstallMode.UPGRADE,
            InstallMode.DOWNGRADE,
            InstallMode.ROLLBACK,
        }
        if requires_source and self.upgrade_from_version is None:
            raise ValueError("upgrade_from_version is required for this install_mode")
        if not requires_source and self.upgrade_from_version is not None:
            raise ValueError("upgrade_from_version is only valid for transition modes")
        if len(set(self.target_hosts)) != len(self.target_hosts):
            raise ValueError("target_hosts must not contain duplicates")
        return self
