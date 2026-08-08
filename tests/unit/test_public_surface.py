"""Unit tests for the initial public surface."""

from cyber_agent_test_core.api import CORE_VERSION
from cyber_agent_test_core.markers import FRAMEWORK_CONTRACT


def test_core_version_is_public() -> None:
    assert CORE_VERSION == "0.2.0"


def test_framework_contract_marker_name_is_public() -> None:
    assert FRAMEWORK_CONTRACT == "framework_contract"
