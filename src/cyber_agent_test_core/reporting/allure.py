"""Optional Allure adapter; Allure types never cross the public boundary."""

from importlib import import_module
from types import ModuleType


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
