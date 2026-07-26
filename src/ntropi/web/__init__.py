"""``ntropi.web`` — the NBotWeb chat-app gateway from Python.

NBotWeb is the front door for building chat applications: a FastAPI server with
its own web server, channel integrations (Telegram / WhatsApp / MCP), auth +
RBAC, that proxies the nbot node. Because it is already Python and owns a web
server, ``ntropi.web`` both launches it (pointed at the nbot instance ntropi
started, via :func:`ntropi.serve_web`) and gives a client to its ``/api/v1/*``
surface for programmatic control.

    import ntropi

    w = ntropi.web.Client("http://127.0.0.1:8080", key="…")
    print(w.health())
    w.tasks.submit("summarise report.pdf", new_session=True)
    key = w.admin.keys.create("mobile-app")   # secret returned once

``Client`` is synchronous; ``AsyncClient`` is its twin with an identical
surface. Admin routes accept either an admin session or an ``admin_token``
(``NTROPI_WEB_ADMIN_TOKEN``); on localhost with no token configured the gateway
treats the caller as admin.
"""

from __future__ import annotations

import os
from typing import Any, cast

from .._base import AsyncBaseClient, BaseClient, _ClientConfig
from .resources import (
    AdaptersResource,
    AdminResource,
    AuthResource,
    BlueprintsResource,
    ChatResource,
    ReadResource,
    TasksResource,
)
from .resources_async import (
    AsyncAdaptersResource,
    AsyncAdminResource,
    AsyncAuthResource,
    AsyncBlueprintsResource,
    AsyncChatResource,
    AsyncReadResource,
    AsyncTasksResource,
)

__all__ = ["AsyncClient", "Client"]


def _headers(admin_token: str | None) -> dict[str, str]:
    token = admin_token or os.environ.get("NTROPI_WEB_ADMIN_TOKEN")
    return {"X-Admin-Token": token} if token else {}


class Client:
    """Synchronous client for a running NBotWeb gateway.

    ``key`` defaults to ``NTROPI_WEB_KEY`` (sent as a bearer token; the gateway
    also accepts it as ``X-API-Key``). On loopback with no API keys created the
    gateway runs open, so a local dev client needs no key at all.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        *,
        key: str | None = None,
        admin_token: str | None = None,
        timeout: float = 600.0,
    ) -> None:
        self._config = _ClientConfig(
            base_url,
            auth_scheme="bearer",
            credential=key or os.environ.get("NTROPI_WEB_KEY"),
            timeout=timeout,
            extra_headers=_headers(admin_token),
        )
        self._http = BaseClient(self._config)
        self.auth = AuthResource(self._http)
        self.tasks = TasksResource(self._http)
        self.chat = ChatResource(self._http)
        self.read = ReadResource(self._http)
        self.blueprints = BlueprintsResource(self._http)
        self.adapters = AdaptersResource(self._http)
        self.admin = AdminResource(self._http)

    def health(self) -> dict[str, Any]:
        """Gateway + upstream nbot health: ``GET /api/v1/health``."""
        return cast("dict[str, Any]", self._http.request("GET", "/api/v1/health"))

    def me(self) -> dict[str, Any]:
        """Current principal — shorthand for ``auth.me()``."""
        return self.auth.me()

    def command(self, command: str) -> dict[str, Any]:
        """Run a slash-command through the gateway (``POST /api/v1/command``)."""
        return cast(
            "dict[str, Any]",
            self._http.request("POST", "/api/v1/command", json={"command": command}),
        )

    def mcp(self, method: str, params: dict[str, Any] | None = None, *, id: int = 1) -> dict[str, Any]:
        """JSON-RPC MCP call (``tools/list`` / ``tools/call``): ``POST /api/v1/mcp``."""
        body = {"id": id, "method": method, "params": params or {}}
        return cast("dict[str, Any]", self._http.request("POST", "/api/v1/mcp", json=body))

    def proxy(self, method: str, path: str, **kwargs: Any) -> Any:
        """Transparent passthrough to the upstream nbot control API (``/proxy/{path}``)."""
        return self._http.request(method, f"/proxy/{path.lstrip('/')}", **kwargs)

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
        base_url: str = "http://127.0.0.1:8080",
        *,
        key: str | None = None,
        admin_token: str | None = None,
        timeout: float = 600.0,
    ) -> None:
        self._config = _ClientConfig(
            base_url,
            auth_scheme="bearer",
            credential=key or os.environ.get("NTROPI_WEB_KEY"),
            timeout=timeout,
            extra_headers=_headers(admin_token),
        )
        self._http = AsyncBaseClient(self._config)
        self.auth = AsyncAuthResource(self._http)
        self.tasks = AsyncTasksResource(self._http)
        self.chat = AsyncChatResource(self._http)
        self.read = AsyncReadResource(self._http)
        self.blueprints = AsyncBlueprintsResource(self._http)
        self.adapters = AsyncAdaptersResource(self._http)
        self.admin = AsyncAdminResource(self._http)

    async def health(self) -> dict[str, Any]:
        return cast("dict[str, Any]", await self._http.request("GET", "/api/v1/health"))

    async def me(self) -> dict[str, Any]:
        return await self.auth.me()

    async def command(self, command: str) -> dict[str, Any]:
        return cast(
            "dict[str, Any]",
            await self._http.request("POST", "/api/v1/command", json={"command": command}),
        )

    async def mcp(
        self, method: str, params: dict[str, Any] | None = None, *, id: int = 1
    ) -> dict[str, Any]:
        body = {"id": id, "method": method, "params": params or {}}
        return cast("dict[str, Any]", await self._http.request("POST", "/api/v1/mcp", json=body))

    async def proxy(self, method: str, path: str, **kwargs: Any) -> Any:
        return await self._http.request(method, f"/proxy/{path.lstrip('/')}", **kwargs)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
