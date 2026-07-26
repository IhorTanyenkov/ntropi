"""Phase-1b config tests — read/write node.toml, pool add/remove — on a tmp
project dir, no live serve."""

from __future__ import annotations

from pathlib import Path

from ntropi.nbot import Config


def test_create_add_save_roundtrip(tmp_path: Path) -> None:
    cfg = Config.create(str(tmp_path), node_id="rtx")
    cfg.pool.add(
        "infercom-gemma-4-31b",
        endpoint="https://api.infercom.ai/v1",
        model="gemma-4-31B-it",
        capacity=8.0,
        n_ctx=131072,
        api_key="env:INFERCOM_APIKEY",
        modalities=["image_in"],
    )
    cfg.set("node.security", "allowed_paths", ["/"])
    path = cfg.save()
    assert path == tmp_path / ".nconfig" / "node.toml"

    reloaded = Config(str(tmp_path))
    assert reloaded.data["node"]["id"] == "rtx"
    entry = reloaded.pool.get("infercom-gemma-4-31b")
    assert entry is not None
    assert entry["model"] == "gemma-4-31B-it"
    assert entry["api_key"] == "env:INFERCOM_APIKEY"
    assert entry["modalities"] == ["image_in"]
    assert reloaded.data["node"]["security"]["allowed_paths"] == ["/"]


def test_add_replaces_same_id(tmp_path: Path) -> None:
    cfg = Config.create(str(tmp_path))
    cfg.pool.add("m", endpoint="e1", model="a")
    cfg.pool.add("m", endpoint="e2", model="b")
    assert len(cfg.pool.list()) == 1
    assert cfg.pool.get("m")["endpoint"] == "e2"


def test_remove(tmp_path: Path) -> None:
    cfg = Config.create(str(tmp_path))
    cfg.pool.add("m", endpoint="e", model="a")
    assert cfg.pool.remove("m") is True
    assert cfg.pool.remove("m") is False
    assert cfg.pool.list() == []


def test_credential_stays_a_reference(tmp_path: Path) -> None:
    cfg = Config.create(str(tmp_path))
    cfg.pool.add("m", endpoint="e", model="a", api_key="env:SECRET")
    text = cfg.save().read_text()
    assert "env:SECRET" in text
    assert "SECRET=" not in text
