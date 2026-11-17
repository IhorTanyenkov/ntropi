"""Synchronous Horizon resource groups.

Horizon is the training / evaluation / observability backend for the nbot node:

- **train** — RL on logged experience (``rl.train``) and live environment
  training (``rl.env_train``), each a :class:`~ntropi._jobs.Job`; registered
  ``trainers`` over datasets.
- **route** — inspect and switch the active routing policy (``routing``) and read
  its learned state / aggregates.
- **optimize prompts** — propose variants, score them on a suite, deploy the best
  (``prompts.optimize``); a versioned prompt registry (``prompts``).
- **evaluate** — case ``suites``, ``grades`` (objective + LLM-judge), a human/LLM
  ``review`` queue, and ``datasets`` of curated samples.
- **observe** — ``sessions`` (traces, graphs, diffs, feedback).

Live-drive calls require a reachable nbot serve and raise ``UpstreamUnavailable``
(502/503) when there is none. The async twins live in ``resources_async``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from urllib.parse import quote

from .._base import BaseClient
from .._exceptions import NtropiError
from .._jobs import Job
from .types import (
    Grade,
    JsonList,
    JudgeVerdict,
    PromptOptimization,
    RoutingPolicies,
    SuiteRun,
    TrainerRun,
)


def _obj(x: Any) -> dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _export_params(tier: str | None) -> dict[str, str]:
    if tier is None:
        return {}
    if tier not in ("local", "global"):
        raise ValueError("tier must be local or global")
    return {"tier": tier}


def _export_result(tier: str | None, value: Any) -> dict[str, Any]:
    result = _obj(value)
    # Older Horizon versions ignore the tier and return local node state.
    if tier == "global" and (
        result.get("scope") != "global" or result.get("format") != "nbot-rl-prior"
    ):
        raise NtropiError("Horizon did not return a global routing prior")
    return result


def _arr(x: Any, key: str = "") -> JsonList:
    if isinstance(x, list):
        return x
    if isinstance(x, dict) and key:
        v = x.get(key, [])
        return v if isinstance(v, list) else []
    return []


class SuitesResource:
    """Curated case suites, run against the serve and scored."""

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
    ) -> SuiteRun:
        """Run every case against the serve and return the scored :class:`SuiteRun`.

        ``eval=True`` freezes learning for the run (no train/eval leakage).
        """
        body: dict[str, Any] = {"eval": eval}
        if model:
            body["model"] = model
        if judge:
            body["judge"] = judge
        return SuiteRun.model_validate(
            _obj(self._http.request("POST", f"/api/suites/{suite_id}/run", json=body))
        )

    def runs(self, suite_id: str) -> JsonList:
        return _arr(self._http.request("GET", f"/api/suites/{suite_id}/runs"), "runs")


class SessionsResource:
    """Sessions, traces, decomposition graphs, diffs, and turn feedback."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> JsonList:
        return _arr(self._http.request("GET", "/api/sessions"), "sessions")

    def trace(self, session_id: str) -> dict[str, Any]:
        return _obj(self._http.request("GET", f"/api/sessions/{session_id}/trace"))

    def graph(self, session_id: str) -> dict[str, Any]:
        return _obj(self._http.request("GET", f"/api/sessions/{session_id}/graph"))

    def diff(self, a: str, b: str) -> dict[str, Any]:
        """Compare two runs turn-by-turn (A/B)."""
        return _obj(self._http.request("GET", f"/api/sessions/{a}/diff/{b}"))

    def feedback(
        self, session_id: str, turn: int, *, polarity: str, comment: str = "", by: str = "user"
    ) -> dict[str, Any]:
        """Nudge the policy from a turn's outcome (``polarity`` = up/down)."""
        body = {"polarity": polarity, "comment": comment, "by": by}
        return _obj(
            self._http.request(
                "POST", f"/api/sessions/{session_id}/turns/{turn}/feedback", json=body
            )
        )

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

    def from_session(self, dataset_id: str, session: str) -> dict[str, Any]:
        """Append samples built from a session, per the dataset's kind."""
        return _obj(
            self._http.request(
                "POST", f"/api/datasets/{dataset_id}/from-session", json={"session": session}
            )
        )

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

    def coverage(self, dataset_id: str) -> dict[str, Any]:
        """Curation report — graded fraction, category/band coverage, empty cells."""
        return _obj(self._http.request("GET", f"/api/datasets/{dataset_id}/coverage"))

    def enrich(self, dataset_id: str, grades: Sequence[dict[str, Any]]) -> dict[str, Any]:
        """Write grades back into matching samples (snapshots the prior version)."""
        return _obj(
            self._http.request(
                "POST", f"/api/datasets/{dataset_id}/enrich", json={"grades": list(grades)}
            )
        )

    def version(self, dataset_id: str) -> dict[str, Any]:
        """Snapshot the current dataset as a new version."""
        return _obj(self._http.request("POST", f"/api/datasets/{dataset_id}/version"))

    def delete(self, dataset_id: str) -> dict[str, Any]:
        return _obj(self._http.request("DELETE", f"/api/datasets/{dataset_id}"))


