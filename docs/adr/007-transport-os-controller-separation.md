# ADR-007: Transport and OS controller separation

- Status: Accepted
- Date: 2026-08-06
- Deciders: Core framework maintainers
- Related issues: None

## Context

Local, SSH, and WinRM connectivity must support Linux, Windows, and macOS
without creating a transport class for every transport/OS combination. Mixing
command construction with connection and file-transfer behavior would invert
dependencies, duplicate lifecycle handling, and make retry classification
unsafe. Product tests must not know either mechanism.

## Decision

`Transport` owns connection lifecycle, opaque command execution, byte transfer,
availability, and normalized transport metadata. It never selects or constructs
OS commands. `LocalTransport` executes argv with `shell=False`; `SSHTransport`
and `WinRMTransport` wrap injected protocol clients; `FakeTransport` is the
deterministic test implementation.

`OperatingSystemController` owns typed OS operations and delegates all I/O to an
injected transport. Linux, Windows, and macOS implementations exclusively own
their command construction and output parsing. `AgentController` sits above OS
controllers and owns product behavior. Flows own business scenarios. Product
tests consume only public fixtures, flows, checks, models, and markers.

`CommandResult` always records exit code, stdout, stderr, duration, host,
redacted command, and transport type. Transport errors have a stable taxonomy.
Automatic retry is permitted only when a caught `TransportError` carries
explicit transport-level retry evidence. Authentication failures, command
timeouts, OS command failures, and product failures are never automatically
retried.

## Alternatives considered

- **OS-specific transports:** rejected because connection mechanics would be
  duplicated for each platform.
- **Transport-owned command strings:** rejected because transports would need OS
  knowledge and violate dependency direction.
- **Controllers opening SSH/WinRM sessions:** rejected because lifecycle,
  transfer, and error normalization would be spread across platform code.
- **Retry every `TransportError`:** rejected because authentication, timeout, and
  remote-side outcomes are not proven transient connectivity failures.

## Consequences

Platform and transport implementations can be combined independently and
tested with fakes. Remote libraries are optional client adapters rather than
core dependencies. OS command coverage belongs to controller contract tests;
transport tests require no real machine. Additional adapter interfaces are
needed for concrete SSH and WinRM libraries.

## Compatibility and release impact

This adds internal implementation boundaries and does not expand the public
product-test API. No framework version change is required. Exposing transport or
controller types publicly would contradict ADR-002 and ADR-004.
