# Reference — `ntropi.nbot`

The node client. `Client` is synchronous; `AsyncClient` is its identical
[async twin](../concepts/async.md).

## Client

```python
ntropi.nbot.Client(base_url=None, *, project=None, token=None, timeout=600.0)
ntropi.nbot.AsyncClient(base_url=None, *, project=None, token=None, timeout=600.0)
```

Pass an explicit `base_url` or a `project` to auto-discover it from
`<project>/.nconfig/control.json`. `token` defaults to `NTROPI_NBOT_TOKEN`.

| Client method | Endpoint | Returns |
|---|---|---|
| `health()` | `GET /v1/health` | dict |
| `plan()` | `GET /v1/plan` | dict |
| `autonomy()` | `GET /v1/autonomy` | dict |
| `close()` / `aclose()` | — | — |

Module helpers: `ntropi.nbot.activate(key)` (store a license key),
`ntropi.nbot.discover_base_url(project)`.

## Resources

### `pool`
- `list() -> list[PoolModel]` — the live model pool (`GET /v1/pool`).

### `projects`
- `list() -> list[dict]`
- `active() -> dict | None`
- `use(path) -> str` — switch the node's active project.

### `sessions`
- `list() -> list[SessionSummary]`
- `current() -> str | None`
- `get(session_id) -> Session`

### `tasks`
- `submit(prompt, *, session_id=None, new_session=False, model=None, complexity=0.0, files=None) -> TaskResult`
- `stream(...) -> Iterator[TaskEvent]` — native `status`/`token`/`artifact`/`done` frames.

### `chat`
- `send(...) -> TaskResult` — an ephemeral, persisted chat turn (`POST /v1/chat`).
- `stream(...) -> Iterator[TaskEvent]`
- `sessions() -> list[SessionSummary]`
- `delete(session_id) -> bool`
- `completions.create(*, model="nbot", messages, **extra) -> dict` — OpenAI-compatible.
- `completions.stream(...) -> Iterator[dict]` — `chat.completion.chunk` frames.

### `models`
- `list() -> list[dict]` — OpenAI-compatible model listing.

### `rl` — the node's routing policy
- `learning() -> dict` / `set_learning(enabled) -> dict` — the eval-freeze toggle.
- `feedback(session_id, signal) -> dict` — `signal` is `"positive"`/`"negative"`.
- `env_outcome(session_id, *, goal_met=False, score=None) -> dict`
- `replay(outcomes=None, *, reset=False, save=True) -> dict`
- `checkpoint(note=None)`, `versions()`, `rollback(version)`, `save()`, `reset()`
- `export() -> dict` / `import_(snapshot, *, save=True) -> dict`

### `blueprints`
- `list()`, `get(id)`, `run(id, params=None)`, `import_(blueprint)`

### `kb`
- `ingest(files)`, `list()`, `file(id) -> bytes`, `delete(id)`

### `research`
- `list()`, `get(id)`

### `artifacts`
- `graph() -> dict` — the provenance graph (`{ok, artifacts}`).

### `prompts`
- `list(model=None)`, `set(id, *, template=None, scope=None)`, `delete(id, *, model=None)`

### `notes`
- `list()`, `add(text, *, category="observation", author="user")`, `delete(id)`

### `connectors`
- `list()`, `test(name, *, input=None, path=None)`, `call(name, input)`

### `routing`
- `policies() -> dict`, `set_policy(name) -> dict`

### `agents`
- `list()`, `get(id)`, `stop(id)`

### `satellites`
- `list()`, `output(id)`, `stop(id)`

### `trace`
- `get() -> dict`, `set(prompts) -> dict` — `prompts` is `"off"`/`"meta"`/`"full"`.

### `files`
- `list(path="")`, `read(path)`, `write(path, content)`

### `manifesto`
- `get(layer="all")`, `set(layer, content)` — layers `"core"`/`"project"`.

### `auth`
- `status() -> dict` — the node's license state, from `/v1/health`.

## `command` — the slash-command namespace

Every nbot slash-command is a typed method on `client.command`, each driving
`POST /v1/command` and returning the command's text output. There is no string
passthrough: a bare string is a *message* to the model, sent via
`tasks.submit`/`chat`. For structured data, prefer the typed resources above over
a command's human-readable text.

```python
c.command.pool()          # /pool
c.command.rl()            # /rl
c.command.rl_reset()      # /rl-reset
c.command.mesh("list")    # /mesh list
c.command.whoami()        # /whoami
```

Available: `status, pool, rl, env, plan, graph, agents, artifacts, identity,
help, sessions, session, new, load, clear, manifesto(+core/project), notes, note,
kb, research, blueprint, satellites, satellite, attach, projects, project,
use_project, new_project, open_project, add_project, add_project_directory,
archive_project, export_project, import_project, mesh, peers, nbots, add_nbot,
remove_nbot, assume, hypothesis, rl_reset, whoami, license, allow_restricted,
init`.

## Typed models

`PoolModel`, `Session`, `SessionSummary`, `SessionMessage`, `Artifact`,
`TaskResult`, `TaskEvent` — all tolerant of unknown server fields
(`extra="allow"`). `TaskEvent` has `is_token` / `is_done` convenience
properties.
