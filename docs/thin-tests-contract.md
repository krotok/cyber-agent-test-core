# Thin Tests Contract

## Purpose

A product test states product intent and verifies an observable outcome. The
framework owns the mechanics required to create that outcome across Linux,
Windows, and macOS. Thin tests remain readable, deterministic, portable, and
independent of infrastructure implementation.

Product regression tests live outside this repository but must follow this
contract when consuming Cyber Agent Test Core.

## A conforming product test

A thin test:

1. Declares requirements through supported markers and fixtures.
2. Arranges state through public fixtures or flows.
3. Performs a product-level action through a public API or flow.
4. Verifies the outcome through public checks and OS-neutral models.
5. Leaves cleanup and diagnostics to lifecycle-managed framework capabilities.

It imports only `cyber_agent_test_core.api`, `.models`, `.fixtures`, `.flows`,
`.checks`, and `.markers`.

## Prohibited behavior

Product tests must not:

- execute shell commands directly, locally or remotely;
- call `time.sleep` or implement polling loops;
- contain secrets in code, parameters, fixtures, files, snapshots, or logs;
- retry assertions, scenarios, or other product failures;
- use OS or OS-version `if`/`elif` branches;
- import controllers, adapters, transports, pytest hooks, retry helpers, leasing,
  distributed locks, or Allure helpers;
- construct OS-specific commands, paths, service names, or process-control logic;
- depend on the concrete host-allocation or reporting mechanism.

## Required alternatives

| Product test need | Framework-owned solution |
| --- | --- |
| Run a host operation | Add/use an OS-neutral public flow or API capability. |
| Wait for state | Add/use a bounded condition-based public check or flow. |
| Handle platform differences | Add/use an OS adapter capability or declarative marker. |
| Supply credentials | Use the approved runtime secret provider and redacted models. |
| Recover transient connectivity | Let a framework-owned infrastructure policy handle it. |
| Attach diagnostics | Return stable evidence; let reporting integration render it. |
| Coordinate hosts | Use framework-owned leasing and distributed locking indirectly. |

An unavailable capability is a framework gap, not permission to put mechanics
in a product test.

## Retry and failure semantics

Product behavior is evaluated once per test attempt. A failed assertion, wrong
agent state, timeout waiting for expected product behavior, or reproducible
product error must be reported as a failure and must not be hidden by retry.

The framework may retry only a narrowly classified transient infrastructure
operation. Such retry must be bounded and observable, and must preserve useful
diagnostics. Retry policy and implementation remain private.

## Cross-platform semantics

The same test body should run on every supported platform for which its declared
capability is available. Product tests express capability requirements through
public fixtures, models, or markers. Adapters resolve OS and version differences.
A test must not inspect the OS to choose commands or expectations.

## Review checklist

- The test reads as arrange, product action, and product outcome.
- All framework imports come from the six allowed public modules.
- There are no shell calls, sleeps, custom polling, or retry wrappers.
- There are no secrets or unredacted sensitive values.
- There is no OS/version conditional logic.
- Assertions describe product behavior rather than transport or command output.
- Required setup and cleanup are lifecycle-managed by public fixtures or flows.
