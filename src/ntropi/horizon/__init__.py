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

from .._base import AsyncBaseClient, BaseClient, _ClientConfig, resolve_credential
from .resources import (
    DatasetsResource,
    GradesResource,
    JobsResource,
    PromptsResource,
    ReviewResource,
    RLResource,
    RoutingResource,
    SessionsResource,
    SuitesResource,
    TrainersResource,
)
from .resources_async import (
    AsyncDatasetsResource,
    AsyncGradesResource,
    AsyncJobsResource,
    AsyncPromptsResource,
    AsyncReviewResource,
    AsyncRLResource,
    AsyncRoutingResource,
    AsyncSessionsResource,
    AsyncSuitesResource,
    AsyncTrainersResource,
)

__all__ = ["AsyncClient", "Client"]


class Client:
    """Synchronous client for a running Horizon server.

    ``key`` defaults to ``NTROPI_HORIZON_KEY``, then the shared platform key
    ``NTROPI_API_KEY`` (one key across nbot, Horizon and the SDK), sent as
    ``X-API-Key``. ``admin_token`` (``NTROPI_HORIZON_ADMIN_TOKEN``) is a distinct,
    higher-privilege credential for admin routes and is not collapsed into the
    platform key.
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
            credential=resolve_credential(key, "NTROPI_HORIZON_KEY", "NTROPI_API_KEY"),
            timeout=timeout,
            extra_headers=headers,
        )
        self._http = BaseClient(self._config)
        self.suites = SuitesResource(self._http)
        self.sessions = SessionsResource(self._http)
        self.datasets = DatasetsResource(self._http)
        self.rl = RLResource(self._http)
        self.routing = RoutingResource(self._http)
        self.prompts = PromptsResource(self._http)
        self.grades = GradesResource(self._http)
        self.review = ReviewResource(self._http)
        self.trainers = TrainersResource(self._http)
        self.jobs = JobsResource(self._http)

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


class AsyncClient:
    """Asynchronous twin of :class:`Client` with an identical surface."""

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
            credential=resolve_credential(key, "NTROPI_HORIZON_KEY", "NTROPI_API_KEY"),
            timeout=timeout,
            extra_headers=headers,
        )
        self._http = AsyncBaseClient(self._config)
        self.suites = AsyncSuitesResource(self._http)
        self.sessions = AsyncSessionsResource(self._http)
        self.datasets = AsyncDatasetsResource(self._http)
        self.rl = AsyncRLResource(self._http)
        self.routing = AsyncRoutingResource(self._http)
        self.prompts = AsyncPromptsResource(self._http)
        self.grades = AsyncGradesResource(self._http)
        self.review = AsyncReviewResource(self._http)
        self.trainers = AsyncTrainersResource(self._http)
        self.jobs = AsyncJobsResource(self._http)

    async def health(self) -> dict[str, Any]:
        return cast("dict[str, Any]", await self._http.request("GET", "/api/health"))

    async def nbot_status(self) -> dict[str, Any]:
        return cast("dict[str, Any]", await self._http.request("GET", "/api/nbot"))

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
