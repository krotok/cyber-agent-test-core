"""Backend client behavior without real network access."""

import json
from collections import deque
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cyber_agent_test_core.backend import (
    BackendAgentState,
    BackendAgentStatus,
    BackendAuthenticationError,
    BackendClient,
    BackendClientSettings,
    BackendConnectionError,
    BackendHTTPError,
    BackendResponseValidationError,
    FakeBackendClient,
    FeatureFlagState,
    HTTPBackendClient,
    HTTPRequest,
    HTTPResponse,
    PackageMetadata,
    PolicyAssignmentResult,
    ProxyConfiguration,
    RefreshingTokenProvider,
    RegistrationResult,
    TLSConfiguration,
)
from cyber_agent_test_core.config import CredentialsReference


class Resolver:
    """Synthetic token resolver."""

    def __init__(self, *tokens: str) -> None:
        self.tokens = deque(tokens)
        self.calls = 0

    def resolve(self, reference: CredentialsReference) -> str:
        self.calls += 1
        assert reference.reference.startswith("vault:")
        return self.tokens.popleft()


class Adapter:
    """Scripted injected HTTP adapter."""

    def __init__(self, *results: HTTPResponse | BackendConnectionError) -> None:
        self.results = deque(results)
        self.requests: list[HTTPRequest] = []

    def send(self, request: HTTPRequest) -> HTTPResponse:
        self.requests.append(request)
        result = self.results.popleft()
        if isinstance(result, BackendConnectionError):
            raise result
        return result


class Sink:
    """Collect sanitized attachment text."""

    def __init__(self) -> None:
        self.values: list[str] = []

    def attach(self, name: str, body: str) -> None:
        self.values.append(f"{name}:{body}")


def response(status: int, value: object) -> HTTPResponse:
    return HTTPResponse(status, {}, json.dumps(value).encode())


def settings(**updates: object) -> BackendClientSettings:
    values: dict[str, object] = {
        "base_url": "https://backend.invalid/control",
        "environment": "stage",
        "authentication": {"reference": "vault:synthetic/backend"},
        "max_safe_attempts": 2,
    }
    values.update(updates)
    return BackendClientSettings.model_validate(values)


def client(
    adapter: Adapter,
    *,
    resolver: Resolver | None = None,
    configured: BackendClientSettings | None = None,
    sink: Sink | None = None,
) -> HTTPBackendClient:
    token_resolver = resolver or Resolver("synthetic-token")
    auth = RefreshingTokenProvider(
        CredentialsReference(reference="vault:synthetic/backend"), token_resolver
    )
    return HTTPBackendClient(
        configured or settings(),
        adapter,
        auth,
        attachment_sink=sink,
        correlation_id_factory=lambda: "correlation-1",
    )


def test_token_provider_resolves_lazily_and_refreshes() -> None:
    resolver = Resolver("first", "second")
    provider = RefreshingTokenProvider(
        CredentialsReference(reference="vault:synthetic/backend"), resolver
    )
    assert provider.get_token() == provider.get_token() == "first"
    assert provider.refresh_token() == "second"
    assert resolver.calls == 2


def test_typed_endpoints_and_transport_options() -> None:
    now = "2026-01-02T03:04:05Z"
    adapter = Adapter(
        response(201, {"agent_id": "agent-1", "registered_at": now}),
        response(200, {"agent_id": "agent-1", "state": "online"}),
        response(200, {"agent_id": "agent-1", "policy_id": "base", "accepted": True}),
        response(200, {"flags": {"remote_commands": True}, "revision": "7"}),
        response(
            200,
            {
                "version": "2.1.0",
                "operating_system": "linux",
                "architecture": "arm64",
                "download_url": "https://packages.invalid/agent.pkg",
                "sha256": "a" * 64,
                "size_bytes": 42,
            },
        ),
    )
    configured = settings(
        request_timeout_seconds=17,
        tls={"ca_bundle": "certs/lab.pem"},
        proxy={"url": "https://proxy.invalid"},
    )
    backend = client(adapter, configured=configured)

    assert backend.register_agent("host-1").agent_id == "agent-1"
    assert backend.get_agent_status("agent-1").state is BackendAgentState.ONLINE
    assert backend.assign_policy("agent-1", "base").accepted
    assert backend.get_feature_flags("tenant-ref").flags["remote_commands"]
    assert backend.get_package_metadata("2.1.0", "linux", "arm64").size_bytes == 42
    assert all(request.timeout_seconds == 17 for request in adapter.requests)
    assert all(request.tls.ca_bundle is not None for request in adapter.requests)
    assert all(request.proxy is not None for request in adapter.requests)
    assert adapter.requests[3].headers["X-Tenant-Reference"] == "tenant-ref"
    assert "operating_system=linux" in adapter.requests[4].url


