"""Server-sent-events parsing for the native streaming surfaces.

nbot's ``/v1/task/stream`` and ``/v1/chat/stream`` emit one JSON object per SSE
``data:`` line — ``status`` / ``token`` / ``artifact`` / ``done`` frames — with
``: ping`` heartbeat comments in between. ``iter_sse`` turns a raw line stream
into those JSON objects; comments and blanks are skipped.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable, Iterator
from typing import Any


def _decode(line: str) -> Any | None:
    """Return the parsed object for a ``data:`` line, or None to skip."""
    line = line.rstrip("\n")
    if not line or line.startswith(":"):
        return None
    if line.startswith("data:"):
        body = line[5:].strip()
        if not body or body == "[DONE]":
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None
    return None


def iter_sse(lines: Iterable[str]) -> Iterator[dict[str, Any]]:
    """Yield each JSON event object from a synchronous line iterator."""
    for line in lines:
        obj = _decode(line)
        if isinstance(obj, dict):
            yield obj


async def aiter_sse(lines: AsyncIterator[str]) -> AsyncIterator[dict[str, Any]]:
    """Yield each JSON event object from an async line iterator."""
    async for line in lines:
        obj = _decode(line)
        if isinstance(obj, dict):
            yield obj
