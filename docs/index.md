# ntropi

**Python SDK and runtime for the Entropi stack.** One import to run and operate
the whole stack from Python — a full developer tool to **develop, teach, trace,
and connect** to the nbot ecosystem.

```python
import ntropi

stack = ntropi.connect(nbot_url="http://127.0.0.1:9991",
                       horizon_url="http://127.0.0.1:8848")
print(stack.nbot.health())
for ev in stack.nbot.tasks.stream("Summarise report.csv", new_session=True):
    if ev.is_token:
        print(ev.text, end="")
```

## What it wraps

ntropi is a thin, typed layer over three services. It does not bundle them — it
drives whatever you have installed, or connects to what is already running.

| Component | What it is | Package |
|---|---|---|
| **nbot** | The cognitive-compute node — tasks, agents, tools, satellites, the model pool, RL routing, mesh, KB, blueprints. Orchestration is one layer, not the whole. | [`ntropi.nbot`](reference/nbot.md) |
| **Horizon** | Eval and observability — suites, datasets, RL training with live reward trajectories, traces, judge; a live web UI. | [`ntropi.horizon`](reference/horizon.md) |
| **NBotWeb** | The chat-app gateway — channel integrations, auth/RBAC — for building chat applications on top of a node. | [`ntropi.web`](reference/web.md) |

It covers the **full** surface of each — the HTTP API, every slash/utility
command, config, and process lifecycle — with typed models, **sync and async**
clients, and a runtime that can [launch](concepts/clients.md#launch) the services
or [connect](concepts/clients.md#connect) to running ones.

## The four things you do

<div class="grid cards" markdown>

- :material-hammer-wrench: **Develop**

    Define a node's model pool and configuration from Python — no hand-editing
    TOML. [Guide →](guides/develop.md)

- :material-school: **Teach**

    Freeze learning for clean evaluation, give feedback, train the routing policy
    on logged experience through Horizon. [Guide →](guides/teach.md)

- :material-radar: **Trace**

    Watch a turn as typed events, read its plan and route, inspect the artifact
    graph and the prompt registry. [Guide →](guides/trace.md)

- :material-connection: **Connect**

    Wire external systems as connectors, capture business methods as blueprints,
    federate nodes into a mesh. [Guide →](guides/connect.md)

</div>

## Why it exists

nbot is model-agnostic: capability **emerges** from decomposing work across a
pool of fungible models rather than depending on any single large one. ntropi is
how you operate that from code — and, because a node can run entirely inside your
own infrastructure, how you stand up a **sovereign** deployment where data never
leaves. See [Sovereign deployment](guides/sovereign.md).

## Next steps

- [Install ntropi](getting-started/installation.md)
- [Quickstart](getting-started/quickstart.md) — a 10-minute path end to end
- [Architecture](concepts/architecture.md) — how the pieces fit
