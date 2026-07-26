"""Phase-3 tests — the ntropi.web gateway surface (sync + async) via respx:
auth, tasks/chat (blocking + SSE), read surfaces, binary downloads, admin
(keys / users / settings), adapters, mcp, and proxy passthrough."""

from __future__ import annotations

import httpx
import respx

import ntropi

BASE = "http://w"


def _c() -> ntropi.web.Client:
    return ntropi.web.Client(BASE, key="k", admin_token="adm")


@respx.mock
def test_health_me_command() -> None:
    respx.get(f"{BASE}/api/v1/health").mock(
        return_value=httpx.Response(200, json={"gateway_status": "ok"})
    )
    respx.get(f"{BASE}/api/v1/auth/me").mock(
        return_value=httpx.Response(200, json={"authenticated": True, "email": "a@b.c"})
    )
    respx.post(f"{BASE}/api/v1/command").mock(
        return_value=httpx.Response(200, json={"ok": True, "output": "pool…"})
    )
    c = _c()
    assert c.health()["gateway_status"] == "ok"
    assert c.me()["email"] == "a@b.c"
    assert c.command("/pool")["output"] == "pool…"


@respx.mock
def test_auth_header_and_admin_token_sent() -> None:
    route = respx.get(f"{BASE}/api/v1/auth/me").mock(
        return_value=httpx.Response(200, json={"authenticated": False})
    )
    _c().me()
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer k"
    assert req.headers["X-Admin-Token"] == "adm"


@respx.mock
def test_tasks_submit_and_stream() -> None:
    respx.post(f"{BASE}/api/v1/tasks").mock(
        return_value=httpx.Response(200, json={"session_id": "s1", "content": "done"})
    )
    sse = "data: {\"type\": \"token\", \"text\": \"hi\"}\n\ndata: {\"type\": \"done\", \"ok\": true}\n\n"
    respx.post(f"{BASE}/api/v1/tasks/stream").mock(
        return_value=httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})
    )
    c = _c()
    assert c.tasks.submit("hello", new_session=True)["session_id"] == "s1"
    events = list(c.tasks.stream("hello"))
    assert [e["type"] for e in events] == ["token", "done"]


@respx.mock
def test_chat_surface() -> None:
    respx.post(f"{BASE}/api/v1/chat").mock(
        return_value=httpx.Response(200, json={"session_id": "c1", "content": "ok"})
    )
    respx.get(f"{BASE}/api/v1/chat/sessions").mock(
        return_value=httpx.Response(200, json={"sessions": [{"id": "c1"}]})
    )
    respx.delete(f"{BASE}/api/v1/chat/session/c1").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    c = _c()
    assert c.chat.send("hi")["session_id"] == "c1"
    assert c.chat.sessions()[0]["id"] == "c1"
    assert c.chat.delete("c1")["ok"] is True


@respx.mock
def test_read_surfaces_and_binary() -> None:
    respx.get(f"{BASE}/api/v1/projects").mock(
        return_value=httpx.Response(200, json={"projects": [{"path": "/p"}]})
    )
    respx.get(f"{BASE}/api/v1/kb").mock(
        return_value=httpx.Response(200, json={"files": [{"id": "f1"}]})
    )
    respx.get(f"{BASE}/api/v1/kb/file/f1").mock(
        return_value=httpx.Response(200, content=b"\x00rawbytes")
    )
    respx.get(f"{BASE}/api/v1/mesh.nbt").mock(return_value=httpx.Response(200, content=b"MESH"))
    c = _c()
    assert c.read.projects()[0]["path"] == "/p"
    assert c.read.kb()[0]["id"] == "f1"
    assert c.read.kb_file("f1") == b"\x00rawbytes"
    assert c.read.mesh() == b"MESH"


@respx.mock
def test_blueprints() -> None:
    respx.get(f"{BASE}/api/v1/blueprints/list").mock(
        return_value=httpx.Response(200, json={"blueprints": [{"id": "bp1"}]})
    )
    respx.post(f"{BASE}/api/v1/blueprints/run").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    respx.get(f"{BASE}/api/v1/blueprints/bp1").mock(
        return_value=httpx.Response(200, content=b"{\"steps\": []}")
    )
    c = _c()
    assert c.blueprints.list()[0]["id"] == "bp1"
    assert c.blueprints.run("bp1", {"x": 1})["ok"] is True
    assert c.blueprints.get("bp1") == b"{\"steps\": []}"


@respx.mock
def test_admin_keys_users_settings() -> None:
    respx.post(f"{BASE}/api/v1/admin/api-keys").mock(
        return_value=httpx.Response(201, json={"key": {"id": "k1"}, "secret": "sk-xyz"})
    )
    respx.delete(f"{BASE}/api/v1/admin/api-keys/k1").mock(
        return_value=httpx.Response(200, json={"id": "k1"})
    )
    respx.post(f"{BASE}/api/v1/admin/users").mock(
        return_value=httpx.Response(201, json={"email": "u@x.y", "role": "user"})
    )
    respx.patch(f"{BASE}/api/v1/admin/users/u@x.y").mock(
        return_value=httpx.Response(200, json={"email": "u@x.y", "role": "admin"})
    )
    respx.put(f"{BASE}/api/v1/admin/settings").mock(
        return_value=httpx.Response(200, json={"nbot_base_url": "http://n:1"})
    )
    c = _c()
    assert c.admin.keys.create("mobile")["secret"] == "sk-xyz"
    assert c.admin.keys.revoke("k1")["id"] == "k1"
    assert c.admin.users.create("u@x.y")["email"] == "u@x.y"
    assert c.admin.users.update("u@x.y", role="admin")["role"] == "admin"
    assert c.admin.update_settings("http://n:1")["nbot_base_url"] == "http://n:1"


@respx.mock
def test_mcp_and_proxy() -> None:
    respx.post(f"{BASE}/api/v1/mcp").mock(
        return_value=httpx.Response(200, json={"id": 1, "result": {"tools": []}})
    )
    respx.get(f"{BASE}/proxy/v1/pool").mock(
        return_value=httpx.Response(200, json={"models": [{"id": "gemma"}]})
    )
    c = _c()
    assert c.mcp("tools/list")["result"]["tools"] == []
    assert c.proxy("GET", "/v1/pool")["models"][0]["id"] == "gemma"


@respx.mock
async def test_async_twin_parity() -> None:
    respx.get(f"{BASE}/api/v1/health").mock(
        return_value=httpx.Response(200, json={"gateway_status": "ok"})
    )
    sse = "data: {\"type\": \"token\", \"text\": \"x\"}\n\n"
    respx.post(f"{BASE}/api/v1/chat/stream").mock(
        return_value=httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})
    )
    async with ntropi.web.AsyncClient(BASE, key="k") as ac:
        assert (await ac.health())["gateway_status"] == "ok"
        events = [e async for e in ac.chat.stream("hi")]
        assert events[0]["text"] == "x"
