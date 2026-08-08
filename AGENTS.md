# Repository Instructions

## Scope

These instructions apply to the entire repository. This repository owns the
reusable test framework for Cybersecurity Agent on Linux, Windows, and macOS.
It must not contain product regression tests.

## Architecture

Preserve this strict dependency direction:

```text
product tests
    -> public core fixtures / flows / checks
    -> controllers
    -> OS adapters
    -> transports
```

Reverse dependencies are prohibited. A lower layer must never import from,
call into, or expose knowledge of a higher layer. Keep OS-specific behavior in
OS adapters and transport mechanics in transports.

## Public boundary

Product tests may import only:

- `cyber_agent_test_core.api`
- `cyber_agent_test_core.models`
- `cyber_agent_test_core.fixtures`
- `cyber_agent_test_core.flows`
- `cyber_agent_test_core.checks`
- `cyber_agent_test_core.markers`

Treat all other modules and implementation details as private. In particular,
never expose transports, OS-specific commands, pytest hooks, retry
implementation, host leasing, distributed locks, or Allure implementation
details to product tests.

## Mandatory engineering rules

- Do not execute shell commands from product tests.
- Do not use `time.sleep`; use framework-owned bounded waiting abstractions.
- Do not store secrets in source, tests, fixtures, logs, snapshots, or example
  configuration.
- Do not retry product failures. Retry only explicitly classified transient
  infrastructure operations inside the framework.
- Do not add OS or OS-version `if`/`elif` branches to product tests.
- Change public API only according to Semantic Versioning.
- Require an accepted ADR and a major release for every breaking public API
  change.
- Add complete type hints and unit tests for every new function.
- Keep product-facing errors and models free of private implementation types.
- Update relevant documentation in the same change as a contract or API change.

## Changes and verification

Prefer the smallest change that preserves the public contract. Add tests at the
lowest useful layer. Before completing a change, run the relevant formatting,
static typing, unit, and architecture-boundary checks once those tools exist.
Do not add implementation merely to make documentation examples executable.
