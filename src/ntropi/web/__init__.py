"""``ntropi.web`` — the NBotWeb chat-app gateway from Python.

NBotWeb is the front door for building chat applications: a FastAPI server with
its own web server, integrations (Telegram / WhatsApp / MCP / generic adapters),
auth + RBAC, that proxies the nbot node. Because it is already Python and owns a
web server, ``ntropi.web`` both launches it (pointed at the nbot instance ntropi
started) and gives a client to its ``/api/v1/*`` surface for programmatic control
(users, keys, projects, adapters).

Phase 0 provides the client shell. Launch integration and the ``/api/v1/*``
resource methods land in Phase 4.
"""

from __future__ import annotations

import os
from typing import Any, cast

from .._base import BaseClient, _ClientConfig


class Client:
    """Synchronous client for a running NBotWeb gateway.

    ``key`` defaults to ``NTROPI_WEB_KEY`` (sent as a bearer token; NBotWeb also
    accepts it as an API key).
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        key: str | None = None,
        timeout: float = 600.0,
    ) -> None:
        self._config = _ClientConfig(
            base_url,
            auth_scheme="bearer",
            credential=key or os.environ.get("NTROPI_WEB_KEY"),
            timeout=timeout,
        )
        self._http = BaseClient(self._config)

    def health(self) -> dict[str, Any]:
        """Gateway + upstream health: ``GET /api/v1/health``."""
        return cast("dict[str, Any]", self._http.request("GET", "/api/v1/health"))

    def me(self) -> dict[str, Any]:
        """Current principal (role, projects): ``GET /api/v1/auth/me``."""
        return cast("dict[str, Any]", self._http.request("GET", "/api/v1/auth/me"))

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
