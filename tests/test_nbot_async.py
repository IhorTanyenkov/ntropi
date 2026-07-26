"""Phase-1d tests — the async twin has parity with sync: health, typed pool,
task submit, streamed events, and the command namespace — via respx."""

from __future__ import annotations

import httpx
import pytest
import respx

import ntropi


def _client() -> ntropi.nbot.AsyncClient:
    return ntropi.nbot.AsyncClient("http://n", token="")


@respx.mock
@pytest.mark.asyncio
async def test_async_health_and_pool() -> None:
    respx.get("http://n/v1/health").mock(return_value=httpx.Response(200, json={"ok": True}))
    respx.get("http://n/v1/pool").mock(
        return_value=httpx.Response(200, json={"models": [{"id": "gemma", "capacity": 8.0}]})
    )
    async with _client() as c:
        assert (await c.health())["ok"] is True
        models = await c.pool.list()
        assert models[0].id == "gemma"


@respx.mock
@pytest.mark.asyncio
async def test_async_task_submit() -> None:
    respx.post("http://n/v1/task/submit").mock(
        return_value=httpx.Response(200, json={"ok": True, "session_id": "s-9", "response": "ok"})
    )
    async with _client() as c:
        r = await c.tasks.submit("hi", new_session=True)
        assert r.session_id == "s-9"


@respx.mock
@pytest.mark.asyncio
async def test_async_task_stream() -> None:
    frames = (
        'data: {"type":"token","text":"he"}\n'
        'data: {"type":"token","text":"llo"}\n'
        'data: {"type":"done","ok":true,"session_id":"s-3"}\n'
    )
    respx.post("http://n/v1/task/stream").mock(
        return_value=httpx.Response(200, text=frames, headers={"content-type": "text/event-stream"})
    )
    async with _client() as c:
        got = [ev async for ev in c.tasks.stream("hi")]
    assert "".join(e.text or "" for e in got if e.is_token) == "hello"
    assert got[-1].is_done


@respx.mock
@pytest.mark.asyncio
async def test_async_command_namespace() -> None:
    respx.post("http://n/v1/command").mock(
        return_value=httpx.Response(200, json={"ok": True, "output": "MODEL NODE\n..."})
    )
    async with _client() as c:
        assert (await c.command.pool()).startswith("MODEL")
        assert (await c.command.status()).startswith("MODEL")


@respx.mock
def test_sync_command_namespace() -> None:
    respx.post("http://n/v1/command").mock(
        return_value=httpx.Response(200, json={"ok": True, "output": "OK"})
    )
    c = ntropi.nbot.Client("http://n", token="")
    assert c.command.rl() == "OK"
    assert c.command.pool() == "OK"
