"""Synchronous typed resources for the nbot node's structured HTTP surface.

These cover the *teach / trace / connect* endpoints that previously were only
reachable as human-text through ``client.command`` (or not at all): node-side RL,
blueprints, KB, research, artifacts, prompts, notes, connectors, routing,
agents, satellites, trace, files, and manifesto. Field names mirror the node's
``/v1/*`` contract exactly. The async twins live in ``resources_ext_async``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal
from urllib.parse import quote

from .._base import BaseClient

Signal = Literal["positive", "negative"]
TracePrompts = Literal["off", "meta", "full"]


def _obj(x: Any) -> dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _arr(x: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        v = x.get(key, [])
        return v if isinstance(v, list) else []
    return []


class RLResource:
    """The node's own routing policy — learning toggle, feedback, checkpoints.

    Distinct from ``ntropi.horizon``'s RL (the training backend): this is the
    live policy on the node itself.
    """

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def learning(self) -> dict[str, Any]:
        """``{ok, learning, notes_learning}`` — is the policy adapting right now?"""
        return _obj(self._http.request("GET", "/v1/rl/learning"))

    def set_learning(self, enabled: bool) -> dict[str, Any]:
        """Freeze (``False``) or resume (``True``) online learning — for clean eval."""
        return _obj(self._http.request("POST", "/v1/rl/learning", json={"enabled": enabled}))

    def feedback(self, session_id: str, signal: Signal) -> dict[str, Any]:
        """Attach a satisfaction signal to a turn (retroactive reward)."""
        body = {"session_id": session_id, "signal": signal}
        return _obj(self._http.request("POST", "/v1/rl/feedback", json=body))

    def replay(
        self,
        outcomes: Sequence[dict[str, Any]] | None = None,
        *,
        reset: bool = False,
        save: bool = True,
    ) -> dict[str, Any]:
        """Replay logged (state, action, reward) outcomes through the policy."""
        body: dict[str, Any] = {"reset": reset, "save": save}
        if outcomes is not None:
            body["outcomes"] = list(outcomes)
        return _obj(self._http.request("POST", "/v1/rl/replay", json=body))

    def checkpoint(self, note: str | None = None) -> dict[str, Any]:
        body = {"note": note} if note is not None else {}
        return _obj(self._http.request("POST", "/v1/rl/checkpoint", json=body))

    def versions(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/v1/rl/versions"), "versions")

    def rollback(self, version: int) -> dict[str, Any]:
        return _obj(self._http.request("POST", f"/v1/rl/rollback/{version}"))

    def save(self) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/v1/rl/save"))

    def env_outcome(
        self, session_id: str, *, goal_met: bool = False, score: float | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"session_id": session_id, "goal_met": goal_met}
        if score is not None:
            body["score"] = score
        return _obj(self._http.request("POST", "/v1/rl/env-outcome", json=body))

    def export(self) -> dict[str, Any]:
        """Export the policy's learned state (policy-defined; may be non-exportable)."""
        return _obj(self._http.request("GET", "/v1/rl/export"))

    def import_(self, snapshot: dict[str, Any], *, save: bool = True) -> dict[str, Any]:
        body = {"snapshot": snapshot, "save": save}
        return _obj(self._http.request("POST", "/v1/rl/import", json=body))

    def reset(self) -> dict[str, Any]:
        """Reset the policy to cold-start (drives the ``/rl-reset`` command)."""
        return _obj(self._http.request("POST", "/v1/command", json={"command": "/rl-reset"}))


