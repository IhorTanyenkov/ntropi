# Installation

ntropi requires **Python ≥ 3.10**.

## Install the package

```bash
pip install ntropi
```

Optional extras:

```bash
pip install "ntropi[cli]"    # the `ntropi` command-line tool (Typer)
pip install "ntropi[dev]"    # test + lint + type-check toolchain
pip install "ntropi[docs]"   # build this documentation site
```

From a checkout, for development:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,cli]"
pytest -q
```

## The service binaries

ntropi **drives** the stack's services; it does not bundle them. Install the
ones you need and put them on `PATH`, or point ntropi at them explicitly:

| Service | Binary | Override env var |
|---|---|---|
| nbot node | `nbot` | `NTROPI_NBOT_BIN` |
| Horizon | `nbot-horizon` | `NTROPI_HORIZON_BIN` |
| NBotWeb gateway | `nbot-web` | `NTROPI_WEB_BIN` |

You only need a binary if you want ntropi to **launch** that service. To
**connect** to an already-running service, no binary is required — just a URL.

## Credentials & environment

Every client reads a sensible default credential from the environment, so local
loopback usage typically needs no arguments.

| Variable | Used by | Purpose |
|---|---|---|
| `NTROPI_NBOT_TOKEN` | `ntropi.nbot` | Bearer token for the node's control API (only when it binds non-loopback). |
| `NTROPI_HORIZON_KEY` | `ntropi.horizon` | `X-API-Key` for Horizon. |
| `NTROPI_HORIZON_ADMIN_TOKEN` | `ntropi.horizon` | `X-Admin-Token` for admin routes. |
| `NTROPI_WEB_KEY` | `ntropi.web` | Bearer/API key for the gateway. |
| `NTROPI_WEB_ADMIN_TOKEN` | `ntropi.web` | `X-Admin-Token` for the gateway admin plane. |

!!! tip "No keys on loopback"
    A node bound to loopback with auto-approve, and a gateway with no API keys
    created yet, both run open — so a local dev session needs no credentials at
    all. This mirrors the stack's no-key-by-default philosophy.

## Verify

```bash
python -c "import ntropi; print(ntropi.__version__)"
ntropi version     # if you installed the cli extra
```
