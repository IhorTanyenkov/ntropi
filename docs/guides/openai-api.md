# OpenAI-compatible API

The node speaks the OpenAI chat-completions protocol natively, so existing OpenAI
clients and tools work against the pool with only a `base_url` change. This page
covers where that endpoint lives, how to control the **tool level** per request,
and which ingress to use under load.

## Where it lives (and why Python is not in the way)

The OpenAI-compatible endpoint is implemented **in the nbot node itself (C++)** —
not in this SDK. `ntropi` is only a *client*; it never sits in the request-serving
path.

| Ingress | Language | Use it for |
|---|---|---|
| **nbot `/v1`** (direct) | C++ | The high-throughput path. Point clients here for maximum performance. |
| **Gateway `/v1`** (NBotWeb) | Python | When you need API-key auth + RBAC in front. Adds one hop; scale it horizontally. |
| **Horizon** | — | Not a serving path. |
| **`ntropi` SDK** | Python | Building/operating — a client, never a server. |

So for a high-load routing environment, clients talk to **nbot directly** and the
whole path is native C++. The gateway is an optional authenticated front door.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /v1/chat/completions` | OpenAI-compatible chat completions. `model:"nbot"` routes across the pool; a real adapter id pins one. |
| `GET /v1/models` | Model discovery — lists `nbot` (the pool) plus the individual adapters. |

Task submission (`/v1/task/submit`) is a **separate, richer nbot-native** surface
(sessions, files, produced-artifact records) — it is not OpenAI-format. The
OpenAI-compatible path is chat-completions.

## Tool levels — the `autonomy` field

Routing, complexity-scoring, planning, and decomposition are **always on**. The
`autonomy` field (an extension in the request body) caps only how far the node may
reach for *tools*:

| `autonomy` | Grants |
|---|---|
| `reason` | no tools — answers by reasoning across the pool |
| `tools` | + bash, file, web, kb, vision, notes… |
| `agents` | + subagents |
| `full` *(default)* | + satellites and blueprints |

Companion body fields: `complexity` (float), `include_manifesto` (bool).

## Point an OpenAI client at nbot

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:9991/v1", api_key="unused-on-loopback")

client.chat.completions.create(
    model="nbot",
    messages=[{"role": "user", "content": "grep the logs for errors"}],
    extra_body={"autonomy": "tools", "complexity": 0.4},   # router fields
)
```

```bash
curl http://127.0.0.1:9991/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"nbot","messages":[{"role":"user","content":"hi"}],"autonomy":"reason","stream":true}'
```

## Through the gateway (auth + RBAC)

The [NBotWeb gateway](chat-apps.md) exposes the same `/v1` surface, gated by an API
key and streaming SSE through:

```python
client = OpenAI(base_url="http://127.0.0.1:8080/v1", api_key="<gateway-api-key>")
client.chat.completions.create(model="nbot", messages=[...], stream=True)
```

Create the key with the gateway admin plane (`w.admin.keys.create(...)`), see
[Build a chat app](chat-apps.md#lock-it-down-the-admin-plane).

## From the ntropi SDK

The SDK's façade is `client.chat.completions` — router fields ride through as
keyword arguments:

```python
c.chat.completions.create(
    model="nbot",
    messages=[{"role": "user", "content": "summarise this"}],
    autonomy="agents",
    complexity=0.5,
)
for chunk in c.chat.completions.stream(model="nbot", messages=[...], autonomy="full"):
    ...

c.models.list()     # OpenAI-compatible model listing
c.autonomy()        # the levels + grants, from GET /v1/autonomy
```
