"""Structured logging context isolated per pytest execution context."""

import json
import logging
from contextvars import ContextVar, Token
from dataclasses import asdict, dataclass

from cyber_agent_test_core.diagnostics.artifacts import redact_text


@dataclass(frozen=True, slots=True)
class LoggingContext:
    execution_id: str
    test_id: str
    host: str
    environment: str
    lab: str
    agent_version: str
    backend_version: str
    ci_build_id: str | None


_CONTEXT: ContextVar[LoggingContext | None] = ContextVar(
    "cyber_agent_logging_context", default=None
)


def bind_logging_context(context: LoggingContext) -> Token[LoggingContext | None]:
    """Bind context for the current thread/task and return a reset token."""
    return _CONTEXT.set(context)


def reset_logging_context(token: Token[LoggingContext | None]) -> None:
    """Restore the previous context without leaking state to another test."""
    _CONTEXT.reset(token)


class StructuredContextFilter(logging.Filter):
    """Add stable context fields to ordinary standard-library log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(record.getMessage())
        record.args = ()
        context = _CONTEXT.get()
        values = {} if context is None else asdict(context)
        for name, value in values.items():
            setattr(record, name, value)
        return True


class JsonLogFormatter(logging.Formatter):
    """Format logs as one JSON object without serializing secrets implicitly."""

    def format(self, record: logging.LogRecord) -> str:
        context = _CONTEXT.get()
        payload: dict[str, object] = {
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        if context is not None:
            payload.update(asdict(context))
        return json.dumps(payload, sort_keys=True, default=str)
