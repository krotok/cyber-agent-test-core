# Architecture Decision Records

This directory records durable architectural decisions for Cyber Agent Test
Core. An ADR is required for every breaking public API change and for material
changes to dependency boundaries, platform strategy, execution semantics, or
cross-cutting infrastructure.

## Index

- [ADR-001: Core framework architecture](001-core-framework-architecture.md)
- [ADR-002: Separation of core and product tests](002-separation-of-core-and-product-tests.md)
- [ADR-003: Dependency direction](003-dependency-direction.md)
- [ADR-004: Public API stability](004-public-api-stability.md)
- [ADR-005: Pydantic typed configuration](005-pydantic-configuration.md)
- [ADR-006: Centralized capability resolution](006-centralized-capability-resolution.md)
- [ADR-007: Transport and OS controller separation](007-transport-os-controller-separation.md)
- [ADR-008: Distributed laboratory host leasing](008-distributed-host-leasing.md)

Copy [000-template.md](000-template.md), assign the next three-digit sequence
number, and use a short kebab-case title. Once accepted, an ADR is immutable
except for corrections that do not alter the decision. Replace a decision by
adding a new ADR and marking the old record `Superseded by ADR-NNN`.
