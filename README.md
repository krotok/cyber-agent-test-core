# Cyber Agent Test Core

Reusable Python test framework for validating Cybersecurity Agent behavior on
Linux, Windows, and macOS. This repository contains framework building blocks;
product regression tests belong in product test repositories.

The repository currently provides the package skeleton and a minimal pytest
plugin. Product-specific framework behavior is not implemented yet.

## Design goals

- Present one stable, OS-neutral API to product tests.
- Keep product tests declarative and focused on observable product behavior.
- Isolate host access, command construction, synchronization, retries, and
  reporting behind framework-owned abstractions.
- Support safe parallel and remote execution across Linux, Windows, and macOS.

## Dependency direction

Dependencies flow in one direction only:

```text
product tests
    -> public core fixtures / flows / checks
    -> controllers
    -> OS adapters
    -> transports
```

Reverse dependencies are forbidden. Lower layers must not import or otherwise
depend on higher layers.

Product tests may import only these public modules:

- `cyber_agent_test_core.api`
- `cyber_agent_test_core.models`
- `cyber_agent_test_core.fixtures`
- `cyber_agent_test_core.flows`
- `cyber_agent_test_core.checks`
- `cyber_agent_test_core.markers`

Everything else is private, even if Python makes it technically importable.

## Documentation

- [Architecture](docs/architecture.md)
- [Public API policy](docs/public-api.md)
- [Thin tests contract](docs/thin-tests-contract.md)
- [Contributing](CONTRIBUTING.md)
- [Release and publication](docs/releases.md)
- [Architecture decision records](docs/adr/README.md)

## Non-negotiable test rules

Product tests must not run shell commands, call `time.sleep`, contain
OS/version branches, store secrets, or retry product failures. Use public
fixtures, flows, checks, models, and markers instead.

Public API changes follow Semantic Versioning. Breaking changes require an ADR
and a major release. Every new function requires type hints and unit tests.

## Development

Python 3.12 or newer is required. Install development tools and run the standard
checks:

```text
python -m pip install -e ".[dev]"
ruff check .
mypy src
pytest
python -m build
```

The pytest plugin is registered through the package entry point. It provides
the `core_version` fixture, `--core-info`, and declarative compatibility markers.
Compatibility is resolved centrally from external YAML/JSON matrix and context
files passed with `--core-compatibility-matrix` and
`--core-capability-context`. It performs no product-specific actions.
