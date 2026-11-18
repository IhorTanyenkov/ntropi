"""Async jobs — the polling surface for long-running work.

Horizon's ``rl/train``, ``rl/env-train`` and session ``replay`` (and nbot's
``rl/replay``) return ``{job_id, status_url}`` and run detached. ``Job`` wraps
one: poll its status, block until it finishes, stream its live trajectory as it
grows, or pause / resume / stop it cooperatively.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

from ._base import AsyncBaseClient, BaseClient
from ._exceptions import NtropiError

# ``outcome_unknown``: Horizon lost a downstream acknowledgement and cannot say
# whether the work was applied. Polling will never resolve it, so waits and
# streams end there — but it is neither success nor failure, and nothing here
# resubmits the work.
OUTCOME_UNKNOWN = "outcome_unknown"
TERMINAL = frozenset({"done", "error", "stopped", "completed", "failed", "interrupted", OUTCOME_UNKNOWN})


class Job:
    """A running Horizon job, addressed by id.

    ``base`` is the job route prefix (default ``/api/jobs``). ``status()`` fetches
    the full document; ``wait()`` blocks to a terminal state; ``stream()`` yields
    new trajectory points as the job produces them.
    """

    def __init__(self, http: BaseClient, job_id: str, *, base: str = "/api/jobs") -> None:
        self._http = http
        self.id = job_id
        self._base = base

    def status(self) -> dict[str, Any]:
        data = self._http.request("GET", f"{self._base}/{self.id}")
        if not isinstance(data, dict):
            raise NtropiError(f"unexpected job payload for {self.id}")
        return data

    @property
    def _is_terminal(self) -> bool:
        return str(self.status().get("status", "")) in TERMINAL

    def wait(self, *, timeout: float | None = None, poll: float = 1.0) -> dict[str, Any]:
        """Block until the job reaches a terminal state; return the final document.

        A document whose ``status`` is ``outcome_unknown`` is returned as-is:
        check ``status`` before treating the result as applied.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            doc = self.status()
            if str(doc.get("status", "")) in TERMINAL:
                return doc
            if deadline is not None and time.monotonic() >= deadline:
                raise NtropiError(f"job {self.id} did not finish in {timeout}s")
            time.sleep(poll)

    def trajectory(self) -> list[dict[str, Any]]:
        """The trajectory points recorded so far (env-train)."""
        traj = self.status().get("trajectory", [])
        return traj if isinstance(traj, list) else []

    def stream(self, *, poll: float = 1.0) -> Any:
        """Yield trajectory points as they appear, ending when the job terminates."""
        seen = 0
        while True:
            doc = self.status()
            traj = doc.get("trajectory", [])
            if isinstance(traj, list) and len(traj) > seen:
                yield from traj[seen:]
                seen = len(traj)
            if str(doc.get("status", "")) in TERMINAL:
                return
            time.sleep(poll)

    def pause(self) -> dict[str, Any]:
        return self._control("pause")

    def resume(self) -> dict[str, Any]:
        return self._control("resume")

    def stop(self) -> dict[str, Any]:
        return self._control("stop")

    def _control(self, action: str) -> dict[str, Any]:
        data = self._http.request("POST", f"{self._base}/{self.id}/{action}")
        return data if isinstance(data, dict) else {"ok": True}


class AsyncJob:
    """Asynchronous twin of :class:`Job` with an identical surface."""

    def __init__(self, http: AsyncBaseClient, job_id: str, *, base: str = "/api/jobs") -> None:
        self._http = http
        self.id = job_id
        self._base = base

    async def status(self) -> dict[str, Any]:
        data = await self._http.request("GET", f"{self._base}/{self.id}")
        if not isinstance(data, dict):
            raise NtropiError(f"unexpected job payload for {self.id}")
        return data

    async def wait(self, *, timeout: float | None = None, poll: float = 1.0) -> dict[str, Any]:
        """Await until the job reaches a terminal state; return the final document.

        A document whose ``status`` is ``outcome_unknown`` is returned as-is:
        check ``status`` before treating the result as applied.
        """
        import asyncio

        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            doc = await self.status()
            if str(doc.get("status", "")) in TERMINAL:
                return doc
            if deadline is not None and time.monotonic() >= deadline:
                raise NtropiError(f"job {self.id} did not finish in {timeout}s")
            await asyncio.sleep(poll)

    async def trajectory(self) -> list[dict[str, Any]]:
        traj = (await self.status()).get("trajectory", [])
        return traj if isinstance(traj, list) else []

    async def stream(self, *, poll: float = 1.0) -> AsyncIterator[dict[str, Any]]:
        """Yield trajectory points as they appear, ending when the job terminates."""
        import asyncio

        seen = 0
        while True:
            doc = await self.status()
            traj = doc.get("trajectory", [])
            if isinstance(traj, list) and len(traj) > seen:
                for point in traj[seen:]:
                    yield point
                seen = len(traj)
            if str(doc.get("status", "")) in TERMINAL:
                return
            await asyncio.sleep(poll)

    async def pause(self) -> dict[str, Any]:
        return await self._control("pause")

    async def resume(self) -> dict[str, Any]:
        return await self._control("resume")

    async def stop(self) -> dict[str, Any]:
        return await self._control("stop")

    async def _control(self, action: str) -> dict[str, Any]:
        data = await self._http.request("POST", f"{self._base}/{self.id}/{action}")
        return data if isinstance(data, dict) else {"ok": True}
