"""Asynchronous twins of ``resources_ext`` — identical surface, awaited."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal
from urllib.parse import quote

from .._base import AsyncBaseClient
from .resources_ext import Signal, TracePrompts, _arr, _obj


class AsyncRLResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def learning(self) -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/v1/rl/learning"))

    async def set_learning(self, enabled: bool) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/v1/rl/learning", json={"enabled": enabled}))

    async def feedback(self, session_id: str, signal: Signal) -> dict[str, Any]:
        body = {"session_id": session_id, "signal": signal}
        return _obj(await self._http.request("POST", "/v1/rl/feedback", json=body))

    async def replay(
        self,
        outcomes: Sequence[dict[str, Any]] | None = None,
        *,
        reset: bool = False,
        save: bool = True,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"reset": reset, "save": save}
        if outcomes is not None:
            body["outcomes"] = list(outcomes)
        return _obj(await self._http.request("POST", "/v1/rl/replay", json=body))

    async def checkpoint(self, note: str | None = None) -> dict[str, Any]:
        body = {"note": note} if note is not None else {}
        return _obj(await self._http.request("POST", "/v1/rl/checkpoint", json=body))

    async def versions(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/v1/rl/versions"), "versions")

    async def rollback(self, version: int) -> dict[str, Any]:
        return _obj(await self._http.request("POST", f"/v1/rl/rollback/{version}"))

    async def save(self) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/v1/rl/save"))

    async def env_outcome(
        self, session_id: str, *, goal_met: bool = False, score: float | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"session_id": session_id, "goal_met": goal_met}
        if score is not None:
            body["score"] = score
        return _obj(await self._http.request("POST", "/v1/rl/env-outcome", json=body))

    async def export(self) -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/v1/rl/export"))

    async def import_(self, snapshot: dict[str, Any], *, save: bool = True) -> dict[str, Any]:
        body = {"snapshot": snapshot, "save": save}
        return _obj(await self._http.request("POST", "/v1/rl/import", json=body))

    async def reset(self) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/v1/command", json={"command": "/rl-reset"}))


class AsyncBlueprintsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/v1/blueprints/list"), "blueprints")

    async def get(self, blueprint_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("GET", f"/v1/blueprints/{quote(blueprint_id, safe='')}"))

    async def run(self, blueprint_id: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        body = {"id": blueprint_id, "params": params or {}}
        return _obj(await self._http.request("POST", "/v1/blueprints/run", json=body))

    async def import_(self, blueprint: dict[str, Any]) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/v1/blueprints/import", json=blueprint))


class AsyncKBResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def ingest(self, files: Sequence[dict[str, Any]]) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/v1/kb/ingest", json={"files": list(files)}))

    async def list(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/v1/kb/list"), "files")

    async def file(self, file_id: str) -> bytes:
        return await self._http.content("GET", f"/v1/kb/file/{quote(file_id, safe='')}")

    async def delete(self, file_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("DELETE", f"/v1/kb/{quote(file_id, safe='')}"))


class AsyncResearchResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/v1/research"), "research")

    async def get(self, research_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("GET", f"/v1/research/{quote(research_id, safe='')}"))


class AsyncArtifactsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def graph(self) -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/v1/artifacts"))


class AsyncPromptsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self, model: str | None = None) -> list[dict[str, Any]]:
        params = {"model": model} if model else None
        return _arr(await self._http.request("GET", "/v1/prompts", params=params), "prompts")

    async def set(
        self, prompt_id: str, *, template: str | None = None, scope: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"id": prompt_id}
        if template is not None:
            body["template"] = template
        if scope is not None:
            body["scope"] = scope
        return _obj(await self._http.request("POST", "/v1/prompts", json=body))

    async def delete(self, prompt_id: str, *, model: str | None = None) -> dict[str, Any]:
        params = {"model": model} if model else None
        return _obj(
            await self._http.request(
                "DELETE", f"/v1/prompts/{quote(prompt_id, safe='')}", params=params
            )
        )


class AsyncNotesResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/v1/notes"), "notes")

    async def add(
        self, text: str, *, category: str = "observation", author: str = "user"
    ) -> dict[str, Any]:
        body = {"text": text, "category": category, "author": author}
        return _obj(await self._http.request("POST", "/v1/notes", json=body))

    async def delete(self, note_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("DELETE", f"/v1/notes/{quote(note_id, safe='')}"))


class AsyncConnectorsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/v1/connectors"), "connectors")

    async def test(
        self, name: str, *, input: str | None = None, path: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if input is not None:
            body["input"] = input
        if path is not None:
            body["path"] = path
        return _obj(
            await self._http.request(
                "POST", f"/v1/connectors/{quote(name, safe='')}/test", json=body
            )
        )

    async def call(self, name: str, input: str) -> dict[str, Any]:
        return _obj(
            await self._http.request(
                "POST", f"/v1/connectors/{quote(name, safe='')}/call", json={"input": input}
            )
        )


class AsyncRoutingResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def policies(self) -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/v1/routing/policies"))

    async def set_policy(self, name: str) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/v1/routing/policy", json={"name": name}))


class AsyncAgentsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/v1/agents"), "agents")

    async def get(self, agent_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("GET", f"/v1/agents/{quote(agent_id, safe='')}"))

    async def stop(self, agent_id: str) -> dict[str, Any]:
        return _obj(await self._http.request("POST", f"/v1/agents/{quote(agent_id, safe='')}/stop"))


class AsyncSatellitesResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/v1/satellites"), "satellites")

    async def output(self, satellite_id: str) -> dict[str, Any]:
        return _obj(
            await self._http.request("GET", f"/v1/satellites/{quote(satellite_id, safe='')}/output")
        )

    async def stop(self, satellite_id: str) -> dict[str, Any]:
        return _obj(
            await self._http.request("POST", f"/v1/satellites/{quote(satellite_id, safe='')}/stop")
        )


class AsyncTraceResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def get(self) -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/v1/trace"))

    async def set(self, prompts: TracePrompts) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/v1/trace", json={"prompts": prompts}))


class AsyncFilesResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self, path: str = "") -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/v1/files", params={"path": path}))

    async def read(self, path: str) -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/v1/files/content", params={"path": path}))

    async def write(self, path: str, content: str) -> dict[str, Any]:
        body = {"path": path, "content": content}
        return _obj(await self._http.request("POST", "/v1/files/content", json=body))


class AsyncManifestoResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def get(self, layer: Literal["all", "core", "project"] = "all") -> dict[str, Any]:
        return _obj(await self._http.request("GET", f"/v1/manifesto/{layer}"))

    async def set(self, layer: Literal["core", "project"], content: str) -> dict[str, Any]:
        return _obj(
            await self._http.request("POST", f"/v1/manifesto/{layer}", json={"content": content})
        )
