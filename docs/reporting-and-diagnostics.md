# Allure, logging, and diagnostics

Lifecycle tests automatically receive the Allure hierarchy `Cybersecurity Agent`
→ feature → story, with parent suite set to environment, suite to OS, and sub-suite
to Agent version. `allure_feature("Protection")` and `allure_story("behavior")`
override inference. Registration is inferred from `registered_agent`; other lifecycle
features default to the configured install mode.

Each result records Agent/backend versions, environment, laboratory, leased host,
OS and version, architecture, feature states, suite, tenant reference, install and
upgrade versions, git commit, CI build ID/URL, package build, execution ID, and core
version. The generated `launch name` parameter follows:

```text
Agent 4.8.1 | Backend 12.5 | Windows 2022 | Regression | Stage
```

The external Allure launcher should use this same value as its launch name; the
Python Allure runtime has no portable API for renaming an already-created launch.

On setup or test failure, the runtime collector supplies Agent/installer logs,
service status, process list, OS information, backend response, redacted command,
Agent events, and network diagnostics. Pytest capture supplies stdout/stderr, and
core supplies the merged test configuration. Every core-managed attachment is
recursively redacted and capped by `--diagnostics-max-attachment-bytes` (2 MiB by
default). Truncation is explicit. Missing lab artifacts are attached as unavailable
rather than silently omitted.

The logging context is task-local and reset after each test. It includes
`execution_id`, `test_id`, `host`, `environment`, `lab`, `agent_version`,
`backend_version`, and `ci_build_id`. `JsonLogFormatter` emits this context with a
redacted message; `StructuredContextFilter` supports existing formatters.

Failures receive a `failure_category` result property and Allure label:

- `product failure`: observable product behavior and assertion failures;
- `infrastructure failure`: transport, host availability, lease, or connectivity;
- `configuration failure`: invalid or unloadable run configuration;
- `cleanup failure`: cleanup execution or verification failure.
