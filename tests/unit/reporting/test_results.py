"""Allure result merge tests."""

from pathlib import Path

from cyber_agent_test_core.reporting.results import merge_allure_results


def test_merges_jobs_without_overwriting_name_collisions(tmp_path: Path) -> None:
    first = tmp_path / "job-1"
    second = tmp_path / "job-2"
    output = tmp_path / "merged"
    first.mkdir()
    second.mkdir()
    (first / "result.json").write_text("first", encoding="utf-8")
    (second / "result.json").write_text("second", encoding="utf-8")

    copied = merge_allure_results((first, second), output)

    assert copied == 2
    assert sorted(path.read_text(encoding="utf-8") for path in output.iterdir()) == [
        "first",
        "second",
    ]
