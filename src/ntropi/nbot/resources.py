"""Synchronous nbot resource groups.

Each wraps a ``BaseClient`` and exposes typed methods over one area of the node.
The async twins live in ``resources_async`` and mirror these exactly. Streaming
uses the node's native SSE frames via :func:`ntropi._streaming.iter_sse`.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .._base import BaseClient
from .._streaming import iter_sse
from .types import (
    PoolModel,
    Session,
    SessionSummary,
    TaskEvent,
    TaskResult,
    submit_payload,
)


class PoolResource:
    """The model pool — who is available and how loaded (``GET /v1/pool``)."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> list[PoolModel]:
        data = self._http.request("GET", "/v1/pool")
        models = data.get("models", []) if isinstance(data, dict) else []
        return [PoolModel.model_validate(m) for m in models]


class ProjectsResource:
    """Project directories. nbot's active project is instance-global; switching
    goes through the command path, so this reads the list and drives ``/project``."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> list[dict[str, Any]]:
        data = self._http.request("GET", "/v1/projects")
        return data.get("projects", []) if isinstance(data, dict) else []

    def active(self) -> dict[str, Any] | None:
        for p in self.list():
            if p.get("active"):
                return p
        return None

    def use(self, path: str) -> str:
        """Switch the node's active project (instance-wide) via ``/project use``."""
        resp = self._http.request("POST", "/v1/command", json={"command": f"/project use {path}"})
        return str(resp.get("output", "")) if isinstance(resp, dict) else str(resp)


class SessionsResource:
    """Persistent sessions on the serve."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def list(self) -> list[SessionSummary]:
        data = self._http.request("GET", "/v1/sessions")
        items = data.get("sessions", []) if isinstance(data, dict) else []
        return [SessionSummary.model_validate(s) for s in items]

    def current(self) -> str | None:
        data = self._http.request("GET", "/v1/sessions")
        return data.get("current") if isinstance(data, dict) else None

    def get(self, session_id: str) -> Session:
        data = self._http.request("GET", f"/v1/session/{session_id}")
        return Session.model_validate(data)


class TasksResource:
    """Run prompts against the serve — blocking (:meth:`submit`) or streamed
    (:meth:`stream`, native ``status``/``token``/``artifact``/``done`` frames)."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def submit(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        new_session: bool = False,
        model: str | None = None,
        complexity: float = 0.0,
        files: list[dict[str, Any]] | None = None,
    ) -> TaskResult:
        body = submit_payload(
            prompt,
            session_id=session_id,
            new_session=new_session,
            model=model,
            complexity=complexity,
            files=files,
        )
        data = self._http.request("POST", "/v1/task/submit", json=body)
        return TaskResult.model_validate(data)

    def stream(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        new_session: bool = False,
        model: str | None = None,
        complexity: float = 0.0,
        files: list[dict[str, Any]] | None = None,
    ) -> Iterator[TaskEvent]:
        """Yield native events as the turn runs. The final frame has ``type=done``."""
        body = submit_payload(
            prompt,
            session_id=session_id,
            new_session=new_session,
            model=model,
            complexity=complexity,
            files=files,
        )
        with self._http._http.stream("POST", "/v1/task/stream", json=body) as resp:
            resp.raise_for_status()
            for obj in iter_sse(resp.iter_lines()):
                yield TaskEvent.model_validate(obj)
