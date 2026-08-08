"""Safe synthetic configuration fixtures."""

from collections.abc import Callable
from typing import Any

import pytest


@pytest.fixture
def run_data() -> Callable[..., dict[str, Any]]:
    """Build a minimal synthetic run mapping with optional overrides."""

    def factory(**overrides: object) -> dict[str, Any]:
        data: dict[str, Any] = {
            "agent_version": "1.2.3",
            "backend_version": "4.5.6",
            "environment": "synthetic-stage",
            "lab": "synthetic-lab",
            "suite": "smoke",
            "tenant": {"reference": "vault:tenants/synthetic"},
            "build_id": "build-placeholder",
            "git_commit": "abcdef1234567",
            "execution_id": "execution-placeholder",
            "architecture": "x86_64",
        }
        data.update(overrides)
        return data

    return factory
