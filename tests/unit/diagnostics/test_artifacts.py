"""Secret safety, attachment bounds, and failure classification tests."""

from cyber_agent_test_core.diagnostics.artifacts import (
    FailureCategory,
    classify_exception,
    make_attachment,
    redact_text,
    redact_value,
)
from cyber_agent_test_core.inventory.flows import HostCleanupError
from cyber_agent_test_core.transports import HostUnavailableError


def test_redacts_text_credentials_without_removing_context() -> None:
    value = "request Authorization: Bearer abc.def password=hunter2 status=failed"

    redacted = redact_text(value)

    assert "abc.def" not in redacted
    assert "hunter2" not in redacted
    assert "status=failed" in redacted
    assert redacted.count("[REDACTED]") == 2


def test_recursively_redacts_secret_keys() -> None:
    value = {"token": "secret-value", "nested": [{"api_key": "key-value"}]}

    assert redact_value(value) == {
        "token": "[REDACTED]",
        "nested": [{"api_key": "[REDACTED]"}],
    }


def test_attachment_is_redacted_and_limited_by_encoded_bytes() -> None:
    attachment = make_attachment(
        "Agent logs", "token=secret-value " + "é" * 200, max_bytes=128
    )

    assert len(attachment.content) <= 128
    assert b"secret-value" not in attachment.content
    assert b"attachment truncated" in attachment.content


def test_classifies_stable_failure_categories() -> None:
    assert classify_exception(AssertionError("bad behavior")) is FailureCategory.PRODUCT
    assert (
        classify_exception(HostUnavailableError("offline"))
        is FailureCategory.INFRASTRUCTURE
    )
    assert (
        classify_exception(HostCleanupError("cleanup failed"))
        is FailureCategory.CLEANUP
    )
