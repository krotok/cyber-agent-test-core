"""Public, implementation-neutral pytest lifecycle models."""

from dataclasses import dataclass
from enum import StrEnum


class HostPreparation(StrEnum):
    """How a leased host is brought to its test baseline."""

    CLEAN_INSTALL = "clean-install"
    REUSE = "reuse"
    SNAPSHOT = "snapshot"


class CleanupMode(StrEnum):
    """When framework-owned state cleanup is performed."""

    ALWAYS = "always"
    ON_SUCCESS = "on-success"
    NEVER = "never"


class DiagnosticDetail(StrEnum):
    """Diagnostic detail selected for a test execution."""

    BASIC = "basic"
    EXTENDED = "extended"
    FULL = "full"


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Resolved lifecycle policy for the current pytest session."""

    host_preparation: HostPreparation
    cleanup_policy: CleanupMode
    diagnostics_level: DiagnosticDetail
    shared_ci: bool
    allow_destructive_reuse: bool
    allow_full_diagnostics_in_prod: bool

