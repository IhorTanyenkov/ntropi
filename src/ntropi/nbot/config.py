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

    def _append_unique(self, table: str, entry: dict[str, Any], key: str) -> dict[str, Any]:
        """Append (or replace by ``key``) an entry into a top-level table-array."""
        arr = self._data.setdefault(table, [])
        if not isinstance(arr, list):
            raise NtropiError(f"node.toml [[{table}]] is not a table array")
        arr[:] = [e for e in arr if e.get(key) != entry.get(key)]
        arr.append(entry)
        return entry

    def set_node(
        self,
        *,
        id: str | None = None,
        listen: str | None = None,
        log_level: str | None = None,
        chrome_path: str | None = None,
    ) -> Config:
        """Set top-level ``[node]`` fields (identity, bind, logging, headless Chrome)."""
        for k, v in {
            "id": id,
            "listen": listen,
            "log_level": log_level,
            "chrome_path": chrome_path,
        }.items():
            if v is not None:
                self.set("node", k, v)
        return self

    def set_security(
        self, *, allowed_paths: Sequence[str] | None = None, peer_secret: str | None = None
    ) -> Config:
        """``[node.security]`` — filesystem allow-list and the mesh peer secret."""
        if allowed_paths is not None:
            self.set("node.security", "allowed_paths", list(allowed_paths))
        if peer_secret is not None:
            self.set("node.security", "peer_secret", peer_secret)
        return self

    def set_license(self, *, key: str | None = None, license_server: str | None = None) -> Config:
        """``[license]`` — the operator key and (optionally) an override server."""
        if key is not None:
            self.set("license", "key", key)
        if license_server is not None:
            self.set("license", "license_server", license_server)
        return self

    def set_network(
        self, *, encrypt: bool | None = None, search_relay: bool | None = None
    ) -> Config:
        """``[network]`` — CURVE encryption and search-delegation relay."""
        if encrypt is not None:
            self.set("network", "encrypt", encrypt)
        if search_relay is not None:
            self.set("network", "search_relay", search_relay)
        return self

    def set_rl(self, policy: str) -> Config:
        """``[rl]`` — the routing policy (``"thompson"`` | ``"epsilon"``)."""
        self.set("rl", "policy", policy)
        return self

    def set_runtime(
        self,
        *,
        max_bg_agents_per_prompt: int | None = None,
        max_recursion_depth: int | None = None,
        blueprint_autoselect: bool | None = None,
    ) -> Config:
        """``[runtime]`` — decomposition/agent budgets and blueprint auto-selection."""
        for k, v in {
            "max_bg_agents_per_prompt": max_bg_agents_per_prompt,
            "max_recursion_depth": max_recursion_depth,
            "blueprint_autoselect": blueprint_autoselect,
        }.items():
            if v is not None:
                self.set("runtime", k, v)
        return self

    def set_trace(self, prompts: str) -> Config:
        """``[trace]`` — prompt-trace verbosity (``"off"`` | ``"meta"`` | ``"full"``)."""
        self.set("trace", "prompts", prompts)
        return self

    def add_connector(
        self,
        name: str,
        *,
        base_url: str,
        type: str = "http",
        description: str | None = None,
        auth: str = "none",
        token: str | None = None,
        header_name: str | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        """Add or replace a ``[[connector]]`` (external-system tool)."""
        entry: dict[str, Any] = {"name": name, "type": type, "base_url": base_url, "auth": auth}
        if description is not None:
            entry["description"] = description
        if token is not None:
            entry["token"] = token
        if header_name is not None:
            entry["header_name"] = header_name
        if timeout_s is not None:
            entry["timeout_s"] = timeout_s
        return self._append_unique("connector", entry, "name")

    def add_peer(
        self, address: str, *, trusted: bool = False, pubkey: str | None = None
    ) -> dict[str, Any]:
        """Add or replace a ``[[peers]]`` mesh peer."""
        entry: dict[str, Any] = {"address": address, "trusted": trusted}
        if pubkey is not None:
            entry["pubkey"] = pubkey
        return self._append_unique("peers", entry, "address")

    def add_satellite(
        self,
        command: str,
        *,
        working_dir: str | None = None,
        autostart: bool = False,
        ready_port: int | None = None,
        ready_log: str | None = None,
        max_restarts: int | None = None,
    ) -> dict[str, Any]:
        """Add or replace a ``[[satellite]]`` managed process."""
        entry: dict[str, Any] = {"command": command, "autostart": autostart}
        if working_dir is not None:
            entry["working_dir"] = working_dir
        if ready_port is not None:
            entry["ready_port"] = ready_port
        if ready_log is not None:
            entry["ready_log"] = ready_log
        if max_restarts is not None:
            entry["max_restarts"] = max_restarts
        return self._append_unique("satellite", entry, "command")

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
