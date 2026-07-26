"""Project config management — read and write a project's ``node.toml``.

This is the "develop" surface: define a node's model pool, control server, and
security from Python, then launch nbot against it — no hand-editing TOML. It is
file-based and bound to a project directory (``<project>/.nconfig/node.toml``),
independent of any running serve.

Credentials stay as references (``api_key="env:INFERCOM_APIKEY"``); this module
never inlines a secret into the file.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

try:
    import tomllib  # type: ignore[import-not-found,unused-ignore]
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

import tomli_w

from .._exceptions import NtropiError


class PoolConfig:
    """The configured ``[[llm]]`` pool — the models a launched node will load.

    Distinct from the *live* pool (``client.pool.list()``): this is what the
    config declares, editable before the node starts.
    """

    def __init__(self, entries: list[dict[str, Any]]) -> None:
        self._entries = entries

    def list(self) -> list[dict[str, Any]]:
        return [*self._entries]

    def get(self, model_id: str) -> dict[str, Any] | None:
        for e in self._entries:
            if e.get("id") == model_id:
                return e
        return None

    def add(
        self,
        model_id: str,
        *,
        endpoint: str,
        model: str,
        type: str = "openai_compat",
        capacity: float = 8.0,
        n_ctx: int | None = None,
        api_key: str | None = None,
        modalities: Sequence[str] | None = None,
        tags: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Add or replace an ``[[llm]]`` entry. ``api_key`` should be an ``env:`` ref."""
        entry: dict[str, Any] = {
            "id": model_id,
            "type": type,
            "endpoint": endpoint,
            "model": model,
            "capacity": capacity,
        }
        if n_ctx is not None:
            entry["n_ctx"] = n_ctx
        if api_key is not None:
            entry["api_key"] = api_key
        if modalities:
            entry["modalities"] = list(modalities)
        if tags:
            entry["tags"] = list(tags)
        self.remove(model_id)
        self._entries.append(entry)
        return entry

    def remove(self, model_id: str) -> bool:
        before = len(self._entries)
        self._entries[:] = [e for e in self._entries if e.get("id") != model_id]
        return len(self._entries) < before


class Config:
    """A project's ``node.toml``, loaded for editing.

    ``Config(project)`` reads ``<project>/.nconfig/node.toml`` (empty if absent).
    Mutate via :attr:`pool` / :meth:`set`, then :meth:`save`.
    """

    def __init__(self, project: str, *, data: dict[str, Any] | None = None) -> None:
        self.project = os.path.abspath(project)
        self.path = Path(self.project) / ".nconfig" / "node.toml"
        if data is not None:
            self._data = data
        elif self.path.exists():
            with open(self.path, "rb") as f:
                self._data = tomllib.load(f)
        else:
            self._data = {}

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    @property
    def pool(self) -> PoolConfig:
        entries = self._data.setdefault("llm", [])
        if not isinstance(entries, list):
            raise NtropiError("node.toml [[llm]] is not a table array")
        return PoolConfig(entries)

    @property
    def control(self) -> dict[str, Any]:
        node = self._data.setdefault("node", {})
        control = node.setdefault("control", {})
        return control if isinstance(control, dict) else {}

    def set(self, section: str, key: str, value: Any) -> None:
        """Set ``value`` under a dotted ``section`` (e.g. ``"node.security"``)."""
        cursor: dict[str, Any] = self._data
        for part in section.split(".") if section else []:
            nxt = cursor.setdefault(part, {})
            if not isinstance(nxt, dict):
                raise NtropiError(f"{section} is not a table")
            cursor = nxt
        cursor[key] = value

    def save(self) -> Path:
        """Write the config back to ``node.toml`` (creating ``.nconfig/``)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "wb") as f:
            tomli_w.dump(self._data, f)
        return self.path

    @classmethod
    def create(cls, project: str, *, node_id: str = "node") -> Config:
        """A minimal config: loopback control on a dynamic port, empty pool."""
        data: dict[str, Any] = {
            "node": {
                "id": node_id,
                "control": {"bind": "127.0.0.1", "port": 0, "http_autoapprove": True},
            },
            "llm": [],
        }
        return cls(project, data=data)
