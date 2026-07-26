# Reference — `ntropi.horizon`

The eval/observability client. `Client` is synchronous; `AsyncClient` is its
identical [async twin](../concepts/async.md) (its RL methods return an
`AsyncJob`).

## Client

```python
ntropi.horizon.Client(base_url="http://127.0.0.1:8848", *, key=None, admin_token=None, timeout=600.0)
ntropi.horizon.AsyncClient(...)   # same signature
```

`key` defaults to `NTROPI_HORIZON_KEY` (sent as `X-API-Key`); `admin_token`
defaults to `NTROPI_HORIZON_ADMIN_TOKEN` (sent as `X-Admin-Token`).

| Client method | Endpoint |
|---|---|
| `health()` | `GET /api/health` |
| `nbot_status()` | `GET /api/nbot` — can Horizon see a live node? |

Live-drive calls (suite run, rl train/env-train) require a reachable node and
raise [`UpstreamUnavailable`](errors.md) (502/503) when there is none.

## Resources

### `suites`
- `list()`, `get(id)`, `create(name)`
- `add_cases(id, cases)`
- `run(id, *, eval=False, model=None, judge=None) -> dict` — `eval=True` freezes learning.
- `runs(id)`

### `datasets`
- `list()`, `get(id)`, `create(name, *, kind="rl")`
- `import_samples(*, name="imported", kind="rl", samples)`
- `merge(ids, *, name=None, min_feedback=None)`

### `sessions`
- `list()`, `trace(id)`, `graph(id)`, `stats()`

### `rl`
- `train(*, datasets=None, session=None, reset=False, save=True) -> Job`
- `env_train(*, prompt=None, session=None, suite=None, case=None, iterations=10, model=None, reset=False, eval=False, judge=None) -> Job`
- `policy()`, `save()`, `checkpoint()`, `versions()`

### `jobs`
- `list()`, `get(id) -> Job`

## Jobs

`rl.train` and `rl.env_train` return a `Job` (or `AsyncJob` on the async client)
for long-running work.

```python
job = h.rl.env_train(prompt="do X", iterations=20)

job.id
job.status()                       # the full document
job.wait(timeout=None, poll=1.0)   # block to a terminal state
job.trajectory()                   # points recorded so far
for point in job.stream(poll=1.0): # yield new points until it terminates
    ...
job.pause(); job.resume(); job.stop()
```

Async form:

```python
job = await ah.rl.env_train(prompt="do X", iterations=20)
await job.wait()
async for point in job.stream():
    ...
```

Terminal states: `done`, `error`, `stopped`, `completed`, `failed`.
