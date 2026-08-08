# ADR-003: Dependency direction

- Status: Accepted
- Date: 2026-08-06
- Deciders: Core framework maintainers
- Related issues: None

## Context

Cross-platform and distributed concerns can easily create cycles: flows call OS
helpers, transports learn product behavior, reporters affect execution, or
leasing depends on pytest workers. Such cycles make isolated unit tests and safe
replacement of infrastructure impossible.

## Decision

Dependencies flow from product intent toward mechanisms:

```text
product tests
    -> public core fixtures / flows / checks
    -> controllers
    -> OS adapters
    -> transports
```

In the detailed design, high-level layers import typed models and capability
protocols. Concrete implementations are injected at the internal composition
root. Lower-level implementations never import their callers. Cross-cutting
logging, diagnostics, and reporting are event sinks, not control dependencies.
Compatibility remains pure; inventory does not lease; transports do not encode
OS or Agent behavior; distributed execution coordinates resources but does not
interpret tests.

The direct dependency allowlist and forbidden dependencies for every layer are
normative in `docs/architecture.md`. Type-only imports and test utilities must
also respect the direction. CI architecture tests will enforce these rules once
implementation begins.

## Alternatives considered

- **Permit cycles behind private modules:** rejected because private cycles still
  prevent isolated evolution and testing.
- **Put all abstractions in implementations:** rejected because high-level policy
  would then depend on infrastructure packages.
- **Global service locator:** rejected because it hides dependencies, complicates
  typing, and creates process-global interference under xdist.

## Consequences

Interfaces and translation boundaries must be explicit, and composition is more
deliberate. This enables pure compatibility tests, fake-driven orchestration
tests, reusable implementation contract suites, and substitution of labs,
transports, coordination stores, and reporters without changing product tests.

## Compatibility and release impact

This decision does not change an implemented public API. A future boundary
change that alters public behavior or types follows ADR-004; a breaking effect
requires a new ADR and major release.
