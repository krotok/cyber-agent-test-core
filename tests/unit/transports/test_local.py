"""Local transport tests with no real process execution."""

import subprocess
from pathlib import Path

import pytest

from cyber_agent_test_core.transports import (
    CommandSpec,
    CommandTimeoutError,
    LocalTransport,
    TransportType,
)


def test_local_execute_uses_argv_without_shell() -> None:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args[0], 0, stdout="out", stderr="")

    transport = LocalTransport(host="synthetic-local", runner=runner)
    transport.connect()
    result = transport.execute(
        CommandSpec(("program", "literal argument"), "program <redacted>"),
        timeout_seconds=3,
    )

    assert calls[0][0][0] == ("program", "literal argument")
    assert calls[0][1]["shell"] is False
    assert result.transport_type is TransportType.LOCAL
    assert result.host == "synthetic-local"


def test_local_timeout_is_not_retryable() -> None:
    def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        raise subprocess.TimeoutExpired(args[0], 1)

    transport = LocalTransport(runner=runner)
    transport.connect()

    with pytest.raises(CommandTimeoutError) as captured:
        transport.execute(CommandSpec(("program",), "program"), timeout_seconds=1)

    assert not captured.value.retryable


def test_local_file_transfer(tmp_path: Path) -> None:
    source = tmp_path / "source"
    remote = tmp_path / "remote"
    downloaded = tmp_path / "downloaded"
    source.write_text("synthetic", encoding="utf-8")
    transport = LocalTransport()
    transport.connect()

    transport.upload(source, str(remote))
    transport.download(str(remote), downloaded)

    assert downloaded.read_text(encoding="utf-8") == "synthetic"
