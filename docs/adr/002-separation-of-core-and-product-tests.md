# ADR-002: Separation of core and product tests

- Status: Accepted
- Date: 2026-08-06
- Deciders: Core framework maintainers
- Related issues: None

## Context

Reusable infrastructure and product regression scenarios evolve for different
reasons. Combining them would couple framework releases to product expectations,
encourage direct access to internal host mechanisms, and make reuse across Agent
versions, environments, and laboratories difficult.

## Decision

Cyber Agent Test Core contains reusable OS-neutral fixtures, flows, checks,
models, capability contracts, platform implementations, and execution
infrastructure. Product regression tests live in separate product repositories.

Product tests may import only `cyber_agent_test_core.api`, `.models`,
`.fixtures`, `.flows`, `.checks`, and `.markers`, and must follow
`docs/thin-tests-contract.md`. They must not execute shell commands, sleep,
store secrets, retry product failures, branch on OS/version, or depend on
leasing, locks, transports, hooks, retries, or Allure internals.

A missing reusable capability is addressed in core through an OS-neutral public
contract; it is not worked around with product-test infrastructure code.

## Alternatives considered

- **Keep regression tests in core:** rejected because product policy would become
  part of reusable framework ownership and release cadence.
- **Allow tests to import internals when needed:** rejected because technical
  reachability is not a stable contract and prevents internal evolution.
- **Share copied helpers between product repositories:** rejected because copies
  drift and bypass common leasing, diagnostics, and security rules.

## Consequences

Core and product suites can version and release independently. Product tests are
smaller and portable, while core bears responsibility for reusable mechanics and
public documentation. Cross-repository compatibility must be managed through
declared package versions, deprecations, and contract tests.

## Compatibility and release impact

This establishes the repository boundary and initial consumer contract. Moving
an established public capability out of core, or requiring product tests to use
a private mechanism, is breaking and requires an ADR plus a major release.
