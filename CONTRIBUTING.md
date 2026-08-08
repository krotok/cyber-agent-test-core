# Contributing

## Repository purpose

This repository contains reusable framework code and contracts for testing
Cybersecurity Agent across Linux, Windows, and macOS. Product-specific
regression scenarios must live in product test repositories.

## Before making a change

1. Identify the layer that owns the behavior.
2. Confirm that the change preserves the dependency direction documented in
   [architecture.md](docs/architecture.md).
3. Decide whether the change affects the public API allowlist documented in
   [public-api.md](docs/public-api.md).
4. For a breaking public API change, write and obtain acceptance of an ADR
   before implementation, and plan a major release.

## Required design boundaries

Dependencies may flow only as follows:

```text
product tests
    -> public core fixtures / flows / checks
    -> controllers
    -> OS adapters
    -> transports
```

Reverse dependencies are forbidden. Product tests may use only the six public
modules listed in [public-api.md](docs/public-api.md). Do not leak private types
or details through public signatures, exceptions, logs, or documentation.

The following are internal implementation details:

- transports;
- OS-specific commands;
- pytest hooks;
- retry implementation;
- host leasing implementation;
- distributed locks;
- Allure implementation details.

## Product test requirements

Product tests must follow the [thin tests contract](docs/thin-tests-contract.md).
In particular, they must not:

- execute shell commands directly;
- call `time.sleep`;
- store or embed secrets;
- retry product failures;
- branch on OS or OS version with `if`/`elif`;
- import private framework modules.

If a test needs any of these mechanisms, add or improve an OS-neutral public
framework capability instead of implementing the mechanism in the product test.

## Code requirements

- Every new function must have complete type hints and unit tests.
- Public models and results should be typed, stable, and OS-neutral.
- Waiting must be bounded and expressed through framework abstractions.
- Infrastructure retries must be bounded, observable, and limited to failures
  explicitly classified as transient. Assertions and product behavior are never
  retried.
- Secrets must be supplied through an approved runtime secret provider and
  redacted from diagnostics.
- Add an adapter capability rather than branching by platform in a caller.

## Public API and releases

Public API changes follow [Semantic Versioning](https://semver.org/):

- Patch: backward-compatible fixes without new public contract requirements.
- Minor: backward-compatible public capabilities or deprecations.
- Major: removals or incompatible behavior, signature, model, fixture, marker,
  or semantic changes.

Breaking changes require both an accepted ADR and a major release. Prefer a
deprecation period when practical. Update API documentation, migration notes,
and tests in the same change.

## Architecture decision records

Use [the ADR template](docs/adr/0000-template.md) for decisions that alter public
contracts, dependency boundaries, platform strategy, execution semantics, or
cross-cutting infrastructure. Number ADRs sequentially; do not rewrite accepted
records. Supersede them with a new ADR.

## Pull request checklist

- The change belongs in reusable core rather than a product regression suite.
- Dependency direction and the public import boundary are preserved.
- Every new function has type hints and unit tests.
- No secrets, direct sleeps, product-failure retries, or product-test shell
  commands were added.
- Platform differences are encapsulated in adapters.
- Public API impact and SemVer release impact are documented.
- A breaking change includes an accepted ADR and targets a major release.
- Relevant documentation is updated.
