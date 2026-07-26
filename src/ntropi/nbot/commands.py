"""The slash-command surface as a typed namespace.

Every nbot slash-command is a method on ``client.command`` —
``client.command.pool()``, ``.rl()``, ``.project.use(path)`` — each driving
``/v1/command`` (the same dispatch the TUI and REPL use) and returning the
command's text output. There is deliberately no string passthrough: a bare
string is a *message* to the model (send it with ``client.tasks.submit`` /
``client.chat``), not a command. For structured data use the typed resources
(``client.pool.list()``) rather than the command's human-readable text.

``Commands`` is synchronous; ``AsyncCommands`` is its twin (each method returns
an awaitable). Command names with aliases in nbot use their canonical form here
(``blueprint`` not ``bp``, ``satellites`` not ``sat``).
"""

from __future__ import annotations

from collections.abc import Awaitable

from .._base import AsyncBaseClient, BaseClient


def _line(name: str, arg: str = "") -> str:
    return f"/{name} {arg}".strip()


def _text(resp: object) -> str:
    if isinstance(resp, dict):
        return str(resp.get("output", ""))
    return str(resp)


class Commands:
    """All nbot slash-commands as typed methods (synchronous)."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def _run(self, line: str) -> str:
        return _text(self._http.request("POST", "/v1/command", json={"command": line}))

    # --- state / inspection ---
    def status(self) -> str:
        return self._run("/status")

    def pool(self) -> str:
        return self._run("/pool")

    def rl(self) -> str:
        return self._run("/rl")

    def env(self) -> str:
        return self._run("/env")

    def plan(self) -> str:
        return self._run("/plan")

    def graph(self, nth: int | None = None) -> str:
        return self._run(_line("graph", str(nth) if nth is not None else ""))

    def agents(self) -> str:
        return self._run("/agents")

    def artifacts(self) -> str:
        return self._run("/artifacts")

    def identity(self) -> str:
        return self._run("/identity")

    def help(self) -> str:
        return self._run("/help")

    # --- sessions ---
    def sessions(self) -> str:
        return self._run("/sessions")

    def session(self) -> str:
        return self._run("/session")

    def new(self, name: str = "") -> str:
        return self._run(_line("new", name))

    def load(self, session_id: str) -> str:
        return self._run(_line("load", session_id))

    def clear(self) -> str:
        return self._run("/clear")

    # --- manifesto ---
    def manifesto(self) -> str:
        return self._run("/manifesto")

    def manifesto_core(self) -> str:
        return self._run("/manifesto_core")

    def manifesto_project(self) -> str:
        return self._run("/manifesto_project")

    # --- notes / kb / research / blueprints / satellites ---
    def notes(self) -> str:
        return self._run("/notes")

    def note(self, text: str) -> str:
        return self._run(_line("note", text))

    def kb(self, args: str = "") -> str:
        return self._run(_line("kb", args))

    def research(self, args: str = "") -> str:
        return self._run(_line("research", args))

    def blueprint(self, args: str = "") -> str:
        return self._run(_line("blueprint", args))

    def satellites(self, args: str = "") -> str:
        return self._run(_line("satellites", args))

    def attach(self, path: str) -> str:
        return self._run(_line("attach", path))

    # --- projects ---
    def projects(self) -> str:
        return self._run("/projects")

    def project(self, args: str = "") -> str:
        return self._run(_line("project", args))

    def use_project(self, path: str) -> str:
        return self._run(_line("use_project", path))

    def new_project(self, path: str) -> str:
        return self._run(_line("new_project", path))

    def open_project(self, path: str) -> str:
        return self._run(_line("open_project", path))

    def add_project(self, path: str) -> str:
        return self._run(_line("add_project", path))

    def add_project_directory(self, path: str) -> str:
        return self._run(_line("add_project_directory", path))

    def archive_project(self, name: str) -> str:
        return self._run(_line("archive_project", name))

    def export_project(self, args: str = "") -> str:
        return self._run(_line("export_project", args))

    def import_project(self, args: str = "") -> str:
        return self._run(_line("import_project", args))

    # --- mesh / peers ---
    def mesh(self, args: str = "") -> str:
        return self._run(_line("mesh", args))

    def peers(self) -> str:
        return self._run("/peers")

    def nbots(self) -> str:
        return self._run("/nbots")

    def add_nbot(self, address: str) -> str:
        return self._run(_line("add_nbot", address))

    def remove_nbot(self, node_id: str) -> str:
        return self._run(_line("remove_nbot", node_id))

    # --- modes ---
    def assume(self) -> str:
        return self._run("/assume")

    def hypothesis(self) -> str:
        return self._run("/hypothesis")

    # --- rl / license / misc ---
    def rl_reset(self) -> str:
        return self._run("/rl-reset")

    def whoami(self) -> str:
        return self._run("/whoami")

    def license(self) -> str:
        return self._run("/license")

    def allow_restricted(self) -> str:
        return self._run("/allow-restricted")

    def init(self) -> str:
        return self._run("/init")

    def satellite(self, args: str = "") -> str:
        return self._run(_line("satellite", args))


class AsyncCommands:
    """All nbot slash-commands as typed methods (asynchronous)."""

    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    def _run(self, line: str) -> Awaitable[str]:
        async def go() -> str:
            resp = await self._http.request("POST", "/v1/command", json={"command": line})
            return _text(resp)

        return go()

    def status(self) -> Awaitable[str]:
        return self._run("/status")

    def pool(self) -> Awaitable[str]:
        return self._run("/pool")

    def rl(self) -> Awaitable[str]:
        return self._run("/rl")

    def env(self) -> Awaitable[str]:
        return self._run("/env")

    def plan(self) -> Awaitable[str]:
        return self._run("/plan")

    def graph(self, nth: int | None = None) -> Awaitable[str]:
        return self._run(_line("graph", str(nth) if nth is not None else ""))

    def agents(self) -> Awaitable[str]:
        return self._run("/agents")

    def artifacts(self) -> Awaitable[str]:
        return self._run("/artifacts")

    def identity(self) -> Awaitable[str]:
        return self._run("/identity")

    def help(self) -> Awaitable[str]:
        return self._run("/help")

    def sessions(self) -> Awaitable[str]:
        return self._run("/sessions")

    def session(self) -> Awaitable[str]:
        return self._run("/session")

    def new(self, name: str = "") -> Awaitable[str]:
        return self._run(_line("new", name))

    def load(self, session_id: str) -> Awaitable[str]:
        return self._run(_line("load", session_id))

    def clear(self) -> Awaitable[str]:
        return self._run("/clear")

    def manifesto(self) -> Awaitable[str]:
        return self._run("/manifesto")

    def manifesto_core(self) -> Awaitable[str]:
        return self._run("/manifesto_core")

    def manifesto_project(self) -> Awaitable[str]:
        return self._run("/manifesto_project")

    def notes(self) -> Awaitable[str]:
        return self._run("/notes")

    def note(self, text: str) -> Awaitable[str]:
        return self._run(_line("note", text))

    def kb(self, args: str = "") -> Awaitable[str]:
        return self._run(_line("kb", args))

    def research(self, args: str = "") -> Awaitable[str]:
        return self._run(_line("research", args))

    def blueprint(self, args: str = "") -> Awaitable[str]:
        return self._run(_line("blueprint", args))

    def satellites(self, args: str = "") -> Awaitable[str]:
        return self._run(_line("satellites", args))

    def attach(self, path: str) -> Awaitable[str]:
        return self._run(_line("attach", path))

    def projects(self) -> Awaitable[str]:
        return self._run("/projects")

    def project(self, args: str = "") -> Awaitable[str]:
        return self._run(_line("project", args))

    def use_project(self, path: str) -> Awaitable[str]:
        return self._run(_line("use_project", path))

    def new_project(self, path: str) -> Awaitable[str]:
        return self._run(_line("new_project", path))

    def open_project(self, path: str) -> Awaitable[str]:
        return self._run(_line("open_project", path))

    def add_project(self, path: str) -> Awaitable[str]:
        return self._run(_line("add_project", path))

    def add_project_directory(self, path: str) -> Awaitable[str]:
        return self._run(_line("add_project_directory", path))

    def archive_project(self, name: str) -> Awaitable[str]:
        return self._run(_line("archive_project", name))

    def export_project(self, args: str = "") -> Awaitable[str]:
        return self._run(_line("export_project", args))

    def import_project(self, args: str = "") -> Awaitable[str]:
        return self._run(_line("import_project", args))

    def mesh(self, args: str = "") -> Awaitable[str]:
        return self._run(_line("mesh", args))

    def peers(self) -> Awaitable[str]:
        return self._run("/peers")

    def nbots(self) -> Awaitable[str]:
        return self._run("/nbots")

    def add_nbot(self, address: str) -> Awaitable[str]:
        return self._run(_line("add_nbot", address))

    def remove_nbot(self, node_id: str) -> Awaitable[str]:
        return self._run(_line("remove_nbot", node_id))

    def assume(self) -> Awaitable[str]:
        return self._run("/assume")

    def hypothesis(self) -> Awaitable[str]:
        return self._run("/hypothesis")

    def rl_reset(self) -> Awaitable[str]:
        return self._run("/rl-reset")

    def whoami(self) -> Awaitable[str]:
        return self._run("/whoami")

    def license(self) -> Awaitable[str]:
        return self._run("/license")

    def allow_restricted(self) -> Awaitable[str]:
        return self._run("/allow-restricted")

    def init(self) -> Awaitable[str]:
        return self._run("/init")

    def satellite(self, args: str = "") -> Awaitable[str]:
        return self._run(_line("satellite", args))
