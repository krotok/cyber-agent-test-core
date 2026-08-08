# ADR-001: Core framework architecture

- Status: Accepted
- Date: 2026-08-06
- Deciders: Core framework maintainers
- Related issues: None

## Context

The framework must support three operating-system families, x86_64 and ARM64,
multiple Agent/backend versions, feature flags, four deployment environments,
multiple laboratories, local and remote execution, xdist and distributed CI,
multiple network modes, disruptive lifecycle operations, reboot, and safe
exclusive/shared host usage. A monolithic test helper would mix policy,
platform commands, resource ownership, and reporting, making concurrent and
cross-platform behavior unsafe and the public API unstable.

## Decision

Adopt the layers and contracts defined in `docs/architecture.md`: public API,
typed models, configuration, capabilities, compatibility, inventory, host
leasing, transports, OS controllers, Agent lifecycle, backend clients, flows,
checks, fixtures, reporting, diagnostics, logging, and distributed execution.

High-level orchestration depends on typed protocols. Concrete transports,
controllers, clients, inventory providers, lease stores, coordination stores,
and reporters are injected at the fixture-owned composition root. Compatibility
is pure policy. Lifecycle operations are explicit state machines. Host leasing
uses TTLs and fencing and models exclusive/shared ownership. Reporting consumes
structured events; Allure is only an adapter.

No framework implementation is introduced by this ADR.

## Alternatives considered

- **One helper layer called directly by tests:** rejected because it exposes
  infrastructure and encourages OS/version branching.
- **Inheritance hierarchy per OS:** rejected because it couples unrelated
  capabilities and scales poorly across architecture/version/network dimensions.
- **Plugin/service locator available to tests:** rejected because runtime lookup
  hides dependencies and leaks private implementations.
- **Separate framework per laboratory:** rejected because it duplicates product
  semantics and prevents consistent compatibility and leasing behavior.

## Consequences

The design has more explicit interfaces and composition work. In return, policy
can be unit-tested without hosts, implementations have reusable contract suites,
new labs/transports/reporters can be added internally, and product tests remain
portable. Distributed coordination, fencing, checkpointed reboot operations,
and strict model translation are required implementation concerns.

## Compatibility and release impact

This is the initial architectural contract and does not change implemented API.
Future changes to public layer semantics follow ADR-004. Changes to these
boundaries require a new ADR; breaking public effects require a major release.
