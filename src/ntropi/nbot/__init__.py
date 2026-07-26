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
through the typed :attr:`Client.command` namespace (``client.command.pool()``,
``client.command.rl()``), which drives ``/v1/command`` — the same dispatch
the TUI and REPL use. ``Client`` is synchronous; ``AsyncClient`` is its twin.
"""

from __future__ import annotations

import json
import os
from typing import Any, cast

from .._base import AsyncBaseClient, BaseClient, _ClientConfig
from .._exceptions import NtropiError
from .auth import AsyncAuthResource, AuthResource, activate
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
from .resources_ext import (
    AgentsResource,
    ArtifactsResource,
    BlueprintsResource,
    ConnectorsResource,
    FilesResource,
    KBResource,
    ManifestoResource,
    NotesResource,
    PromptsResource,
    ResearchResource,
    RLResource,
    RoutingResource,
    SatellitesResource,
    TraceResource,
)
from .resources_ext_async import (
    AsyncAgentsResource,
    AsyncArtifactsResource,
    AsyncBlueprintsResource,
    AsyncConnectorsResource,
    AsyncFilesResource,
    AsyncKBResource,
    AsyncManifestoResource,
    AsyncNotesResource,
    AsyncPromptsResource,
    AsyncResearchResource,
    AsyncRLResource,
    AsyncRoutingResource,
    AsyncSatellitesResource,
    AsyncTraceResource,
)

__all__ = ["AsyncClient", "Client", "Config", "activate", "discover_base_url"]


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
        self.auth = AuthResource(self._http)
        self.rl = RLResource(self._http)
        self.blueprints = BlueprintsResource(self._http)
        self.kb = KBResource(self._http)
        self.research = ResearchResource(self._http)
        self.artifacts = ArtifactsResource(self._http)
        self.prompts = PromptsResource(self._http)
        self.notes = NotesResource(self._http)
        self.connectors = ConnectorsResource(self._http)
        self.routing = RoutingResource(self._http)
        self.agents = AgentsResource(self._http)
        self.satellites = SatellitesResource(self._http)
        self.trace = TraceResource(self._http)
        self.files = FilesResource(self._http)
        self.manifesto = ManifestoResource(self._http)

    def health(self) -> dict[str, Any]:
        """Liveness probe: ``GET /v1/health``."""
        return cast("dict[str, Any]", self._http.request("GET", "/v1/health"))

    def plan(self) -> dict[str, Any]:
        """The current execution plan: ``GET /v1/plan``."""
        return cast("dict[str, Any]", self._http.request("GET", "/v1/plan"))

    def autonomy(self) -> dict[str, Any]:
        """Autonomy levels/state: ``GET /v1/autonomy``."""
        return cast("dict[str, Any]", self._http.request("GET", "/v1/autonomy"))

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
        self.auth = AsyncAuthResource(self._http)
        self.rl = AsyncRLResource(self._http)
        self.blueprints = AsyncBlueprintsResource(self._http)
        self.kb = AsyncKBResource(self._http)
        self.research = AsyncResearchResource(self._http)
        self.artifacts = AsyncArtifactsResource(self._http)
        self.prompts = AsyncPromptsResource(self._http)
        self.notes = AsyncNotesResource(self._http)
        self.connectors = AsyncConnectorsResource(self._http)
        self.routing = AsyncRoutingResource(self._http)
        self.agents = AsyncAgentsResource(self._http)
        self.satellites = AsyncSatellitesResource(self._http)
        self.trace = AsyncTraceResource(self._http)
        self.files = AsyncFilesResource(self._http)
        self.manifesto = AsyncManifestoResource(self._http)

    async def health(self) -> dict[str, Any]:
        """Liveness probe: ``GET /v1/health``."""
        return cast("dict[str, Any]", await self._http.request("GET", "/v1/health"))

    async def plan(self) -> dict[str, Any]:
        """The current execution plan: ``GET /v1/plan``."""
        return cast("dict[str, Any]", await self._http.request("GET", "/v1/plan"))

    async def autonomy(self) -> dict[str, Any]:
        """Autonomy levels/state: ``GET /v1/autonomy``."""
        return cast("dict[str, Any]", await self._http.request("GET", "/v1/autonomy"))

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
