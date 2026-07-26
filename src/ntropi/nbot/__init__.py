"""``ntropi.nbot`` — the full nbot developer surface from Python.

nbot is the cognitive-compute node, not merely an orchestrator: orchestration is
one layer alongside tools, agents, satellites, the model pool, RL, mesh, and KB.
This wraps everything you can do with it — the HTTP control API, every slash /
utility command, config, projects, and process signals — so the four things a
developer does against the ecosystem are one import away:

- **develop** — projects, config, the model pool, run + stream tasks/sessions
- **teach**   — RL train/checkpoint/feedback, datasets, notes
- **trace**   — sessions, plans, live activity, the route a turn actually took
- **connect** — connectors, blueprints, agents/satellites, mesh

Structured operations get typed methods; the full slash-command set is reachable
through the callable :attr:`Client.command` namespace (``client.command("/x")``
or ``client.command.pool()``), which drives ``/v1/command`` — the same dispatch
the TUI and REPL use. ``Client`` is synchronous; ``AsyncClient`` is its twin.
"""

from __future__ import annotations

import json
import os
from typing import Any, cast

from .._base import AsyncBaseClient, BaseClient, _ClientConfig
from .._exceptions import NtropiError
from .commands import AsyncCommands, Commands
from .config import Config
from .resources import (
    ChatResource,
    ModelsResource,
    PoolResource,
    ProjectsResource,
    SessionsResource,
    TasksResource,
)
from .resources_async import (
    AsyncChatResource,
    AsyncModelsResource,
    AsyncPoolResource,
    AsyncProjectsResource,
    AsyncSessionsResource,
    AsyncTasksResource,
)

__all__ = ["AsyncClient", "Client", "Config", "discover_base_url"]


def discover_base_url(project: str | None) -> str | None:
    """Read ``<project>/.nconfig/control.json`` for the live serve's base_url.

    With no project, tries the current working directory. Returns None when no
    control file is present (no serve advertised yet).
    """
    root = project or os.getcwd()
    path = os.path.join(root, ".nconfig", "control.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    base = data.get("base_url")
    return base if isinstance(base, str) and base else None


def _resolve(base_url: str | None, project: str | None) -> str:
    resolved = base_url or discover_base_url(project)
    if not resolved:
        raise NtropiError(
            "no nbot base_url — pass base_url=, or project= with a live serve "
            "(.nconfig/control.json), or start one via ntropi.Stack"
        )
    return resolved


class Client:
    """Synchronous client for a running nbot serve.

    Construct with an explicit ``base_url`` or a ``project`` to auto-discover it
    from ``control.json``. ``token`` defaults to ``NTROPI_NBOT_TOKEN``.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        project: str | None = None,
        token: str | None = None,
        timeout: float = 600.0,
    ) -> None:
        self._config = _ClientConfig(
            _resolve(base_url, project),
            auth_scheme="bearer",
            credential=token or os.environ.get("NTROPI_NBOT_TOKEN"),
            timeout=timeout,
        )
        self._http = BaseClient(self._config)
        self.command = Commands(self._http)
        self.pool = PoolResource(self._http)
        self.projects = ProjectsResource(self._http)
        self.sessions = SessionsResource(self._http)
        self.tasks = TasksResource(self._http)
        self.chat = ChatResource(self._http)
        self.models = ModelsResource(self._http)

    def health(self) -> dict[str, Any]:
        """Liveness probe: ``GET /v1/health``."""
        return cast("dict[str, Any]", self._http.request("GET", "/v1/health"))

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class AsyncClient:
    """Asynchronous twin of :class:`Client` with an identical surface."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        project: str | None = None,
        token: str | None = None,
        timeout: float = 600.0,
    ) -> None:
        self._config = _ClientConfig(
            _resolve(base_url, project),
            auth_scheme="bearer",
            credential=token or os.environ.get("NTROPI_NBOT_TOKEN"),
            timeout=timeout,
        )
        self._http = AsyncBaseClient(self._config)
        self.command = AsyncCommands(self._http)
        self.pool = AsyncPoolResource(self._http)
        self.projects = AsyncProjectsResource(self._http)
        self.sessions = AsyncSessionsResource(self._http)
        self.tasks = AsyncTasksResource(self._http)
        self.chat = AsyncChatResource(self._http)
        self.models = AsyncModelsResource(self._http)

    async def health(self) -> dict[str, Any]:
        """Liveness probe: ``GET /v1/health``."""
        return cast("dict[str, Any]", await self._http.request("GET", "/v1/health"))

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
