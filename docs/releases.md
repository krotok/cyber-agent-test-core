# Release pipeline and publication

The `cyber-agent-test-core` GitHub Actions workflow is the only supported package
publication path. It runs lint, strict typing, unit tests on Linux/Windows/macOS,
framework integration tests, public API contracts, vulnerability and secret scans,
then builds one wheel and sdist. The release artifact also contains an SPDX JSON
SBOM, SHA-256 checksums, Sigstore keyless signatures, and PyPI attestations.

All Python CI dependencies are exact pins in `requirements/ci.lock`. Updates are
reviewed as ordinary pull requests and must pass vulnerability scanning. Runtime
dependency ranges remain appropriately broad in package metadata because core is a
library; the lock controls the environment used to certify a release.

## Version policy

Versions are canonical PEP 440/SemVer-compatible values. Examples:

- `1.4.2`: backward-compatible patch or hotfix;
- `1.5.0`: backward-compatible capability or deprecation;
- `2.0.0`: approved breaking migration;
- `1.6.0rc1`: release candidate published to the pre-release repository.

The version must already match `pyproject.toml` and public `CORE_VERSION` in the
release commit. CI never rewrites version metadata. This makes the tested commit,
signed artifacts, tag, and release notes traceable to identical source.

## Release procedures

### Normal release

Create a release branch, update version, changelog/migration notes and compatibility
data, then obtain approval. Dispatch the workflow with that version and an exact
product-tests candidate ref. After every gate succeeds, stable artifacts are
published with Trusted Publishing, an annotated `v<version>` tag is pushed, and a
GitHub release is generated.

### Hotfix

Branch `hotfix/<version>` from the affected supported tag. Include only the minimal
backward-compatible fix and regression test, increment the patch version, and run
the same complete pipeline. Never reuse or overwrite a published version.

### Pre-release

Use an `rc` version such as `1.6.0rc1`. The complete pipeline publishes it to the
configured `testpypi` environment. Promote by committing the final stable version
and running a new pipeline; do not rename an rc artifact.

### Major migration

A major version requires an accepted ADR, migration guide, explicit compatibility
candidate, and removal list. Consumers must demonstrate compatibility with the
candidate wheel before stable publication. Breaking changes never ship in minor or
patch releases.

### Deprecation period

Deprecations begin in a minor release with documentation and a runtime warning where
appropriate. Maintain them for at least one complete minor release and the stated
support window. Removal requires the next major release and migration notes.

### Rollback

Published package files and tags are immutable. Stop deployment/promotion, mark the
GitHub release as affected, and pin consumers to the previous signed version. Then
publish a forward-fix patch through the hotfix procedure. PyPI deletion, tag moves,
force-pushes, and version reuse are prohibited because they break provenance.

## Product-tests compatibility boundary

The compatibility job sparse-checks out and runs only
`tests/framework_compatibility` from the supplied product-tests candidate. That
directory owns its pinned `requirements.lock` and must accept the candidate wheel.
The core pipeline never discovers or runs the product regression tree. Full product
regression belongs to the product release pipeline after a core candidate passes
this framework contract gate.
