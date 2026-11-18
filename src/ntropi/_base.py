"""Shared HTTP machinery for every service client.

``BaseClient`` (sync) and ``AsyncBaseClient`` (async) hold an ``httpx`` client,
attach auth, retry idempotent failures with backoff, and turn error responses
into the typed ``APIError`` tree. Concrete service clients (nbot, Horizon, web)
subclass these and add resource methods; they never re-implement transport.

The two twins deliberately share request-building and error-mapping via
module-level helpers so their behaviour cannot drift.
"""

from __future__ import annotations

import json as _json
import os
import time
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Any

import httpx

from ._exceptions import APIConnectionError, APITimeoutError, error_for_status

RETRY_STATUSES = frozenset({408, 409, 429, 500, 502, 503, 504})
DEFAULT_TIMEOUT = 600.0
DEFAULT_MAX_RETRIES = 2


def resolve_credential(explicit: str | None, *env_vars: str) -> str | None:
    """Resolve a credential: an explicit value wins, else the first set env var.

    The env-var chain lets a service-specific key (e.g. ``NTROPI_NBOT_TOKEN``)
    take precedence over the shared platform key ``NTROPI_API_KEY`` — so one key
    authenticates the SDK to both nbot and Horizon, with a per-service override
    when a deployment wants distinct credentials.
    """
    if explicit:
        return explicit
    for var in env_vars:
        val = os.environ.get(var)
        if val:
            return val
    return None


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


@dataclass(frozen=True)
class HTTPReceipt:
    """What one request actually sent and received, kept whole for evidence.

    ``request_body`` is the exact bytes sent. ``status`` is the HTTP status, or
    ``None`` when no response arrived (``error`` then says why). The response
    is kept as bytes whatever its status; :meth:`json` parses it. ``elapsed_s``
    is measured on the monotonic clock around the one attempt. A receipt is
    never retried and never raises on an HTTP error status: the caller decides
    what a 500 means.
    """

    method: str
    url: str
    request_body: bytes
    status: int | None
    response_body: bytes = b""
    content_type: str = ""
    elapsed_s: float = 0.0
    error: str | None = None
    response_headers: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300

    def json(self) -> Any:
        """The response parsed as JSON, or ``None`` when it is not JSON."""
        try:
            return _json.loads(self.response_body)
        except ValueError:
            return None


# Response headers worth keeping on a receipt. Anything that can carry a
# credential or a cookie is left out.
_RECEIPT_HEADERS = ("content-type", "content-length", "date", "x-request-id")


