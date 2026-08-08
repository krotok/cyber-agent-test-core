"""Shared safe command construction helpers for platform adapters."""

import json
from base64 import b64encode


def encoded_text(value: str) -> str:
    """Encode text for transport as non-secret base64 command data."""
    return b64encode(value.encode("utf-8")).decode("ascii")


def parse_os_info_json(output: str) -> tuple[str, str, str]:
    """Parse a platform adapter's OS information payload."""
    parsed = json.loads(output)
    if not isinstance(parsed, dict):
        raise ValueError("OS information must be a JSON object")
    version = parsed.get("version")
    kernel = parsed.get("kernel_build")
    architecture = parsed.get("architecture")
    if (
        not isinstance(version, str)
        or not isinstance(kernel, str)
        or not isinstance(architecture, str)
    ):
        raise ValueError("OS information fields must be strings")
    return version, kernel, architecture
