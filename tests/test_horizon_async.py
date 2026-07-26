"""Phase-5 tests — the Horizon AsyncClient twin (parity + AsyncJob)."""

from __future__ import annotations

import httpx
import respx

import ntropi

BASE = "http://h"


@respx.mock
async def test_async_suites_and_datasets() -> None:
    respx.get(f"{BASE}/api/suites").mock(
        return_value=httpx.Response(200, json=[{"id": "gsm8k"}])
    )
    respx.post(f"{BASE}/api/datasets/merge").mock(
        return_value=httpx.Response(200, json={"id": "d2"})
    )
    async with ntropi.horizon.AsyncClient(BASE, key="k") as ac:
        assert (await ac.suites.list())[0]["id"] == "gsm8k"
        assert (await ac.datasets.merge(["a", "b"]))["id"] == "d2"


@respx.mock
async def test_async_rl_train_job_streams() -> None:
    respx.post(f"{BASE}/api/rl/env-train").mock(
        return_value=httpx.Response(200, json={"ok": True, "job_id": "e1"})
    )
    poll = respx.get(f"{BASE}/api/jobs/e1")
    poll.side_effect = [
        httpx.Response(200, json={"status": "running", "trajectory": [{"iter": 0}]}),
        httpx.Response(200, json={"status": "done", "trajectory": [{"iter": 0}, {"iter": 1}]}),
    ]
    async with ntropi.horizon.AsyncClient(BASE, key="k") as ac:
        job = await ac.rl.env_train(prompt="x", iterations=2)
        assert job.id == "e1"
        points = [p async for p in job.stream(poll=0.0)]
        assert [p["iter"] for p in points] == [0, 1]
