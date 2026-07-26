"""ntropi — Python SDK and runtime for the Entropi stack.

One import to run and operate the whole stack from Python: the **nbot**
cognitive-compute node, the **Horizon** eval/observability backend, and the
**NBotWeb** chat-app gateway. Start the services (or connect to running ones),
manage config / projects / sessions, and each service is live as its normal self
— Horizon's web UI included.

    import ntropi

    stack = ntropi.connect(nbot_url="http://127.0.0.1:9991",
                           horizon_url="http://127.0.0.1:8848")
    print(stack.nbot.health())
    print(stack.nbot.command("/pool"))

The design goal is a full dev tool to **develop, teach, trace, and connect** to
the nbot ecosystem. Phase 0 ships the foundation — clients, auth, discovery,
error hierarchy, process runtime; resource methods land in later phases (see
docs/plans).
"""

from __future__ import annotations

from . import horizon as horizon
from . import nbot as nbot
from . import web as web
from ._exceptions import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequest,
    InternalServerError,
    NotFoundError,
    NtropiError,
    PermissionDenied,
    RateLimitError,
    ServiceStartError,
    UnprocessableEntity,
    UpstreamUnavailable,
)

__version__ = "0.0.1"


class Stack:
    """Handles to the three services, however they were obtained.

    Built by :func:`connect` (attach to running services) or, once the runtime
    launch helpers land, by starting the services ntropi owns. Sub-clients are
    also usable directly: ``ntropi.nbot.Client(...)`` etc.
    """

    def __init__(
        self,
        nbot: nbot.Client | None = None,
        horizon: horizon.Client | None = None,
        web: web.Client | None = None,
    ) -> None:
        self.nbot = nbot
        self.horizon = horizon
        self.web = web

    def close(self) -> None:
        for svc in (self.nbot, self.horizon, self.web):
            if svc is not None:
                svc.close()

    def __enter__(self) -> Stack:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def connect(
    *,
    nbot_url: str | None = None,
    nbot_project: str | None = None,
    nbot_token: str | None = None,
    horizon_url: str | None = None,
    horizon_key: str | None = None,
    web_url: str | None = None,
    web_key: str | None = None,
) -> Stack:
    """Attach to services already running and return a :class:`Stack`.

    Each service is wired only when enough to reach it is given (a URL, or for
    nbot a project to discover ``control.json``). Nothing is started or stopped.
    """
    nbot_client = None
    if nbot_url or nbot_project:
        nbot_client = nbot.Client(nbot_url, project=nbot_project, token=nbot_token)
    horizon_client = horizon.Client(horizon_url, key=horizon_key) if horizon_url else None
    web_client = web.Client(web_url, key=web_key) if web_url else None
    return Stack(nbot=nbot_client, horizon=horizon_client, web=web_client)


__all__ = [
    "APIConnectionError",
    "APIError",
    "APITimeoutError",
    "AuthenticationError",
    "BadRequest",
    "InternalServerError",
    "NotFoundError",
    "NtropiError",
    "PermissionDenied",
    "RateLimitError",
    "ServiceStartError",
    "Stack",
    "UnprocessableEntity",
    "UpstreamUnavailable",
    "__version__",
    "connect",
    "horizon",
    "nbot",
    "web",
]
