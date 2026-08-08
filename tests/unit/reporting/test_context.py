"""Structured logging context tests."""

import json
import logging

from cyber_agent_test_core.reporting.context import (
    JsonLogFormatter,
    LoggingContext,
    StructuredContextFilter,
    bind_logging_context,
    reset_logging_context,
)


def test_json_formatter_includes_bound_context_and_resets_it() -> None:
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        "core", logging.INFO, __file__, 1, "token=unsafe ready", (), None
    )
    context = LoggingContext(
        execution_id="execution-1",
        test_id="test_example",
        host="host-1",
        environment="stage",
        lab="lab-1",
        agent_version="4.8.1",
        backend_version="12.5",
        ci_build_id="build-7",
    )
    token = bind_logging_context(context)
    try:
        payload = json.loads(formatter.format(record))
    finally:
        reset_logging_context(token)

    assert payload["execution_id"] == "execution-1"
    assert payload["test_id"] == "test_example"
    assert "unsafe" not in payload["message"]
    assert "execution_id" not in json.loads(formatter.format(record))


def test_context_filter_redacts_message_for_non_json_formatters() -> None:
    record = logging.LogRecord(
        "core", logging.INFO, __file__, 1, "password=%s", ("unsafe",), None
    )

    assert StructuredContextFilter().filter(record)

    assert record.getMessage() == "password=[REDACTED]"
