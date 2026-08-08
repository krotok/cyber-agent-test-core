"""Transport model and fake implementation tests."""

from pathlib import Path

import pytest

from cyber_agent_test_core.transports import (
    CommandResult,
    CommandSpec,
    FakeTransport,
    HostUnavailableError,
    TransportType,
)


def test_command_result_contains_required_metadata() -> None:
    result = CommandResult(
        exit_code=7,
        stdout="out",
        stderr="err",
        duration=0.25,
        host="synthetic-host",
        redacted_command="synthetic-command <redacted>",
        transport_type=TransportType.FAKE,
    )

    assert result.exit_code == 7
    assert result.stdout == "out"
    assert result.stderr == "err"
    assert result.duration == 0.25
    assert result.host == "synthetic-host"
    assert result.redacted_command == "synthetic-command <redacted>"
    assert result.transport_type is TransportType.FAKE


def test_command_models_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="argv"):
        CommandSpec((), "display")
    with pytest.raises(ValueError, match="duration"):
        CommandResult(0, "", "", -1, "host", "command", TransportType.FAKE)


def test_fake_transport_records_operations(tmp_path: Path) -> None:
    transport = FakeTransport()
    command = CommandSpec(("program", "argument"), "program <redacted>")
    transport.queue_result(stdout="synthetic output", duration=0.5)
    transport.connect()

    result = transport.execute(command)
    transport.upload(tmp_path / "local", "/synthetic/remote")
    transport.download("/synthetic/remote", tmp_path / "download")

    assert result.stdout == "synthetic output"
    assert result.redacted_command == "program <redacted>"
    assert transport.commands == [command]
    assert transport.uploads == [(tmp_path / "local", "/synthetic/remote")]
    assert transport.downloads == [
        ("/synthetic/remote", tmp_path / "download")
    ]


def test_fake_transport_requires_connection() -> None:
    transport = FakeTransport()

    with pytest.raises(HostUnavailableError):
        transport.execute(CommandSpec(("program",), "program"))