def _receipt(method: str, url: str, body: bytes, started: float, resp: httpx.Response) -> HTTPReceipt:
    return HTTPReceipt(
        method=method.upper(),
        url=url,
        request_body=body,
        status=resp.status_code,
        response_body=resp.content,
        content_type=resp.headers.get("content-type", ""),
        elapsed_s=time.monotonic() - started,
        response_headers={k: resp.headers[k] for k in _RECEIPT_HEADERS if k in resp.headers},
    )


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

    def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Issue a request with idempotent-failure retries, returning the raw response."""
        last: Exception | None = None
        retries = self._config.max_retries if method.upper() in {"GET", "HEAD", "OPTIONS"} else 0
        for attempt in range(retries + 1):
            try:
                resp = self._http.request(method, path, **kwargs)
            except httpx.TimeoutException as exc:
                last = APITimeoutError(str(exc))
            except httpx.TransportError as exc:
                last = APIConnectionError(str(exc))
            else:
                if resp.status_code in RETRY_STATUSES and attempt < retries:
                    time.sleep(_backoff(attempt))
                    continue
                return resp
            if attempt < retries:
                time.sleep(_backoff(attempt))
        assert last is not None
        raise last

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Issue a request, retrying idempotent failures, returning the parsed body."""
        return _map_response(self._send(method, path, **kwargs))

    @contextmanager
    def stream(self, method: str, path: str, **kwargs: Any) -> Iterator[httpx.Response]:
        """Open one stream with typed errors; never replay partially executed work."""
        try:
            with self._http.stream(method, path, **kwargs) as response:
                if not response.is_success:
                    response.read()
                    _map_response(response)
                yield response
        except httpx.TimeoutException as exc:
            raise APITimeoutError(str(exc)) from exc
        except httpx.TransportError as exc:
            raise APIConnectionError(str(exc)) from exc

    def content(self, method: str, path: str, **kwargs: Any) -> bytes:
        """Like :meth:`request`, but return the raw response bytes (for downloads)."""
        resp = self._send(method, path, **kwargs)
        if not resp.is_success:
            _map_response(resp)  # raises the typed error
        return resp.content

    def exchange(
        self, method: str, path: str, body: bytes, *, content_type: str = "application/json"
    ) -> HTTPReceipt:
        """Send exactly ``body`` once and return the whole :class:`HTTPReceipt`.

        Nothing is added to the body, no attempt is repeated and no HTTP
        status raises; a transport failure is a receipt with ``status=None``.
        """
        url = self._config.base_url + path
        started = time.monotonic()
        try:
            resp = self._http.request(
                method, path, content=body, headers={"Content-Type": content_type}
            )
        except httpx.TimeoutException as exc:
            return HTTPReceipt(method.upper(), url, body, None, elapsed_s=time.monotonic() - started,
                               error=f"timeout: {exc}")
        except httpx.TransportError as exc:
            return HTTPReceipt(method.upper(), url, body, None, elapsed_s=time.monotonic() - started,
                               error=f"connection: {exc}")
        return _receipt(method, url, body, started, resp)

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

    async def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        import asyncio

        last: Exception | None = None
        retries = self._config.max_retries if method.upper() in {"GET", "HEAD", "OPTIONS"} else 0
        for attempt in range(retries + 1):
            try:
                resp = await self._http.request(method, path, **kwargs)
            except httpx.TimeoutException as exc:
                last = APITimeoutError(str(exc))
            except httpx.TransportError as exc:
                last = APIConnectionError(str(exc))
            else:
                if resp.status_code in RETRY_STATUSES and attempt < retries:
                    await asyncio.sleep(_backoff(attempt))
                    continue
                return resp
            if attempt < retries:
                await asyncio.sleep(_backoff(attempt))
        assert last is not None
        raise last

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Issue a request, retrying idempotent failures, returning the parsed body."""
        return _map_response(await self._send(method, path, **kwargs))

    @asynccontextmanager
    async def stream(
        self, method: str, path: str, **kwargs: Any
    ) -> AsyncIterator[httpx.Response]:
        """Open one stream with typed errors; never replay partially executed work."""
        try:
            async with self._http.stream(method, path, **kwargs) as response:
                if not response.is_success:
                    await response.aread()
                    _map_response(response)
                yield response
        except httpx.TimeoutException as exc:
            raise APITimeoutError(str(exc)) from exc
        except httpx.TransportError as exc:
            raise APIConnectionError(str(exc)) from exc

    async def content(self, method: str, path: str, **kwargs: Any) -> bytes:
        """Like :meth:`request`, but return the raw response bytes (for downloads)."""
        resp = await self._send(method, path, **kwargs)
        if not resp.is_success:
            _map_response(resp)  # raises the typed error
        return resp.content

    async def exchange(
        self, method: str, path: str, body: bytes, *, content_type: str = "application/json"
    ) -> HTTPReceipt:
        """Async twin of :meth:`BaseClient.exchange`: one exact attempt, whole receipt."""
        url = self._config.base_url + path
        started = time.monotonic()
        try:
            resp = await self._http.request(
                method, path, content=body, headers={"Content-Type": content_type}
            )
        except httpx.TimeoutException as exc:
            return HTTPReceipt(method.upper(), url, body, None, elapsed_s=time.monotonic() - started,
                               error=f"timeout: {exc}")
        except httpx.TransportError as exc:
            return HTTPReceipt(method.upper(), url, body, None, elapsed_s=time.monotonic() - started,
                               error=f"connection: {exc}")
        return _receipt(method, url, body, started, resp)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncBaseClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