class BlueprintsResource:
    """Proven, followable-but-mutable recipe sequences on the node."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/v1/blueprints/list"), "blueprints")

    def get(self, blueprint_id: str) -> dict[str, Any]:
        return _obj(self._http.request("GET", f"/v1/blueprints/{quote(blueprint_id, safe='')}"))

    def run(self, blueprint_id: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        body = {"id": blueprint_id, "params": params or {}}
        return _obj(self._http.request("POST", "/v1/blueprints/run", json=body))

    def import_(self, blueprint: dict[str, Any]) -> dict[str, Any]:
        """Import a blueprint — the body IS the blueprint JSON."""
        return _obj(self._http.request("POST", "/v1/blueprints/import", json=blueprint))


class KBResource:
    """Knowledge base — ingest, list, download, forget."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def ingest(self, files: Sequence[dict[str, Any]]) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/v1/kb/ingest", json={"files": list(files)}))

    def list(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/v1/kb/list"), "files")

    def file(self, file_id: str) -> bytes:
        return self._http.content("GET", f"/v1/kb/file/{quote(file_id, safe='')}")

    def delete(self, file_id: str) -> dict[str, Any]:
        return _obj(self._http.request("DELETE", f"/v1/kb/{quote(file_id, safe='')}"))


class ResearchResource:
    """Deep-research jobs (search → fetch → cross-check → cited report)."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/v1/research"), "research")

    def get(self, research_id: str) -> dict[str, Any]:
        return _obj(self._http.request("GET", f"/v1/research/{quote(research_id, safe='')}"))


class ArtifactsResource:
    """The produced-artifact ledger (provenance graph)."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def graph(self) -> dict[str, Any]:
        """``{ok, artifacts}`` — the provenance graph of produced/derived files."""
        return _obj(self._http.request("GET", "/v1/artifacts"))


class PromptsResource:
    """The prompt registry — inspect and override control-plane prompts."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self, model: str | None = None) -> list[dict[str, Any]]:
        params = {"model": model} if model else None
        return _arr(self._http.request("GET", "/v1/prompts", params=params), "prompts")

    def set(
        self, prompt_id: str, *, template: str | None = None, scope: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"id": prompt_id}
        if template is not None:
            body["template"] = template
        if scope is not None:
            body["scope"] = scope
        return _obj(self._http.request("POST", "/v1/prompts", json=body))

    def delete(self, prompt_id: str, *, model: str | None = None) -> dict[str, Any]:
        params = {"model": model} if model else None
        return _obj(
            self._http.request("DELETE", f"/v1/prompts/{quote(prompt_id, safe='')}", params=params)
        )


class NotesResource:
    """The learned notes store (second bandit's content)."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/v1/notes"), "notes")

    def add(
        self, text: str, *, category: str = "observation", author: str = "user"
    ) -> dict[str, Any]:
        body = {"text": text, "category": category, "author": author}
        return _obj(self._http.request("POST", "/v1/notes", json=body))

    def delete(self, note_id: str) -> dict[str, Any]:
        return _obj(self._http.request("DELETE", f"/v1/notes/{quote(note_id, safe='')}"))


class ConnectorsResource:
    """Configured external-system connectors — inspect, probe, invoke."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/v1/connectors"), "connectors")

    def test(
        self, name: str, *, input: str | None = None, path: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if input is not None:
            body["input"] = input
        if path is not None:
            body["path"] = path
        return _obj(
            self._http.request("POST", f"/v1/connectors/{quote(name, safe='')}/test", json=body)
        )

    def call(self, name: str, input: str) -> dict[str, Any]:
        """Invoke a connector with an ``"METHOD /path [body]"`` instruction."""
        return _obj(
            self._http.request(
                "POST", f"/v1/connectors/{quote(name, safe='')}/call", json={"input": input}
            )
        )


class RoutingResource:
    """The active routing policy and the space it decides over."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def policies(self) -> dict[str, Any]:
        """``{ok, active, policies, action_space, state_space}``."""
        return _obj(self._http.request("GET", "/v1/routing/policies"))

    def set_policy(self, name: str) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/v1/routing/policy", json={"name": name}))


class AgentsResource:
    """Background autonomous agents — list, inspect, stop."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/v1/agents"), "agents")

    def get(self, agent_id: str) -> dict[str, Any]:
        return _obj(self._http.request("GET", f"/v1/agents/{quote(agent_id, safe='')}"))

    def stop(self, agent_id: str) -> dict[str, Any]:
        return _obj(self._http.request("POST", f"/v1/agents/{quote(agent_id, safe='')}/stop"))


class SatellitesResource:
    """Managed long-running processes — list, read output, stop."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/v1/satellites"), "satellites")

    def output(self, satellite_id: str) -> dict[str, Any]:
        return _obj(self._http.request("GET", f"/v1/satellites/{quote(satellite_id, safe='')}/output"))

    def stop(self, satellite_id: str) -> dict[str, Any]:
        return _obj(self._http.request("POST", f"/v1/satellites/{quote(satellite_id, safe='')}/stop"))


class TraceResource:
    """Prompt-trace verbosity of the node."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def get(self) -> dict[str, Any]:
        return _obj(self._http.request("GET", "/v1/trace"))

    def set(self, prompts: TracePrompts) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/v1/trace", json={"prompts": prompts}))


class FilesResource:
    """The project's file surface — list a directory, read, write."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self, path: str = "") -> dict[str, Any]:
        return _obj(self._http.request("GET", "/v1/files", params={"path": path}))

    def read(self, path: str) -> dict[str, Any]:
        """``{ok, path, size, binary, content | content_base64}``."""
        return _obj(self._http.request("GET", "/v1/files/content", params={"path": path}))

    def write(self, path: str, content: str) -> dict[str, Any]:
        body = {"path": path, "content": content}
        return _obj(self._http.request("POST", "/v1/files/content", json=body))


class ManifestoResource:
    """The composed manifesto and its editable layers (core / project)."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def get(self, layer: Literal["all", "core", "project"] = "all") -> dict[str, Any]:
        return _obj(self._http.request("GET", f"/v1/manifesto/{layer}"))

    def set(self, layer: Literal["core", "project"], content: str) -> dict[str, Any]:
        return _obj(self._http.request("POST", f"/v1/manifesto/{layer}", json={"content": content}))
