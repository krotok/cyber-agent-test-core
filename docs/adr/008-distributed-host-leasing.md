# ADR-008: Distributed laboratory host leasing

- Status: Accepted
- Date: 2026-08-08
- Deciders: Core framework maintainers
- Related issues: CORE-07

## Context

Laboratory hosts are shared by pytest-xdist workers and independent CI jobs.
Process-local locks cannot prevent two jobs from selecting the same exclusive
host. Failed tests, worker termination, reboot, preparation failures, and stale
heartbeats must not leave unsafe hosts silently reusable. Inventory must contain
credential references, never credential values.

## Decision

`HostInventory` stores strict logical host records and mutable observed state.
`HostSelector` performs deterministic typed filtering but never grants
ownership. `HostLeaseManager` grants ownership only after acquiring a
`DistributedLockProvider` token with TTL. The token is the fencing identity and
remains authoritative even when separate jobs have independent inventory
objects.

Exclusive hosts use one stable lock key. Shared hosts use a declared number of
stable slot keys. Lease heartbeat refreshes the same token. Lost heartbeat
quarantines the host; expired locally known leases are reaped; context-managed
leases release in `finally`. Cleanup must be explicitly verified before reuse,
and any preparation or cleanup uncertainty quarantines the host with a reason.

Core provides a cross-process atomic `FileLockProvider`, a deterministic
`FakeLockProvider`, and the `RedisLockProvider` interface. Production-grade
multi-node deployments should implement Redis ownership with atomic SET-NX,
token comparison, TTL refresh, and token-checked release. In-memory locking
alone is forbidden as an ownership authority.

Host records include only opaque `CredentialsReference` values. Real hostnames,
credentials, tenants, customers, and production endpoints are external data and
must not be committed to core.

## Alternatives considered

- **Inventory state alone:** rejected because separate workers and jobs can read
  stale state concurrently.
- **Python thread/process locks:** rejected because they do not coordinate
  independent CI jobs or machines.
- **Leases without TTL:** rejected because crashed owners could block a host
  indefinitely.
- **Release without cleanup verification:** rejected because contaminated hosts
  could create false product failures or leak state between tests.
- **Embed credentials in inventory:** rejected because inventory is routinely
  logged, validated, and version-controlled.

## Consequences

Every host-consuming fixture must own a lease lifecycle and heartbeat. Lock
providers require contract tests for atomic acquisition, fencing, expiry,
refresh, and release. Inventory state improves observability but lock tokens
decide correctness. Quarantined and broken hosts require an explicit repair and
clear operation before selection.

## Compatibility and release impact

This adds internal inventory and leasing infrastructure without expanding the
product-test public import surface. It is backward compatible within the 0.2.x
development line. Exposing lease or lock implementation details publicly would
violate ADR-002 and ADR-004.
