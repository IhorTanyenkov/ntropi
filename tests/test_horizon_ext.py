"""Tests for the completed Horizon surface — prompt optimization, routing,
grades/judge, trainers, and the enriched RL controls (sync + async, respx)."""

from __future__ import annotations

import httpx
import pytest
import respx

import ntropi

BASE = "http://h"


def _c() -> ntropi.horizon.Client:
    return ntropi.horizon.Client(BASE, key="k")


@respx.mock
def test_prompt_optimize_returns_typed_result() -> None:
    respx.post(f"{BASE}/api/promptopt").mock(
        return_value=httpx.Response(
            200,
            json={
                "prompt_id": "router",
                "suite_id": "gsm8k",
                "metric": "rate",
                "deployed": True,
                "best_label": "v2",
                "best_rate": 0.92,
                "trials": [
                    {"label": "baseline", "rate": 0.80, "passed": 40, "total": 50},
                    {"label": "v2", "rate": 0.92, "passed": 46, "total": 50},
                ],
            },
        )
    )
    opt = _c().prompts.optimize("router", "gsm8k", generate=2)
    assert opt.deployed is True
    assert opt.best_label == "v2"
    assert opt.trials[1].rate == 0.92
    assert opt.trials[0].label == "baseline"


@respx.mock
def test_prompt_registry() -> None:
    respx.get(f"{BASE}/api/prompts").mock(
        return_value=httpx.Response(200, json={"prompts": [{"id": "router", "version": 3}]})
    )
    respx.post(f"{BASE}/api/prompts/router/revert").mock(
        return_value=httpx.Response(200, json={"ok": True, "id": "router"})
    )
    c = _c()
    assert c.prompts.list(model="gemma")[0]["id"] == "router"
    assert c.prompts.revert("router", 2)["ok"] is True


@respx.mock
def test_routing_policies_typed_and_switch() -> None:
    respx.get(f"{BASE}/api/routing").mock(
        return_value=httpx.Response(
            200,
            json={"active": "thompson", "policies": ["thompson", "epsilon"],
                  "action_space": {"model_id": True}, "state_space": ["category"]},
        )
    )
    switch = respx.post(f"{BASE}/api/routing/policy").mock(
        return_value=httpx.Response(200, json={"ok": True, "active": "epsilon"})
    )
    c = _c()
    pol = c.routing.policies()
    assert pol.active == "thompson"
    assert "epsilon" in pol.policies
    assert pol.action_space == {"model_id": True}
    assert c.routing.set_policy("epsilon")["active"] == "epsilon"
    assert switch.calls.last.request.read() == b'{"name":"epsilon"}'


@respx.mock
def test_grade_and_judge() -> None:
    respx.post(f"{BASE}/api/grade").mock(
        return_value=httpx.Response(200, json={"ok": True, "session_id": "s1", "goal_met": True})
    )
    respx.post(f"{BASE}/api/grade/judge").mock(
        return_value=httpx.Response(200, json={"score": 0.9, "goal_met": True, "by": "judge"})
    )
    c = _c()
    g = c.grades.grade("s1", goal_met=True, score=1.0)
    assert g.goal_met is True and g.session_id == "s1"
    v = c.grades.judge("what is 2+2?", "4", rubric="correctness")
    assert v.score == 0.9 and v.by == "judge"


@respx.mock
def test_rl_rollback_export_import() -> None:
    respx.post(f"{BASE}/api/rl/rollback/3").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    respx.get(f"{BASE}/api/rl/export").mock(
        return_value=httpx.Response(200, json={"policy": "thompson", "state": {"arms": 30}})
    )
    imp = respx.post(f"{BASE}/api/rl/import").mock(
        return_value=httpx.Response(200, json={"ok": True, "imported": True})
    )
    c = _c()
    assert c.rl.rollback(3)["ok"] is True
    snap = c.rl.export()
    assert snap["state"]["arms"] == 30
    assert c.rl.import_(snap)["imported"] is True
    assert b'"arms"' in imp.calls.last.request.read()


@pytest.mark.parametrize("tier", [None, "local", "global"])
@respx.mock
async def test_policy_export_forwards_tier(tier: str | None) -> None:
    doc = {"format": "nbot-rl-prior", "scope": "global"} if tier == "global" else {"scope": "routing-core"}
    route = respx.get(f"{BASE}/api/rl/export").mock(return_value=httpx.Response(200, json=doc))
    with _c() as client:
        assert client.rl.export(tier=tier) == doc
    async with ntropi.horizon.AsyncClient(BASE) as client_async:
        assert await client_async.rl.export(tier=tier) == doc
    assert [dict(call.request.url.params) for call in route.calls] == [
        {"tier": tier} if tier is not None else {}
    ] * 2


@respx.mock
async def test_policy_export_rejects_unknown_tier_and_legacy_local_reply() -> None:
    legacy = {"scope": "routing-core", "models": [{"id": "node-only"}]}
    route = respx.get(f"{BASE}/api/rl/export").mock(return_value=httpx.Response(200, json=legacy))
    with _c() as client:
        with pytest.raises(ValueError, match="tier must be local or global"):
            client.rl.export(tier="invalid")
        with pytest.raises(ntropi.NtropiError, match="did not return a global routing prior"):
            client.rl.export(tier="global")
    async with ntropi.horizon.AsyncClient(BASE) as client_async:
        with pytest.raises(ValueError, match="tier must be local or global"):
            await client_async.rl.export(tier="invalid")
        with pytest.raises(ntropi.NtropiError, match="did not return a global routing prior"):
            await client_async.rl.export(tier="global")
    assert route.call_count == 2


@respx.mock
def test_trainers_train_typed() -> None:
    respx.post(f"{BASE}/api/trainers/t1/train").mock(
        return_value=httpx.Response(200, json={"ok": True, "applied": 128, "saved": True})
    )
    run = _c().trainers.train("t1", "gsm8k-train", reset=True)
    assert run.applied == 128 and run.saved is True


@respx.mock
async def test_async_prompt_optimize_and_routing() -> None:
    respx.post(f"{BASE}/api/promptopt").mock(
        return_value=httpx.Response(200, json={"prompt_id": "p", "suite_id": "s", "deployed": False})
    )
    respx.get(f"{BASE}/api/routing").mock(
        return_value=httpx.Response(200, json={"active": "thompson", "policies": []})
    )
    async with ntropi.horizon.AsyncClient(BASE, key="k") as ac:
        opt = await ac.prompts.optimize("p", "s")
        assert opt.deployed is False
        assert (await ac.routing.policies()).active == "thompson"
