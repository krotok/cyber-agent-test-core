# Core Framework Architecture

## 1. Scope and quality attributes

Cyber Agent Test Core is a reusable Python framework consumed by product test
repositories. It supports:

- Linux, Windows, and macOS on x86_64 and ARM64;
- multiple Agent and backend versions plus feature flags;
- dev, stage, preprod, and prod environments;
- multiple laboratories with different inventory providers;
- local and remote execution;
- pytest-xdist workers and distributed CI jobs;
- install, uninstall, upgrade, downgrade, rollback, and reboot scenarios;
- online, offline, proxy, and restricted network modes;
- exclusive and shared hosts;
- diagnostics and Allure reporting without exposing reporting internals.

Product regression tests are not part of this repository. The architecture
optimizes for stable product-facing contracts, deterministic parallel execution,
explicit compatibility decisions, safe host ownership, and actionable failure
evidence.

## 2. Governing dependency rule

The conceptual dependency direction remains:

```text
product tests
    -> public core fixtures / flows / checks
    -> controllers
    -> OS adapters
    -> transports
```

The detailed architecture applies dependency inversion: high-level code depends
on typed models and capability protocols, never on concrete infrastructure.
Concrete implementations are selected and injected by an internal composition
root owned by fixtures and distributed execution.

```text
product tests
        |
        v
public API / fixtures / flows / checks / markers
        |
        v
typed models + capability protocols + compatibility policy
        |
        v
Agent lifecycle + OS controller protocols + backend client protocols
        |
        v
OS controller implementations + backend clients
        |
        v
transport protocols and implementations

composition inputs: configuration -> inventory -> host leasing
cross-cutting sinks: logging -> diagnostics -> reporting
coordination: distributed execution -> leases, locks, worker identity
```

An arrow means "may use." Reverse dependencies are forbidden. Implementations
may implement a protocol owned by a higher policy layer, but the protocol must
not import the implementation. Imports used only for typing are still
dependencies and follow the same rules.

## 3. Public boundary

Product tests may import only:

- `cyber_agent_test_core.api`
- `cyber_agent_test_core.models`
- `cyber_agent_test_core.fixtures`
- `cyber_agent_test_core.flows`
- `cyber_agent_test_core.checks`
- `cyber_agent_test_core.markers`

All other modules are internal. Public signatures contain only standard-library
types and public typed models/protocols. They never expose transports, commands,
pytest hooks, retry machinery, leases, distributed locks, backend wire models,
or Allure objects.

## 4. Runtime context and selection

A test requirement is expressed as typed constraints, not imperative branching:

- platform: OS family, OS version, architecture;
- product: current and target Agent versions;
- service: backend version and environment;
- behavior: required feature flags and capabilities;
- placement: laboratory, labels, exclusivity, and sharing policy;
- connectivity: online, offline, proxy, or restricted;
- execution: local/remote, CI job identity, and xdist worker identity.

Configuration parses trusted inputs. Inventory describes available hosts.
Compatibility evaluates whether a candidate satisfies a requirement. Leasing
atomically reserves a compatible host. Fixtures compose the resulting scoped
objects and expose only public views. Unsupported combinations are explicit
skip/unsupported decisions with reasons; they are not discovered through
OS/version `if`/`elif` in product tests.

## 5. Layer contracts

"Allowed dependencies" below are an allowlist of direct framework imports.
Standard-library dependencies are allowed where appropriate. Every new function
in every layer requires complete type hints and unit tests.

### 5.1 Public API

- **Responsibility:** Provide cohesive OS-neutral entry points, public errors,
  supported markers, and stable facades. Define product-facing lifecycle and
  ownership semantics without revealing implementation objects.
- **Status:** Public through `api` and `markers` only.
- **Allowed dependencies:** typed models; public flows and checks; capability
  protocols needed in public type signatures.
- **Forbidden dependencies:** concrete configuration loaders, inventory, leasing,
  transports, OS implementations, backend wire clients, pytest hooks, Allure,
  locks, retry implementation, and concrete logging/diagnostics backends.
- **Unit-test strategy:** API contract and export snapshots, signature/type tests,
  delegation tests with protocol fakes, stable exception tests, and tests proving
  private types do not escape.

### 5.2 Typed models

- **Responsibility:** Represent OS/architecture, versions, environments,
  laboratories, feature flags, network modes, host requirements, lifecycle
  requests/results, evidence, and public errors. Models are immutable where
  practical and validate invariants at construction.
