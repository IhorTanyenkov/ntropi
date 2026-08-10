"""One platform key across nbot + Horizon: ``NTROPI_API_KEY`` is the shared
fallback, with per-service vars (``NTROPI_NBOT_TOKEN`` / ``NTROPI_HORIZON_KEY``)
taking precedence when a deployment wants distinct credentials."""

from __future__ import annotations

import httpx
import pytest
import respx

import ntropi
from ntropi._base import resolve_credential


def test_resolve_credential_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SVC", "svc")
    monkeypatch.setenv("PLATFORM", "plat")
    assert resolve_credential("explicit", "SVC", "PLATFORM") == "explicit"
    assert resolve_credential(None, "SVC", "PLATFORM") == "svc"
    monkeypatch.delenv("SVC", raising=False)
    assert resolve_credential(None, "SVC", "PLATFORM") == "plat"
    monkeypatch.delenv("PLATFORM", raising=False)
    assert resolve_credential(None, "SVC", "PLATFORM") is None


@respx.mock
def test_nbot_uses_platform_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NTROPI_NBOT_TOKEN", raising=False)
    monkeypatch.setenv("NTROPI_API_KEY", "PLATKEY")
    route = respx.get("http://n/v1/health").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    ntropi.nbot.Client("http://n").auth.status()
    assert route.calls.last.request.headers["authorization"] == "Bearer PLATKEY"


@respx.mock
def test_horizon_uses_platform_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NTROPI_HORIZON_KEY", raising=False)
    monkeypatch.setenv("NTROPI_API_KEY", "PLATKEY")
    route = respx.get("http://h/api/suites").mock(
        return_value=httpx.Response(200, json=[{"id": "gsm8k"}])
    )
    ntropi.horizon.Client("http://h").suites.list()
    assert route.calls.last.request.headers["x-api-key"] == "PLATKEY"


@respx.mock
def test_service_var_beats_platform_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NTROPI_NBOT_TOKEN", "SVCKEY")
    monkeypatch.setenv("NTROPI_API_KEY", "PLATKEY")
    route = respx.get("http://n/v1/health").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    ntropi.nbot.Client("http://n").auth.status()
    assert route.calls.last.request.headers["authorization"] == "Bearer SVCKEY"
