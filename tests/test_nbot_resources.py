"""Phase-1 nbot resource tests — pool, sessions, tasks (submit + stream),
projects — against respx-mocked responses (no live serve)."""

from __future__ import annotations

import httpx
import respx

import ntropi


def _client() -> ntropi.nbot.Client:
    return ntropi.nbot.Client("http://n", token="")


@respx.mock
def test_pool_list_typed() -> None:
    respx.get("http://n/v1/pool").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "models": [
                {"id": "gemma", "capacity": 8.0, "vision": True, "modalities": ["image_in"]},
                {"id": "oss-120b", "capacity": 8.5},
            ]},
        )
    )
    models = _client().pool.list()
    assert [m.id for m in models] == ["gemma", "oss-120b"]
    assert models[0].vision is True
    assert models[0].modalities == ["image_in"]


@respx.mock
def test_sessions_list_and_current() -> None:
    respx.get("http://n/v1/sessions").mock(
        return_value=httpx.Response(
            200,
            json={"current": "s-1", "sessions": [{"id": "s-1", "msg_count": 4}]},
        )
    )
    c = _client()
    assert c.sessions.current() == "s-1"
    assert c.sessions.list()[0].msg_count == 4


@respx.mock
def test_session_get_messages() -> None:
    respx.get("http://n/v1/session/s-1").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "id": "s-1", "project_id": "p",
                  "messages": [{"role": "user", "content": "hi"}]},
        )
    )
    s = _client().sessions.get("s-1")
    assert s.messages[0].role == "user"


@respx.mock
def test_task_submit_typed() -> None:
    respx.post("http://n/v1/task/submit").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "session_id": "s-2", "response": "done",
                  "produced": [{"id": "k-1", "name": "out.png", "kind": "image", "size": 10}]},
        )
    )
    r = _client().tasks.submit("make a png", new_session=True)
    assert r.ok and r.session_id == "s-2"
    assert r.produced[0].name == "out.png"


@respx.mock
def test_task_stream_typed_events() -> None:
    frames = (
        'data: {"type":"status","kind":"route","text":"-> gemma"}\n'
        ": ping\n"
        'data: {"type":"token","text":"hel"}\n'
        'data: {"type":"token","text":"lo"}\n'
        'data: {"type":"artifact","id":"k-9","name":"a.txt","kind":"file","size":2}\n'
        'data: {"type":"done","ok":true,"session_id":"s-3"}\n'
    )
    respx.post("http://n/v1/task/stream").mock(
        return_value=httpx.Response(200, text=frames, headers={"content-type": "text/event-stream"})
    )
    events = list(_client().tasks.stream("hi"))
    kinds = [e.type for e in events]
    assert kinds == ["status", "token", "token", "artifact", "done"]
    assert "".join(e.text or "" for e in events if e.is_token) == "hello"
    assert events[-1].is_done and events[-1].session_id == "s-3"


@respx.mock
def test_projects_use_via_command() -> None:
    respx.post("http://n/v1/command").mock(
        return_value=httpx.Response(200, json={"ok": True, "output": "switched to /p"})
    )
    assert "switched" in _client().projects.use("/p")
