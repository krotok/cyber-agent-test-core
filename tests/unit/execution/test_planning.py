"""Execution planning, sharding, and reassignment policy tests."""

import pytest

from cyber_agent_test_core.diagnostics.artifacts import FailureCategory
from cyber_agent_test_core.execution import (
    ExecutionPlanner,
    LabTarget,
    ReassignmentCoordinator,
    TestRequirement,
    may_reassign,
)
from cyber_agent_test_core.transports import HostUnavailableError


def _test(nodeid: str, duration: float, os_name: str = "linux") -> TestRequirement:
    return TestRequirement(
        nodeid=nodeid,
        operating_systems=frozenset({os_name}),
        suite="regression",
        estimated_duration=duration,
        feature_set=frozenset({"protection"}),
        agent_version="4.8.1",
        required_capabilities=frozenset({"offline_scan"}),
    )


def test_balances_tests_across_shards_and_labs() -> None:
    labs = (
        LabTarget("lab-a", frozenset({"linux"}), frozenset({"offline_scan"}), 2),
        LabTarget("lab-b", frozenset({"linux"}), frozenset({"offline_scan"}), 2),
    )

    plan = ExecutionPlanner().build(
        (_test("test_a", 10), _test("test_b", 8), _test("test_c", 2)),
        labs,
        shard_count=2,
    )

    assert {test.shard for test in plan.selected_tests} == {0, 1}
    assert {test.lab for test in plan.selected_tests} == {"lab-a", "lab-b"}
    assert not plan.skipped_unsupported


def test_records_unsupported_combinations() -> None:
    plan = ExecutionPlanner().build(
        (_test("test_windows", 1, "windows"),),
        (LabTarget("linux-lab", frozenset({"linux"}), frozenset(), 1),),
        shard_count=1,
    )

    assert not plan.selected_tests
    assert plan.skipped_unsupported[0].nodeid == "test_windows"


def test_only_infrastructure_failure_can_be_reassigned() -> None:
    assert may_reassign(FailureCategory.INFRASTRUCTURE, remaining_hosts=1)
    assert not may_reassign(FailureCategory.PRODUCT, remaining_hosts=3)
    assert not may_reassign(FailureCategory.INFRASTRUCTURE, remaining_hosts=0)


def test_coordinator_reassigns_infrastructure_failure_to_another_host() -> None:
    attempts: list[str] = []

    def execute(host: str) -> str:
        attempts.append(host)
        if host == "host-a":
            raise HostUnavailableError("offline")
        return host

    result = ReassignmentCoordinator().execute(("host-a", "host-b"), execute)

    assert result == "host-b"
    assert attempts == ["host-a", "host-b"]


def test_coordinator_never_reassigns_product_failure() -> None:
    attempts: list[str] = []

    def execute(host: str) -> str:
        attempts.append(host)
        raise AssertionError("product behavior failed")

    with pytest.raises(AssertionError, match="product behavior failed"):
        ReassignmentCoordinator().execute(("host-a", "host-b"), execute)

    assert attempts == ["host-a"]