- **Status:** Public models live in `models`; private wire/storage models remain
  internal and must be explicitly translated.
- **Allowed dependencies:** standard library and deliberately selected typing or
  validation primitives that are part of the compatibility promise.
- **Forbidden dependencies:** every operational layer, pytest, Allure, transport
  results, shell command objects, lease-provider records, and backend payloads.
- **Unit-test strategy:** construction and validation tables, equality/hash and
  serialization contracts where promised, redaction tests, version boundary
  cases, and static typing checks.

### 5.3 Configuration

- **Responsibility:** Load and validate layered runtime settings for environments,
  labs, inventory providers, backend endpoints, transports, network policy,
  timeouts, and secret references. Precedence is explicit: defaults < repository
  config < environment/lab config < CI/runtime overrides. Secret values are
  resolved only at runtime and never rendered.
- **Status:** Internal; public fixtures may expose a sanitized typed view.
- **Allowed dependencies:** typed models, capability protocols, logging redaction,
  and secret-provider protocols.
- **Forbidden dependencies:** product tests, flows, checks, Agent lifecycle, OS
  controllers, concrete transports, pytest hooks, Allure, and mutable global
  configuration.
- **Unit-test strategy:** precedence matrices, schema and invalid-input tests,
  secret-reference/redaction tests, environment isolation, and deterministic
  config snapshots containing no secrets.

Configuration uses Pydantic v2 as decided by
[ADR-005](adr/005-pydantic-configuration.md). Source priority is fixed, from
lowest to highest: defaults, environment YAML, laboratory inventory,
environment variables, and CLI arguments. Unknown fields are rejected. Runtime
validation completes before host leasing or transport construction.

### 5.4 Capabilities

- **Responsibility:** Define small typed protocols and capability identifiers for
  host operations, lifecycle actions, backend operations, waits, reboot, network
  control, diagnostics, clock/randomness, and infrastructure retry classification.
  Capabilities express what can be done, not how.
- **Status:** Internal contracts; selected OS-neutral protocols may be re-exported
  by `api` and thereby become public.
- **Allowed dependencies:** typed models only.
- **Forbidden dependencies:** all concrete implementations, pytest, Allure,
  product tests, configuration parsing, and service locators.
- **Unit-test strategy:** protocol conformance/static typing fixtures, contract
  suites reusable by implementations, capability-name uniqueness, and tests that
  contracts contain no implementation types.

Capability support is resolved centrally as defined by
[ADR-006](adr/006-centralized-capability-resolution.md). Raw OS, version,
feature-flag, license, architecture, and environment checks outside the resolver
are prohibited. Compatibility policy is declarative YAML/JSON data supplied by
the consuming deployment, not hard-coded product data in core.

### 5.5 Compatibility

- **Responsibility:** Make pure, explainable decisions across OS/architecture,
  Agent/backend versions, environments, feature flags, network modes, and
  lifecycle transition paths. Produce supported/unsupported decisions and
  reasons, never hidden fallback.
- **Status:** Internal policy surfaced through public decisions/models.
- **Allowed dependencies:** typed models and capability identifiers.
- **Forbidden dependencies:** inventory access, leasing, transports, controllers,
  backend I/O, pytest, reporting, and environment-variable reads.
- **Unit-test strategy:** decision tables and pairwise/boundary matrices, semantic
  version edge cases, feature-flag precedence, transition graph tests, and
  property tests for deterministic/explainable outcomes.

### 5.6 Inventory

- **Responsibility:** Discover and normalize hosts from different laboratories;
  report platform, architecture, reachability, network modes, sharing support,
  mutable state, and labels without reserving them.
- **Status:** Internal.
- **Allowed dependencies:** configuration, typed models, capability protocols,
  logging, and provider SDK adapters behind inventory-owned interfaces.
- **Forbidden dependencies:** product tests, public flows/checks, fixtures,
  leasing policy, Agent lifecycle, OS controllers, Allure, and assumptions about
  a single laboratory.
- **Unit-test strategy:** provider contract tests with recorded/fake responses,
  normalization and stale-data tests, malformed-record isolation, architecture
  and network-mode mapping tables, and no-live-lab unit tests.

Inventory and leasing follow
[ADR-008](adr/008-distributed-host-leasing.md). Inventory state is descriptive;
it is never the ownership authority. Host records contain opaque credential
references only and no real credentials or connection secrets.

### 5.7 Host leasing

