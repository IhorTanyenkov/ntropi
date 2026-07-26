"""Phase-2b tests — launch/runtime wiring, without spawning real binaries.

find_binary resolution is tested directly; the spawn path is tested by stubbing
ServiceProcess so we verify argv, health wiring, client construction, and that a
Stack stops only what it started."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

import ntropi
from ntropi import _launch
from ntropi._exceptions import ServiceStartError
from ntropi._runtime import find_binary


def test_find_binary_explicit_env_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake = tmp_path / "nbot"
    fake.write_text("#!/bin/sh\n")
    assert find_binary(str(fake), "X", "nbot") == str(fake)
    monkeypatch.setenv("NTROPI_NBOT_BIN", str(fake))
    assert find_binary(None, "NTROPI_NBOT_BIN", "nbot") == str(fake)
    monkeypatch.delenv("NTROPI_NBOT_BIN", raising=False)
    with pytest.raises(ServiceStartError):
        find_binary(None, "NTROPI_NBOT_BIN", "definitely-not-a-real-binary-xyz")


class _StubProc:
    """Records argv and pretends to be an already-healthy process."""

    instances: ClassVar[list[_StubProc]] = []

    def __init__(self, **kw: object) -> None:
        self.kw = kw
        self.stopped = False
        _StubProc.instances.append(self)

    def start(self) -> _StubProc:
        return self

    def stop(self) -> None:
        self.stopped = True


def test_launch_wires_and_owns_processes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _StubProc.instances.clear()
    # a discoverable control.json so nbot.Client(project=...) constructs
    nconf = tmp_path / ".nconfig"
    nconf.mkdir()
    (nconf / "control.json").write_text('{"base_url": "http://127.0.0.1:9991"}')

    monkeypatch.setattr(_launch, "ServiceProcess", _StubProc)
    monkeypatch.setattr(_launch, "find_binary", lambda *a, **k: "/usr/bin/fake")

    stack = ntropi.launch(str(tmp_path), horizon_port=8899)
    assert stack.nbot is not None
    assert stack.horizon is not None

    # nbot argv: nbot --config <cfg> serve
    nbot_argv = list(_StubProc.instances[0].kw["argv"])  # type: ignore[arg-type]
    assert nbot_argv[0] == "/usr/bin/fake"
    assert "serve" in nbot_argv and "--config" in nbot_argv
    # horizon argv: --project <p> --port 8899
    hz_argv = list(_StubProc.instances[1].kw["argv"])  # type: ignore[arg-type]
    assert "--port" in hz_argv and "8899" in hz_argv
    assert "--project" in hz_argv

    stack.close()
    assert all(p.stopped for p in _StubProc.instances)


def test_launch_without_horizon(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _StubProc.instances.clear()
    nconf = tmp_path / ".nconfig"
    nconf.mkdir()
    (nconf / "control.json").write_text('{"base_url": "http://127.0.0.1:9991"}')
    monkeypatch.setattr(_launch, "ServiceProcess", _StubProc)
    monkeypatch.setattr(_launch, "find_binary", lambda *a, **k: "/usr/bin/fake")

    stack = ntropi.launch(str(tmp_path), with_horizon=False)
    assert stack.horizon is None
    assert len(_StubProc.instances) == 1
    stack.close()
