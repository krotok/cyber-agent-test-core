"""Release version and channel validation used by CI."""

import argparse
import re
import tomllib
from pathlib import Path

_VERSION = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)(?:(?P<pre>rc)(?P<pre_number>[1-9]\d*))?$"
)


def validate_version(value: str) -> bool:
    """Accept stable and rc PEP 440 versions used by the release pipeline."""
    return _VERSION.fullmatch(value) is not None


def is_prerelease(value: str) -> bool:
    """Return whether a validated version is an rc release."""
    if not validate_version(value):
        raise ValueError(f"invalid release version: {value}")
    return "rc" in value


def project_version(project_root: Path) -> str:
    """Read the immutable version from project metadata."""
    with (project_root / "pyproject.toml").open("rb") as stream:
        value = tomllib.load(stream)["project"]["version"]
    if not isinstance(value, str):
        raise ValueError("project.version must be a string")
    return value


def validate_release(project_root: Path, requested: str) -> None:
    """Require requested, package, and public API versions to match exactly."""
    if not validate_version(requested):
        raise ValueError(f"invalid release version: {requested}")
    configured = project_version(project_root)
    source = project_root / "src/cyber_agent_test_core/api/__init__.py"
    match = re.search(
        r'^CORE_VERSION:\s*str\s*=\s*"([^"]+)"$',
        source.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    public = None if match is None else match.group(1)
    if requested != configured or requested != public:
        raise ValueError(
            "release version mismatch: "
            f"requested={requested}, project={configured}, public={public}"
        )


def main() -> int:
    """Validate a release and emit shell-friendly channel information."""
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    validate_release(arguments.project_root, arguments.version)
    print("prerelease=true" if is_prerelease(arguments.version) else "prerelease=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
