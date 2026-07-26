"""Typed models for the nbot surface.

Requests and the load-bearing responses are pydantic models for DX and
validation; the long tail of endpoints returns plain dicts until a model earns
its keep. ``extra="allow"`` on response models keeps forward-compatibility — a
new server field never breaks a client.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ExecMode = Literal["DIRECT", "TOOL_LIGHT", "TOOL_FULL", "DECOMPOSE"]


class _Response(BaseModel):
    """Base for server responses — tolerant of unknown fields."""

    model_config = ConfigDict(extra="allow")


class PoolModel(_Response):
    """One entry of ``GET /v1/pool``."""

    id: str
    node: str = "local"
    capacity: float = 0.0
    load: float = 0.0
    online: bool = True
    vision: bool = False
    supports_tools: bool = False
    supports_reasoning: bool = False
    modalities: list[str] = Field(default_factory=list)


class SessionSummary(_Response):
    """One entry of ``GET /v1/sessions``."""

    id: str
    msg_count: int = 0
    updated_at: int | None = None


class SessionMessage(_Response):
    """One message of ``GET /v1/session/{id}``."""

    role: str
    content: str = ""
    ts: int | None = None
    origin: str | None = None


class Session(_Response):
    """Full session from ``GET /v1/session/{id}``."""

    id: str
    project_id: str | None = None
    messages: list[SessionMessage] = Field(default_factory=list)


class Artifact(_Response):
    """A produced/ingested file reference."""

    id: str
    name: str = ""
    kind: str = ""
    size: int = 0


class TaskResult(_Response):
    """Response of ``POST /v1/task/submit`` (blocking)."""

    ok: bool = False
    node_id: str | None = None
    session_id: str | None = None
    response: str = ""
    produced: list[Artifact] = Field(default_factory=list)
    ingested: list[Artifact] = Field(default_factory=list)
    files: list[Artifact] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)


class TaskEvent(_Response):
    """One frame of a native stream (``/v1/task/stream``, ``/v1/chat/stream``).

    ``type`` ∈ status | token | artifact | done. Field presence depends on type:
    status → ``kind``/``text``; token → ``text``; artifact → id/name/kind/size;
    done → ``ok``/``session_id``.
    """

    type: str
    kind: str | None = None
    text: str | None = None
    id: str | None = None
    name: str | None = None
    size: int | None = None
    ok: bool | None = None
    session_id: str | None = None

    @property
    def is_token(self) -> bool:
        return self.type == "token"

    @property
    def is_done(self) -> bool:
        return self.type == "done"


def submit_payload(
    prompt: str,
    *,
    session_id: str | None = None,
    new_session: bool = False,
    model: str | None = None,
    complexity: float = 0.0,
    files: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the shared request body for submit / stream / chat."""
    body: dict[str, Any] = {
        "prompt": prompt,
        "new_session": new_session,
        "session_id": session_id or "",
        "complexity": complexity,
        "model": model or "",
    }
    if files:
        body["files"] = files
    return body
