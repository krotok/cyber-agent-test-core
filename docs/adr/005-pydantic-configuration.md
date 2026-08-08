# ADR-005: Pydantic typed configuration

- Status: Accepted
- Date: 2026-08-06
- Deciders: Core framework maintainers
- Related issues: None

## Context

Configuration crosses YAML, laboratory inventory, environment variables, CLI
arguments, and internal composition. It contains nested policies, enums,
versions, host constraints, and secret references. Failures must be reported
before hosts are leased or product actions begin, while unknown keys and unsafe
production combinations must not be silently accepted.

## Decision

Use Pydantic v2 for internal configuration schemas and boundary parsing. Models
are frozen and reject unknown fields. Pydantic performs structural parsing and
local invariants; a separate validation service checks contextual facts such as
catalog existence, compatibility, capabilities, host capacity, and production
safety.

Configuration merges left-to-right in this fixed priority, where later sources
win: defaults, environment YAML, laboratory inventory, environment variables,
then CLI arguments. Nested mappings merge recursively; sequences and scalar
values replace earlier values.

Secrets are never configuration values. `CredentialsReference` contains only an
opaque external-provider reference, resolved later by an internal secret
provider. Core contains schemas, loaders, merge and validation logic, but no real
hostnames, production URLs, tenant IDs, credentials, or customer names.

The configuration package remains internal and is not added to the product-test
public import allowlist.

## Alternatives considered

- **Dataclasses plus handwritten parsing:** rejected because maintaining strict
  nested coercion, useful path-aware errors, and JSON/YAML boundary validation
  would duplicate mature functionality.
- **TypedDict only:** rejected because it helps static analysis but provides no
  runtime validation for external sources.
- **Pydantic Settings as the sole loader:** rejected because the required five
  source types and precedence must remain explicit and independently testable.
- **Untyped dictionaries throughout:** rejected because errors would surface too
  late and secret-bearing or unknown fields could propagate unnoticed.

## Consequences

Pydantic becomes a runtime dependency and its major version is constrained.
Schema behavior is deterministic, typed, and independently testable. Source
loading and contextual policy remain decoupled from Pydantic, so inventory and
compatibility providers can evolve without embedding I/O in models.

## Compatibility and release impact

This adds an internal subsystem in a minor framework release and does not expand
the public API. If configuration models are later re-exported publicly, their
fields and validation semantics become subject to ADR-004 and Semantic
Versioning.
