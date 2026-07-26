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
| **nbot** | the cognitive-compute node — tasks, agents, tools, satellites, the model pool, RL, mesh, KB, blueprints (orchestration is one layer, not the whole) | `ntropi.nbot` |
| **Horizon** | eval / observability — suites, datasets, RL train, traces, judge; live web UI | `ntropi.horizon` |
| **NBotWeb** | the chat-app gateway — integrations, auth/RBAC — for building chat apps | `ntropi.web` |

It wraps the **full** surface — the HTTP API, every slash/utility command,
config, and process lifecycle — with typed models, sync **and** async clients,
and a runtime that can launch the services (or connect to running ones).

## Quickstart

```python
import ntropi

# develop: define a (sovereign) node's pool + config from Python — no TOML editing
cfg = ntropi.nbot.Config.create("/my/project", node_id="rtx")
cfg.pool.add("gemma", endpoint="https://api.infercom.ai/v1",
             model="gemma-4-31B-it", api_key="env:INFERCOM_APIKEY",
             modalities=["image_in"])
cfg.set_network(encrypt=True).set_rl("thompson")
cfg.set_security(allowed_paths=["/data"])          # jurisdiction / data-in-place
cfg.save()

# connect to a running node (auto-discovers .nconfig/control.json)
c = ntropi.nbot.Client(project="/my/project")

for m in c.pool.list():
    print(m.id, m.capacity, m.modalities)

# trace: run and observe a turn as typed events
for ev in c.tasks.stream("Plot the data in report.csv", new_session=True):
    if ev.is_token:
        print(ev.text, end="")

# teach: freeze learning for a clean eval, inspect the policy, give feedback
c.rl.set_learning(False)
print(c.routing.policies()["active"])
c.rl.feedback("s-123", "positive")

# connect: blueprints, connectors, mesh — all typed
c.blueprints.run("kyc-check", {"customer_id": "42"})
print(c.connectors.list())

# every slash-command is a typed method (a bare string is a message)
print(c.command.pool())
print(c.command.rl())

# drop-in OpenAI-compatible facade
c.chat.completions.create(model="nbot", messages=[{"role": "user", "content": "hi"}])
```

Everything above has an async twin with an identical surface — for **all three**
components:

```python
async with ntropi.nbot.AsyncClient(project="/my/project") as ac:
    await ac.tasks.submit("hello")
    print(await ac.rl.learning())

async with ntropi.horizon.AsyncClient("http://127.0.0.1:8848") as ah:
    job = await ah.rl.env_train(prompt="do X", iterations=5)
    async for point in job.stream():
        print(point["reward"])
```

### Launch the stack from Python

```python
# start nbot (+ Horizon UI, + the NBotWeb chat gateway) for a project
stack = ntropi.launch("/my/project", with_web=True)
print(stack.nbot.health())
# … Horizon is live on :8848, the web gateway on :8080 …
stack.close()   # stops only what it started
```

### Build a chat app on the gateway

```python
w = ntropi.web.Client("http://127.0.0.1:8080")
w.tasks.submit("summarise the attached report", new_session=True)
key = w.admin.keys.create("mobile-app")     # secret returned once
w.admin.users.create("dev@team.com", role="user", projects=["/my/project"])
```

### From the shell (`pip install 'ntropi[cli]'`)

```bash
ntropi launch ./my-project --web
ntropi pool --project ./my-project
ntropi chat "summarise report.csv" --project ./my-project
ntropi rl-learning off --project ./my-project      # freeze for eval
```

## Install (dev)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,cli]"
pytest -q
```

Requires Python ≥ 3.10. ntropi drives the `nbot` / `nbot-horizon` / `nbot-web`
binaries — it does not bundle them; install them and put them on `PATH` (or set
`NTROPI_NBOT_BIN` / `NTROPI_HORIZON_BIN` / `NTROPI_WEB_BIN`).

## Status

`0.5.0` — full coverage across the stack:

- **nbot** — pool, projects, sessions, tasks, chat (+ OpenAI facade), models,
  the typed command namespace, **and** the structured surface (node RL,
  blueprints, kb, research, artifacts, prompts, notes, connectors, routing,
  agents, satellites, trace, files, manifesto).
- **Horizon** — suites, datasets, RL train/env-train (`Job`), sessions/traces.
- **NBotWeb** — the full gateway: auth, tasks/chat, read surfaces, adapters,
  admin (keys/users/settings), MCP, proxy.
- Sync **and** async everywhere; typed `Config`; runtime `launch`; a `ntropi` CLI.

See [`CHANGELOG.md`](CHANGELOG.md) and [`docs/plans`](docs/plans/).
