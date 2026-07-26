"""Auth surface — activate() writes the key file 0600; auth.status() projects the
license fields out of /v1/health (sync + async)."""

from __future__ import annotations

import stat
from pathlib import Path

import httpx
import pytest
import respx

import ntropi


def test_activate_writes_key_0600(tmp_path: Path) -> None:
    target = tmp_path / ".nbot" / "license.json"
    p = ntropi.nbot.activate("NBOT-XXXX-YYYY-ZZZZ", path=target)
    assert p == target
    import json

    assert json.loads(target.read_text())["key"] == "NBOT-XXXX-YYYY-ZZZZ"
    mode = stat.S_IMODE(target.stat().st_mode)
    assert mode == 0o600


@respx.mock
def test_status_licensed() -> None:
    respx.get("http://n/v1/health").mock(
        return_value=httpx.Response(
            200, json={"ok": True, "licensed": True, "operator": "it@e.ai", "plan": "pro"}
        )
    )
    st = ntropi.nbot.Client("http://n", token="").auth.status()
    assert st["enforced"] and st["licensed"] and st["plan"] == "pro"


@respx.mock
def test_status_not_enforced() -> None:
    respx.get("http://n/v1/health").mock(return_value=httpx.Response(200, json={"ok": True}))
    st = ntropi.nbot.Client("http://n", token="").auth.status()
    assert st == {"enforced": False}


@respx.mock
def test_status_denied_with_reason_and_grace() -> None:
    respx.get("http://n/v1/health").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "licensed": False, "operator": "", "plan": "",
                  "license_reason": "revoked", "grace_days_left": 3},
        )
    )
    st = ntropi.nbot.Client("http://n", token="").auth.status()
    assert st["licensed"] is False and st["reason"] == "revoked" and st["grace_days_left"] == 3


@respx.mock
@pytest.mark.asyncio
async def test_async_status() -> None:
    respx.get("http://n/v1/health").mock(
        return_value=httpx.Response(200, json={"ok": True, "licensed": True, "plan": "team"})
    )
    async with ntropi.nbot.AsyncClient("http://n", token="") as c:
        st = await c.auth.status()
    assert st["licensed"] and st["plan"] == "team"
