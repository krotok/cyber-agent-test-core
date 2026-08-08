"""Release version policy tests."""

from pathlib import Path

import pytest

from tools.release import (
    is_prerelease,
    project_version,
    validate_release,
    validate_version,
)


@pytest.mark.parametrize("version", ["1.4.2", "1.5.0", "2.0.0", "1.6.0rc1"])
def test_supported_release_versions(version: str) -> None:
    assert validate_version(version)


@pytest.mark.parametrize("version", ["v1.4.2", "1.4", "1.6.0-rc1", "1.6.0rc0"])
def test_rejects_noncanonical_release_versions(version: str) -> None:
    assert not validate_version(version)


def test_distinguishes_stable_and_prerelease() -> None:
    assert not is_prerelease("1.5.0")
    assert is_prerelease("1.6.0rc1")


def test_validates_repository_versions_match() -> None:
    root = Path(__file__).resolve().parents[2]

    validate_release(root, project_version(root))
