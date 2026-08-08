"""Backend boundary failures with explicit retry classification."""


class BackendError(RuntimeError):
    """Base class for internal backend client failures."""


class BackendConnectionError(BackendError):
    """Network failure reported by an HTTP adapter."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class BackendRequestTimeoutError(BackendConnectionError):
    """Backend request exceeded its configured deadline."""


class BackendAuthenticationError(BackendError):
    """Authentication failed even after one token refresh."""


class BackendHTTPError(BackendError):
    """Backend returned an unsuccessful HTTP status."""

    def __init__(self, status_code: int, correlation_id: str) -> None:
        super().__init__(
            f"backend returned HTTP {status_code}; correlation_id={correlation_id}"
        )
        self.status_code = status_code
        self.correlation_id = correlation_id


class BackendResponseValidationError(BackendError):
    """Backend response did not conform to the expected schema."""

