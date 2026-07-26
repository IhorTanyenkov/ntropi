"""Process lifecycle for the stack.

ntropi can either *start* a service (spawn its binary / app and wait for health)
or *connect* to one already running. ``ServiceProcess`` wraps a spawned process
with a health probe and teardown; ``Stack`` composes the three services and only
ever stops what it started — a connected service is left running on exit.

Binaries are located by explicit path, then env var, then PATH. ntropi never
bundles the C++ binaries (nbot, nbot-horizon); it drives whatever is installed.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from ._exceptions import ServiceStartError


def find_binary(explicit: str | None, env_var: str, *names: str) -> str:
    """Resolve a binary path: explicit arg, then ``env_var``, then PATH names."""
    if explicit:
        return explicit
    from_env = os.environ.get(env_var)
    if from_env:
        return from_env
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    raise ServiceStartError(
        f"could not find {' / '.join(names)} — install it or set {env_var} "
        f"or pass an explicit path"
    )


@dataclass
class ServiceProcess:
    """A spawned service process with a health gate.

    ``health`` returns True once the service is ready. ``start`` blocks until it
    does or raises ``ServiceStartError`` after ``timeout`` seconds.
    """

    argv: Sequence[str]
    health: Callable[[], bool]
    name: str
    cwd: str | None = None
    env: dict[str, str] | None = None
    log_path: str | None = None
    timeout: float = 180.0
    _proc: subprocess.Popen[bytes] | None = field(default=None, init=False, repr=False)

    def start(self) -> ServiceProcess:
        if self.health():
            return self
        out = open(self.log_path, "ab") if self.log_path else subprocess.DEVNULL  # noqa: SIM115
        self._proc = subprocess.Popen(
            list(self.argv),
            cwd=self.cwd,
            env={**os.environ, **(self.env or {})},
            stdout=out,
            stderr=out,
            start_new_session=True,
        )
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                raise ServiceStartError(
                    f"{self.name} exited during startup (code {self._proc.returncode})"
                )
            if self.health():
                return self
            time.sleep(0.5)
        self.stop()
        raise ServiceStartError(f"{self.name} did not become healthy in {self.timeout}s")

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                os.killpg(os.getpgid(self._proc.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(self._proc.pid), signal.SIGKILL)
        self._proc = None

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None