- **Responsibility:** Atomically acquire, renew, and release compatible hosts;
  enforce exclusive/shared modes, TTLs, ownership tokens, fencing, and cleanup
  across xdist workers and distributed CI jobs. Shared leases require declared,
  non-conflicting resource scopes.
- **Status:** Internal; product tests receive only a public host capability.
- **Allowed dependencies:** typed models, capabilities, compatibility, inventory
  interfaces, configuration, distributed lock/coordination protocols, logging,
  and diagnostics.
- **Forbidden dependencies:** product tests, flows/checks, pytest node internals,
  OS command implementations, Agent lifecycle policy, concrete Allure APIs, and
  leases represented as process-local locks only.
- **Unit-test strategy:** state-machine and concurrency tests, TTL/renewal with a
  fake clock, fencing and stale-owner tests, shared-scope conflict matrices,
  idempotent release, crash recovery, and provider contract tests.

Every exclusive host or declared shared-capacity slot is protected by a stable
distributed lock key with TTL, heartbeat, and fencing token. File and Redis
providers coordinate outside the pytest worker process; in-memory locks alone
are prohibited. Preparation and cleanup uncertainty quarantine the host.

### 5.8 Transports

- **Responsibility:** Provide local and remote process execution, file transfer,
  connectivity checks, and session recovery primitives. Preserve stdout/stderr,
  exit status, timing, and transport classification. They do not encode OS or
  product behavior.
- **Status:** Internal.
- **Allowed dependencies:** private transport models, minimal typed host identity,
  configuration, capability protocols, logging, diagnostics, and narrowly scoped
  transient-infrastructure retry policy.
- **Forbidden dependencies:** product tests, public API, flows/checks, Agent
  lifecycle, OS commands/policy, compatibility selection, leasing policy,
  backend domain clients, pytest, and Allure.
- **Unit-test strategy:** implementation contract suites, quoting/encoding and
  timeout tests, partial-output and cancellation tests, transient error
  classification, local/remote parity, and fake-server tests without real hosts.

As specified by [ADR-007](adr/007-transport-os-controller-separation.md), a
transport accepts an opaque controller-built command and returns normalized
metadata. It does not construct, select, or interpret OS commands. Retry is
limited to failures carrying explicit transport-level retry evidence.

### 5.9 OS controllers

- **Responsibility:** Implement OS-specific process, filesystem, package,
  service, certificate, network, proxy, reboot, and boot-readiness operations for
  Linux, Windows, and macOS on x86_64/ARM64. Version-specific commands and path
  conventions live here.
- **Status:** Internal.
- **Allowed dependencies:** typed models, capability protocols, compatibility
  decisions, transports, logging, and diagnostics.
- **Forbidden dependencies:** product tests, fixtures, public flows/checks, Agent
  business lifecycle policy, backend clients, leasing, pytest, and Allure.
- **Unit-test strategy:** one shared controller contract suite plus per-OS command
  rendering tests, mocked transport transcripts, architecture/version matrices,
  reboot disconnect/reconnect state tests, and negative/error normalization.

OS controllers own command construction and parsing but never connection or
file-transfer mechanics. Agent controllers own product behavior, flows own
business scenarios, and product tests know none of these implementation layers.

### 5.10 Agent lifecycle

- **Responsibility:** Orchestrate install, uninstall, upgrade, downgrade,
  rollback, recovery, and post-reboot validation as explicit state machines with
  preconditions, checkpoints, bounded waits, and compensating cleanup. Package
  acquisition respects the selected network mode.
- **Status:** Internal orchestration exposed only through public API/flows.
- **Allowed dependencies:** typed models, capabilities, compatibility, OS
  controller protocols, backend client protocols, diagnostics, and logging.
- **Forbidden dependencies:** concrete transports, OS-specific commands,
  inventory/leasing implementations, fixtures, pytest, Allure, `time.sleep`, and
  retries of product failures.
- **Unit-test strategy:** transition/state-machine tables for every lifecycle
  action, fake controllers/clients/clock, failure injection at each checkpoint,
  idempotency and rollback tests, offline/proxy/restricted matrices, and reboot
  continuation tests.

### 5.11 Backend clients

- **Responsibility:** Provide typed domain operations against supported backend
  versions/environments, including authentication, Agent enrollment/state,
  feature-flag lookup, and eventual-consistency observation. Translate versioned
  wire schemas into stable internal domain models.
- **Status:** Internal; credentials and wire models never escape.
- **Allowed dependencies:** configuration, typed models, capability protocols,
  compatibility, logging/redaction, diagnostics, and low-level HTTP/RPC adapters
  owned by this layer.
