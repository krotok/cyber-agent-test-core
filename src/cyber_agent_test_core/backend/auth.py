"""Authentication token resolution and refresh contracts."""

from typing import Protocol

from cyber_agent_test_core.config import CredentialsReference


class SecretResolver(Protocol):
    """Resolve a credential reference at runtime without logging its value."""

    def resolve(self, reference: CredentialsReference) -> str: ...


class AuthenticationProvider(Protocol):
    """Supply and refresh an in-memory authorization token."""

    def get_token(self) -> str: ...

    def refresh_token(self) -> str: ...


class RefreshingTokenProvider:
    """Lazy token provider backed by an external secret resolver."""

    def __init__(
        self,
        reference: CredentialsReference,
        resolver: SecretResolver,
    ) -> None:
        self._reference = reference
        self._resolver = resolver
        self._token: str | None = None

    def get_token(self) -> str:
        """Resolve once and retain only the runtime token in memory."""
        if self._token is None:
            self._token = self._resolver.resolve(self._reference)
        return self._token

    def refresh_token(self) -> str:
        """Force re-resolution after an authentication rejection."""
        self._token = self._resolver.resolve(self._reference)
        return self._token
