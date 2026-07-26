"""Synchronous Horizon resource groups.

Covers the core eval / observability loop: suites (run against a live serve and
score), sessions / traces (read from nbot's logs), datasets (curated sample
buckets), and RL (train / env-train as :class:`~ntropi._jobs.Job` s). Live-drive
calls (suite run, rl train/env-train) require a reachable nbot serve and raise
``UpstreamUnavailable`` (502/503) when there is none.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .._base import BaseClient
from .._jobs import Job

JsonList = list[dict[str, Any]]


def _obj(x: Any) -> dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _arr(x: Any, key: str = "") -> JsonList:
    if isinstance(x, list):
        return x
    if isinstance(x, dict) and key:
        v = x.get(key, [])
        return v if isinstance(v, list) else []
    return []


class SuitesResource:
    """Curated case suites run against the serve and scored."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> JsonList:
        return _arr(self._http.request("GET", "/api/suites"), "suites")

    def get(self, suite_id: str) -> dict[str, Any]:
        return _obj(self._http.request("GET", f"/api/suites/{suite_id}"))

    def create(self, name: str) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/api/suites", json={"name": name}))

    def add_cases(self, suite_id: str, cases: Sequence[dict[str, Any]]) -> dict[str, Any]:
        return _obj(
            self._http.request("POST", f"/api/suites/{suite_id}/cases", json={"cases": list(cases)})
        )

    def run(
        self,
        suite_id: str,
        *,
        eval: bool = False,
        model: str | None = None,
        judge: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run every case against the serve and return the scored run.

        ``eval=True`` freezes learning (no train/eval leakage). ``judge`` opts in
        an LLM-as-judge for the run.
        """
        body: dict[str, Any] = {"eval": eval}
        if model:
            body["model"] = model
        if judge:
            body["judge"] = judge
        return _obj(self._http.request("POST", f"/api/suites/{suite_id}/run", json=body))

    def runs(self, suite_id: str) -> JsonList:
        return _arr(self._http.request("GET", f"/api/suites/{suite_id}/runs"), "runs")


class SessionsResource:
    """Sessions and traces, read from nbot's on-disk logs."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> JsonList:
        return _arr(self._http.request("GET", "/api/sessions"), "sessions")

    def trace(self, session_id: str) -> dict[str, Any]:
        return _obj(self._http.request("GET", f"/api/sessions/{session_id}/trace"))

    def graph(self, session_id: str) -> dict[str, Any]:
        return _obj(self._http.request("GET", f"/api/sessions/{session_id}/graph"))

    def stats(self) -> dict[str, Any]:
        return _obj(self._http.request("GET", "/api/stats"))


class DatasetsResource:
    """Curated, versioned sample buckets for offline training."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> JsonList:
        return _arr(self._http.request("GET", "/api/datasets"), "datasets")

    def get(self, dataset_id: str) -> dict[str, Any]:
        return _obj(self._http.request("GET", f"/api/datasets/{dataset_id}"))

    def create(self, name: str, *, kind: str = "rl") -> dict[str, Any]:
        return _obj(self._http.request("POST", "/api/datasets", json={"name": name, "kind": kind}))

    def import_samples(
        self, *, name: str = "imported", kind: str = "rl", samples: Sequence[dict[str, Any]]
    ) -> dict[str, Any]:
        return _obj(
            self._http.request(
                "POST",
                "/api/datasets/import",
                json={"name": name, "kind": kind, "samples": list(samples)},
            )
        )

    def merge(
        self, ids: Sequence[str], *, name: str | None = None, min_feedback: int | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"ids": list(ids)}
        if name:
            body["name"] = name
        if min_feedback is not None:
            body["min_feedback"] = min_feedback
        return _obj(self._http.request("POST", "/api/datasets/merge", json=body))


class RLResource:
    """Training, policy, and versioning. ``train`` / ``env_train`` return a Job."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def train(
        self,
        *,
        datasets: Sequence[str] | None = None,
        session: str | None = None,
        reset: bool = False,
        save: bool = True,
    ) -> Job:
        """Replay logged experience through nbot as an async training Job."""
        body: dict[str, Any] = {"reset": reset, "save": save}
        if datasets:
            body["datasets"] = list(datasets)
        if session:
            body["session"] = session
        data = _obj(self._http.request("POST", "/api/rl/train", json=body))
        return Job(self._http, str(data["job_id"]))

    def env_train(
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
    ) -> Job:
        """Run one task N times as a live environment loop (async Job with trajectory)."""
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
        data = _obj(self._http.request("POST", "/api/rl/env-train", json=body))
        return Job(self._http, str(data["job_id"]))

    def policy(self) -> dict[str, Any]:
        return _obj(self._http.request("GET", "/api/rl/policy"))

    def save(self) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/api/rl/save"))

    def checkpoint(self) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/api/rl/checkpoint"))

    def versions(self) -> JsonList:
        return _arr(self._http.request("GET", "/api/rl/versions"), "versions")


class JobsResource:
    """Direct access to the async job registry."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> JsonList:
        return _arr(self._http.request("GET", "/api/jobs"), "jobs")

    def get(self, job_id: str) -> Job:
        return Job(self._http, job_id)
