"""``ntropi.horizon`` — the eval / observability surface from Python.

Horizon reads nbot's session logs and drives a live nbot serve to train, grade,
and benchmark. When you start it from Python its web UI is live on its port —
the same Horizon you would open normally. This client covers its ``/api/*``
surface: suites, datasets, RL train / env-train (async jobs with live
trajectories), sessions / traces / replay, grades, LLM-judge, review queue.

Phase 0 provides the client shell, health, and auth. Resource namespaces are
filled in Phase 2+.
"""

from __future__ import annotations

import os
from typing import Any, cast

from .._base import BaseClient, _ClientConfig


class Client:
    """Synchronous client for a running Horizon server.

    ``key`` defaults to ``NTROPI_HORIZON_KEY`` (sent as ``X-API-Key``);
    ``admin_token`` (``NTROPI_HORIZON_ADMIN_TOKEN``) is attached for admin routes.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8848",
        *,
        key: str | None = None,
        admin_token: str | None = None,
        timeout: float = 600.0,
    ) -> None:
        headers: dict[str, str] = {}
        token = admin_token or os.environ.get("NTROPI_HORIZON_ADMIN_TOKEN")
        if token:
            headers["X-Admin-Token"] = token
        self._config = _ClientConfig(
            base_url,
            auth_scheme="x-api-key",
            credential=key or os.environ.get("NTROPI_HORIZON_KEY"),
            timeout=timeout,
            extra_headers=headers,
        )
        self._http = BaseClient(self._config)

    def health(self) -> dict[str, Any]:
        """Liveness probe: ``GET /api/health`` (unauthenticated)."""
        return cast("dict[str, Any]", self._http.request("GET", "/api/health"))

    def nbot_status(self) -> dict[str, Any]:
        """Whether Horizon can see a live nbot serve: ``GET /api/nbot``."""
        return cast("dict[str, Any]", self._http.request("GET", "/api/nbot"))

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
