"""Phase-0 smoke tests: the package imports, clients construct, transport maps
errors and retries — all without a live service (respx mocks httpx)."""

from __future__ import annotations

import httpx
import pytest
import respx

import ntropi
from ntropi._exceptions import AuthenticationError, NotFoundError, UpstreamUnavailable


def test_package_surface() -> None:
    assert ntropi.__version__
    assert hasattr(ntropi.nbot, "Client")
    assert hasattr(ntropi.horizon, "Client")
    assert hasattr(ntropi.web, "Client")


@respx.mock
def test_nbot_health() -> None:
    respx.get("http://n/v1/health").mock(
        return_value=httpx.Response(200, json={"ok": True, "node_id": "rtx"})
    )
    c = ntropi.nbot.Client("http://n", token="")
    assert c.health()["node_id"] == "rtx"


@respx.mock
def test_command_passthrough() -> None:
    respx.post("http://n/v1/command").mock(
        return_value=httpx.Response(200, json={"ok": True, "output": "MODEL  NODE\n..."})
    )
    c = ntropi.nbot.Client("http://n", token="")
    assert c.command("/pool").startswith("MODEL")


@respx.mock
def test_error_mapping() -> None:
    respx.get("http://n/v1/health").mock(return_value=httpx.Response(401, json={"error": "x"}))
    with pytest.raises(AuthenticationError):
        ntropi.nbot.Client("http://n", token="").health()


@respx.mock
def test_horizon_upstream_unavailable() -> None:
    respx.get("http://h/api/nbot").mock(return_value=httpx.Response(502, json={"error": "no nbot"}))
    with pytest.raises(UpstreamUnavailable):
        ntropi.horizon.Client("http://h").nbot_status()


@respx.mock
def test_retry_then_success() -> None:
    route = respx.get("http://n/v1/health")
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(200, json={"ok": True}),
    ]
    assert ntropi.nbot.Client("http://n", token="").health()["ok"] is True


@respx.mock
def test_not_found() -> None:
    respx.get("http://h/api/health").mock(return_value=httpx.Response(404))
    with pytest.raises(NotFoundError):
        ntropi.horizon.Client("http://h").health()


def test_connect_wires_given_services() -> None:
    stack = ntropi.connect(nbot_url="http://n", horizon_url="http://h")
    assert stack.nbot is not None
    assert stack.horizon is not None
    assert stack.web is None
