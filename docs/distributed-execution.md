# Parallel and distributed execution

The same deterministic collection runs under ordinary pytest and pytest-xdist.
Install the `distributed` extra to use xdist. Function-scoped lifecycle fixtures
keep worker state isolated, while TTL/fencing locks coordinate workers, independent
CI jobs, and labs. `CI_NODE_TOTAL`/`CI_NODE_INDEX` provide defaults for
`--core-shard-count`/`--core-shard-index`; explicit options take precedence.

## Resource ownership

Resources are classified as:

- `immutable`: read-only and lock-free;
- `shared`: concurrent use up to declared fixed capacity;
- `exclusive`: one owner at a time;
- `stateful`: mutable ownership requiring exclusive cleanup and verification.

`ResourceLeaseManager` locks host, tenant, license, backend configuration, network
namespace, and test user identifiers. Global keys include resource type and opaque
identifier. Multi-resource acquisition uses sorted keys to avoid lock-order
deadlocks, releases partial acquisition atomically, and releases final leases in
reverse order. Distributed providers remain the ownership authority across CI jobs.

## Planning and sharding

An `ExecutionPlan` is created after collection and before test execution. Optional
`--core-execution-plan=path.json` persists it. The plan lists selected node IDs,
required OS, selected lab, required host count, estimated duration/shard, and
unsupported combinations with exact reasons.

Markers `supported_os`, `core_suite`, `estimated_duration`, `requires_feature`,
version compatibility markers, `requires_capability`, and `required_hosts` supply
the sharding dimensions. Longest-estimated-duration-first balancing uses all of
these dimensions as a deterministic tie-break key. A `--core-plan-labs` JSON list
supplies each lab's name, OS set, capability set, and host count. Tests unsupported
by every lab are recorded rather than assigned.

xdist distributes the already selected CI shard among local workers. Independent
jobs compute the same complete plan and select only their shard, so collection does
not depend on process-random hashes or collection order.

## Failure reassignment

`ReassignmentCoordinator` may execute an operation on the next candidate host only
when the caught error classifies as `infrastructure failure` and a different host
remains. Product, configuration, and cleanup failures are immediately propagated.
This policy is the scheduler boundary: core never turns a product assertion into a
host retry. The failed infrastructure host must be quarantined by the laboratory
runtime before it submits a replacement candidate.

## Allure result merging

Pass each worker/job directory with repeated `--core-allure-results-input` and set
`--core-allure-results-output`. Only the standalone process or xdist controller
merges results. Identical duplicates are ignored; different same-name artifacts are
retained with content-hash suffixes. Generate the final Allure report from the
merged directory after all CI jobs have published their result directories.
