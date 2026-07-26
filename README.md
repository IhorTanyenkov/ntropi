# ntropi

[![CI](https://github.com/IhorTanyenkov/ntropi/actions/workflows/ci.yml/badge.svg)](https://github.com/IhorTanyenkov/ntropi/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Types](https://img.shields.io/badge/mypy-strict-blue)
![License](https://img.shields.io/badge/license-Proprietary-lightgrey)

**Python SDK and runtime for the Entropi stack.** One import to run and operate
the whole stack from Python — a full dev tool to **develop, teach, trace, and
connect** to the nbot ecosystem.

| Component | What it is | In ntropi |
|---|---|---|
| **nbot** | the cognitive-compute node — tasks, agents, tools, satellites, the model pool, RL, mesh, KB (orchestration is one layer, not the whole) | `ntropi.nbot` |
| **Horizon** | eval / observability — suites, datasets, RL train, traces, judge; live web UI | `ntropi.horizon` |
| **NBotWeb** | the chat-app gateway — integrations, auth/RBAC — for building chat apps | `ntropi.web` |

It wraps the **full** surface (HTTP API + every slash/utility command + config +
signals), not just a REST subset, with typed models, sync **and** async clients,
and a process runtime that can launch the services (or connect to running ones).

## Quickstart

```python
import ntropi

# develop: define a node's pool from Python — no hand-editing TOML
cfg = ntropi.nbot.Config.create("/my/project", node_id="rtx")
cfg.pool.add("gemma", endpoint="https://api.infercom.ai/v1",
             model="gemma-4-31B-it", api_key="env:INFERCOM_APIKEY",
             modalities=["image_in"])
cfg.save()

# connect to a running node (auto-discovers .nconfig/control.json)
c = ntropi.nbot.Client(project="/my/project")

for m in c.pool.list():
    print(m.id, m.capacity, m.modalities)

# trace: run and observe a turn as typed events
for ev in c.tasks.stream("Plot the data in report.csv", new_session=True):
    if ev.is_token:
        print(ev.text, end="")

# the full slash-command surface, typed + escape hatch
print(c.command.pool())      # typed shortcut
print(c.command("/rl"))      # anything

# drop-in OpenAI-compatible facade
c.chat.completions.create(model="nbot", messages=[{"role": "user", "content": "hi"}])
```

Everything above has an async twin with an identical surface:

```python
async with ntropi.nbot.AsyncClient(project="/my/project") as ac:
    await ac.tasks.submit("hello")
    print(await ac.command.pool())
```

## Install (dev)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Requires Python ≥ 3.10. ntropi drives the `nbot` / `nbot-horizon` binaries — it
does not bundle them; install them and put them on `PATH` (or set
`NTROPI_NBOT_BIN` / `NTROPI_HORIZON_BIN`).

## Status

`0.1.0` — Phase 1 complete: the full `ntropi.nbot` basics (config/projects/
sessions/tasks/chat/pool/models/commands), sync + async. Horizon, the web
gateway, and the runtime launch helpers land next. See
[`docs/plans`](docs/plans/) and [`CHANGELOG.md`](CHANGELOG.md).
