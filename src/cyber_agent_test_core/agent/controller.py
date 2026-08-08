"""Agent product behavior boundary above OS controllers."""

from typing import Protocol


class AgentController(Protocol):
    """Product-level operations; implementations may use an OS controller."""

    def is_healthy(self) -> bool:
        """Return product health without exposing OS commands."""
        ...
