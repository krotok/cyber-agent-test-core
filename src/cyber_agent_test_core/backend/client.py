"""Typed backend client implemented over an injected HTTP adapter."""

import json
from collections.abc import Callable
from typing import TypeVar
from urllib.parse import quote, urlencode
from uuid import uuid4

from pydantic import ValidationError

from cyber_agent_test_core.backend.auth import AuthenticationProvider
from cyber_agent_test_core.backend.exceptions import (
    BackendAuthenticationError,
    BackendConnectionError,
    BackendHTTPError,
    BackendResponseValidationError,
)
from cyber_agent_test_core.backend.http import (
    AttachmentSink,
    HTTPAdapter,
    HTTPAttachmentPolicy,
    HTTPRequest,
    HTTPResponse,
)
from cyber_agent_test_core.backend.models import (
    BackendAgentStatus,
    BackendClientSettings,
    FeatureFlagState,
    PackageMetadata,
    PolicyAssignmentResult,
    RegistrationResult,
    StrictBackendModel,
)

ResponseT = TypeVar("ResponseT", bound=StrictBackendModel)


class HTTPBackendClient:
    """Synchronous control-plane client with bounded safe retries."""

    _TRANSIENT_STATUSES = frozenset({502, 503, 504})

    def __init__(
        self,
        settings: BackendClientSettings,
        adapter: HTTPAdapter,
        authentication: AuthenticationProvider,
        *,
        attachment_sink: AttachmentSink | None = None,
        correlation_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._settings = settings
        self._adapter = adapter
        self._authentication = authentication
        self._attachment_sink = attachment_sink
        self._attachment_policy = HTTPAttachmentPolicy(settings)
        self._correlation_id_factory = correlation_id_factory or (lambda: str(uuid4()))

    def _url(self, path: str) -> str:
        return f"{str(self._settings.base_url).rstrip('/')}/{path.lstrip('/')}"

    def _send(self, request: HTTPRequest) -> HTTPResponse:
        if self._attachment_sink is not None:
            self._attachment_sink.attach(
                "backend HTTP request",
                self._attachment_policy.request_attachment(request),
            )
        response = self._adapter.send(request)
        if self._attachment_sink is not None:
            self._attachment_sink.attach(
                "backend HTTP response",
                self._attachment_policy.response_attachment(response),
            )
        return response

    def _request(
        self,
        method: str,
        path: str,
        response_type: type[ResponseT],
        *,
        payload: dict[str, object] | None = None,
        idempotency_key: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> ResponseT:
        safe_to_retry = method == "GET" or idempotency_key is not None
        maximum_attempts = self._settings.max_safe_attempts if safe_to_retry else 1
        correlation_id = self._correlation_id_factory()
        body = None if payload is None else json.dumps(payload).encode()
        refreshed = False
        attempt = 0

        while attempt < maximum_attempts:
            attempt += 1
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self._authentication.get_token()}",
                "X-Correlation-ID": correlation_id,
            }
            if body is not None:
                headers["Content-Type"] = "application/json"
            if idempotency_key is not None:
                headers["Idempotency-Key"] = idempotency_key
            if extra_headers is not None:
                headers.update(extra_headers)
            request = HTTPRequest(
                method=method,
                url=self._url(path),
                headers=headers,
                body=body,
                timeout_seconds=self._settings.request_timeout_seconds,
                tls=self._settings.tls,
                proxy=self._settings.proxy,
            )
            try:
                response = self._send(request)
            except BackendConnectionError as error:
                if not error.retryable or attempt >= maximum_attempts:
                    raise
                continue

            if response.status_code == 401:
                if refreshed:
                    raise BackendAuthenticationError(
                        "backend rejected refreshed token; "
                        f"correlation_id={correlation_id}"
                    )
                self._authentication.refresh_token()
                refreshed = True
                attempt -= 1
                continue
            if (
                response.status_code in self._TRANSIENT_STATUSES
                and attempt < maximum_attempts
            ):
                continue
            if not 200 <= response.status_code < 300:
                raise BackendHTTPError(response.status_code, correlation_id)
            return self._validate_response(response, response_type, correlation_id)

        raise AssertionError("bounded request loop exited without a result")

    @staticmethod
    def _validate_response(
        response: HTTPResponse,
        response_type: type[ResponseT],
        correlation_id: str,
    ) -> ResponseT:
        try:
            value = json.loads(response.body)
            if not isinstance(value, dict):
                raise ValueError("response root must be an object")
            if "correlation_id" in response_type.model_fields:
                value.setdefault("correlation_id", correlation_id)
            return response_type.model_validate(value)
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValidationError,
            ValueError,
        ) as error:
            raise BackendResponseValidationError(
                f"invalid {response_type.__name__}; correlation_id={correlation_id}"
            ) from error

    def register_agent(
        self, logical_name: str, *, idempotency_key: str | None = None
    ) -> RegistrationResult:
        return self._request(
            "POST",
            "/agents/registrations",
            RegistrationResult,
            payload={"logical_name": logical_name},
            idempotency_key=idempotency_key,
        )

    def get_agent_status(self, agent_id: str) -> BackendAgentStatus:
        return self._request(
            "GET", f"/agents/{quote(agent_id, safe='')}/status", BackendAgentStatus
        )

    def assign_policy(
        self,
        agent_id: str,
        policy_id: str,
        *,
        idempotency_key: str | None = None,
    ) -> PolicyAssignmentResult:
        return self._request(
            "POST",
            f"/agents/{quote(agent_id, safe='')}/policy",
            PolicyAssignmentResult,
            payload={"policy_id": policy_id},
            idempotency_key=idempotency_key,
        )

    def get_feature_flags(self, tenant_reference: str) -> FeatureFlagState:
        return self._request(
            "GET",
            "/feature-flags",
            FeatureFlagState,
            extra_headers={"X-Tenant-Reference": tenant_reference},
        )

    def get_package_metadata(
        self, version: str, operating_system: str, architecture: str
    ) -> PackageMetadata:
        query = urlencode(
            {"operating_system": operating_system, "architecture": architecture}
        )
        return self._request(
            "GET",
            f"/packages/{quote(version, safe='')}?{query}",
            PackageMetadata,
        )
