# Authentication & licensing

Each service authenticates differently. ntropi picks the right scheme per client
and reads a default credential from the environment, so loopback usage usually
needs nothing.

## nbot — bearer token

The node's control API requires a bearer token **only when it binds to a
non-loopback address**. On loopback with `http_autoapprove`, it runs open.

```python
c = ntropi.nbot.Client("https://node.internal:9991", token="…")
# or NTROPI_NBOT_TOKEN in the environment
```

The same token is the mesh/control secret you set in config via
`Config` (`[node.control].secret`) or `set_security(peer_secret=…)`.

## Horizon — API key + admin token

```python
h = ntropi.horizon.Client(
    "http://127.0.0.1:8848",
    key="…",           # X-API-Key       (NTROPI_HORIZON_KEY)
    admin_token="…",   # X-Admin-Token   (NTROPI_HORIZON_ADMIN_TOKEN)
)
```

## NBotWeb — key or admin token, with bootstrap-open

```python
w = ntropi.web.Client(
    "http://127.0.0.1:8080",
    key="…",           # Bearer / X-API-Key   (NTROPI_WEB_KEY)
    admin_token="…",   # X-Admin-Token        (NTROPI_WEB_ADMIN_TOKEN)
)
```

The gateway grants full access when **no API keys have been created yet and there
is no session** — so a fresh local gateway is usable immediately, and you lock it
down by creating the first key (see [Build a chat app](../guides/chat-apps.md)).
Admin routes also pass for a localhost caller when no admin token is configured.

## Licensing

A node's **license** is separate from these transport credentials — it is how the
operator authorises the node itself. ntropi does not talk to the license server;
it only writes the key where the node reads it.

```python
# equivalent to `nbot license <key>` — writes ~/.nbot/license.json (mode 0600)
path = ntropi.nbot.activate("NBOT-XXXX-XXXX-XXXX")

# read the node's license state (from /v1/health)
status = c.auth.status()
# {enforced, licensed, operator, plan, [reason], [grace_days_left]}
```

`enforced` is `False` on a build without license enforcement — there is nothing
to report. When enforced, the node validates the key against its license server
on start and once per day, with an offline grace window.

!!! warning "Keys are secrets"
    A license key and any control secret are credentials. Prefer `env:VAR`
    references in config over inlined values; `activate()` stores the key with
    owner-only permissions and never logs it.
