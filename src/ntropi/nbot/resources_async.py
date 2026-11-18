"""Asynchronous nbot resource groups — exact mirrors of ``resources`` with
``await`` and async-iterator streaming (:func:`ntropi._streaming.aiter_sse`)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from .._base import AsyncBaseClient, HTTPReceipt
from .._streaming import aiter_sse
from .types import (
    PoolModel,
    Session,
    SessionSummary,
    TaskEvent,
    TaskResult,
    submit_payload,
)


class AsyncPoolResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> list[PoolModel]:
        data = await self._http.request("GET", "/v1/pool")
        models = data.get("models", []) if isinstance(data, dict) else []
        return [PoolModel.model_validate(m) for m in models]


class AsyncProjectsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> list[dict[str, Any]]:
        data = await self._http.request("GET", "/v1/projects")
        return data.get("projects", []) if isinstance(data, dict) else []

    async def active(self) -> dict[str, Any] | None:
        for p in await self.list():
            if p.get("active"):
                return p
        return None

    async def use(self, path: str) -> str:
        resp = await self._http.request("POST", "/v1/command", json={"command": f"/project use {path}"})
        return str(resp.get("output", "")) if isinstance(resp, dict) else str(resp)


class AsyncSessionsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> list[SessionSummary]:
        data = await self._http.request("GET", "/v1/sessions")
        items = data.get("sessions", []) if isinstance(data, dict) else []
        return [SessionSummary.model_validate(s) for s in items]

    async def current(self) -> str | None:
        data = await self._http.request("GET", "/v1/sessions")
        return data.get("current") if isinstance(data, dict) else None

    async def get(self, session_id: str) -> Session:
        data = await self._http.request("GET", f"/v1/session/{session_id}")
        return Session.model_validate(data)


class AsyncTasksResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def submit(
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
            prompt, session_id=session_id, new_session=new_session,
            model=model, complexity=complexity, files=files,
        )
        data = await self._http.request("POST", "/v1/task/submit", json=body)
        return TaskResult.model_validate(data)

    async def stream(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        new_session: bool = False,
        model: str | None = None,
        complexity: float = 0.0,
        files: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[TaskEvent]:
        body = submit_payload(
            prompt, session_id=session_id, new_session=new_session,
            model=model, complexity=complexity, files=files,
        )
        async with self._http.stream("POST", "/v1/task/stream", json=body) as resp:
            async for obj in aiter_sse(resp.aiter_lines()):
                yield TaskEvent.model_validate(obj)


class AsyncModelsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def list(self) -> list[dict[str, Any]]:
        data = await self._http.request("GET", "/v1/models")
        return data.get("data", []) if isinstance(data, dict) else []


class AsyncCompletionsResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    def _body(self, model: str, messages: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
        body: dict[str, Any] = {"model": model, "messages": messages}
        body.update(extra)
        return body

    async def create(
        self, *, model: str = "nbot", messages: list[dict[str, Any]], **extra: Any
    ) -> dict[str, Any]:
        body = self._body(model, messages, stream=False, **extra)
        data = await self._http.request("POST", "/v1/chat/completions", json=body)
        return data if isinstance(data, dict) else {"raw": data}

    async def stream(
        self, *, model: str = "nbot", messages: list[dict[str, Any]], **extra: Any
    ) -> AsyncIterator[dict[str, Any]]:
        body = self._body(model, messages, stream=True, **extra)
        async with self._http.stream("POST", "/v1/chat/completions", json=body) as resp:
            async for obj in aiter_sse(resp.aiter_lines()):
                yield obj

    async def send_exact(self, body: bytes) -> HTTPReceipt:
        """Async twin of :meth:`CompletionsResource.send_exact`."""
        return await self._http.exchange("POST", "/v1/chat/completions", body)


class AsyncChatResource:
    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http
        self.completions = AsyncCompletionsResource(http)

    async def send(
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
            prompt, session_id=session_id, new_session=new_session,
            model=model, complexity=complexity, files=files,
        )
        data = await self._http.request("POST", "/v1/chat", json=body)
        return TaskResult.model_validate(data)

    async def stream(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        new_session: bool = False,
        model: str | None = None,
        complexity: float = 0.0,
        files: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[TaskEvent]:
        body = submit_payload(
            prompt, session_id=session_id, new_session=new_session,
            model=model, complexity=complexity, files=files,
        )
        async with self._http.stream("POST", "/v1/chat/stream", json=body) as resp:
            async for obj in aiter_sse(resp.aiter_lines()):
                yield TaskEvent.model_validate(obj)

    async def sessions(self) -> list[SessionSummary]:
        data = await self._http.request("GET", "/v1/chat/sessions")
        items = data.get("sessions", []) if isinstance(data, dict) else []
        return [SessionSummary.model_validate(s) for s in items]

    async def delete(self, session_id: str) -> bool:
        data = await self._http.request("DELETE", f"/v1/chat/session/{session_id}")
        return bool(data.get("ok", True)) if isinstance(data, dict) else True
