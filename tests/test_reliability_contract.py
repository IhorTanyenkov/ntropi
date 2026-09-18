"""Prevent duplicate writes and preserve real Horizon timestamp responses."""

import httpx
import pytest

from ntropi._base import AsyncBaseClient, BaseClient, _ClientConfig
from ntropi._exceptions import APITimeoutError, UpstreamUnavailable
from ntropi.horizon.types import SuiteRun


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize("failure", ["503", "timeout"])
def test_mutation_is_never_automatically_replayed(method, failure):
    calls = []

    def handler(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("ambiguous response", request=request)
        return httpx.Response(503, json={"error": "unavailable"})

    with httpx.Client(base_url="http://fixture", transport=httpx.MockTransport(handler)) as http:
        client = BaseClient(_ClientConfig("http://fixture"), http=http)
        with pytest.raises(APITimeoutError if failure == "timeout" else UpstreamUnavailable):
            client.request(method, "/mutation", json={})
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize("failure", ["503", "timeout"])
async def test_async_mutation_is_never_automatically_replayed(method, failure):
    calls = []

    def handler(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("ambiguous response", request=request)
        return httpx.Response(503, json={"error": "unavailable"})

    async with httpx.AsyncClient(base_url="http://fixture", transport=httpx.MockTransport(handler)) as http:
        client = AsyncBaseClient(_ClientConfig("http://fixture"), http=http)
        with pytest.raises(APITimeoutError if failure == "timeout" else UpstreamUnavailable):
            await client.request(method, "/mutation", json={})
    assert len(calls) == 1


def test_safe_read_retries(monkeypatch):
    calls = []
    monkeypatch.setattr("ntropi._base._backoff", lambda _: 0)

    def handler(request):
        calls.append(request)
        return httpx.Response(503 if len(calls) < 3 else 200, json={"ok": True})

    with httpx.Client(base_url="http://fixture", transport=httpx.MockTransport(handler)) as http:
        client = BaseClient(_ClientConfig("http://fixture"), http=http)
        assert client.request("GET", "/status") == {"ok": True}
    assert len(calls) == 3


@pytest.mark.parametrize("stamp", [1789670941000, "2026-09-17T21:00:00Z", None])
def test_suite_preserves_wire_timestamp(stamp):
    result = SuiteRun.model_validate({"run_at": stamp, "passed": 2, "total": 2, "rate": 1.0})
    assert result.run_at == stamp
    assert result.passed == result.total == 2
