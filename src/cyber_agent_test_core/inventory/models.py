"""Strict internal laboratory inventory models."""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cyber_agent_test_core.config import CredentialsReference, NetworkMode
from cyber_agent_test_core.models import Architecture, Capability, OperatingSystemFamily

Name = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")]


class ConnectionType(StrEnum):
    """Connection mechanism selected by the composition root."""

    LOCAL = "local"
    SSH = "ssh"
    WINRM = "winrm"


class HostState(StrEnum):
    """Current inventory lifecycle state."""

    AVAILABLE = "available"
    RESERVED = "reserved"
    UNAVAILABLE = "unavailable"
    BROKEN = "broken"
    QUARANTINED = "quarantined"


class HostAccessMode(StrEnum):
    """Host reservation cardinality."""

    EXCLUSIVE = "exclusive"
    SHARED = "shared"


class Host(BaseModel):
    """Logical host record containing references but never credential values."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    logical_name: Name
    operating_system: OperatingSystemFamily
    os_version: Annotated[str, Field(min_length=1, max_length=128)]
    architecture: Architecture
    connection_type: ConnectionType
    credentials_reference: CredentialsReference
    labels: frozenset[Name] = frozenset()
    installed_software: dict[Name, str] = Field(default_factory=dict)
    state: HostState = HostState.AVAILABLE
    access_mode: HostAccessMode = HostAccessMode.EXCLUSIVE
    shared_capacity: Annotated[int, Field(ge=1, le=128)] = 1
    snapshot_supported: bool = False
    reboot_supported: bool = False
    network_profile: NetworkMode = NetworkMode.ONLINE
    capabilities: frozenset[Capability] = frozenset()

    @model_validator(mode="after")
    def validate_access_mode(self) -> "Host":
        """Require exclusive hosts to expose exactly one reservation slot."""
        if self.access_mode is HostAccessMode.EXCLUSIVE and self.shared_capacity != 1:
            raise ValueError("exclusive hosts must have shared_capacity=1")
        return self


class HostRequirement(BaseModel):
    """Declarative placement constraints used by HostSelector."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operating_systems: frozenset[OperatingSystemFamily] = frozenset()
    os_versions: frozenset[str] = frozenset()
    architectures: frozenset[Architecture] = frozenset()
    connection_types: frozenset[ConnectionType] = frozenset()
    required_labels: frozenset[Name] = frozenset()
    required_software: frozenset[Name] = frozenset()
    required_capabilities: frozenset[Capability] = frozenset()
    network_profiles: frozenset[NetworkMode] = frozenset()
    access_mode: HostAccessMode | None = None
    require_snapshot: bool = False
    require_reboot: bool = False
    logical_names: frozenset[Name] = frozenset()
