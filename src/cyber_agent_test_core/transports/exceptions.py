"""Transport error taxonomy used for safe retry classification."""


class TransportError(RuntimeError):
    """Base transport failure with explicit retry evidence."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        self.retryable = retryable
        super().__init__(message)


class AuthenticationError(TransportError):
    """Authentication failed and must never be retried automatically."""


class CommandTimeoutError(TransportError):
    """A command exceeded its deadline and has an unknown product-side outcome."""


class UnsupportedOperationError(TransportError):
    """The selected implementation does not support an operation."""


class HostUnavailableError(TransportError):
    """The host is proven unreachable and the operation may be retried."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=True)
