"""Framework-owned bounded waiting with diagnostic timeout errors."""

from collections.abc import Callable
from dataclasses import dataclass
from threading import Event
from time import monotonic
from typing import Protocol, TypeVar

ValueT = TypeVar("ValueT")


class WaitTimeoutError(AssertionError):
    """Expected product condition was not observed before its deadline."""


class WaitClock(Protocol):
    """Injectable monotonic clock and interruptible interval wait."""

    def now(self) -> float: ...

    def wait(self, seconds: float) -> None: ...


class SystemWaitClock:
    """Production clock that avoids direct sleeps."""

    def now(self) -> float:
        return monotonic()

    def wait(self, seconds: float) -> None:
        Event().wait(seconds)


@dataclass(frozen=True, slots=True)
class WaitPolicy:
    """Bounded polling parameters."""

    timeout_seconds: float = 30
    interval_seconds: float = 1

    def __post_init__(self) -> None:
        if self.timeout_seconds < 0:
            raise ValueError("timeout_seconds must be non-negative")
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")


class Waiter:
    """Poll a condition until it matches, preserving last-value diagnostics."""

    def __init__(
        self, policy: WaitPolicy | None = None, clock: WaitClock | None = None
    ) -> None:
        self._policy = policy or WaitPolicy()
        self._clock = clock or SystemWaitClock()

    def until(
        self,
        observe: Callable[[], ValueT],
        matches: Callable[[ValueT], bool],
        *,
        description: str,
        diagnose: Callable[[ValueT], str] = repr,
    ) -> ValueT:
        deadline = self._clock.now() + self._policy.timeout_seconds
        while True:
            value = observe()
            if matches(value):
                return value
            remaining = deadline - self._clock.now()
            if remaining <= 0:
                raise WaitTimeoutError(
                    f"timed out waiting for {description}; "
                    f"last observation: {diagnose(value)}"
                )
            self._clock.wait(min(self._policy.interval_seconds, remaining))
