"""Deterministic multi-lab execution planning and CI sharding."""

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol, TypeVar

from cyber_agent_test_core.diagnostics.artifacts import (
    FailureCategory,
    classify_exception,
)

ResultT = TypeVar("ResultT", covariant=True)


class HostExecution(Protocol[ResultT]):
    def __call__(self, host: str) -> ResultT: ...


@dataclass(frozen=True, slots=True)
class LabTarget:
    name: str
    operating_systems: frozenset[str]
    capabilities: frozenset[str]
    host_count: int


@dataclass(frozen=True, slots=True)
class TestRequirement:
    __test__ = False

    nodeid: str
    operating_systems: frozenset[str]
    suite: str
    estimated_duration: float
    feature_set: frozenset[str]
    agent_version: str
    required_capabilities: frozenset[str]
    required_hosts: int = 1


@dataclass(frozen=True, slots=True)
class PlannedTest:
    nodeid: str
    lab: str
    shard: int
    operating_systems: tuple[str, ...]
    suite: str
    required_hosts: int
    estimated_duration: float


@dataclass(frozen=True, slots=True)
class SkippedCombination:
    nodeid: str
    reason: str


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    selected_tests: tuple[PlannedTest, ...]
    skipped_unsupported: tuple[SkippedCombination, ...]
    shard_count: int

    def write_json(self, path: Path) -> None:
        """Persist a stable plan before test execution begins."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(self), indent=2, sort_keys=True), encoding="utf-8"
        )


class ExecutionPlanner:
    """Place supported tests, then balance longest tests across shards."""

    @staticmethod
    def _labs(
        requirement: TestRequirement, labs: tuple[LabTarget, ...]
    ) -> list[LabTarget]:
        return [
            lab
            for lab in labs
            if (
                not requirement.operating_systems
                or requirement.operating_systems & lab.operating_systems
            )
            and requirement.required_capabilities <= lab.capabilities
            and requirement.required_hosts <= lab.host_count
        ]

    def build(
        self,
        tests: tuple[TestRequirement, ...],
        labs: tuple[LabTarget, ...],
        *,
        shard_count: int,
    ) -> ExecutionPlan:
        if shard_count < 1:
            raise ValueError("shard_count must be positive")
        loads = [0.0] * shard_count
        lab_loads = {lab.name: 0.0 for lab in labs}
        selected: list[PlannedTest] = []
        skipped: list[SkippedCombination] = []
        ordered = sorted(
            tests, key=lambda test: (-test.estimated_duration, test.nodeid)
        )
        for requirement in ordered:
            candidates = self._labs(requirement, labs)
            if not candidates:
                skipped.append(
                    SkippedCombination(
                        requirement.nodeid,
                        "no lab supports required OS/capabilities/hosts",
                    )
                )
                continue
            lab = min(candidates, key=lambda value: (lab_loads[value.name], value.name))
            dimension_key = "|".join(
                (
                    ",".join(sorted(requirement.operating_systems)),
                    requirement.suite,
                    ",".join(sorted(requirement.feature_set)),
                    requirement.agent_version,
                    ",".join(sorted(requirement.required_capabilities)),
                )
            )
            preferred = stable_shard(dimension_key, shard_count)
            shard = min(
                range(shard_count),
                key=lambda value: (
                    loads[value],
                    (value - preferred) % shard_count,
                ),
            )
            loads[shard] += requirement.estimated_duration
            lab_loads[lab.name] += requirement.estimated_duration
            selected.append(
                PlannedTest(
                    requirement.nodeid,
                    lab.name,
                    shard,
                    tuple(sorted(requirement.operating_systems)),
                    requirement.suite,
                    requirement.required_hosts,
                    requirement.estimated_duration,
                )
            )
        return ExecutionPlan(tuple(selected), tuple(skipped), shard_count)


def stable_shard(value: str, shard_count: int) -> int:
    """Return a process-independent fallback shard for an opaque test identity."""
    if shard_count < 1:
        raise ValueError("shard_count must be positive")
    return int.from_bytes(sha256(value.encode()).digest()[:8], "big") % shard_count


def may_reassign(category: FailureCategory, remaining_hosts: int) -> bool:
    """Permit host reassignment only for proven infrastructure failures."""
    return category is FailureCategory.INFRASTRUCTURE and remaining_hosts > 0


class ReassignmentCoordinator:
    """Retry on a different host only after a proven infrastructure failure."""

    def execute(
        self,
        hosts: tuple[str, ...],
        operation: HostExecution[ResultT],
    ) -> ResultT:
        if not hosts:
            raise ValueError("at least one candidate host is required")
        for index, host in enumerate(hosts):
            try:
                return operation(host)
            except Exception as error:
                category = classify_exception(error)
                if not may_reassign(category, len(hosts) - index - 1):
                    raise
        raise AssertionError("host reassignment loop exited without a result")
