# CORE-16 Principal SDET architecture review

Date: 2026-08-08

Scope: source, tests, package boundary, lifecycle fixtures, reporting, release
pipeline, fake vertical slice, and architecture/ADR documentation. This review
treats implementation behavior as evidence and does not assume that an ADR alone
proves compliance.

## Executive assessment

No Critical or High finding remains open after this review. The framework has a
sound layered core, a small repository `conftest.py`, explicit public allowlist,
bounded product waits, transient-infrastructure-only retries, fenced ownership,
production gates, and an executable fake vertical slice.

The most serious discovered defect was that private autouse lifecycle fixtures were
defined in a module but not registered by the package plugin. Consequently prod
guards and automatic Allure/logging context were not guaranteed to execute. The
review also found non-atomic file-lock compare/mutate operations, missing lease
heartbeat, and failure-evidence paths capable of replacing the primary error. All
were corrected with regression tests.

## Closed Critical and High findings

| Severity | Affected files | Violation | Correction | Version impact |
| --- | --- | --- | --- | --- |
| Critical | `fixtures/__init__.py`, `fixtures/lifecycle.py` | Private autouse safety/reporting fixtures were not registered in the active pytest plugin, so prod checks and metadata could be bypassed. | Explicitly register the private fixtures, make reporting depend on the safety guard, and add a contract proving no host acquisition occurs before prod rejection. | PATCH defect fix; no intended public contract change. |
| High | `execution/locks.py`, `tests/unit/inventory/test_locks.py` | File lock refresh/release performed read-token and write/unlink as separate operations. A stale owner could race a replacement owner. | Serialize the complete read/compare/write transaction with an OS file lock, retain the state file, clear state under lock, fsync mutations, and test refresh/acquire interleaving. | PATCH. |
| High | `fixtures/lifecycle.py`, `internal/pytest_plugin.py`, `testing/vertical.py` | A function-scoped host lease had no heartbeat; TTL expiry could allow a second worker/job onto a live test host. | Add a bounded daemon heartbeat, derive an interval no greater than one-third of known lease duration, stop before release, and propagate heartbeat loss as infrastructure failure. | MINOR because a backward-compatible CLI option and integration-runtime operation are added. |
| High | `execution/resources.py` | Tenant/license/backend/network/user resource leases had TTL but no fenced renewal API. | Add aggregate token refresh and explicit `ResourceLeaseLostError`, with renewal/loss tests. | PATCH internal behavior. |
| High | `fixtures/lifecycle.py` | Diagnostics or rollback failure could replace the original install/product failure. Cleanup failures could lack evidence. | Make diagnostics strictly best-effort and idempotent, preserve the primary exception while adding rollback failure as a note, and collect before failed uninstall/cleanup is re-raised. | PATCH. |
| High | `fixtures/lifecycle.py`, `internal/pytest_plugin.py` | `prod_safe` alone did not prove run-level approval, and destructive prod execution was not unconditionally blocked before lease. | Require `production_approved`, reject destructive prod tests regardless of preparation mode, retain explicit full-diagnostics permission, and enforce ordering before host acquisition. | PATCH safety correction. |
| High | `diagnostics/artifacts.py`, `reporting/context.py` | URL userinfo and standard logging through `StructuredContextFilter` could retain credentials. | Redact URL credentials and normalize/redact `LogRecord.msg` plus arguments before any formatter sees them. | PATCH. |
| High | `fixtures/__init__.py`, `fixtures/lifecycle.py` | The private composition-root runtime fixture was accidentally included in the public `__all__`. | Register it under its pytest name through a private symbol and remove it from the supported exports; add a contract test. | PATCH while unreleased/private-by-documentation; MAJOR if consumers had been promised this accidental export. |

## Open findings

