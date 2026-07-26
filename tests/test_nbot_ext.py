"""Phase-4 tests — the nbot structured surface newly typed on ntropi.nbot:
node RL (incl. the eval-freeze learning toggle), blueprints, kb (+binary),
research, artifacts, prompts, notes, connectors, routing, agents, satellites,
trace, files, manifesto, plan/autonomy, and the new command tokens."""

from __future__ import annotations

import httpx
import respx

import ntropi

BASE = "http://n"


def _c() -> ntropi.nbot.Client:
    return ntropi.nbot.Client(BASE, token="t")


@respx.mock
def test_rl_learning_toggle_and_feedback() -> None:
    get = respx.get(f"{BASE}/v1/rl/learning").mock(
        return_value=httpx.Response(200, json={"ok": True, "learning": True, "notes_learning": True})
    )
    post = respx.post(f"{BASE}/v1/rl/learning").mock(
        return_value=httpx.Response(200, json={"ok": True, "learning": False, "notes_learning": False})
    )
    respx.post(f"{BASE}/v1/rl/feedback").mock(
        return_value=httpx.Response(200, json={"ok": True, "signal": "positive"})
    )
    c = _c()
    assert c.rl.learning()["learning"] is True
    assert c.rl.set_learning(False)["learning"] is False
    assert post.calls.last.request.read() == b'{"enabled":false}'
    assert c.rl.feedback("s-1", "positive")["signal"] == "positive"
    assert get.called


@respx.mock
def test_rl_versions_rollback_reset() -> None:
    respx.get(f"{BASE}/v1/rl/versions").mock(
        return_value=httpx.Response(200, json={"ok": True, "versions": [{"v": 1}, {"v": 2}]})
    )
    respx.post(f"{BASE}/v1/rl/rollback/2").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    reset = respx.post(f"{BASE}/v1/command").mock(
        return_value=httpx.Response(200, json={"ok": True, "output": "RL reset"})
    )
    c = _c()
    assert [v["v"] for v in c.rl.versions()] == [1, 2]
    assert c.rl.rollback(2)["ok"] is True
    assert c.rl.reset()["output"] == "RL reset"
    assert reset.calls.last.request.read() == b'{"command":"/rl-reset"}'


@respx.mock
def test_blueprints_and_kb_binary() -> None:
    respx.get(f"{BASE}/v1/blueprints/list").mock(
        return_value=httpx.Response(200, json={"ok": True, "blueprints": [{"id": "bp"}]})
    )
    respx.post(f"{BASE}/v1/blueprints/run").mock(
        return_value=httpx.Response(200, json={"ok": True, "id": "bp", "steps": []})
    )
    respx.get(f"{BASE}/v1/kb/list").mock(
        return_value=httpx.Response(200, json={"ok": True, "files": [{"id": "k1"}]})
    )
    respx.get(f"{BASE}/v1/kb/file/k1").mock(return_value=httpx.Response(200, content=b"BYTES"))
    respx.delete(f"{BASE}/v1/kb/k1").mock(return_value=httpx.Response(200, json={"ok": True, "id": "k1"}))
    c = _c()
    assert c.blueprints.list()[0]["id"] == "bp"
    assert c.blueprints.run("bp", {"x": "1"})["id"] == "bp"
    assert c.kb.list()[0]["id"] == "k1"
    assert c.kb.file("k1") == b"BYTES"
    assert c.kb.delete("k1")["id"] == "k1"


@respx.mock
def test_prompts_notes_query_params() -> None:
    plist = respx.get(f"{BASE}/v1/prompts").mock(
        return_value=httpx.Response(200, json={"prompts": [{"id": "router"}]})
    )
    respx.post(f"{BASE}/v1/notes").mock(return_value=httpx.Response(200, json={"ok": True, "id": "n1"}))
    respx.get(f"{BASE}/v1/notes").mock(
        return_value=httpx.Response(200, json={"notes": [{"id": "n1", "text": "x"}]})
    )
    c = _c()
    assert c.prompts.list(model="gemma")[0]["id"] == "router"
    assert plist.calls.last.request.url.params["model"] == "gemma"
    assert c.notes.add("hello", category="fact")["id"] == "n1"
    assert c.notes.list()[0]["text"] == "x"


@respx.mock
def test_routing_agents_satellites_trace() -> None:
    respx.get(f"{BASE}/v1/routing/policies").mock(
        return_value=httpx.Response(200, json={"ok": True, "active": "thompson", "policies": ["thompson", "epsilon"]})
    )
    respx.post(f"{BASE}/v1/routing/policy").mock(
        return_value=httpx.Response(200, json={"ok": True, "active": "epsilon"})
    )
    respx.get(f"{BASE}/v1/agents").mock(
        return_value=httpx.Response(200, json={"ok": True, "agents": [{"id": "a1", "state": "running"}]})
    )
    respx.post(f"{BASE}/v1/satellites/sat1/stop").mock(
        return_value=httpx.Response(200, json={"ok": True, "id": "sat1"})
    )
    respx.post(f"{BASE}/v1/trace").mock(
        return_value=httpx.Response(200, json={"ok": True, "prompts": "full", "level": 2})
    )
    c = _c()
    assert c.routing.policies()["active"] == "thompson"
    assert c.routing.set_policy("epsilon")["active"] == "epsilon"
    assert c.agents.list()[0]["id"] == "a1"
    assert c.satellites.stop("sat1")["id"] == "sat1"
    assert c.trace.set("full")["prompts"] == "full"


@respx.mock
def test_files_manifesto_plan_autonomy() -> None:
    respx.get(f"{BASE}/v1/files/content").mock(
        return_value=httpx.Response(200, json={"ok": True, "path": "a.txt", "binary": False, "content": "hi"})
    )
    respx.post(f"{BASE}/v1/files/content").mock(
        return_value=httpx.Response(200, json={"ok": True, "path": "a.txt", "size": 2})
    )
    respx.get(f"{BASE}/v1/manifesto/all").mock(
        return_value=httpx.Response(200, json={"ok": True, "composed": "MANIFESTO"})
    )
    respx.get(f"{BASE}/v1/plan").mock(return_value=httpx.Response(200, json={"panels": []}))
    respx.get(f"{BASE}/v1/autonomy").mock(
        return_value=httpx.Response(200, json={"default": 1, "always": False, "levels": []})
    )
    c = _c()
    assert c.files.read("a.txt")["content"] == "hi"
    assert c.files.write("a.txt", "hi")["size"] == 2
    assert c.manifesto.get()["composed"] == "MANIFESTO"
    assert c.plan() == {"panels": []}
    assert c.autonomy()["default"] == 1


@respx.mock
async def test_async_ext_parity() -> None:
    respx.post(f"{BASE}/v1/rl/learning").mock(
        return_value=httpx.Response(200, json={"ok": True, "learning": False})
    )
    respx.get(f"{BASE}/v1/connectors").mock(
        return_value=httpx.Response(200, json={"ok": True, "connectors": [{"name": "jira"}]})
    )
    async with ntropi.nbot.AsyncClient(BASE, token="t") as ac:
        assert (await ac.rl.set_learning(False))["learning"] is False
        assert (await ac.connectors.list())[0]["name"] == "jira"
