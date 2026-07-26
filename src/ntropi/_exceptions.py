"""Error hierarchy for the ntropi SDK.

One root, ``NtropiError``, so a caller can catch everything from the stack with a
single ``except``. HTTP failures map to typed subclasses by status; two errors
are specific to this stack rather than a generic status:

- ``UpstreamUnavailable`` — a Horizon live call returned 502/503 because no nbot
  serve was reachable. Callers routinely need to catch exactly this and start or
  wait for nbot, so it is not folded into the generic 5xx type.
- ``ServiceStartError`` — a process ntropi spawned (nbot / Horizon / webkit)
  failed to become healthy within its start timeout.
"""

from __future__ import annotations

from typing import Any


class NtropiError(Exception):
    """Base class for every error raised by the SDK."""


class APIError(NtropiError):
    """An HTTP request reached a service but the response was an error.

    ``status`` is the HTTP status code; ``payload`` is the parsed JSON body when
    the service returned one, else the raw text.
    """

    status: int | None
    payload: Any

    def __init__(self, message: str, *, status: int | None = None, payload: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.payload = payload


class APIConnectionError(NtropiError):
    """The service could not be reached (DNS, refused, reset)."""


class APITimeoutError(APIConnectionError):
    """The request exceeded its timeout."""


class BadRequest(APIError):
    """400 — the request was malformed or violated a contract."""


class AuthenticationError(APIError):
    """401 — missing or invalid credentials."""


class PermissionDenied(APIError):
    """403 — authenticated but not allowed."""


class NotFoundError(APIError):
    """404 — the resource does not exist."""


class UnprocessableEntity(APIError):
    """422 — well-formed but semantically rejected (e.g. a non-exportable policy)."""


class RateLimitError(APIError):
    """429 — throttled."""


class InternalServerError(APIError):
    """5xx — the service failed internally."""


class UpstreamUnavailable(APIError):
    """502/503 — a service is up but its upstream (nbot for Horizon) is not."""


class ServiceStartError(NtropiError):
    """A process ntropi spawned did not become healthy in time."""


def error_for_status(status: int, message: str, payload: Any = None) -> APIError:
    """Map an HTTP status to the most specific ``APIError`` subclass."""
    table: dict[int, type[APIError]] = {
        400: BadRequest,
        401: AuthenticationError,
        403: PermissionDenied,
        404: NotFoundError,
        422: UnprocessableEntity,
        429: RateLimitError,
        502: UpstreamUnavailable,
        503: UpstreamUnavailable,
    }
    cls = table.get(status)
    if cls is None:
        cls = InternalServerError if status >= 500 else APIError
    return cls(message, status=status, payload=payload)
