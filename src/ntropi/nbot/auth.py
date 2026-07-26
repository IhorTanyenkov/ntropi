"""``ntropi.nbot`` license/auth surface.

nbot owns license validation; the SDK does not talk to the license server. This
module provides two small things:

- :func:`activate` — store an operator's license key where nbot reads it
  (``~/.nbot/license.json``), so a node launched next picks it up. No running
  node required.
- ``AuthResource`` (``client.auth``) — read the node's license status from its
  ``/v1/health`` (``licensed`` / ``operator`` / ``plan`` / grace).
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

from .._base import AsyncBaseClient, BaseClient


def license_path() -> Path:
    """``~/.nbot/license.json`` — where nbot reads the operator key."""
    return Path(os.path.expanduser("~")) / ".nbot" / "license.json"


def activate(key: str, *, path: Path | str | None = None) -> Path:
    """Store a license key (mode 0600) for nbot to use, and return the path.

    This is the Python equivalent of ``nbot license <key>``: it writes the key
    where a node reads it; the node validates it against the license server on
    its next start.
    """
    target = Path(path) if path else license_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"key": key}))
    target.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return target


def _status_from_health(health: dict[str, Any]) -> dict[str, Any]:
    """Project the license fields out of a ``/v1/health`` response."""
    if "licensed" not in health:
        return {"enforced": False}
    out: dict[str, Any] = {
        "enforced": True,
        "licensed": bool(health.get("licensed")),
        "operator": health.get("operator", ""),
        "plan": health.get("plan", ""),
    }
    if "license_reason" in health:
        out["reason"] = health["license_reason"]
    if "grace_days_left" in health:
        out["grace_days_left"] = health["grace_days_left"]
    return out


class AuthResource:
    """License status for a running node (synchronous)."""

    def __init__(self, http: BaseClient) -> None:
        self._http = http

    def status(self) -> dict[str, Any]:
        """``{enforced, licensed, operator, plan, [reason], [grace_days_left]}``.

        ``enforced`` is False when the node is a build without license
        enforcement (nothing to report).
        """
        data = self._http.request("GET", "/v1/health")
        return _status_from_health(data if isinstance(data, dict) else {})


class AsyncAuthResource:
    """License status for a running node (asynchronous)."""

    def __init__(self, http: AsyncBaseClient) -> None:
        self._http = http

    async def status(self) -> dict[str, Any]:
        data = await self._http.request("GET", "/v1/health")
        return _status_from_health(data if isinstance(data, dict) else {})
