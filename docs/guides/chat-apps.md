# Build a chat app

`ntropi.web` drives **NBotWeb** — a FastAPI gateway with its own web server for
building chat applications on top of a node. It adds auth/RBAC, channel adapters
(Telegram/WhatsApp), an MCP endpoint, an admin plane, and a transparent proxy to
the node's control API.

## Start the gateway

Launch it pointed at a node ntropi started:

```python
stack = ntropi.launch("/my/project", with_web=True)   # gateway on :8080
w = stack.web
```

or run it standalone against any node:

```python
proc, w = ntropi.serve_web("http://127.0.0.1:9991", port=8080)
```

or connect to a running gateway:

```python
w = ntropi.web.Client("http://127.0.0.1:8080", key="…")
```

## Health & identity

```python
w.health()          # gateway + upstream nbot health
w.me()              # the current principal (role, projects, is_admin)
```

## Run turns

The gateway has two surfaces: TUI-parity **tasks** and ephemeral **chat**
sessions. Both stream over SSE.

```python
# blocking
w.tasks.submit("Summarise the attached report", new_session=True)

# streaming (artifact download links are injected as tokens)
for ev in w.tasks.stream("Chart the trend in report.csv"):
    print(ev)

# ephemeral chat sessions
w.chat.send("Hello", new_session=True)
for ev in w.chat.stream("Continue"):
    ...
w.chat.sessions()
w.chat.delete("c-1")
```

## Read surfaces

```python
w.read.projects()
w.read.sessions();  w.read.session("s-1")
w.read.kb();        w.read.kb_file("k-1")     # bytes
w.read.agents();    w.read.satellites()
w.read.artifacts()
w.read.file("f-1")                            # bytes
w.read.mesh()                                 # the mesh document (bytes)
w.blueprints.list(); w.blueprints.run("bp", {"x": "1"})
```

## Lock it down — the admin plane

A fresh gateway runs open until you create the first API key. Then you manage
keys and RBAC users.

```python
created = w.admin.keys.create("mobile-app")   # secret returned ONCE
print(created["secret"])
w.admin.keys.list()
w.admin.keys.revoke(created["key"]["id"])

w.admin.users.create("dev@team.com", role="user", projects=["/my/project"])
w.admin.users.update("dev@team.com", role="admin")
w.admin.users.list()
w.admin.users.delete("dev@team.com")

w.admin.settings()                            # current upstream nbot URL
w.admin.update_settings("http://127.0.0.1:9991")
```

!!! warning "The create secret is shown once"
    `admin.keys.create` returns the plaintext `secret` a single time. Store it
    then; only its hash is kept.

## Channels & MCP

```python
# webhooks (mostly server-side; useful for testing)
w.adapters.telegram_webhook(update_payload)
w.adapters.whatsapp_webhook(update_payload)

# JSON-RPC MCP surface (tools/list, tools/call)
w.mcp("tools/list")
w.mcp("tools/call", {"name": "nbot.submit_task", "arguments": {"prompt": "hi"}})
```

## Raw proxy

For anything not yet wrapped, pass a request straight through to the node's
control API:

```python
w.proxy("GET", "/v1/pool")
```

Everything above has an [async twin](../concepts/async.md) on
`ntropi.web.AsyncClient`.
