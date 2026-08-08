"""HTTP adapter boundary and safe diagnostic attachment policy."""

import json
from dataclasses import dataclass, field
from typing import Protocol

from cyber_agent_test_core.backend.models import (
    BackendClientSettings,
    ProxyConfiguration,
    TLSConfiguration,
)


@dataclass(frozen=True, slots=True)
class HTTPRequest:
    """Complete HTTP request passed to an injected network adapter."""

    method: str
    url: str
    headers: dict[str, str] = field(repr=False)
    body: bytes | None
    timeout_seconds: float
    tls: TLSConfiguration
    proxy: ProxyConfiguration | None


@dataclass(frozen=True, slots=True)
class HTTPResponse:
    """Raw HTTP response returned by a network adapter."""

    status_code: int
    headers: dict[str, str]
    body: bytes


class HTTPAdapter(Protocol):
    """Injectable network implementation; tests use a fake adapter."""

    def send(self, request: HTTPRequest) -> HTTPResponse: ...


class AttachmentSink(Protocol):
    """Internal reporting sink for already-sanitized HTTP evidence."""

    def attach(self, name: str, body: str) -> None: ...


SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "client_secret",
        "password",
        "secret",
        "token",
        "x-tenant-reference",
    }
)


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Mask authorization and other credential-bearing HTTP headers."""
    return {
        key: "<redacted>" if key.casefold() in SENSITIVE_KEYS else value
        for key, value in headers.items()
    }


def _redact_json(value: object) -> object:
    """Recursively redact common sensitive JSON keys."""
    if isinstance(value, dict):
        return {
            str(key): (
                "<redacted>"
                if str(key).casefold() in SENSITIVE_KEYS
                else _redact_json(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    return value


def sanitize_body(
    body: bytes | None,
    *,
    limit: int,
    suppress: bool,
) -> str:
    """Suppress production data, redact JSON, and enforce a byte-size budget."""
    if body is None:
        return ""
    if suppress:
        return "<suppressed production body>"
    truncated = body[:limit]
    suffix = "<truncated>" if len(body) > limit else ""
    try:
        parsed = json.loads(truncated.decode("utf-8"))
        rendered = json.dumps(_redact_json(parsed), sort_keys=True)
    except (UnicodeDecodeError, json.JSONDecodeError):
        rendered = truncated.decode("utf-8", errors="replace")
    return rendered + suffix


class HTTPAttachmentPolicy:
    """Create bounded sanitized request/response evidence."""

    def __init__(self, settings: BackendClientSettings) -> None:
        self._settings = settings

    def _suppress_body(self) -> bool:
        """Default-deny all body attachments in production."""
        return (
            self._settings.environment.casefold() == "prod"
            and not self._settings.allow_production_body_attachments
        )

    def request_attachment(self, request: HTTPRequest) -> str:
        """Render a sanitized request attachment."""
        return json.dumps(
            {
                "method": request.method,
                "url": (
                    "<suppressed production URL>"
                    if self._suppress_body()
                    else request.url
                ),
                "headers": redact_headers(request.headers),
                "body": sanitize_body(
                    request.body,
                    limit=self._settings.max_attachment_body_bytes,
                    suppress=self._suppress_body(),
                ),
            },
            sort_keys=True,
        )

    def response_attachment(self, response: HTTPResponse) -> str:
        """Render a sanitized response attachment."""
        return json.dumps(
            {
                "status_code": response.status_code,
                "headers": redact_headers(response.headers),
                "body": sanitize_body(
                    response.body,
                    limit=self._settings.max_attachment_body_bytes,
                    suppress=self._suppress_body(),
                ),
            },
            sort_keys=True,
        )