class RLResource:
    """The training framework — replay training, environment training, policy state.

    ``train`` / ``env_train`` return a :class:`~ntropi._jobs.Job` you poll, wait
    on, or stream.
    """

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def train(
        self,
        *,
        datasets: Sequence[str] | None = None,
        dataset: str | None = None,
        session: str | None = None,
        reset: bool = False,
        save: bool = True,
        idempotency_key: str | None = None,
    ) -> Job:
        """Replay logged experience (live logs, or named dataset buckets) as a Job.

        ``idempotency_key`` is forwarded verbatim so Horizon can deduplicate the
        submission. The SDK never replays this POST: if the acknowledgement is
        lost (timeout, dropped connection), call ``train`` again with the *same*
        key and arguments to get the original job back instead of starting a
        second run. Omitting it leaves the request body unchanged.
        """
        body: dict[str, Any] = {"reset": reset, "save": save}
        if datasets:
            body["datasets"] = list(datasets)
        if dataset:
            body["dataset"] = dataset
        if session:
            body["session"] = session
        if idempotency_key is not None:
            body["idempotency_key"] = idempotency_key
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
        expect: dict[str, Any] | None = None,
        reset: bool = False,
        eval: bool = False,
        judge: dict[str, Any] | None = None,
        dataset_id: str | None = None,
        enqueue_ungraded: bool = False,
    ) -> Job:
        """Run one task N times as a live environment loop, learning between runs."""
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
        data = _obj(self._http.request("POST", "/api/rl/env-train", json=body))
        return Job(self._http, str(data["job_id"]))

    def policy(self) -> dict[str, Any]:
        """The current learned policy state."""
        return _obj(self._http.request("GET", "/api/rl/policy"))

    def schema(self) -> dict[str, Any]:
        """The RL state / action / reward schema."""
        return _obj(self._http.request("GET", "/api/rl/schema"))

    def aggregate(self, by: str = "model") -> dict[str, Any]:
        """KPI + per-group policy view, grouped by ``model`` | ``category`` | ``exec_mode``."""
        return _obj(self._http.request("GET", "/api/rl/aggregate", params={"by": by}))

    def dataset(self, session: str | None = None) -> JsonList:
        """The RL samples (feedback- and grade-adjusted) for a session, or all."""
        params = {"session": session} if session else None
        data = self._http.request("GET", "/api/rl/dataset", params=params)
        return data if isinstance(data, list) else _arr(data, "samples")

    def save(self) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/api/rl/save"))

    def checkpoint(self, note: str | None = None) -> dict[str, Any]:
        body = {"note": note} if note is not None else {}
        return _obj(self._http.request("POST", "/api/rl/checkpoint", json=body))

    def versions(self) -> JsonList:
        return _arr(self._http.request("GET", "/api/rl/versions"), "versions")

    def rollback(self, version: int) -> dict[str, Any]:
        return _obj(self._http.request("POST", f"/api/rl/rollback/{version}"))

    def export(self, *, tier: str | None = None) -> dict[str, Any]:
        """Export the node's local snapshot (default), or its shareable global prior."""
        data = self._http.request("GET", "/api/rl/export", params=_export_params(tier))
        return _export_result(tier, data)

    def import_(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/api/rl/import", json=snapshot))


class RoutingResource:
    """The routing policy — inspect the active one and the space it decides over."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def policies(self) -> RoutingPolicies:
        """Registered policies, the active one, and the action / state space."""
        return RoutingPolicies.model_validate(_obj(self._http.request("GET", "/api/routing")))

    def set_policy(self, name: str) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/api/routing/policy", json={"name": name}))


class PromptsResource:
    """Prompt optimization and the versioned prompt registry (PromptLab)."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def optimize(
        self,
        prompt_id: str,
        suite_id: str,
        *,
        scope: str | None = None,
        metric: str = "rate",
        candidates: Sequence[str] | None = None,
        generate: int = 3,
    ) -> PromptOptimization:
        """Propose variants, score each on a suite, and deploy the best.

        With ``candidates`` the given templates are trialled; otherwise ``generate``
        variants are auto-proposed. ``metric`` is ``"rate"`` or ``"reward"``.
        """
        body: dict[str, Any] = {"prompt_id": prompt_id, "suite_id": suite_id, "metric": metric}
        if scope:
            body["scope"] = scope
        if candidates is not None:
            body["candidates"] = list(candidates)
        else:
            body["generate"] = generate
        return PromptOptimization.model_validate(
            _obj(self._http.request("POST", "/api/promptopt", json=body))
        )

    def list(self, model: str | None = None) -> JsonList:
        params = {"model": model} if model else None
        return _arr(self._http.request("GET", "/api/prompts", params=params), "prompts")

    def get(self, prompt_id: str, model: str | None = None) -> dict[str, Any]:
        params = {"model": model} if model else None
        return _obj(
            self._http.request("GET", f"/api/prompts/{quote(prompt_id, safe='')}", params=params)
        )

    def deploy(
        self, prompt_id: str, template: str, *, note: str | None = None, scope: str | None = None
    ) -> dict[str, Any]:
        """Deploy a prompt override and snapshot a version."""
        body: dict[str, Any] = {"id": prompt_id, "template": template}
        if note is not None:
            body["note"] = note
        if scope is not None:
            body["scope"] = scope
        return _obj(self._http.request("POST", "/api/prompts", json=body))

    def versions(self, prompt_id: str) -> JsonList:
        return _arr(
            self._http.request("GET", f"/api/prompts/{quote(prompt_id, safe='')}/versions"),
            "versions",
        )

    def runs(self, prompt_id: str) -> JsonList:
        return _arr(
            self._http.request("GET", f"/api/prompts/{quote(prompt_id, safe='')}/runs"), "runs"
        )

    def revert(self, prompt_id: str, version: int) -> dict[str, Any]:
        return _obj(
            self._http.request(
                "POST", f"/api/prompts/{quote(prompt_id, safe='')}/revert", json={"version": version}
            )
        )

    def delete(self, prompt_id: str, model: str | None = None) -> dict[str, Any]:
        params = {"model": model} if model else None
        return _obj(
            self._http.request("DELETE", f"/api/prompts/{quote(prompt_id, safe='')}", params=params)
        )


