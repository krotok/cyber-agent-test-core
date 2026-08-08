# ADR-004: Public API stability

- Status: Accepted
- Date: 2026-08-06
- Deciders: Core framework maintainers
- Related issues: None

## Context

Product repositories need to upgrade core independently and safely. Python makes
internal modules technically importable, while fixture names, model fields,
marker semantics, errors, and behavior can break consumers even when import
paths remain unchanged. The supported boundary and release rules must therefore
be explicit.

## Decision

The only product-test import paths are:

- `cyber_agent_test_core.api`;
- `cyber_agent_test_core.models`;
- `cyber_agent_test_core.fixtures`;
- `cyber_agent_test_core.flows`;
- `cyber_agent_test_core.checks`;
- `cyber_agent_test_core.markers`.

The compatibility promise covers documented exports, signatures, public types,
fixture names/scopes, marker semantics, errors, lifecycle/ownership semantics,
and documented side effects. Public signatures contain no private types.

Public changes follow Semantic Versioning. Compatible additions and
deprecations require a minor release; compatible fixes require a patch release;
incompatible removals or semantic changes require an accepted ADR and a major
release. Prefer a documented deprecation and migration period. Every new
function, public or internal, has complete type hints and unit tests. Public
exports and signatures will be checked in CI once implementation begins.

## Alternatives considered

- **Treat every importable symbol as public:** rejected because it freezes the
  implementation and defeats layering.
- **Guarantee only import paths:** rejected because behavioral and fixture/model
  changes also break tests.
- **Use calendar versioning without compatibility rules:** rejected because it
  does not communicate consumer upgrade risk.
- **Allow breaking changes in minor releases with release notes:** rejected
  because distributed product repositories cannot upgrade safely.

## Consequences

Maintainers must document public behavior, classify release impact, maintain
export/signature contract tests, and provide migrations for deprecations.
Internal implementations remain free to evolve when observable public contracts
are preserved. Consumers receive a small, predictable import surface.

## Compatibility and release impact

This defines the initial stability policy. Any exception to the six-module
allowlist or to Semantic Versioning requires a superseding ADR. Every breaking
public change requires an ADR and ships only in a major release.
