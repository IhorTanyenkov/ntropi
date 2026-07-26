"""Synchronous NBotWeb gateway resource groups.

Each wraps a ``BaseClient`` and covers one area of the chat-app gateway's
``/api/v1/*`` surface: auth/session, task + ephemeral-chat turns (blocking and
SSE), the read surfaces (projects / sessions / kb / agents / satellites /
artifacts / blueprints / files / mesh), channel adapters, and the admin plane
(API keys, RBAC users, settings). The async twins live in ``resources_async``
and mirror these exactly.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any
from urllib.parse import quote

from .._base import BaseClient
from .._streaming import iter_sse


def _obj(x: Any) -> dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _arr(x: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        v = x.get(key, [])
        return v if isinstance(v, list) else []
    return []


def _task_body(
    prompt: str,
    *,
    new_session: bool,
    session_id: str | None,
    files: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """The gateway's JSON task/chat body (mirrors ``_task_submission_from_request``)."""
    return {
        "prompt": prompt,
        "new_session": new_session,
        "session_id": session_id,
        "json": True,
        "files": files or [],
    }


class AuthResource:
    """Session auth: Google sign-in, logout, and the current principal."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def google(self, id_token: str) -> dict[str, Any]:
        """Verify a Google ID token and start a session (``POST /auth/google``)."""
        return _obj(self._http.request("POST", "/api/v1/auth/google", json={"id_token": id_token}))

    def logout(self) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/api/v1/auth/logout"))

    def me(self) -> dict[str, Any]:
        """``{authenticated, [email, role, projects, is_admin, is_service]}``."""
        return _obj(self._http.request("GET", "/api/v1/auth/me"))


class TasksResource:
    """TUI-parity task turns against the gateway (blocking or SSE)."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def submit(
        self,
        prompt: str,
        *,
        new_session: bool = False,
        session_id: str | None = None,
        files: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        body = _task_body(prompt, new_session=new_session, session_id=session_id, files=files)
        return _obj(self._http.request("POST", "/api/v1/tasks", json=body))

    def stream(
        self,
        prompt: str,
        *,
        new_session: bool = False,
        session_id: str | None = None,
        files: list[dict[str, Any]] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield native task events (with injected artifact download-link tokens)."""
        body = _task_body(prompt, new_session=new_session, session_id=session_id, files=files)
        with self._http._http.stream("POST", "/api/v1/tasks/stream", json=body) as resp:
            resp.raise_for_status()
            yield from iter_sse(resp.iter_lines())


class ChatResource:
    """Ephemeral, per-session chat turns — a surface separate from tasks."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def send(
        self,
        prompt: str,
        *,
        new_session: bool = False,
        session_id: str | None = None,
        files: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        body = _task_body(prompt, new_session=new_session, session_id=session_id, files=files)
        return _obj(self._http.request("POST", "/api/v1/chat", json=body))

    def stream(
        self,
        prompt: str,
        *,
        new_session: bool = False,
        session_id: str | None = None,
        files: list[dict[str, Any]] | None = None,
    ) -> Iterator[dict[str, Any]]:
        body = _task_body(prompt, new_session=new_session, session_id=session_id, files=files)
        with self._http._http.stream("POST", "/api/v1/chat/stream", json=body) as resp:
            resp.raise_for_status()
            yield from iter_sse(resp.iter_lines())

    def sessions(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/api/v1/chat/sessions"), "sessions")

    def delete(self, session_id: str) -> dict[str, Any]:
        return _obj(
            self._http.request("DELETE", f"/api/v1/chat/session/{quote(session_id, safe='')}")
        )


class ReadResource:
    """The gateway's read surfaces — one thin class over several list/download routes."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def projects(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/api/v1/projects"), "projects")

    def sessions(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/api/v1/sessions"), "sessions")

    def session(self, session_id: str) -> dict[str, Any]:
        return _obj(self._http.request("GET", f"/api/v1/sessions/{quote(session_id, safe='')}"))

    def kb(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/api/v1/kb"), "files")

    def kb_file(self, file_id: str) -> bytes:
        return self._http.content("GET", f"/api/v1/kb/file/{quote(file_id, safe='')}")

    def agents(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/api/v1/agents"), "agents")

    def satellites(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/api/v1/satellites"), "satellites")

    def artifacts(self) -> dict[str, Any]:
        return _obj(self._http.request("GET", "/api/v1/artifacts"))

    def file(self, file_id: str) -> bytes:
        return self._http.content("GET", f"/api/v1/files/{quote(file_id, safe='')}")

    def mesh(self) -> bytes:
        return self._http.content("GET", "/api/v1/mesh.nbt")


class BlueprintsResource:
    """List / download / run / import blueprints through the gateway."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/api/v1/blueprints/list"), "blueprints")

    def get(self, blueprint_id: str) -> bytes:
        return self._http.content("GET", f"/api/v1/blueprints/{quote(blueprint_id, safe='')}")

    def run(self, blueprint_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        body = {"id": blueprint_id, "params": params or {}}
        return _obj(self._http.request("POST", "/api/v1/blueprints/run", json=body))

    def import_(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/api/v1/blueprints/import", json=payload))


class AdaptersResource:
    """Channel webhooks (Telegram / WhatsApp) — mostly server-side, useful for testing."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def telegram_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/api/v1/adapters/telegram/webhook", json=payload))

    def whatsapp_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/api/v1/adapters/whatsapp/webhook", json=payload))


class ApiKeysResource:
    """Admin: API-key lifecycle (the secret is returned once on create)."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/api/v1/admin/api-keys"), "keys")

    def create(self, name: str) -> dict[str, Any]:
        """Create a key; the response carries the plaintext ``secret`` exactly once."""
        return _obj(self._http.request("POST", "/api/v1/admin/api-keys", json={"name": name}))

    def revoke(self, key_id: str) -> dict[str, Any]:
        return _obj(
            self._http.request("DELETE", f"/api/v1/admin/api-keys/{quote(key_id, safe='')}")
        )


class UsersResource:
    """Admin: RBAC users — role + owned-project assignment."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/api/v1/admin/users"), "users")

    def create(
        self, email: str, *, role: str = "user", projects: Sequence[str] | None = None
    ) -> dict[str, Any]:
        body = {"email": email, "role": role, "projects": list(projects or [])}
        return _obj(self._http.request("POST", "/api/v1/admin/users", json=body))

    def update(
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
            self._http.request("PATCH", f"/api/v1/admin/users/{quote(email, safe='')}", json=body)
        )

    def delete(self, email: str) -> dict[str, Any]:
        return _obj(self._http.request("DELETE", f"/api/v1/admin/users/{quote(email, safe='')}"))


class AdminResource:
    """The admin plane — settings, restart, keys, users, unfiltered projects."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http
        self.keys = ApiKeysResource(http)
        self.users = UsersResource(http)

    def settings(self) -> dict[str, Any]:
        return _obj(self._http.request("GET", "/api/v1/admin/settings"))

    def update_settings(self, nbot_base_url: str) -> dict[str, Any]:
        """Persist the upstream nbot base URL and rebuild the gateway."""
        return _obj(
            self._http.request(
                "PUT", "/api/v1/admin/settings", json={"nbot_base_url": nbot_base_url}
            )
        )

    def restart(self) -> dict[str, Any]:
        return _obj(self._http.request("POST", "/api/v1/admin/restart"))

    def projects(self) -> list[dict[str, Any]]:
        return _arr(self._http.request("GET", "/api/v1/admin/projects"), "projects")
