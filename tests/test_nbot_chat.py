"""Phase-1c tests — models, the OpenAI-compatible completions facade (create +
stream), and native chat mode — against respx mocks."""

from __future__ import annotations

import httpx
import respx

import ntropi


def _client() -> ntropi.nbot.Client:
    return ntropi.nbot.Client("http://n", token="")


@respx.mock
def test_models_list() -> None:
    respx.get("http://n/v1/models").mock(
        return_value=httpx.Response(
            200, json={"object": "list", "data": [{"id": "nbot"}, {"id": "gemma"}]}
        )
    )
    assert [m["id"] for m in _client().models.list()] == ["nbot", "gemma"]


@respx.mock
def test_completions_create_openai_shape() -> None:
    route = respx.post("http://n/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "hi"}}],
            },
        )
    )
    r = _client().chat.completions.create(
        model="nbot", messages=[{"role": "user", "content": "hi"}], autonomy="full"
    )
    assert r["choices"][0]["message"]["content"] == "hi"
    sent = route.calls.last.request
    body = sent.read().decode()
    assert '"stream": false' in body or '"stream":false' in body
    assert "autonomy" in body


@respx.mock
def test_completions_stream_chunks() -> None:
    frames = (
        'data: {"choices":[{"delta":{"role":"assistant"}}]}\n'
        'data: {"choices":[{"delta":{"content":"he"}}]}\n'
        'data: {"choices":[{"delta":{"content":"llo"}}]}\n'
        "data: [DONE]\n"
    )
    respx.post("http://n/v1/chat/completions").mock(
        return_value=httpx.Response(200, text=frames, headers={"content-type": "text/event-stream"})
    )
    chunks = list(
        _client().chat.completions.stream(messages=[{"role": "user", "content": "hi"}])
    )
    text = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks)
    assert text == "hello"


@respx.mock
def test_native_chat_send() -> None:
    respx.post("http://n/v1/chat").mock(
        return_value=httpx.Response(200, json={"ok": True, "session_id": "c-1", "response": "ok"})
    )
    r = _client().chat.send("hi", new_session=True)
    assert r.session_id == "c-1" and r.response == "ok"


@respx.mock
def test_native_chat_sessions_and_delete() -> None:
    respx.get("http://n/v1/chat/sessions").mock(
        return_value=httpx.Response(200, json={"sessions": [{"id": "c-1", "msg_count": 2}]})
    )
    respx.delete("http://n/v1/chat/session/c-1").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    c = _client()
    assert c.chat.sessions()[0].id == "c-1"
    assert c.chat.delete("c-1") is True
