"""Optional Allure skip-reason adapter tests."""

from types import SimpleNamespace
from typing import Any

from pytest import MonkeyPatch

from cyber_agent_test_core.reporting import allure as allure_adapter


def test_allure_absence_does_not_change_behavior(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(allure_adapter, "_load_allure", lambda: None)

    allure_adapter.attach_skip_reason("synthetic reason")


def test_attaches_exact_skip_reason(monkeypatch: MonkeyPatch) -> None:
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    fake = SimpleNamespace(
        attachment_type=SimpleNamespace(TEXT="text"),
        attach=lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    monkeypatch.setattr(allure_adapter, "_load_allure", lambda: fake)

    allure_adapter.attach_skip_reason("synthetic reason")

    assert calls == [
        (
            ("synthetic reason",),
            {"name": "Capability skip reason", "attachment_type": "text"},
        )
    ]
