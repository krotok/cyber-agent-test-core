# ADR-009: Safe typed backend clients

- **Status:** Accepted
- **Date:** 2026-08-08

## Context

The core must communicate with multiple control-plane versions without exposing
HTTP details, credentials, tenant data, or unsafe retry behavior to product
tests. Tests also need deterministic backend substitutes.

## Decision

Backend clients are internal typed services implemented over an injected
`HTTPAdapter`. Pydantic response models perform strict validation at the wire
boundary. This extends ADR-005's Pydantic decision: one validation technology is
used for configuration and external response schemas, while domain protocols
remain ordinary typed Python interfaces.

Authentication resolves only opaque `CredentialsReference` values. A 401 may
trigger one token refresh. Requests carry a stable correlation ID, bounded
timeout, explicit TLS/mTLS and proxy settings. Production certificate validation
cannot be disabled.

Automatic retries are bounded and allowed only for GET or an operation carrying
an idempotency key, and only for explicitly retryable connection failures or
502/503/504 responses. A non-idempotent operation without an idempotency key is
sent once. No client retries a valid product/business failure.

Diagnostic attachments pass through one policy that redacts authorization and
secret-shaped fields and caps body size. Production URLs and bodies are denied
by default; attaching them requires explicit configuration. `FakeBackendClient`
implements the semantic protocols without network access.

## Consequences

- OS controllers and transports do not acquire HTTP/control-plane concerns.
- Response drift fails early with a correlation ID and no response-body leak in
  the exception.
- Concrete HTTP libraries are replaceable and unit tests never need a backend.
- Adding operations requires a typed response, an idempotency classification,
  redaction review, and unit tests.

