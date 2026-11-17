"""Idempotent ``rl.train`` submission and the ``outcome_unknown`` job state.

Every case drives the real Horizon clients and job handles over the mocked
HTTP transport; nothing here reaches a live Horizon or starts a training run.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

import ntropi
from ntropi._exceptions import APITimeoutError, NtropiError
from ntropi._jobs import OUTCOME_UNKNOWN, TERMINAL

BASE = "http://h"
KEY = "train-2026-11-17/gsm8k  Ünïcode:01"  # must reach the wire unchanged

UNKNOWN_DOC: dict[str, Any] = {
    "status": "outcome_unknown",
    "error": "downstream acknowledgement lost",
    "trajectory": [{"iter": 0}, {"iter": 1}],
}
FULL_ARGS: dict[str, Any] = {
    "datasets": ["a"],
    "dataset": "b",
    "session": "s",
    "reset": True,
    "save": False,
}
FULL_BODY: dict[str, Any] = {
    "reset": True,
    "save": False,
    "datasets": ["a"],
    "dataset": "b",
    "session": "s",
}
DEFAULT_BODY: dict[str, Any] = {"reset": False, "save": True}


def _body(call: Any) -> dict[str, Any]:
    data = json.loads(call.request.content)
    assert isinstance(data, dict)
    return data


def _posts() -> list[Any]:
    return [c for c in respx.calls if c.request.method == "POST"]


def _running_then_unknown_twice() -> list[httpx.Response]:
    running = {"status": "running", "trajectory": [{"iter": 0}]}
    return [
        httpx.Response(200, json=running),
        httpx.Response(200, json=UNKNOWN_DOC),
        httpx.Response(200, json=running),
        httpx.Response(200, json=UNKNOWN_DOC),
    ]


class _Horizon:
    """A Horizon that deduplicates by key and loses the first acknowledgement."""

    def __init__(self) -> None:
        self.jobs_by_key: dict[str, str] = {}
        self.started = 0
        self.lose_next_ack = True

    def submit(self, request: httpx.Request) -> httpx.Response:
        key = json.loads(request.content)["idempotency_key"]
        if key not in self.jobs_by_key:
            self.started += 1
            self.jobs_by_key[key] = f"t{self.started}"
        if self.lose_next_ack:
            self.lose_next_ack = False
            raise httpx.ReadTimeout("acknowledgement lost", request=request)
        return httpx.Response(200, json={"ok": True, "job_id": self.jobs_by_key[key]})


def test_outcome_unknown_is_terminal_but_distinct() -> None:
    assert OUTCOME_UNKNOWN == "outcome_unknown"
    assert OUTCOME_UNKNOWN in TERMINAL


# --------------------------------------------------------------------- sync


@respx.mock
def test_train_without_key_keeps_existing_body() -> None:
    route = respx.post(f"{BASE}/api/rl/train").mock(
        return_value=httpx.Response(200, json={"ok": True, "job_id": "t1"})
    )
    with ntropi.horizon.Client(BASE, key="k") as h:
        h.rl.train()
        h.rl.train(**FULL_ARGS)
        h.rl.train(idempotency_key=None)
    assert _body(route.calls[0]) == DEFAULT_BODY
    assert _body(route.calls[1]) == FULL_BODY
    assert _body(route.calls[2]) == DEFAULT_BODY


@respx.mock
def test_train_forwards_key_exactly() -> None:
    route = respx.post(f"{BASE}/api/rl/train").mock(
        return_value=httpx.Response(200, json={"ok": True, "job_id": "t1"})
    )
    with ntropi.horizon.Client(BASE, key="k") as h:
        job = h.rl.train(**FULL_ARGS, idempotency_key=KEY)
        h.rl.train(idempotency_key="")
    assert job.id == "t1"
    assert _body(route.calls[0]) == {**FULL_BODY, "idempotency_key": KEY}
    assert _body(route.calls[1]) == {**DEFAULT_BODY, "idempotency_key": ""}


def test_idempotency_key_is_keyword_only() -> None:
    with ntropi.horizon.Client(BASE, key="k") as h, pytest.raises(TypeError):
        h.rl.train(KEY)  # type: ignore[misc]


@respx.mock
def test_retried_keyed_submission_resumes_the_same_job() -> None:
    server = _Horizon()
    respx.post(f"{BASE}/api/rl/train").mock(side_effect=server.submit)
    respx.get(f"{BASE}/api/jobs/t1").mock(return_value=httpx.Response(200, json=UNKNOWN_DOC))

    with ntropi.horizon.Client(BASE, key="k") as h:
        with pytest.raises(APITimeoutError):
            h.rl.train(datasets=["a"], idempotency_key=KEY)
        assert len(_posts()) == 1  # the SDK did not replay the lost submission

        job = h.rl.train(datasets=["a"], idempotency_key=KEY)
        assert job.id == "t1"
        final = job.wait(timeout=5, poll=0.0)

    posts = _posts()
    assert len(posts) == 2
    assert _body(posts[0]) == _body(posts[1])
    assert _body(posts[1])["idempotency_key"] == KEY
    assert server.started == 1
    assert final == UNKNOWN_DOC  # the unknown result, not a success claim


@respx.mock
def test_wait_and_stream_end_on_outcome_unknown() -> None:
    poll = respx.get(f"{BASE}/api/jobs/t1")
    poll.side_effect = _running_then_unknown_twice()
    with ntropi.horizon.Client(BASE, key="k") as h:
        job = h.jobs.get("t1")  # resuming by id, as after a restart
        final = job.wait(timeout=5, poll=0.0)
        points = list(job.stream(poll=0.0))

    assert final == UNKNOWN_DOC
    assert "applied" not in final
    assert [p["iter"] for p in points] == [0, 1]
    assert poll.call_count == 4  # each loop stopped at the unknown document
    assert _posts() == []  # no automatic replay, pause, resume or stop


@respx.mock
def test_wait_still_times_out_on_a_running_job() -> None:
    respx.get(f"{BASE}/api/jobs/t1").mock(
        return_value=httpx.Response(200, json={"status": "running"})
    )
    with ntropi.horizon.Client(BASE, key="k") as h, pytest.raises(NtropiError):
        h.jobs.get("t1").wait(timeout=0.0, poll=0.0)


# -------------------------------------------------------------------- async


@respx.mock
async def test_async_train_without_key_keeps_existing_body() -> None:
    route = respx.post(f"{BASE}/api/rl/train").mock(
        return_value=httpx.Response(200, json={"ok": True, "job_id": "t1"})
    )
    async with ntropi.horizon.AsyncClient(BASE, key="k") as ah:
        await ah.rl.train()
        await ah.rl.train(**FULL_ARGS)
        await ah.rl.train(idempotency_key=None)
    assert _body(route.calls[0]) == DEFAULT_BODY
    assert _body(route.calls[1]) == FULL_BODY
    assert _body(route.calls[2]) == DEFAULT_BODY


@respx.mock
async def test_async_train_forwards_key_exactly() -> None:
    route = respx.post(f"{BASE}/api/rl/train").mock(
        return_value=httpx.Response(200, json={"ok": True, "job_id": "t1"})
    )
    async with ntropi.horizon.AsyncClient(BASE, key="k") as ah:
        job = await ah.rl.train(**FULL_ARGS, idempotency_key=KEY)
        await ah.rl.train(idempotency_key="")
    assert job.id == "t1"
    assert _body(route.calls[0]) == {**FULL_BODY, "idempotency_key": KEY}
    assert _body(route.calls[1]) == {**DEFAULT_BODY, "idempotency_key": ""}


async def test_async_idempotency_key_is_keyword_only() -> None:
    async with ntropi.horizon.AsyncClient(BASE, key="k") as ah:
        with pytest.raises(TypeError):
            await ah.rl.train(KEY)  # type: ignore[misc]


@respx.mock
async def test_async_retried_keyed_submission_resumes_the_same_job() -> None:
    server = _Horizon()
    respx.post(f"{BASE}/api/rl/train").mock(side_effect=server.submit)
    respx.get(f"{BASE}/api/jobs/t1").mock(return_value=httpx.Response(200, json=UNKNOWN_DOC))

    async with ntropi.horizon.AsyncClient(BASE, key="k") as ah:
        with pytest.raises(APITimeoutError):
            await ah.rl.train(datasets=["a"], idempotency_key=KEY)
        assert len(_posts()) == 1

        job = await ah.rl.train(datasets=["a"], idempotency_key=KEY)
        assert job.id == "t1"
        final = await job.wait(timeout=5, poll=0.0)

    posts = _posts()
    assert len(posts) == 2
    assert _body(posts[0]) == _body(posts[1])
    assert _body(posts[1])["idempotency_key"] == KEY
    assert server.started == 1
    assert final == UNKNOWN_DOC


@respx.mock
async def test_async_wait_and_stream_end_on_outcome_unknown() -> None:
    poll = respx.get(f"{BASE}/api/jobs/t1")
    poll.side_effect = _running_then_unknown_twice()
    async with ntropi.horizon.AsyncClient(BASE, key="k") as ah:
        job = ah.jobs.get("t1")
        final = await job.wait(timeout=5, poll=0.0)
        points = [p async for p in job.stream(poll=0.0)]

    assert final == UNKNOWN_DOC
    assert "applied" not in final
    assert [p["iter"] for p in points] == [0, 1]
    assert poll.call_count == 4
    assert _posts() == []
