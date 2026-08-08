"""End-to-end collection policy tests for capability markers."""

import json
from pathlib import Path

import pytest


def _write_compatibility_files(
    root: Path,
    *,
    agent_version: str = "2.0.0",
) -> tuple[Path, Path]:
    """Write synthetic declarative data for an isolated pytest run."""
    matrix = root / "matrix.json"
    context = root / "context.json"
    matrix.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "rules": [
                    {
                        "rule_id": "synthetic-supported",
                        "agent_version": ">=2,<3",
                        "grants": ["offline_scan", "agent_health_api"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    context.write_text(
        json.dumps(
            {
                "agent_version": agent_version,
                "backend_version": "5.0.0",
                "operating_system": "linux",
                "os_version": "24.04",
                "kernel_build": "6.8.0",
                "architecture": "x86_64",
                "feature_flags": ["feature-a"],
                "licenses": ["license-a"],
                "environment": "synthetic-stage",
            }
        ),
        encoding="utf-8",
    )
    return matrix, context


def _run_with_compatibility(
    pytester: pytest.Pytester,
    matrix: Path,
    context: Path,
) -> pytest.RunResult:
    """Run isolated pytest with explicit capability inputs."""
    return pytester.runpytest(
        "--core-compatibility-matrix",
        str(matrix),
        "--core-capability-context",
        str(context),
        "--no-cov",
        "-rs",
    )


def test_supported_markers_run_at_inclusive_boundary(pytester: pytest.Pytester) -> None:
    matrix, context = _write_compatibility_files(pytester.path)
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.requires_capability("offline_scan")
        @pytest.mark.requires_feature("feature-a")
        @pytest.mark.incompatible_feature("feature-b")
        @pytest.mark.supported_os("linux", "macos")
        @pytest.mark.min_agent_version("2.0.0")
        @pytest.mark.max_agent_version("2.0.0")
        def test_supported() -> None:
            pass
        """
    )

    result = _run_with_compatibility(pytester, matrix, context)

    result.assert_outcomes(passed=1)


def test_missing_capability_skips_with_exact_reason(pytester: pytest.Pytester) -> None:
    matrix, context = _write_compatibility_files(pytester.path)
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.requires_capability("network_isolation")
        def test_unsupported() -> None:
            pass
        """
    )

    result = _run_with_compatibility(pytester, matrix, context)

    result.assert_outcomes(skipped=1)
    result.stdout.fnmatch_lines(["*missing capabilities: network_isolation*"])


def test_unsupported_target_skips_all_tests(pytester: pytest.Pytester) -> None:
    matrix, context = _write_compatibility_files(
        pytester.path,
        agent_version="3.0.0",
    )
    pytester.makepyfile("def test_unmarked() -> None:\n    pass")

    result = _run_with_compatibility(pytester, matrix, context)

    result.assert_outcomes(skipped=1)
    result.stdout.fnmatch_lines(
        ["*no compatibility rule matches the target configuration*"]
    )


def test_invalid_compatibility_data_is_not_hidden(pytester: pytest.Pytester) -> None:
    matrix, context = _write_compatibility_files(pytester.path)
    matrix.write_text("not-json", encoding="utf-8")
    pytester.makepyfile("def test_never_collected() -> None:\n    pass")

    result = _run_with_compatibility(pytester, matrix, context)

    assert result.ret != pytest.ExitCode.OK
    result.stderr.fnmatch_lines(["*invalid compatibility data*"])
