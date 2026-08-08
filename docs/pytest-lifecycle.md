# Pytest fixtures and lifecycle

The core plugin owns orchestration, while a laboratory integration supplies the
private `lifecycle_runtime` composition root. Product tests consume only fixture
names and public models; they never receive transports, commands, lock providers,
credentials, or cleanup implementation details.

## Fixture scopes

| Fixture | Scope | Reason |
| --- | --- | --- |
| `test_run_config` | session | The immutable run contract must not change during execution. |
| `execution_context` | session | CLI lifecycle and safety policy is resolved exactly once. |
| `environment_config` | session | One run targets one immutable environment policy. |
| `lab_inventory` | session | A stable snapshot makes placement deterministic; leases still enforce live ownership. |
| `host_lease` | function | Every test gets bounded ownership and unconditional release. |
| `host` | function | A host reference must never outlive its lease. |
| `clean_host` | function | Preparation and verified cleanup isolate mutable host state. |
| `os_controller` | function | The controller is tied to the leased host and transport session. |
| `agent_controller` | function | Agent operations are tied to one host/controller pair. |
| `backend_client` | function | Authentication and correlation state cannot leak between tests. |
| `installed_agent` | function | Installation is isolated; failed upgrades roll back and cleanup uninstalls. |
| `running_agent` | function | Runtime service state cannot leak between tests. |
| `registered_agent` | function | Registration belongs to the current Agent lifecycle. |
| `healthy_agent` | function | Health observes the current running Agent with bounded waiting. |
| `capability_set` | function | Capabilities depend on the host and installed version. |
| `diagnostics_collector` | function | Artifacts belong to one test and precede cleanup/release. |

## Policies and guarantees

`--host-preparation=clean-install|reuse|snapshot` selects clean preparation,
verification/reuse, or snapshot restoration. `--cleanup-policy=always|on-success|never`
controls state cleanup; lease release remains unconditional. Every performed cleanup
is verified, and failed verification fails teardown. `--diagnostics-level=basic|extended|full`
controls failure artifacts. Collection is idempotent and occurs for setup or test
failures before uninstall and host cleanup. Failed upgrade installation invokes
rollback before propagating the original failure.

Safety is enforced before lifecycle mutation: destructive tests cannot use `reuse`
without `--allow-destructive-reuse`; `never` cannot be combined with `--shared-ci`;
production lifecycle tests require `prod_safe`; and full production diagnostics
require `--allow-full-diagnostics-in-prod`. Laboratory runtimes should quarantine
hosts after snapshot restoration, cleanup, or verification failure.
