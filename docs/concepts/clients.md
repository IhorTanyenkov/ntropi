# Clients & the Stack

There are two ways to get a client: **connect** to a running service, or
**launch** one and get a client wired to it. Either yields the same clients.

## connect

`ntropi.connect(...)` attaches to services that are already running and returns a
[`Stack`](#the-stack). It starts nothing and stops nothing.

```python
import ntropi

stack = ntropi.connect(
    nbot_url="http://127.0.0.1:9991",     # or nbot_project= to auto-discover
    horizon_url="http://127.0.0.1:8848",
    web_url="http://127.0.0.1:8080",
)
```

Each service is wired only when you give enough to reach it. For nbot you can
pass `nbot_project=` instead of a URL and ntropi reads the live server address
from `<project>/.nconfig/control.json`.

You can also build a single client directly:

```python
c = ntropi.nbot.Client(project="/my/project")   # discovers the URL
h = ntropi.horizon.Client("http://127.0.0.1:8848", key="…")
w = ntropi.web.Client("http://127.0.0.1:8080")
```

## launch

`ntropi.launch(project, ...)` spawns the service binaries, waits for each to
become healthy, and returns a `Stack` wired to them. When Horizon comes up its
web UI is live on its port — the same Horizon you would open normally.

```python
stack = ntropi.launch(
    "/my/project",
    with_horizon=True,    # default
    with_web=False,       # also start the NBotWeb gateway
    horizon_port=8848,
    web_port=8080,
)
```

Lower-level helpers start one service each and return `(process, client)`:

```python
proc, client = ntropi.serve_nbot("/my/project")
proc, client = ntropi.serve_horizon("/my/project", port=8848)
proc, client = ntropi.serve_web("http://127.0.0.1:9991", port=8080)
```

Binaries are resolved by explicit path, then the `NTROPI_*_BIN` env var, then
`PATH`. See [Installation](../getting-started/installation.md#the-service-binaries).

## The Stack

A `Stack` bundles the three clients and any processes ntropi started.

```python
stack.nbot       # ntropi.nbot.Client | None
stack.horizon    # ntropi.horizon.Client | None
stack.web        # ntropi.web.Client | None
```

Its defining rule: **it stops only what it started.** A service reached through
`connect()` is left running on exit; a service started through `launch()` is torn
down.

```python
with ntropi.launch("/my/project", with_web=True) as stack:
    stack.nbot.tasks.submit("hello")
# nbot + Horizon + web are stopped here

stack = ntropi.connect(nbot_url="http://127.0.0.1:9991")
stack.close()   # nothing is stopped — you only connected
```

## Lifetimes & cleanup

- Sync clients are context managers (`with client: ...`) and expose `close()`.
- Async clients use `async with` and expose `aclose()`.
- Closing a `Stack` closes its clients and stops its owned processes, in reverse
  order.
