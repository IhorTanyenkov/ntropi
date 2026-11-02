"""Every streaming surface uses the SDK error contract without replaying work."""

import httpx
import pytest

from ntropi._base import AsyncBaseClient, BaseClient, _ClientConfig
from ntropi._exceptions import APITimeoutError, AuthenticationError
from ntropi.nbot import resources, resources_async
from ntropi.web import resources as web_resources
from ntropi.web import resources_async as web_resources_async

SYNC_RESOURCES = [
    resources.TasksResource,
    resources.ChatResource,
    resources.CompletionsResource,
    web_resources.TasksResource,
    web_resources.ChatResource,
]
ASYNC_RESOURCES = [
    resources_async.AsyncTasksResource,
    resources_async.AsyncChatResource,
    resources_async.AsyncCompletionsResource,
    web_resources_async.AsyncTasksResource,
    web_resources_async.AsyncChatResource,
]


def _events(resource):
    if "Completions" in type(resource).__name__:
        return resource.stream(messages=[{"role": "user", "content": "hello"}])
    return resource.stream("hello")


def _handler(calls, failure):
    def handler(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("fixture timeout", request=request)
        return httpx.Response(401, json={"error": "fixture unauthorized"})

    return handler


@pytest.mark.parametrize("resource_type", SYNC_RESOURCES)
@pytest.mark.parametrize("failure", ["unauthorized", "timeout"])
def test_sync_stream_errors_are_typed_and_never_retried(resource_type, failure):
    calls = []
    transport = httpx.MockTransport(_handler(calls, failure))
    with httpx.Client(base_url="http://fixture", transport=transport) as http:
        base = BaseClient(_ClientConfig("http://fixture"), http=http)
        expected = APITimeoutError if failure == "timeout" else AuthenticationError
        with pytest.raises(expected) as caught:
            list(_events(resource_type(base)))
    if failure == "unauthorized":
        assert caught.value.status == 401
        assert caught.value.payload == {"error": "fixture unauthorized"}
    assert len(calls) == 1


def test_sync_partial_stream_timeout_closes_response_without_replay():
    calls = []
    closed = []

    class InterruptedStream(httpx.SyncByteStream):
        def __iter__(self):
            yield b'data: {"type":"token","text":"partial"}\n\n'
            raise httpx.ReadTimeout("fixture interrupted")

        def close(self):
            closed.append(True)

    def handler(request):
        calls.append(request)
        return httpx.Response(200, stream=InterruptedStream())

    with httpx.Client(base_url="http://fixture", transport=httpx.MockTransport(handler)) as http:
        base = BaseClient(_ClientConfig("http://fixture"), http=http)
        events = resources.TasksResource(base).stream("hello")
        assert next(events).text == "partial"
        with pytest.raises(APITimeoutError):
            next(events)
    assert len(calls) == 1
    assert closed == [True]


@pytest.mark.parametrize("resource_type", ASYNC_RESOURCES)
@pytest.mark.parametrize("failure", ["unauthorized", "timeout"])
async def test_async_stream_errors_are_typed_and_never_retried(resource_type, failure):
    calls = []
    transport = httpx.MockTransport(_handler(calls, failure))
    async with httpx.AsyncClient(base_url="http://fixture", transport=transport) as http:
        base = AsyncBaseClient(_ClientConfig("http://fixture"), http=http)
        expected = APITimeoutError if failure == "timeout" else AuthenticationError
        with pytest.raises(expected) as caught:
            [event async for event in _events(resource_type(base))]
    if failure == "unauthorized":
        assert caught.value.status == 401
        assert caught.value.payload == {"error": "fixture unauthorized"}
    assert len(calls) == 1


async def test_async_partial_stream_timeout_closes_response_without_replay():
    calls = []
    closed = []

    class InterruptedStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"type":"token","text":"partial"}\n\n'
            raise httpx.ReadTimeout("fixture interrupted")

        async def aclose(self):
            closed.append(True)

    def handler(request):
        calls.append(request)
        return httpx.Response(200, stream=InterruptedStream())

    async with httpx.AsyncClient(
        base_url="http://fixture", transport=httpx.MockTransport(handler)
    ) as http:
        base = AsyncBaseClient(_ClientConfig("http://fixture"), http=http)
        events = resources_async.AsyncTasksResource(base).stream("hello")
        assert (await anext(events)).text == "partial"
        with pytest.raises(APITimeoutError):
            await anext(events)
    assert len(calls) == 1
    assert closed == [True]
