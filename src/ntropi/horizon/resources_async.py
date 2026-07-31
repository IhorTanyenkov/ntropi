"""Asynchronous Horizon resource groups — twins of ``resources`` with an
identical surface. ``rl.train`` / ``rl.env_train`` return an :class:`AsyncJob`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from urllib.parse import quote

from .._base import AsyncBaseClient
from .._jobs import AsyncJob
from .resources import _arr, _obj
from .types import (
    Grade,
    JsonList,
    JudgeVerdict,
    PromptOptimization,
    RoutingPolicies,
    SuiteRun,
    TrainerRun,
)


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
    ) -> SuiteRun:
        body: dict[str, Any] = {"eval": eval}
        if model:
            body["model"] = model
        if judge:
            body["judge"] = judge
        return SuiteRun.model_validate(
            _obj(await self._http.request("POST", f"/api/suites/{suite_id}/run", json=body))
        )

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

    async def diff(self, a: str, b: str) -> dict[str, Any]:
        return _obj(await self._http.request("GET", f"/api/sessions/{a}/diff/{b}"))

    async def feedback(
        self, session_id: str, turn: int, *, polarity: str, comment: str = "", by: str = "user"
    ) -> dict[str, Any]:
        body = {"polarity": polarity, "comment": comment, "by": by}
        return _obj(
            await self._http.request(
                "POST", f"/api/sessions/{session_id}/turns/{turn}/feedback", json=body
            )
        )

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

    async def from_session(self, dataset_id: str, session: str) -> dict[str, Any]:
        return _obj(
            await self._http.request(
                "POST", f"/api/datasets/{dataset_id}/from-session", json={"session": session}
            )
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

    async def coverage(self, dataset_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("GET", f"/api/datasets/{dataset_id}/coverage"))

    async def enrich(self, dataset_id: str, grades: Sequence[dict[str, Any]]) -> dict[str, Any]:
        return _obj(
            await self._http.request(
                "POST", f"/api/datasets/{dataset_id}/enrich", json={"grades": list(grades)}
            )
        )

    async def version(self, dataset_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("POST", f"/api/datasets/{dataset_id}/version"))

    async def delete(self, dataset_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("DELETE", f"/api/datasets/{dataset_id}"))


class AsyncRLResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def train(
        self,
        *,
        datasets: Sequence[str] | None = None,
        dataset: str | None = None,
        session: str | None = None,
        reset: bool = False,
        save: bool = True,
    ) -> AsyncJob:
        body: dict[str, Any] = {"reset": reset, "save": save}
        if datasets:
            body["datasets"] = list(datasets)
        if dataset:
            body["dataset"] = dataset
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
        expect: dict[str, Any] | None = None,
        reset: bool = False,
        eval: bool = False,
        judge: dict[str, Any] | None = None,
        dataset_id: str | None = None,
        enqueue_ungraded: bool = False,
    ) -> AsyncJob:
        body: dict[str, Any] = {
            "iterations": iterations,
            "reset": reset,
            "eval": eval,
            "enqueue_ungraded": enqueue_ungraded,
        }
        if prompt:
            body["prompt"] = prompt
        if session:
            body["session"] = session
        if suite and case:
            body["suite"] = suite
            body["case"] = case
        if model:
            body["model"] = model
        if expect:
            body["expect"] = expect
        if judge:
            body["judge"] = judge
        if dataset_id:
            body["dataset_id"] = dataset_id
        data = _obj(await self._http.request("POST", "/api/rl/env-train", json=body))
        return AsyncJob(self._http, str(data["job_id"]))

    async def policy(self) -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/api/rl/policy"))

    async def schema(self) -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/api/rl/schema"))

    async def aggregate(self, by: str = "model") -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/api/rl/aggregate", params={"by": by}))

    async def dataset(self, session: str | None = None) -> JsonList:
        params = {"session": session} if session else None
        data = await self._http.request("GET", "/api/rl/dataset", params=params)
        return data if isinstance(data, list) else _arr(data, "samples")

    async def save(self) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/api/rl/save"))

    async def checkpoint(self, note: str | None = None) -> dict[str, Any]:
        body = {"note": note} if note is not None else {}
        return _obj(await self._http.request("POST", "/api/rl/checkpoint", json=body))

    async def versions(self) -> JsonList:
        return _arr(await self._http.request("GET", "/api/rl/versions"), "versions")

    async def rollback(self, version: int) -> dict[str, Any]:
        return _obj(await self._http.request("POST", f"/api/rl/rollback/{version}"))

    async def export(self) -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/api/rl/export"))

    async def import_(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/api/rl/import", json=snapshot))


class AsyncRoutingResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def policies(self) -> RoutingPolicies:
        return RoutingPolicies.model_validate(_obj(await self._http.request("GET", "/api/routing")))

    async def set_policy(self, name: str) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/api/routing/policy", json={"name": name}))


class AsyncPromptsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def optimize(
        self,
        prompt_id: str,
        suite_id: str,
        *,
        scope: str | None = None,
        metric: str = "rate",
        candidates: Sequence[str] | None = None,
        generate: int = 3,
    ) -> PromptOptimization:
        body: dict[str, Any] = {"prompt_id": prompt_id, "suite_id": suite_id, "metric": metric}
        if scope:
            body["scope"] = scope
        if candidates is not None:
            body["candidates"] = list(candidates)
        else:
            body["generate"] = generate
        return PromptOptimization.model_validate(
            _obj(await self._http.request("POST", "/api/promptopt", json=body))
        )

    async def list(self, model: str | None = None) -> JsonList:
        params = {"model": model} if model else None
        return _arr(await self._http.request("GET", "/api/prompts", params=params), "prompts")

    async def get(self, prompt_id: str, model: str | None = None) -> dict[str, Any]:
        params = {"model": model} if model else None
        return _obj(
            await self._http.request(
                "GET", f"/api/prompts/{quote(prompt_id, safe='')}", params=params
            )
        )

    async def deploy(
        self, prompt_id: str, template: str, *, note: str | None = None, scope: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"id": prompt_id, "template": template}
        if note is not None:
            body["note"] = note
        if scope is not None:
            body["scope"] = scope
        return _obj(await self._http.request("POST", "/api/prompts", json=body))

    async def versions(self, prompt_id: str) -> JsonList:
        return _arr(
            await self._http.request("GET", f"/api/prompts/{quote(prompt_id, safe='')}/versions"),
            "versions",
        )

    async def runs(self, prompt_id: str) -> JsonList:
        return _arr(
            await self._http.request("GET", f"/api/prompts/{quote(prompt_id, safe='')}/runs"), "runs"
        )

    async def revert(self, prompt_id: str, version: int) -> dict[str, Any]:
        return _obj(
            await self._http.request(
                "POST", f"/api/prompts/{quote(prompt_id, safe='')}/revert", json={"version": version}
            )
        )

    async def delete(self, prompt_id: str, model: str | None = None) -> dict[str, Any]:
        params = {"model": model} if model else None
        return _obj(
            await self._http.request(
                "DELETE", f"/api/prompts/{quote(prompt_id, safe='')}", params=params
            )
        )


class AsyncGradesResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def grade(
        self,
        session_id: str,
        *,
        turn: int = 0,
        goal_met: bool = False,
        score: float | None = None,
        grader: str = "human",
        note: str | None = None,
    ) -> Grade:
        body: dict[str, Any] = {
            "session_id": session_id,
            "turn": turn,
            "goal_met": goal_met,
            "grader": grader,
        }
        if score is not None:
            body["score"] = score
        if note is not None:
            body["note"] = note
        return Grade.model_validate(_obj(await self._http.request("POST", "/api/grade", json=body)))

    async def judge(
        self,
        task: str,
        response: str,
        *,
        rubric: str | None = None,
        judge_model: str | None = None,
        panel: int = 1,
        threshold: float | None = None,
        session_id: str | None = None,
        turn: int = 0,
        eval: bool = False,
    ) -> JudgeVerdict:
        body: dict[str, Any] = {"task": task, "response": response, "panel": panel, "eval": eval}
        if rubric is not None:
            body["rubric"] = rubric
        if judge_model is not None:
            body["judge_model"] = judge_model
        if threshold is not None:
            body["threshold"] = threshold
        if session_id is not None:
            body["session_id"] = session_id
            body["turn"] = turn
        return JudgeVerdict.model_validate(
            _obj(await self._http.request("POST", "/api/grade/judge", json=body))
        )


class AsyncReviewResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def queue(self, *, status: str | None = None, limit: int | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit
        return _obj(await self._http.request("GET", "/api/review/queue", params=params or None))

    async def sample(
        self,
        *,
        rate: float | None = None,
        limit: int = 50,
        session: str | None = None,
        dataset_id: str | None = None,
        job: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"limit": limit}
        if rate is not None:
            body["rate"] = rate
        if session:
            body["session"] = session
        if dataset_id:
            body["dataset_id"] = dataset_id
        if job:
            body["job"] = job
        return _obj(await self._http.request("POST", "/api/review/sample", json=body))

    async def grade(
        self,
        item_id: str,
        *,
        goal_met: bool,
        score: float | None = None,
        note: str | None = None,
        by: str | None = None,
        eval: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"goal_met": goal_met, "eval": eval}
        if score is not None:
            body["score"] = score
        if note is not None:
            body["note"] = note
        if by is not None:
            body["by"] = by
        return _obj(
            await self._http.request(
                "POST", f"/api/review/{quote(item_id, safe='')}/grade", json=body
            )
        )

    async def judge(
        self,
        item_id: str,
        *,
        judge_model: str | None = None,
        rubric: str | None = None,
        threshold: float | None = None,
        panel: int = 1,
        eval: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"panel": panel, "eval": eval}
        if judge_model is not None:
            body["judge_model"] = judge_model
        if rubric is not None:
            body["rubric"] = rubric
        if threshold is not None:
            body["threshold"] = threshold
        return _obj(
            await self._http.request(
                "POST", f"/api/review/{quote(item_id, safe='')}/judge", json=body
            )
        )

    async def judge_batch(
        self,
        *,
        limit: int = 20,
        judge_model: str | None = None,
        rubric: str | None = None,
        threshold: float | None = None,
        panel: int = 1,
        eval: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"limit": limit, "panel": panel, "eval": eval}
        if judge_model is not None:
            body["judge_model"] = judge_model
        if rubric is not None:
            body["rubric"] = rubric
        if threshold is not None:
            body["threshold"] = threshold
        return _obj(await self._http.request("POST", "/api/review/judge-batch", json=body))

    async def clear(self, *, status: str | None = None) -> dict[str, Any]:
        body = {"status": status} if status else {}
        return _obj(await self._http.request("POST", "/api/review/clear", json=body))

    async def delete(self, item_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("DELETE", f"/api/review/{quote(item_id, safe='')}"))


class AsyncTrainersResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> JsonList:
        return _arr(await self._http.request("GET", "/api/trainers"), "trainers")

    async def create(
        self, name: str, *, kind: str = "nbot-replay", cmd: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "kind": kind}
        if cmd is not None:
            body["cmd"] = cmd
        return _obj(await self._http.request("POST", "/api/trainers", json=body))

    async def get(self, trainer_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("GET", f"/api/trainers/{quote(trainer_id, safe='')}"))

    async def jobs(self, trainer_id: str) -> JsonList:
        return _arr(
            await self._http.request("GET", f"/api/trainers/{quote(trainer_id, safe='')}/jobs"),
            "jobs",
        )

    async def train(
        self, trainer_id: str, dataset_id: str, *, reset: bool = False, save: bool = True
    ) -> TrainerRun:
        body = {"dataset_id": dataset_id, "reset": reset, "save": save}
        return TrainerRun.model_validate(
            _obj(
                await self._http.request(
                    "POST", f"/api/trainers/{quote(trainer_id, safe='')}/train", json=body
                )
            )
        )

    async def delete(self, trainer_id: str) -> dict[str, Any]:
        return _obj(
            await self._http.request("DELETE", f"/api/trainers/{quote(trainer_id, safe='')}")
        )


class AsyncJobsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> JsonList:
        return _arr(await self._http.request("GET", "/api/jobs"), "jobs")

    def get(self, job_id: str) -> AsyncJob:
        return AsyncJob(self._http, job_id)
