# Public API Contract

Fixture lifecycle scopes, cleanup ordering, and safety flags are specified in
[pytest-lifecycle.md](pytest-lifecycle.md).

## Supported import surface

Product tests may import only these modules:

```python
cyber_agent_test_core.api
cyber_agent_test_core.models
cyber_agent_test_core.fixtures
cyber_agent_test_core.flows
cyber_agent_test_core.checks
cyber_agent_test_core.markers
```

This list is an allowlist. Submodules, symbols re-exported from undocumented
locations, and other package paths are private unless this document explicitly
adds them to the public contract.

## Module responsibilities

| Module | Stable responsibility |
| --- | --- |
| `api` | Cohesive, OS-neutral framework entry points and capability protocols. |
| `models` | Typed public inputs, results, states, capabilities, and product-facing errors. |
| `fixtures` | Supported pytest fixtures and their documented lifecycle. |
| `flows` | Reusable product-level actions and scenario building blocks. |
| `checks` | Reusable observations, assertions, and diagnostic results. |
| `markers` | Supported declarative test metadata and selection semantics. |

No implementation is defined by this document; concrete symbols will be added
only when implemented and documented.

### Beginner-friendly flows and checks

The public `models` module exports OS-neutral Agent handles and typed lifecycle,
registration, health, threat, isolation, log-upload, event, process, and service
observations. `api.AgentOperations` is the environment integration port; product
tests consume its behavior only through fixtures and flows.

The public `flows` module exports `AgentInstallationFlow`,
`AgentRegistrationFlow`, `AgentHealthFlow`, `AgentUpgradeFlow`,
`AgentDowngradeFlow`, `AgentRollbackFlow`, `AgentUninstallFlow`,
`ThreatDetectionFlow`, `NetworkIsolationFlow`, and `LogUploadFlow`.

The public `checks` module exports `AgentChecks`, `BackendChecks`,
`ProcessChecks`, `ServiceChecks`, `EventChecks`, `LogChecks`, and
`VersionChecks`. Assertion messages describe the product outcome and include
sanitized observations; they never expose commands or transport objects.

The pytest plugin registers flow/check fixtures plus `installed_agent` and
`healthy_agent`. A laboratory integration supplies `agent_operations`,
`agent_handle`, and `agent_version`; core fails explicitly if they are absent.

```python
def test_agent_is_healthy(healthy_agent, agent_checks):
    agent_checks.is_healthy(healthy_agent)


def test_registration(installed_agent, registration_flow, agent_checks):
    result = registration_flow.register(installed_agent)
    agent_checks.is_registered(result)
```

### Capability models

The public `models` module exports `Capability`, `CapabilitySet`,
`CapabilityContext`, `CompatibilityResult`, `Architecture`,
`OperatingSystemFamily`, and `UnsupportedConfigurationError`. Product tests may
declare capability names through markers and inspect stable results supplied by
public fixtures. They must not instantiate a resolver, load a matrix, or repeat
OS/version/feature compatibility checks.

### Capability markers

The public `markers` module defines these marker names:

- `requires_capability(*names)`;
- `requires_feature(*names)`;
- `incompatible_feature(*names)`;
- `supported_os(*families)`;
- `min_agent_version(version)`;
- `max_agent_version(version)`;
- `framework_contract`.

Capability markers require a resolved compatibility matrix and target context.
A valid unsupported combination is skipped with an exact reason. Missing,
malformed, or inconsistent compatibility data is a configuration error and must
not be converted to a skip. Version bounds are inclusive.

## Private surface

Everything outside the allowlist is internal and may change without direct
compatibility guarantees. The following must always remain hidden from product
tests and from public signatures:

- transports and transport-specific objects;
- OS-specific commands and command results;
- pytest hooks;
- retry implementation and policy machinery;
- host leasing implementation;
- distributed locks;
- Allure implementation details.

Private objects must not be returned, raised, required as arguments, exposed as
fixture values, or required for configuration through public modules.

## Compatibility promise

The public contract includes more than import paths. It includes documented
names, call signatures, types, fixture names and scopes, model fields, marker
semantics, exceptions, and documented behavior.

Public API changes follow Semantic Versioning:

- backward-compatible fixes are patch releases;
- backward-compatible additions and deprecations are minor releases;
- incompatible removals or semantic changes are major releases.

Every breaking change requires an accepted ADR before implementation and must
ship only in a major release. A rename, signature change, fixture scope change,
model field removal, changed marker meaning, or newly raised exception can be a
breaking change. Prefer documented deprecation and migration paths when feasible.

## Requirements for additions

Every new public or private function must include complete type hints and unit
tests. A new public capability must also:

- be OS-neutral at its boundary;
- avoid exposing private implementation types;
- document inputs, outputs, errors, lifecycle, and side effects;
- define behavior for Linux, Windows, and macOS, including an explicit typed
  unsupported outcome where necessary;
- include compatibility and release-impact review.

## Usage boundary example

This illustrates the intended imports, not implemented API names:

```python
from cyber_agent_test_core import checks, flows, markers, models
from cyber_agent_test_core.fixtures import agent_host
```

Importing a transport, adapter, controller, hook, retry helper, lease manager,
lock implementation, or Allure helper from a product test violates the contract.
