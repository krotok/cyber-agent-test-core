"""Optional Allure adapter; Allure types never cross the public boundary."""

from importlib import import_module
from types import ModuleType
from typing import Any

from cyber_agent_test_core.diagnostics.artifacts import DiagnosticAttachment


def _load_allure() -> ModuleType | None:
    """Load Allure only when the optional integration is installed."""
    try:
        return import_module("allure")
    except ModuleNotFoundError:
        return None


def attach_skip_reason(reason: str) -> None:
    """Attach a capability skip explanation without affecting test behavior."""
    allure = _load_allure()
    if allure is None:
        return
    attachment_type = allure.attachment_type.TEXT
    allure.attach(
        reason,
        name="Capability skip reason",
        attachment_type=attachment_type,
    )


def apply_test_metadata(
    parameters: dict[str, str],
    *,
    feature: str,
    story: str,
) -> None:
    """Apply the standard hierarchy and reproducibility parameters."""
    allure = _load_allure()
    if allure is None:
        return
    dynamic = allure.dynamic
    dynamic.epic("Cybersecurity Agent")
    dynamic.feature(feature)
    dynamic.story(story)
    dynamic.parent_suite(parameters["environment"])
    dynamic.suite(parameters["OS"])
    dynamic.sub_suite(parameters["Agent version"])
    for name, value in parameters.items():
        dynamic.parameter(name, value)


def attach_diagnostic(attachment: DiagnosticAttachment) -> None:
    """Attach an already redacted and bounded artifact when Allure is installed."""
    allure = _load_allure()
    if allure is None:
        return
    attachment_type: Any = allure.attachment_type.TEXT
    allure.attach(
        attachment.content,
        name=attachment.name,
        attachment_type=attachment_type,
    )


def attach_failure_category(category: str) -> None:
    """Expose the stable failure category as an Allure label."""
    allure = _load_allure()
    if allure is not None:
        allure.dynamic.label("failure_category", category)