class GradesResource:
    """Grade turns — objectively, or with an LLM judge — feeding the policy."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def grade(
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
        return Grade.model_validate(_obj(self._http.request("POST", "/api/grade", json=body)))

    def judge(
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
        """LLM-as-judge on a (task, response). Applies to the policy when ``session_id`` is given."""
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
            _obj(self._http.request("POST", "/api/grade/judge", json=body))
        )


class ReviewResource:
    """The human/LLM grading queue — curate graded data that feeds training."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def queue(self, *, status: str | None = None, limit: int | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit
        return _obj(self._http.request("GET", "/api/review/queue", params=params or None))

    def sample(
        self,
        *,
        rate: float | None = None,
        limit: int = 50,
        session: str | None = None,
        dataset_id: str | None = None,
        job: str | None = None,
    ) -> dict[str, Any]:
        """Sample real traffic into the review queue."""
        body: dict[str, Any] = {"limit": limit}
        if rate is not None:
            body["rate"] = rate
        if session:
            body["session"] = session
        if dataset_id:
            body["dataset_id"] = dataset_id
        if job:
            body["job"] = job
        return _obj(self._http.request("POST", "/api/review/sample", json=body))

    def grade(
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
            self._http.request("POST", f"/api/review/{quote(item_id, safe='')}/grade", json=body)
        )

    def judge(
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
            self._http.request("POST", f"/api/review/{quote(item_id, safe='')}/judge", json=body)
        )

    def judge_batch(
        self,
        *,
        limit: int = 20,
        judge_model: str | None = None,
        rubric: str | None = None,
        threshold: float | None = None,
        panel: int = 1,
        eval: bool = False,
    ) -> dict[str, Any]:
        """Drain N pending items with the LLM judge."""
        body: dict[str, Any] = {"limit": limit, "panel": panel, "eval": eval}
        if judge_model is not None:
            body["judge_model"] = judge_model
        if rubric is not None:
            body["rubric"] = rubric
        if threshold is not None:
            body["threshold"] = threshold
        return _obj(self._http.request("POST", "/api/review/judge-batch", json=body))

    def clear(self, *, status: str | None = None) -> dict[str, Any]:
        body = {"status": status} if status else {}
        return _obj(self._http.request("POST", "/api/review/clear", json=body))

    def delete(self, item_id: str) -> dict[str, Any]:
        return _obj(self._http.request("DELETE", f"/api/review/{quote(item_id, safe='')}"))