- **Forbidden dependencies:** product tests, fixtures, flows/checks, host leasing,
  OS controllers, transports for host shell execution, Allure, and product-level
  assertion retries.
- **Unit-test strategy:** fake-server/contract tests per supported backend schema,
  request and response mapping, auth redaction, pagination, timeout/error
  taxonomy, feature flags, and version negotiation boundaries.

### 5.12 Flows

- **Responsibility:** Offer reusable product-level workflows that compose public
  capabilities, such as preparing a host or performing a lifecycle scenario.
  Flows return typed outcomes and evidence and contain no assertions unless the
  flow contract explicitly defines one.
- **Status:** Public through `flows`.
- **Allowed dependencies:** typed models, public API/capability protocols, Agent
  lifecycle protocols, checks where composition is explicitly documented,
  diagnostics interfaces, and logging facade.
- **Forbidden dependencies:** concrete transports/controllers/backend clients,
  configuration loaders, inventory/leasing, pytest hooks, Allure, shell commands,
  `time.sleep`, OS/version branches, and product-failure retry.
- **Unit-test strategy:** behavior tests with protocol fakes, scenario tables for
  all lifecycle/network modes, bounded-wait and failure propagation tests,
  evidence tests, and OS-independent test bodies.

### 5.13 Checks

- **Responsibility:** Observe and assert stable product outcomes with bounded,
  condition-based waits and useful evidence. Distinguish product failure,
  unsupported capability, and infrastructure failure.
- **Status:** Public through `checks`.
- **Allowed dependencies:** typed models, public capability protocols,
  diagnostics interfaces, and logging facade.
- **Forbidden dependencies:** concrete transports/controllers/backend clients,
  configuration, inventory/leasing, fixtures, pytest hooks, Allure, shell
  commands, `time.sleep`, and retry of assertions/product failures.
- **Unit-test strategy:** fake-clock polling tests, deadline boundaries, outcome
  taxonomy, stable assertion messages, evidence/redaction, and proof that each
  observation is side-effect free unless explicitly documented.

### 5.14 Fixtures

- **Responsibility:** Act as the pytest composition root: parse markers, resolve
  runtime context, acquire/renew/release hosts, construct scoped capabilities,
  handle reboot continuity, attach cleanup/diagnostics, and expose only public
  typed fixtures. Scope and ownership must be xdist-safe.
- **Status:** Fixture names and returned public types are public through
  `fixtures`; hooks and composition implementation are internal.
- **Allowed dependencies:** public API/models/markers, configuration,
  capabilities, compatibility, inventory, leasing, transports, controllers,
  Agent lifecycle, backend clients, reporting, diagnostics, logging, and
  distributed execution.
- **Forbidden dependencies:** product test modules, product-specific scenarios,
  private objects in returned values, worker-local coordination assumptions, and
  direct Allure objects in fixture contracts.
- **Unit-test strategy:** pytester tests for scope/finalization/markers, dependency
  override tests, xdist worker identity simulation, acquisition-failure cleanup,
  reboot handoff, public return-type checks, and no-secret output capture.

### 5.15 Reporting

- **Responsibility:** Convert structured events, steps, results, and diagnostic
  artifacts into reporter output. Allure is an adapter behind a reporting
  protocol; absent Allure must not change test behavior.
- **Status:** Internal; Allure implementation details are strictly private.
- **Allowed dependencies:** typed models, reporting capability protocols,
  diagnostics artifacts, logging/event records, and optional Allure SDK adapter.
- **Forbidden dependencies:** product tests, lifecycle decisions, host control,
  transports, inventory/leasing, compatibility decisions, and reporter objects
  in public signatures.
- **Unit-test strategy:** event-to-report mapping, fake reporter tests, attachment
  naming/MIME/size policy, redaction, disabled-reporter behavior, and Allure SDK
  adapter contract tests.

### 5.16 Diagnostics

- **Responsibility:** Collect bounded, structured failure evidence from
  registered providers; correlate test/job/worker/lease/host operations; redact
  secrets; and retain evidence across reboot or connection loss. Collection is
  best-effort and must not replace the primary failure.
- **Status:** Internal; public checks may return sanitized evidence models.
- **Allowed dependencies:** typed models, diagnostic capability protocols,
  logging event interfaces, storage/artifact interfaces, and injected providers.
