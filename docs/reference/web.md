# Reference — `ntropi.web`

The NBotWeb gateway client. `Client` is synchronous; `AsyncClient` is its
identical [async twin](../concepts/async.md). See the
[Build a chat app](../guides/chat-apps.md) guide for a task-oriented walkthrough.

## Client

```python
ntropi.web.Client(base_url="http://127.0.0.1:8080", *, key=None, admin_token=None, timeout=600.0)
ntropi.web.AsyncClient(...)   # same signature
```

`key` defaults to `NTROPI_WEB_KEY` (Bearer; the gateway also accepts `X-API-Key`);
`admin_token` defaults to `NTROPI_WEB_ADMIN_TOKEN` (`X-Admin-Token`). A fresh
gateway with no keys created runs open on loopback.

| Client method | Endpoint |
|---|---|
| `health()` | `GET /api/v1/health` |
| `me()` | `GET /api/v1/auth/me` |
| `command(text)` | `POST /api/v1/command` |
| `mcp(method, params=None, *, id=1)` | `POST /api/v1/mcp` |
| `proxy(method, path, **kwargs)` | `{METHOD} /proxy/{path}` |

## Resources

### `auth`
- `google(id_token)`, `logout()`, `me()`

### `tasks`
- `submit(prompt, *, new_session=False, session_id=None, files=None) -> dict`
- `stream(...) -> Iterator[dict]` — SSE with injected artifact download-link tokens.

### `chat` (ephemeral sessions)
- `send(...)`, `stream(...)`, `sessions()`, `delete(session_id)`

### `read`
- `projects()`, `sessions()`, `session(id)`
- `kb()`, `kb_file(id) -> bytes`
- `agents()`, `satellites()`, `artifacts()`
- `file(id) -> bytes`, `mesh() -> bytes`

### `blueprints`
- `list()`, `get(id) -> bytes`, `run(id, params=None)`, `import_(payload)`

### `adapters`
- `telegram_webhook(payload)`, `whatsapp_webhook(payload)`

### `admin`
- `settings()`, `update_settings(nbot_base_url)`, `restart()`, `projects()`
- `admin.keys`: `list()`, `create(name) -> dict` (secret returned once), `revoke(id)`
- `admin.users`: `list()`, `create(email, *, role="user", projects=None)`, `update(email, *, role=None, projects=None)`, `delete(email)`

## Notes

- Binary responses (`kb_file`, `read.file`, `read.mesh`, `blueprints.get`) return
  `bytes`.
- `admin.keys.create` returns the plaintext `secret` exactly once.
- The gateway proxies the node's control API — for any endpoint not wrapped here,
  `proxy("GET", "/v1/…")` passes through.
