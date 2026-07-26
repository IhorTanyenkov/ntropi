"""Phase-5 tests — the ntropi CLI (Typer) via CliRunner + respx."""

from __future__ import annotations

import httpx
import respx
from typer.testing import CliRunner

from ntropi.cli import _build_app

runner = CliRunner()
BASE = "http://n"


def test_version() -> None:
    import ntropi

    result = runner.invoke(_build_app(), ["version"])
    assert result.exit_code == 0
    assert ntropi.__version__ in result.stdout


@respx.mock
def test_pool_command() -> None:
    respx.get(f"{BASE}/v1/pool").mock(
        return_value=httpx.Response(
            200, json={"models": [{"id": "gemma-31b", "node": "rtx", "capacity": 8.0}]}
        )
    )
    result = runner.invoke(_build_app(), ["pool", "--url", BASE])
    assert result.exit_code == 0
    assert "gemma-31b" in result.stdout


@respx.mock
def test_rl_learning_show_and_set() -> None:
    respx.get(f"{BASE}/v1/rl/learning").mock(
        return_value=httpx.Response(200, json={"ok": True, "learning": True})
    )
    set_route = respx.post(f"{BASE}/v1/rl/learning").mock(
        return_value=httpx.Response(200, json={"ok": True, "learning": False})
    )
    show = runner.invoke(_build_app(), ["rl-learning", "--url", BASE])
    assert show.exit_code == 0 and '"learning": true' in show.stdout
    off = runner.invoke(_build_app(), ["rl-learning", "off", "--url", BASE])
    assert off.exit_code == 0 and '"learning": false' in off.stdout
    assert set_route.calls.last.request.read() == b'{"enabled":false}'