- **Forbidden dependencies:** product-test imports, Allure SDK, lifecycle policy,
  inventory/leasing decisions, hard-coded OS commands, and throwing away the
  original exception.
- **Unit-test strategy:** provider aggregation, deterministic budgets, provider
  failure isolation, redaction/property tests, correlation propagation, reboot
  persistence, and primary-error preservation.

### 5.17 Logging

- **Responsibility:** Emit structured, correlated, redacted events with test,
  CI-job, xdist-worker, lease, host, and operation identifiers. Logging is an
  observation sink and never controls behavior.
- **Status:** Internal facade and implementation.
- **Allowed dependencies:** minimal typed correlation models, redaction utility,
  and standard logging/event sinks.
- **Forbidden dependencies:** all orchestration and policy layers, product tests,
  pytest/Allure objects in the core event schema, and secret-bearing object
  stringification.
- **Unit-test strategy:** structured schema and correlation tests, nested-context
  isolation, concurrent worker tests, redaction fuzz/property tests, and tests
  that sink failure cannot alter product outcomes.

### 5.18 Distributed execution

- **Responsibility:** Provide globally unique run/job/worker identity,
  distributed locks, heartbeats, barriers where unavoidable, idempotency keys,
  and recovery semantics across CI jobs and pytest-xdist workers. It coordinates
  resources; it does not schedule or interpret product tests.
- **Status:** Internal; distributed locks are never exposed publicly.
- **Allowed dependencies:** configuration, typed identity/resource models,
  capability protocols, logging, diagnostics, and injected coordination-store
  adapters. Host leasing may consume its protocols; fixtures compose them.
- **Forbidden dependencies:** product tests, public flows/checks, OS controllers,
  Agent lifecycle, backend domain clients, pytest test semantics, Allure, and
  correctness based solely on process-local state.
- **Unit-test strategy:** deterministic multi-worker simulations, lock/fencing
  state machines, partition/timeout/crash recovery, idempotency, fairness where
  promised, xdist identity mapping, and coordination-store contract tests.

## 6. End-to-end execution lifecycle

1. Configuration creates a sanitized run context and provider settings.
2. Distributed execution assigns run, CI-job, and xdist-worker identities.
3. Markers and fixture parameters become a typed host/test requirement.
4. Inventory returns normalized candidates from the selected laboratory.
5. Compatibility filters candidates and explains unsupported combinations.
6. Host leasing atomically acquires an exclusive host or compatible shared scope.
7. Fixtures inject transports, controllers, backend clients, lifecycle services,
   diagnostics, and reporting behind public capability facades.
8. Product tests call public flows/checks. Lifecycle operations may cross reboot;
   the lease and operation checkpoint survive transport loss.
9. Structured events and sanitized diagnostics feed reporting; Allure renders
   them if enabled.
10. Finalizers collect bounded evidence, clean state according to policy, release
    the lease with its fencing token, and close clients.

## 7. Failure and retry taxonomy

- **Product failure:** An observed product outcome violates the contract. Never
  retried by the framework.
- **Unsupported combination:** Compatibility cannot satisfy typed requirements.
  Reported as an explicit unsupported/skip decision with reasons.
- **Infrastructure failure:** A lab, transport, coordination store, or backend is
  unavailable. Only operations explicitly classified as transient may receive a
  bounded, observable internal retry.
- **Framework defect:** An invariant or translation fails. Reported distinctly
  with sanitized diagnostics.

No layer uses `time.sleep`. Waiting uses injected clocks, monotonic deadlines,
condition probes, cancellation, and bounded backoff. Secrets are runtime-only,
redacted at source, and never stored in reports or logs.

## 8. Architecture enforcement when implementation begins

CI must eventually enforce:

- forbidden import and package dependency rules;
- the six-module public import allowlist and export snapshots;
- absence of private types in public annotations and exceptions;
- complete type hints and unit tests for every new function;
- no shell execution, `time.sleep`, OS/version branching, or retry helpers in
  product-test contract examples;
- controller contract suites on every OS/architecture implementation;
- deterministic tests for leasing and distributed coordination;
- secret scanning and redaction tests;
- documentation and SemVer review for public changes.

## 9. Related decisions

- [ADR-001: Core framework architecture](adr/001-core-framework-architecture.md)
- [ADR-002: Separation of core and product tests](adr/002-separation-of-core-and-product-tests.md)
- [ADR-003: Dependency direction](adr/003-dependency-direction.md)
- [ADR-004: Public API stability](adr/004-public-api-stability.md)
