"""The slash-command surface as a typed, callable namespace.

``client.command`` is both callable — ``client.command("/anything")``, the
escape hatch for the full command set — and a namespace of typed shortcuts for
the common ones: ``client.command.pool()``, ``.rl()``, ``.status()``. Each drives
``/v1/command`` (the same dispatch the TUI and REPL use) and returns the
command's text output. For structured data use the typed resources instead
(``client.pool.list()`` vs ``client.command.pool()`` = the human-readable table).
"""

from __future__ import annotations

from collections.abc import Awaitable

from .._base import AsyncBaseClient, BaseClient


def _extract(resp: object) -> str:
    if isinstance(resp, dict):
        return str(resp.get("output", ""))
    return str(resp)


class Commands:
    """Callable namespace of nbot slash-commands (synchronous)."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def __call__(self, line: str) -> str:
        return _extract(self._http.request("POST", "/v1/command", json={"command": line}))

    def status(self) -> str:
        return self("/status")

    def pool(self) -> str:
        return self("/pool")

    def rl(self) -> str:
        return self("/rl")

    def env(self) -> str:
        return self("/env")

    def sessions(self) -> str:
        return self("/sessions")

    def plan(self) -> str:
        return self("/plan")

    def graph(self, nth: int | None = None) -> str:
        return self(f"/graph {nth}" if nth is not None else "/graph")

    def agents(self) -> str:
        return self("/agents")

    def artifacts(self) -> str:
        return self("/artifacts")


class AsyncCommands:
    """Callable namespace of nbot slash-commands (asynchronous)."""

    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    def __call__(self, line: str) -> Awaitable[str]:
        async def run() -> str:
            resp = await self._http.request("POST", "/v1/command", json={"command": line})
            return _extract(resp)

        return run()

    def status(self) -> Awaitable[str]:
        return self("/status")

    def pool(self) -> Awaitable[str]:
        return self("/pool")

    def rl(self) -> Awaitable[str]:
        return self("/rl")

    def env(self) -> Awaitable[str]:
        return self("/env")

    def sessions(self) -> Awaitable[str]:
        return self("/sessions")

    def plan(self) -> Awaitable[str]:
        return self("/plan")

    def graph(self, nth: int | None = None) -> Awaitable[str]:
        return self(f"/graph {nth}" if nth is not None else "/graph")

    def agents(self) -> Awaitable[str]:
        return self("/agents")

    def artifacts(self) -> Awaitable[str]:
        return self("/artifacts")

