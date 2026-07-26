# ntropi

Python SDK and runtime for the Entropi stack. One import to **run and operate**
the whole stack from Python:

- **nbot** — the cognitive-compute node (tasks, agents, tools, satellites, the
  model pool, RL, mesh, KB). Orchestration is one layer of it, not the whole.
- **Horizon** — eval / observability (suites, datasets, RL train, traces, judge).
  Start it from Python and its web UI is live as normal.
- **NBotWeb** — the chat-app gateway (integrations, auth/RBAC) for building apps.

The goal is a full dev tool to **develop, teach, trace, and connect** to the nbot
ecosystem — the complete surface (HTTP API + every slash/utility command +
config + signals), not just a REST subset.

```python
import ntropi

stack = ntropi.connect(
    nbot_url="http://127.0.0.1:9991",
    horizon_url="http://127.0.0.1:8848",
)
print(stack.nbot.health())
print(stack.nbot.command("/pool"))   # any slash-command, from Python
```

## Status

Early scaffold (Phase 0): clients, auth, discovery, error hierarchy, process
runtime. Resource methods land per the roadmap in
[`docs/plans`](docs/plans/). Requires Python ≥ 3.10 and the `nbot` /
`nbot-horizon` binaries installed (ntropi drives them, it does not bundle them).

## Install (dev)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```
