"""Shared HTTP machinery for every service client.

``BaseClient`` (sync) and ``AsyncBaseClient`` (async) hold an ``httpx`` client,
attach auth, retry idempotent failures with backoff, and turn error responses
into the typed ``APIError`` tree. Concrete service clients (nbot, Horizon, web)
subclass these and add resource methods; they never re-implement transport.

The two twins deliberately share request-building and error-mapping via
module-level helpers so their behaviour cannot drift.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

import httpx

from ._exceptions import APIConnectionError, APITimeoutError, error_for_status

RETRY_STATUSES = frozenset({408, 409, 429, 500, 502, 503, 504})
DEFAULT_TIMEOUT = 600.0
DEFAULT_MAX_RETRIES = 2


def _auth_headers(scheme: str, credential: str | None) -> dict[str, str]:
    """Build the auth header for a credential under a named scheme.

    ``scheme`` is ``"bearer"`` (nbot) or ``"x-api-key"`` (Horizon). An empty
    credential yields no header, which matches services that run open on
    loopback.
    """
    if not credential:
        return {}
    if scheme == "bearer":
        return {"Authorization": f"Bearer {credential}"}
    if scheme == "x-api-key":
        return {"X-API-Key": credential}
    raise ValueError(f"unknown auth scheme: {scheme}")


def _map_response(resp: httpx.Response) -> Any:
    """Return the parsed body on success, or raise the typed error on failure."""
    if resp.is_success:
        ctype = resp.headers.get("content-type", "")
        if "application/json" in ctype:
            return resp.json()
        return resp.text
    payload: Any
    try:
        payload = resp.json()
    except ValueError:
        payload = resp.text
    message = f"{resp.request.method} {resp.request.url} -> {resp.status_code}"
    raise error_for_status(resp.status_code, message, payload)


def _backoff(attempt: int) -> float:
    """Exponential backoff (0.5s, 1s, 2s, ...) for retry ``attempt`` (0-based)."""
    return 0.5 * float(2**attempt)


class _ClientConfig:
    """Immutable connection settings for one service."""

    def __init__(
        self,
        base_url: str,
        *,
        auth_scheme: str = "bearer",
        credential: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth_scheme = auth_scheme
        self.credential = credential
        self.timeout = timeout
        self.max_retries = max_retries
        self.extra_headers = dict(extra_headers or {})

    def headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        h.update(_auth_headers(self.auth_scheme, self.credential))
        h.update(self.extra_headers)
        return h


class BaseClient:
    """Synchronous HTTP client shared by the service clients."""

    def __init__(self, config: _ClientConfig, http: httpx.Client | None = None) -> None:
        self._config = config
        self._http = http or httpx.Client(
            base_url=config.base_url, timeout=config.timeout, headers=config.headers()
        )

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Issue a request, retrying idempotent failures, returning the parsed body."""
        last: Exception | None = None
        for attempt in range(self._config.max_retries + 1):
            try:
                resp = self._http.request(method, path, **kwargs)
            except httpx.TimeoutException as exc:
                last = APITimeoutError(str(exc))
            except httpx.TransportError as exc:
                last = APIConnectionError(str(exc))
            else:
                if resp.status_code in RETRY_STATUSES and attempt < self._config.max_retries:
                    time.sleep(_backoff(attempt))
                    continue
                return _map_response(resp)
            if attempt < self._config.max_retries:
                time.sleep(_backoff(attempt))
        assert last is not None
        raise last

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> BaseClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class AsyncBaseClient:
    """Asynchronous twin of ``BaseClient`` with an identical surface."""

    def __init__(self, config: _ClientConfig, http: httpx.AsyncClient | None = None) -> None:
        self._config = config
        self._http = http or httpx.AsyncClient(
            base_url=config.base_url, timeout=config.timeout, headers=config.headers()
        )

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        import asyncio

        last: Exception | None = None
        for attempt in range(self._config.max_retries + 1):
            try:
                resp = await self._http.request(method, path, **kwargs)
            except httpx.TimeoutException as exc:
                last = APITimeoutError(str(exc))
            except httpx.TransportError as exc:
                last = APIConnectionError(str(exc))
            else:
                if resp.status_code in RETRY_STATUSES and attempt < self._config.max_retries:
                    await asyncio.sleep(_backoff(attempt))
                    continue
                return _map_response(resp)
            if attempt < self._config.max_retries:
                await asyncio.sleep(_backoff(attempt))
        assert last is not None
        raise last

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncBaseClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
