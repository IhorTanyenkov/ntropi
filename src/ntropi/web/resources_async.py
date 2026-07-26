"""Asynchronous NBotWeb resource groups — twins of ``resources`` with an
identical surface. Streaming uses :func:`ntropi._streaming.aiter_sse`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any
from urllib.parse import quote

from .._base import AsyncBaseClient
from .._streaming import aiter_sse
from .resources import _arr, _obj, _task_body


class AsyncAuthResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def google(self, id_token: str) -> dict[str, Any]:
        return _obj(
            await self._http.request("POST", "/api/v1/auth/google", json={"id_token": id_token})
        )

    async def logout(self) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/api/v1/auth/logout"))

    async def me(self) -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/api/v1/auth/me"))


class AsyncTasksResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def submit(
        self,
        prompt: str,
        *,
        new_session: bool = False,
        session_id: str | None = None,
        files: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        body = _task_body(prompt, new_session=new_session, session_id=session_id, files=files)
        return _obj(await self._http.request("POST", "/api/v1/tasks", json=body))

    async def stream(
        self,
        prompt: str,
        *,
        new_session: bool = False,
        session_id: str | None = None,
        files: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        body = _task_body(prompt, new_session=new_session, session_id=session_id, files=files)
        async with self._http._http.stream("POST", "/api/v1/tasks/stream", json=body) as resp:
            resp.raise_for_status()
            async for obj in aiter_sse(resp.aiter_lines()):
                yield obj


class AsyncChatResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def send(
        self,
        prompt: str,
        *,
        new_session: bool = False,
        session_id: str | None = None,
        files: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        body = _task_body(prompt, new_session=new_session, session_id=session_id, files=files)
        return _obj(await self._http.request("POST", "/api/v1/chat", json=body))

    async def stream(
        self,
        prompt: str,
        *,
        new_session: bool = False,
        session_id: str | None = None,
        files: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        body = _task_body(prompt, new_session=new_session, session_id=session_id, files=files)
        async with self._http._http.stream("POST", "/api/v1/chat/stream", json=body) as resp:
            resp.raise_for_status()
            async for obj in aiter_sse(resp.aiter_lines()):
                yield obj

    async def sessions(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/api/v1/chat/sessions"), "sessions")

    async def delete(self, session_id: str) -> dict[str, Any]:
        return _obj(
            await self._http.request(
                "DELETE", f"/api/v1/chat/session/{quote(session_id, safe='')}"
            )
        )


class AsyncReadResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def projects(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/api/v1/projects"), "projects")

    async def sessions(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/api/v1/sessions"), "sessions")

    async def session(self, session_id: str) -> dict[str, Any]:
        return _obj(
            await self._http.request("GET", f"/api/v1/sessions/{quote(session_id, safe='')}")
        )

    async def kb(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/api/v1/kb"), "files")

    async def kb_file(self, file_id: str) -> bytes:
        return await self._http.content("GET", f"/api/v1/kb/file/{quote(file_id, safe='')}")

    async def agents(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/api/v1/agents"), "agents")

    async def satellites(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/api/v1/satellites"), "satellites")

    async def artifacts(self) -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/api/v1/artifacts"))

    async def file(self, file_id: str) -> bytes:
        return await self._http.content("GET", f"/api/v1/files/{quote(file_id, safe='')}")

    async def mesh(self) -> bytes:
        return await self._http.content("GET", "/api/v1/mesh.nbt")


class AsyncBlueprintsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/api/v1/blueprints/list"), "blueprints")

    async def get(self, blueprint_id: str) -> bytes:
        return await self._http.content(
            "GET", f"/api/v1/blueprints/{quote(blueprint_id, safe='')}"
        )

    async def run(self, blueprint_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        body = {"id": blueprint_id, "params": params or {}}
        return _obj(await self._http.request("POST", "/api/v1/blueprints/run", json=body))

    async def import_(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/api/v1/blueprints/import", json=payload))


class AsyncAdaptersResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def telegram_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(
            await self._http.request("POST", "/api/v1/adapters/telegram/webhook", json=payload)
        )

    async def whatsapp_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(
            await self._http.request("POST", "/api/v1/adapters/whatsapp/webhook", json=payload)
        )


class AsyncApiKeysResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/api/v1/admin/api-keys"), "keys")

    async def create(self, name: str) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/api/v1/admin/api-keys", json={"name": name}))

    async def revoke(self, key_id: str) -> dict[str, Any]:
        return _obj(
            await self._http.request("DELETE", f"/api/v1/admin/api-keys/{quote(key_id, safe='')}")
        )


class AsyncUsersResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/api/v1/admin/users"), "users")

    async def create(
        self, email: str, *, role: str = "user", projects: Sequence[str] | None = None
    ) -> dict[str, Any]:
        body = {"email": email, "role": role, "projects": list(projects or [])}
        return _obj(await self._http.request("POST", "/api/v1/admin/users", json=body))

    async def update(
        self,
        email: str,
        *,
        role: str | None = None,
        projects: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if role is not None:
            body["role"] = role
        if projects is not None:
            body["projects"] = list(projects)
        return _obj(
            await self._http.request(
                "PATCH", f"/api/v1/admin/users/{quote(email, safe='')}", json=body
            )
        )

    async def delete(self, email: str) -> dict[str, Any]:
        return _obj(
            await self._http.request("DELETE", f"/api/v1/admin/users/{quote(email, safe='')}")
        )


class AsyncAdminResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http
        self.keys = AsyncApiKeysResource(http)
        self.users = AsyncUsersResource(http)

    async def settings(self) -> dict[str, Any]:
        return _obj(await self._http.request("GET", "/api/v1/admin/settings"))

    async def update_settings(self, nbot_base_url: str) -> dict[str, Any]:
        return _obj(
            await self._http.request(
                "PUT", "/api/v1/admin/settings", json={"nbot_base_url": nbot_base_url}
            )
        )

    async def restart(self) -> dict[str, Any]:
        return _obj(await self._http.request("POST", "/api/v1/admin/restart"))

    async def projects(self) -> list[dict[str, Any]]:
        return _arr(await self._http.request("GET", "/api/v1/admin/projects"), "projects")