| Severity | Affected files | Violation/risk | Concrete correction | Version impact |
| --- | --- | --- | --- | --- |
| Medium | `internal/pytest_plugin.py`, `fixtures/lifecycle.py`, `testing/vertical.py` | These composition modules are large (roughly 400–600 lines). They are cohesive composition roots, not domain God objects, but change collision risk is rising. | Split compatibility collection, execution planning, reporting hooks, lifecycle safety, and fake config/controller registry into private plugins/services. Preserve fixture names and hook ordering with contract tests. | PATCH if purely internal. |
| Medium | `fixtures/lifecycle.py`, `config/schemas.py` | Several integration-facing fixture annotations expose private config classes or `object`; the intended product path uses higher-level fixtures, but the boundary is not mechanically clean. | Add sanitized public run/environment/lab/host views and public capability protocols; keep raw config/controllers on `_core_*` fixtures. | MINOR additive migration; MAJOR only if existing documented fixture value semantics are replaced without deprecation. |
| Medium | `execution/locks.py` | `FileLockProvider` coordinates processes only when every runner sees the same lock-capable filesystem. It is not a multi-node coordination service. `RedisLockProvider` remains a protocol. | Supply and certify a Redis implementation with atomic SET-NX, Lua/token compare, TTL renewal, partition tests, and operational health checks. | MINOR. |
| Medium | `reporting/results.py` | Same-name Allure files are retained with a hash suffix, but JSON references are not rewritten when an attachment—not a result file—collides. UUID naming makes this rare, not impossible. | Build a per-source rename map and rewrite attachment references in copied result JSON before finalization. | PATCH. |
| Medium | `diagnostics/artifacts.py`, `fixtures/lifecycle.py` | Provider failure is correctly prevented from masking the primary failure, but the collector failure itself is currently silent. | Emit one bounded/redacted framework diagnostic event or attachment without raising. | PATCH. |
| Medium | `models/capabilities.py`, `internal/pytest_plugin.py` | Capability identifiers are a closed enum; a new capability needs a core code change and MINOR release rather than matrix-only extension. | Retain this for typo safety, or introduce validated namespaced extension identifiers alongside built-ins. | MINOR additive; MAJOR if replacing the enum. |
| Medium | `tests/contract`, `.github/workflows/cyber-agent-test-core.yml` | xdist behavior is designed and deterministically sharded, but CI lacks a dedicated multi-process crash/worker-loss contract using installed `pytest-xdist`. | Add an xdist job that kills/loses a worker in a synthetic suite and proves fencing, cleanup/quarantine, and reassignment policy. | PATCH test-only. |
| Low | `tests/unit/test_public_surface.py`, `tests/contract/test_architecture_boundaries.py` | Public export and lower-layer dependency tests now exist, but there is no versioned signature/fixture-scope snapshot. | Store a reviewed API manifest and compare names, signatures, model fields, marker semantics, and fixture scopes in CI. | MINOR when introducing the manifest; later changes follow their actual SemVer impact. |

## Checklist conclusions

- **God objects:** no domain God object; three oversized internal composition modules remain Medium refactoring debt.
- **Large `conftest.py`:** no. Repository `tests/conftest.py` only registers `pytester`.
- **Transport / OSController / AgentController separation:** correct. Transports execute opaque commands, OS controllers own commands/parsing, Agent controller owns product state.
- **Public API stability:** documented six-module allowlist and SemVer policy exist. Export boundary tests were strengthened; sanitized fixture views remain Medium debt.
- **Internal modules closed:** convention and export boundary are enforced; Python cannot make modules physically unimportable. Private composition root is no longer publicly exported.
- **Semantic Versioning:** defined in ADR/docs and enforced by release validation. Breaking public changes require ADR plus major release.
- **Contract tests:** present for plugin, capability collection, package installation, architecture imports, public exports, prod ordering, heartbeat, rollback preservation, and fake vertical slice.
- **Cleanup:** yield finalizers uninstall, collect evidence, verify cleanup, and release lease even after failures. Cleanup errors remain visible.
- **Retries:** transport retry requires explicit `retryable`; backend retries only GET/idempotent requests and known transient statuses. Product assertions/lifecycle failures are not retried.
- **Secrets:** references rather than values, HTTP/body policy, recursive redaction, URL/header/key-value redaction, size limits, secret scan, and production suppression are present.
- **Prod safety:** explicit run approval, `prod_safe`, destructive prohibition, certificate validation, cleanup/shared-CI guard, and explicit full-diagnostics permission run before lease.
- **Parallel execution:** deterministic CI shards and xdist-compatible function scopes exist; dedicated worker-crash CI remains Medium debt.
- **Distributed locks:** fencing, TTL, serialized file transactions, heartbeat, stale-owner rejection, shared slots, and aggregate resource renewal are correct. Multi-node production needs a concrete Redis provider.
- **Diagnostics:** broad and bounded; provider-failure observability remains Medium debt.
- **Rollback:** failed transitions attempt rollback, preserve the primary error if rollback also fails, then cleanup/release.
- **New OS:** product tests remain unchanged. Add enum/config support, one OS controller implementation, composition mapping, and controller contract tests; this is normally MINOR.
- **New transport:** implement the `Transport` contract and inject it; OS and product tests need no behavior change. Normally MINOR for a supported adapter.
- **New capability:** possible without OS branches in product tests, but currently requires adding the typed enum member, resolver data, and tests; normally MINOR.

## Release recommendation

The closed safety/concurrency fixes should be included before the next release.
Because host heartbeat adds a supported CLI option and integration operation, the
aggregate change is best released as a **MINOR** version. If the runtime composition
fixture had ever been explicitly documented as public in a stable 1.x release,
removing it would instead require a deprecation period and the next **MAJOR** release.
