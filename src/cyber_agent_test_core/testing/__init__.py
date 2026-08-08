"""Private deterministic fakes used by the packaged vertical slice."""

from cyber_agent_test_core.testing.vertical import (
    FakeAgentController,
    FakeHostLeaseManager,
    FakeInventory,
    FakeSSHTransport,
    FakeVerticalSliceRuntime,
    FakeWinRMTransport,
)

__all__ = [
    "FakeAgentController",
    "FakeHostLeaseManager",
    "FakeInventory",
    "FakeSSHTransport",
    "FakeVerticalSliceRuntime",
    "FakeWinRMTransport",
]

