"""Safe diagnostic attachment normalization and failure classification."""

import json
import re
from dataclasses import dataclass
from enum import StrEnum

DEFAULT_ATTACHMENT_LIMIT_BYTES = 2 * 1024 * 1024
TRUNCATION_NOTICE = b"\n...[attachment truncated by cyber-agent-test-core]"

_SECRET_KEYS = re.compile(
    r"(?i)(password|passwd|token|secret|authorization|api[_-]?key|cookie)"
)
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]+")
_KEY_VALUE = re.compile(
    r"(?i)\b(password|passwd|token|secret|api[_-]?key)\s*([=:])\s*([^\s,;&]+)"
)


class FailureCategory(StrEnum):
    """Stable top-level result categories used by reporting and triage."""

    PRODUCT = "product failure"
    INFRASTRUCTURE = "infrastructure failure"
    CONFIGURATION = "configuration failure"
    CLEANUP = "cleanup failure"


@dataclass(frozen=True, slots=True)
class DiagnosticAttachment:
    """One bounded UTF-8 diagnostic artifact."""

    name: str
    content: bytes
    media_type: str = "text/plain"


def redact_text(value: str) -> str:
    """Redact common credential representations while preserving diagnostics."""
    redacted = _BEARER.sub(lambda match: f"{match.group(1)} [REDACTED]", value)
    return _KEY_VALUE.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", redacted
    )


def redact_value(value: object) -> object:
    """Recursively redact structured configuration and backend payloads."""
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]" if _SECRET_KEYS.search(str(key)) else redact_value(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def make_attachment(
    name: str,
    value: object,
    *,
    max_bytes: int = DEFAULT_ATTACHMENT_LIMIT_BYTES,
) -> DiagnosticAttachment:
    """Serialize, redact, and byte-limit one diagnostic artifact."""
    if max_bytes < len(TRUNCATION_NOTICE) + 1:
        raise ValueError("max_bytes is too small for the truncation notice")
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    elif isinstance(value, str):
        text = value
    else:
        text = json.dumps(redact_value(value), sort_keys=True, indent=2, default=str)
    content = redact_text(text).encode("utf-8")
    if len(content) > max_bytes:
        content = content[: max_bytes - len(TRUNCATION_NOTICE)] + TRUNCATION_NOTICE
    return DiagnosticAttachment(name=name, content=content)


def classify_exception(error: BaseException) -> FailureCategory:
    """Classify failures without exposing implementation exception types publicly."""
    names = {cls.__name__ for cls in type(error).__mro__}
    if names & {"ConfigurationValidationError", "ConfigSourceError", "ValidationError"}:
        return FailureCategory.CONFIGURATION
    if names & {"HostCleanupError"} or "cleanup" in str(error).lower():
        return FailureCategory.CLEANUP
    if names & {
        "TransportError",
        "HostUnavailableError",
        "NoHostAvailableError",
        "LeaseLostError",
        "BackendConnectionError",
    }:
        return FailureCategory.INFRASTRUCTURE
    return FailureCategory.PRODUCT
