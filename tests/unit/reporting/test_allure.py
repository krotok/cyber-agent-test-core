"""Optional Allure skip-reason adapter tests."""

from types import SimpleNamespace
from typing import Any

from pytest import MonkeyPatch

from cyber_agent_test_core.diagnostics.artifacts import DiagnosticAttachment
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


def test_applies_standard_allure_hierarchy(monkeypatch: MonkeyPatch) -> None:
    calls: list[tuple[str, tuple[Any, ...]]] = []

    class Dynamic:
        def epic(self, value: str) -> None:
            calls.append(("epic", (value,)))

        def feature(self, value: str) -> None:
            calls.append(("feature", (value,)))

        def story(self, value: str) -> None:
            calls.append(("story", (value,)))

        def parent_suite(self, value: str) -> None:
            calls.append(("parent_suite", (value,)))

        def suite(self, value: str) -> None:
            calls.append(("suite", (value,)))

        def sub_suite(self, value: str) -> None:
            calls.append(("sub_suite", (value,)))

        def parameter(self, name: str, value: str) -> None:
            calls.append(("parameter", (name, value)))

    fake = SimpleNamespace(dynamic=Dynamic())
    monkeypatch.setattr(allure_adapter, "_load_allure", lambda: fake)

    allure_adapter.apply_test_metadata(
        {"environment": "stage", "OS": "windows", "Agent version": "4.8.1"},
        feature="Installation",
        story="installs package",
    )

    assert ("epic", ("Cybersecurity Agent",)) in calls
    assert ("parent_suite", ("stage",)) in calls
    assert ("suite", ("windows",)) in calls
    assert ("sub_suite", ("4.8.1",)) in calls


def test_attaches_bounded_diagnostic_and_failure_category(
    monkeypatch: MonkeyPatch,
) -> None:
    attached: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    labels: list[tuple[str, str]] = []
    fake = SimpleNamespace(
        attachment_type=SimpleNamespace(TEXT="text"),
        attach=lambda *args, **kwargs: attached.append((args, kwargs)),
        dynamic=SimpleNamespace(label=lambda *args: labels.append(args)),
    )
    monkeypatch.setattr(allure_adapter, "_load_allure", lambda: fake)

    allure_adapter.attach_diagnostic(DiagnosticAttachment("Agent logs", b"safe"))
    allure_adapter.attach_failure_category("product failure")

    assert attached[0][1]["name"] == "Agent logs"
    assert labels == [("failure_category", "product failure")]
