"""Start the stack from Python.

``launch(project)`` spawns nbot (``nbot --config <cfg> serve``) and, by default,
Horizon (``nbot-horizon --project <p> --port N``), waits for each to become
healthy, and returns a :class:`~ntropi.Stack` wired to both. When Horizon comes
up its web UI is live on its port — the same Horizon you would open normally.

The returned Stack owns the processes it started and stops them on
``close()`` / context exit; a service reached via :func:`~ntropi.connect`
instead is never stopped.
"""

from __future__ import annotations

import os

import httpx

from . import horizon, nbot, web
from ._exceptions import ServiceStartError
from ._runtime import ServiceProcess, find_binary
from .nbot import discover_base_url


def _http_ok(url: str) -> bool:
    try:
        return httpx.get(url, timeout=2.0).status_code < 500
    except httpx.HTTPError:
        return False


def serve_nbot(
    project: str,
    *,
    binary: str | None = None,
    config: str | None = None,
    token: str | None = None,
    timeout: float = 180.0,
    log: str | None = None,
) -> tuple[ServiceProcess, nbot.Client]:
    """Spawn ``nbot serve`` for a project and return (process, client)."""
    proj = os.path.abspath(project)
    cfg = config or os.path.join(proj, ".nconfig", "node.toml")
    exe = find_binary(binary, "NTROPI_NBOT_BIN", "nbot")
    data_dir = os.path.join(proj, ".nconfig")

    def health() -> bool:
        base = discover_base_url(proj)
        return bool(base) and _http_ok(f"{base}/v1/health")

    proc = ServiceProcess(
        argv=[exe, "--config", cfg, "serve"],
        health=health,
        name="nbot",
        cwd=proj,
        env={"NBOT_DATA_DIR": data_dir},
        log_path=log,
        timeout=timeout,
    ).start()
    return proc, nbot.Client(project=proj, token=token)


def serve_horizon(
    project: str,
    *,
    port: int = 8848,
    binary: str | None = None,
    key: str | None = None,
    timeout: float = 120.0,
    log: str | None = None,
) -> tuple[ServiceProcess, horizon.Client]:
    """Spawn ``nbot-horizon`` for a project (UI live on ``port``); return (process, client)."""
    proj = os.path.abspath(project)
    exe = find_binary(binary, "NTROPI_HORIZON_BIN", "nbot-horizon")
    base = f"http://127.0.0.1:{port}"
    proc = ServiceProcess(
        argv=[exe, "--project", proj, "--port", str(port)],
        health=lambda: _http_ok(f"{base}/api/health"),
        name="horizon",
        cwd=proj,
        log_path=log,
        timeout=timeout,
    ).start()
    return proc, horizon.Client(base, key=key)


def serve_web(
    nbot_base_url: str,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    binary: str | None = None,
    key: str | None = None,
    control_secret: str | None = None,
    timeout: float = 120.0,
    log: str | None = None,
) -> tuple[ServiceProcess, web.Client]:
    """Spawn the NBotWeb gateway pointed at a running nbot; return (process, client).

    The gateway is the ``nbot-gateway`` console script (uvicorn); it is configured
    by ``NBOT_WEB_*`` environment variables, so ``nbot_base_url`` is passed through
    as ``NBOT_WEB_NBOT_BASE_URL``. Its own web UI is live on ``host:port``.
    """
    exe = find_binary(binary, "NTROPI_WEB_BIN", "nbot-gateway", "nbot-web")
    base = f"http://{host}:{port}"
    env = {
        "NBOT_WEB_HOST": host,
        "NBOT_WEB_PORT": str(port),
        "NBOT_WEB_NBOT_BASE_URL": nbot_base_url.rstrip("/"),
    }
    if control_secret:
        env["NBOT_WEB_NBOT_CONTROL_SECRET"] = control_secret
    proc = ServiceProcess(
        argv=[exe],
        health=lambda: _http_ok(f"{base}/api/v1/health"),
        name="web",
        env=env,
        log_path=log,
        timeout=timeout,
    ).start()
    return proc, web.Client(base, key=key)


def launch(
    project: str,
    *,
    token: str | None = None,
    with_horizon: bool = True,
    with_web: bool = False,
    horizon_port: int = 8848,
    web_port: int = 8080,
    nbot_binary: str | None = None,
    horizon_binary: str | None = None,
    web_binary: str | None = None,
    horizon_key: str | None = None,
    web_key: str | None = None,
    timeout: float = 180.0,
) -> object:
    """Start nbot (+ Horizon, + web) for a project and return a wired, self-owning Stack.

    ``with_web`` also starts the NBotWeb gateway pointed at the nbot instance this
    call started (it needs the ``nbot-web`` binary on PATH or ``NTROPI_WEB_BIN``).
    """
    from . import Stack

    procs: list[ServiceProcess] = []
    nproc, nclient = serve_nbot(project, binary=nbot_binary, token=token, timeout=timeout)
    procs.append(nproc)
    hclient = None
    if with_horizon:
        hproc, hclient = serve_horizon(
            project, port=horizon_port, binary=horizon_binary, key=horizon_key, timeout=timeout
        )
        procs.append(hproc)
    wclient = None
    if with_web:
        base = discover_base_url(os.path.abspath(project))
        if not base:
            raise ServiceStartError("nbot serve did not advertise a base_url for the web gateway")
        wproc, wclient = serve_web(
            base,
            port=web_port,
            binary=web_binary,
            key=web_key,
            control_secret=token,
            timeout=timeout,
        )
        procs.append(wproc)
    return Stack(nbot=nclient, horizon=hclient, web=wclient, procs=procs)
