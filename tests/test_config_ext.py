"""Phase-5 tests — typed Config setters for the sovereignty / mesh sections."""

from __future__ import annotations

from pathlib import Path

from ntropi.nbot import Config


def test_typed_sections_write_expected_toml(tmp_path: Path) -> None:
    cfg = Config.create(str(tmp_path), node_id="rtx")
    cfg.set_license(key="env:NBOT_LICENSE_KEY", license_server="https://horizon.nbotchat.app")
    cfg.set_network(encrypt=True, search_relay=False)
    cfg.set_security(allowed_paths=["/data", "/models"], peer_secret="env:PEER")
    cfg.set_rl("epsilon")
    cfg.set_runtime(max_recursion_depth=4, blueprint_autoselect=True)
    cfg.add_connector("jira", base_url="https://jira.example", auth="bearer", token="env:JIRA")
    cfg.add_peer("tcp://10.0.0.2:5555", trusted=True, pubkey="abc")
    cfg.add_satellite("python worker.py", autostart=True, ready_port=9000)
    path = cfg.save()

    data = Config(str(tmp_path)).data  # reload from disk
    assert path.exists()
    assert data["license"]["license_server"] == "https://horizon.nbotchat.app"
    assert data["network"] == {"encrypt": True, "search_relay": False}
    assert data["node"]["security"]["allowed_paths"] == ["/data", "/models"]
    assert data["rl"]["policy"] == "epsilon"
    assert data["runtime"]["max_recursion_depth"] == 4
    assert data["connector"][0]["name"] == "jira"
    assert data["peers"][0]["trusted"] is True
    assert data["satellite"][0]["ready_port"] == 9000


def test_add_is_idempotent_by_key(tmp_path: Path) -> None:
    cfg = Config.create(str(tmp_path))
    cfg.add_connector("jira", base_url="https://a")
    cfg.add_connector("jira", base_url="https://b")  # replace, not duplicate
    connectors = cfg.data["connector"]
    assert len(connectors) == 1
    assert connectors[0]["base_url"] == "https://b"
