# ADR-006: Centralized capability resolution

- Status: Accepted
- Date: 2026-08-06
- Deciders: Core framework maintainers
- Related issues: None

## Context

Capabilities vary across Agent/backend versions, OS and OS version,
kernel/build, architecture, feature flags, licenses, and environments. Encoding
those dimensions as scattered `if os ==`, version comparisons, or feature checks
in tests and controllers would duplicate policy, produce inconsistent skips,
and make support boundaries impossible to audit.

## Decision

All support policy is resolved by `CapabilityResolver` from a typed
`CapabilityContext`, a `FeatureFlagProvider`, and a strict declarative
`CompatibilityMatrix`. Matrix data is supplied outside core as YAML or JSON;
the schema, loader, resolver, capability vocabulary, result, and stable error
belong to core.

Rules may match every supported dimension and grant/remove capabilities or
reject a combination with an exact reason. PEP 440 specifiers define inclusive
and exclusive version boundaries. An unmatched target is unsupported when the
matrix requires a match. Callers consume only `CompatibilityResult` and
`CapabilitySet`; they must not repeat raw OS/version/flag decisions.

Pytest collection interprets public declarative markers against the resolved
result. Valid unsupported combinations are skipped with exact reasons. Missing
or invalid matrix/context data is a configuration error and is never converted
to a skip. Skip reasons are passed to the optional internal Allure adapter.

## Alternatives considered

- **Conditional checks in product tests:** rejected because they violate the
  thin-test contract and duplicate platform policy.
- **Conditional checks in each flow/controller:** rejected because policy would
  remain distributed and contradictory.
- **Hard-coded Python compatibility tables:** rejected because product support
  data could not change independently or be reviewed declaratively.
- **Skip every resolver error:** rejected because malformed configuration would
  look like an unsupported product combination.

## Consequences

Compatibility data must be version-controlled and validated for each consuming
product suite. Resolver and schema changes require core tests, while ordinary
support-matrix changes require no code branch. Every unsupported decision is
explainable, and version edges are covered by deterministic unit tests.

## Compatibility and release impact

`Capability`, `CapabilitySet`, `CompatibilityResult`, context enums, and
`UnsupportedConfigurationError` are backward-compatible additions to the public
`models` module. The framework version advances to 0.2.0. Future incompatible
changes to these types or marker semantics require an ADR and major release.