def test_get_retries_connection_failure_with_same_correlation_id() -> None:
    adapter = Adapter(
        BackendConnectionError("temporary"),
        response(200, {"agent_id": "agent-1", "state": "offline"}),
    )
    result = client(adapter).get_agent_status("agent-1")
    assert result.state is BackendAgentState.OFFLINE
    assert [r.headers["X-Correlation-ID"] for r in adapter.requests] == [
        "correlation-1",
        "correlation-1",
    ]


def test_non_idempotent_request_is_not_retried_without_key() -> None:
    backend = client(Adapter(BackendConnectionError("temporary")))
    with pytest.raises(BackendConnectionError):
        backend.register_agent("host-1")


def test_idempotency_key_enables_retry() -> None:
    adapter = Adapter(
        response(503, {}),
        response(201, {"agent_id": "agent-1", "registered_at": "2026-01-01T00:00:00Z"}),
    )
    client(adapter).register_agent("host-1", idempotency_key="operation-1")
    assert [r.headers["Idempotency-Key"] for r in adapter.requests] == [
        "operation-1",
        "operation-1",
    ]


def test_unauthorized_refreshes_token_once() -> None:
    resolver = Resolver("expired", "fresh")
    adapter = Adapter(
        response(401, {}),
        response(200, {"agent_id": "agent-1", "state": "online"}),
    )
    client(adapter, resolver=resolver).get_agent_status("agent-1")
    assert [r.headers["Authorization"] for r in adapter.requests] == [
        "Bearer expired",
        "Bearer fresh",
    ]
    failing = client(
        Adapter(response(401, {}), response(401, {})), resolver=Resolver("a", "b")
    )
    with pytest.raises(BackendAuthenticationError):
        failing.get_agent_status("agent-1")


def test_response_validation_and_http_error_are_explicit() -> None:
    with pytest.raises(BackendResponseValidationError):
        client(Adapter(response(200, {"state": "online"}))).get_agent_status("missing")
    with pytest.raises(BackendHTTPError, match="correlation-1"):
        client(Adapter(response(404, {}))).get_agent_status("missing")


def test_attachments_redact_bound_and_suppress_production() -> None:
    sink = Sink()
    adapter = Adapter(
        response(
            200, {"agent_id": "agent-1", "state": "online", "token": "leak"}
        )
    )
    with pytest.raises(BackendResponseValidationError):
        backend = client(
            adapter, sink=sink, configured=settings(max_attachment_body_bytes=40)
        )
        backend.get_agent_status("agent-1")
    joined = "".join(sink.values)
    assert "synthetic-token" not in joined
    assert "tenant-ref" not in joined
    assert "<redacted>" in joined
    assert "<truncated>" in joined

    prod_sink = Sink()
    prod_adapter = Adapter(response(200, {"agent_id": "agent-1", "state": "online"}))
    prod_backend = client(
        prod_adapter, sink=prod_sink, configured=settings(environment="prod")
    )
    prod_backend.get_agent_status("agent-1")
    prod_text = "".join(prod_sink.values)
    assert "backend.invalid" not in prod_text
    assert "agent-1" not in prod_text
    assert "suppressed production" in prod_text


def test_tls_and_mtls_validation() -> None:
    with pytest.raises(ValidationError, match="certificate validation"):
        settings(environment="prod", tls={"verify_certificate": False})
    with pytest.raises(ValidationError, match="mTLS"):
        TLSConfiguration(
            client_certificate=CredentialsReference(reference="vault:synthetic/cert")
        )
    proxy = ProxyConfiguration(
        url="https://proxy.invalid",
        credentials=CredentialsReference(reference="vault:synthetic/proxy"),
    )
    assert proxy.credentials is not None


def test_fake_client_satisfies_protocol_without_network() -> None:
    fake = FakeBackendClient()
    fake.registrations["host-1"] = RegistrationResult(
        agent_id="agent-1",
        registered_at=datetime(2026, 1, 1, tzinfo=UTC),
        correlation_id="fake-correlation",
    )
    fake.statuses["agent-1"] = BackendAgentStatus(
        agent_id="agent-1", state=BackendAgentState.ONLINE
    )
    fake.policy_assignments[("agent-1", "base")] = PolicyAssignmentResult(
        agent_id="agent-1", policy_id="base", accepted=True, correlation_id="fake"
    )
    fake.feature_flags["tenant-ref"] = FeatureFlagState(flags={}, revision="1")
    fake.packages[("2.1.0", "linux", "arm64")] = PackageMetadata(
        version="2.1.0",
        operating_system="linux",
        architecture="arm64",
        download_url="https://packages.invalid/agent.pkg",
        sha256="a" * 64,
        size_bytes=1,
    )
    typed: BackendClient = fake
    assert typed.register_agent("host-1").agent_id == "agent-1"
    assert typed.get_agent_status("agent-1").state is BackendAgentState.ONLINE
    assert typed.assign_policy("agent-1", "base").accepted
    assert typed.get_feature_flags("tenant-ref").revision == "1"
    assert typed.get_package_metadata("2.1.0", "linux", "arm64").size_bytes == 1
    assert len(fake.calls) == 5