class TrainersResource:
    """Registered trainers over datasets — the second (offline) training path."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> JsonList:
        return _arr(self._http.request("GET", "/api/trainers"), "trainers")

    def create(
        self, name: str, *, kind: str = "nbot-replay", cmd: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "kind": kind}
        if cmd is not None:
            body["cmd"] = cmd
        return _obj(self._http.request("POST", "/api/trainers", json=body))

    def get(self, trainer_id: str) -> dict[str, Any]:
        return _obj(self._http.request("GET", f"/api/trainers/{quote(trainer_id, safe='')}"))

    def jobs(self, trainer_id: str) -> JsonList:
        return _arr(
            self._http.request("GET", f"/api/trainers/{quote(trainer_id, safe='')}/jobs"), "jobs"
        )

    def train(
        self, trainer_id: str, dataset_id: str, *, reset: bool = False, save: bool = True
    ) -> TrainerRun:
        """Run the trainer over a dataset (synchronous for nbot-replay)."""
        body = {"dataset_id": dataset_id, "reset": reset, "save": save}
        return TrainerRun.model_validate(
            _obj(
                self._http.request(
                    "POST", f"/api/trainers/{quote(trainer_id, safe='')}/train", json=body
                )
            )
        )

    def delete(self, trainer_id: str) -> dict[str, Any]:
        return _obj(self._http.request("DELETE", f"/api/trainers/{quote(trainer_id, safe='')}"))


class JobsResource:
    """Direct access to the async job registry."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> JsonList:
        return _arr(self._http.request("GET", "/api/jobs"), "jobs")

    def get(self, job_id: str) -> Job:
        return Job(self._http, job_id)
