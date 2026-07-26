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

Structured operations get typed methods; anything without a dedicated endpoint is
reachable through :meth:`Client.command` (which drives nbot's ``/v1/command`` —
the same dispatch the TUI and REPL use). Config / lifecycle helpers that need no
running node shell out to the binary.

Phase 0 provides the client shell, health, discovery, and the command
passthrough. Resource namespaces (tasks, chat, sessions, pool, rl, ...) are
filled in Phase 1+.
"""

from __future__ import annotations

import json
import os
from typing import Any, cast

from .._base import BaseClient, _ClientConfig
from .._exceptions import NtropiError
from .resources import (
    PoolResource,
    ProjectsResource,
    SessionsResource,
    TasksResource,
)


def discover_base_url(project: str | None) -> str | None:
    """Read ``<project>/.nconfig/control.json`` for the live serve's base_url.

    With no project, tries the current working directory. Returns None when no
    control file is present (no serve advertised yet).
    """
    root = project or os.getcwd()
    path = os.path.join(root, ".nconfig", "control.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    base = data.get("base_url")
    return base if isinstance(base, str) and base else None


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
        resolved = base_url or discover_base_url(project)
        if not resolved:
            raise NtropiError(
                "no nbot base_url — pass base_url=, or project= with a live "
                "serve (.nconfig/control.json), or start one via ntropi.Stack"
            )
        self._config = _ClientConfig(
            resolved,
            auth_scheme="bearer",
            credential=token or os.environ.get("NTROPI_NBOT_TOKEN"),
            timeout=timeout,
        )
        self._http = BaseClient(self._config)
        self.pool = PoolResource(self._http)
        self.projects = ProjectsResource(self._http)
        self.sessions = SessionsResource(self._http)
        self.tasks = TasksResource(self._http)

    def health(self) -> dict[str, Any]:
        """Liveness probe: ``GET /v1/health``."""
        return cast("dict[str, Any]", self._http.request("GET", "/v1/health"))

    def command(self, line: str) -> str:
        """Run any slash-command through ``/v1/command`` and return its text output.

        The escape hatch that makes the *whole* command surface available before
        (or without) a dedicated typed method — ``client.command("/pool")``,
        ``client.command("/rl")``, ``client.command("/project use ...")``.
        """
        resp = self._http.request("POST", "/v1/command", json={"command": line})
        if isinstance(resp, dict):
            return str(resp.get("output", ""))
        return str(resp)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
