# Fake vertical slice

The packaged fake mode proves the complete public fixture lifecycle without SSH,
WinRM, HTTP, remote machines, credentials, or product binaries. It is intended for
framework development, product-tests contract validation, examples, and package
smoke tests—not as a substitute for product regression.

The private composition root contains `FakeInventory`, `FakeHostLeaseManager`,
`FakeSSHTransport`, `FakeWinRMTransport`, `FakeBackendClient`, and
`FakeAgentController`. Product tests do not import them. They request public fixtures
such as `registered_agent`, `healthy_agent`, and `observed_agent_version`.

For each test the framework selects the requested OS host, leases it exclusively,
creates the real Linux/Windows/macOS OS controller over a fake transport, installs
the Agent, starts its service, registers through the fake backend, waits with the
bounded core waiter for online status, exposes the installed version, applies the
normal Allure metadata, uninstalls and verifies cleanup, then releases the lease.

Run the thin example from source:

```text
pytest examples/fake_vertical_slice --fake-vertical-slice --fake-os=linux --no-cov
pytest examples/fake_vertical_slice --fake-vertical-slice --fake-os=windows --no-cov
pytest examples/fake_vertical_slice --fake-vertical-slice --fake-os=macos --no-cov
```

Run framework checks and build the wheel:

```text
ruff check src tests examples
mypy src
pytest --no-cov
python -m build --wheel
```

Validate an installed wheel in a clean environment:

```text
python -m venv .package-smoke
.package-smoke/bin/python -m pip install dist/cyber_agent_test_core-*.whl
.package-smoke/bin/python -m pytest examples/fake_vertical_slice \
  --fake-vertical-slice --fake-os=linux --no-cov
```

On Windows, use `.package-smoke\Scripts\python.exe` for the last two commands.
No command opens a real remote connection; transport commands are only recorded in
memory.
