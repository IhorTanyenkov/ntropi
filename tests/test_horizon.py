"""Phase-2a tests — Horizon suites, sessions/traces, datasets, and the Job object
(train/env-train returning a Job that polls + streams trajectory) via respx."""

from __future__ import annotations

import httpx
import respx

import ntropi


def _client() -> ntropi.horizon.Client:
    return ntropi.horizon.Client("http://h", key="k")


@respx.mock
def test_suites_list_and_run() -> None:
    respx.get("http://h/api/suites").mock(
        return_value=httpx.Response(200, json=[{"id": "gsm8k", "cases": 50}])
    )
    respx.post("http://h/api/suites/gsm8k/run").mock(
        return_value=httpx.Response(200, json={"passed": 45, "total": 50, "eval": True})
    )
    c = _client()
    assert c.suites.list()[0]["id"] == "gsm8k"
    run = c.suites.run("gsm8k", eval=True)
    assert run["passed"] == 45


@respx.mock
def test_sessions_trace() -> None:
    respx.get("http://h/api/sessions/s-1/trace").mock(
        return_value=httpx.Response(200, json={"turns": [{"index": 0, "model": "gemma"}]})
    )
    assert _client().sessions.trace("s-1")["turns"][0]["model"] == "gemma"


@respx.mock
def test_datasets_import_and_merge() -> None:
    respx.post("http://h/api/datasets/import").mock(
        return_value=httpx.Response(200, json={"id": "d1", "samples": 2})
    )
    respx.post("http://h/api/datasets/merge").mock(
        return_value=httpx.Response(200, json={"id": "d2"})
    )
    c = _client()
    assert c.datasets.import_samples(samples=[{"a": 1}, {"a": 2}])["id"] == "d1"
    assert c.datasets.merge(["d1", "dx"], min_feedback=1)["id"] == "d2"


@respx.mock
def test_rl_train_returns_job_and_waits() -> None:
    respx.post("http://h/api/rl/train").mock(
        return_value=httpx.Response(200, json={"ok": True, "job_id": "tr-1", "status": "running"})
    )
    poll = respx.get("http://h/api/jobs/tr-1")
    poll.side_effect = [
        httpx.Response(200, json={"id": "tr-1", "status": "running"}),
        httpx.Response(200, json={"id": "tr-1", "status": "done", "applied": 12}),
    ]
    job = _client().rl.train(datasets=["gsm8k-train"], reset=True)
    assert job.id == "tr-1"
    final = job.wait(poll=0.0)
    assert final["status"] == "done" and final["applied"] == 12


@respx.mock
def test_env_train_job_streams_trajectory() -> None:
    respx.post("http://h/api/rl/env-train").mock(
        return_value=httpx.Response(200, json={"ok": True, "job_id": "env-1"})
    )
    poll = respx.get("http://h/api/jobs/env-1")
    poll.side_effect = [
        httpx.Response(200, json={"status": "running", "trajectory": [{"iter": 0, "reward": 0.1}]}),
        httpx.Response(
            200,
            json={"status": "done", "trajectory": [{"iter": 0, "reward": 0.1}, {"iter": 1, "reward": 0.4}]},
        ),
    ]
    job = _client().rl.env_train(prompt="do X", iterations=2)
    points = list(job.stream(poll=0.0))
    assert [p["iter"] for p in points] == [0, 1]
    assert points[-1]["reward"] == 0.4


@respx.mock
def test_upstream_unavailable_on_suite_run() -> None:
    respx.post("http://h/api/suites/x/run").mock(
        return_value=httpx.Response(502, json={"error": "no nbot serve reachable"})
    )
    from ntropi import UpstreamUnavailable

    try:
        _client().suites.run("x")
        raise AssertionError("expected UpstreamUnavailable")
    except UpstreamUnavailable:
        pass
