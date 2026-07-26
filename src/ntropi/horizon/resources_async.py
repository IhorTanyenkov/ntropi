"""Asynchronous Horizon resource groups — twins of ``resources`` with an
identical surface. ``rl.train`` / ``rl.env_train`` return an :class:`AsyncJob`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .._base import AsyncBaseClient
from .._jobs import AsyncJob
from .resources import JsonList, _arr, _obj


class AsyncSuitesResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> JsonList:
        return _arr(await self._http.request("GET", "/api/suites"), "suites")

    async def get(self, suite_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("GET", f"/api/suites/{suite_id}"))

    async def create(self, name: str) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/api/suites", json={"name": name}))

    async def add_cases(self, suite_id: str, cases: Sequence[dict[str, Any]]) -> dict[str, Any]:
        return _obj(
            await self._http.request(
                "POST", f"/api/suites/{suite_id}/cases", json={"cases": list(cases)}
            )
        )

    async def run(
        self,
        suite_id: str,
        *,
        eval: bool = False,
        model: str | None = None,
        judge: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"eval": eval}
        if model:
            body["model"] = model
        if judge:
            body["judge"] = judge
        return _obj(await self._http.request("POST", f"/api/suites/{suite_id}/run", json=body))

    async def runs(self, suite_id: str) -> JsonList:
        return _arr(await self._http.request("GET", f"/api/suites/{suite_id}/runs"), "runs")


class AsyncSessionsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> JsonList:
        return _arr(await self._http.request("GET", "/api/sessions"), "sessions")

    async def trace(self, session_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("GET", f"/api/sessions/{session_id}/trace"))

    async def graph(self, session_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("GET", f"/api/sessions/{session_id}/graph"))

    async def stats(self) -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/api/stats"))


class AsyncDatasetsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> JsonList:
        return _arr(await self._http.request("GET", "/api/datasets"), "datasets")

    async def get(self, dataset_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("GET", f"/api/datasets/{dataset_id}"))

    async def create(self, name: str, *, kind: str = "rl") -> dict[str, Any]:
        return _obj(
            await self._http.request("POST", "/api/datasets", json={"name": name, "kind": kind})
        )

    async def import_samples(
        self, *, name: str = "imported", kind: str = "rl", samples: Sequence[dict[str, Any]]
    ) -> dict[str, Any]:
        return _obj(
            await self._http.request(
                "POST",
                "/api/datasets/import",
                json={"name": name, "kind": kind, "samples": list(samples)},
            )
        )

    async def merge(
        self, ids: Sequence[str], *, name: str | None = None, min_feedback: int | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"ids": list(ids)}
        if name:
            body["name"] = name
        if min_feedback is not None:
            body["min_feedback"] = min_feedback
        return _obj(await self._http.request("POST", "/api/datasets/merge", json=body))


class AsyncRLResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def train(
        self,
        *,
        datasets: Sequence[str] | None = None,
        session: str | None = None,
        reset: bool = False,
        save: bool = True,
    ) -> AsyncJob:
        body: dict[str, Any] = {"reset": reset, "save": save}
        if datasets:
            body["datasets"] = list(datasets)
        if session:
            body["session"] = session
        data = _obj(await self._http.request("POST", "/api/rl/train", json=body))
        return AsyncJob(self._http, str(data["job_id"]))

    async def env_train(
        self,
        *,
        prompt: str | None = None,
        session: str | None = None,
        suite: str | None = None,
        case: str | None = None,
        iterations: int = 10,
        model: str | None = None,
        reset: bool = False,
        eval: bool = False,
        judge: dict[str, Any] | None = None,
    ) -> AsyncJob:
        body: dict[str, Any] = {"iterations": iterations, "reset": reset, "eval": eval}
        if prompt:
            body["prompt"] = prompt
        if session:
            body["session"] = session
        if suite and case:
            body["suite"] = suite
            body["case"] = case
        if model:
            body["model"] = model
        if judge:
            body["judge"] = judge
        data = _obj(await self._http.request("POST", "/api/rl/env-train", json=body))
        return AsyncJob(self._http, str(data["job_id"]))

    async def policy(self) -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/api/rl/policy"))

    async def save(self) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/api/rl/save"))

    async def checkpoint(self) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/api/rl/checkpoint"))

    async def versions(self) -> JsonList:
        return _arr(await self._http.request("GET", "/api/rl/versions"), "versions")


class AsyncJobsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> JsonList:
        return _arr(await self._http.request("GET", "/api/jobs"), "jobs")

    def get(self, job_id: str) -> AsyncJob:
        return AsyncJob(self._http, job_id)
