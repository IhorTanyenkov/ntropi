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
- `train(*, datasets=None, dataset=None, session=None, reset=False, save=True, idempotency_key=None) -> Job` (see [Idempotent training submission](#idempotent-training-submission))
- `env_train(*, prompt=None, session=None, suite=None, case=None, iterations=10, model=None, reset=False, eval=False, judge=None) -> Job`
- `policy()`, `save()`, `checkpoint()`, `versions()`
- `export()` or `export(tier="local")` returns the connected node's local snapshot. `export(tier="global")` requests the shareable routing prior for its active policy. Older servers that ignore the global tier raise an error in the SDK.

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

Terminal states: `done`, `error`, `stopped`, `completed`, `failed`,
`outcome_unknown`.

### `outcome_unknown`

Horizon reports `outcome_unknown` when a downstream acknowledgement was lost:
the work may or may not have been applied, and further polling will not settle
it. `wait()` and `stream()` (sync and async) stop on this state like any other
terminal state. `wait()` returns the document unchanged, with
`status == "outcome_unknown"`; `stream()` yields the points recorded so far and
ends. The SDK does not raise, does not report success, and never resubmits the
work, so check the status before reading result fields:

```python
final = job.wait()
if final["status"] == "outcome_unknown":
    ...  # reconcile (e.g. inspect h.rl.policy()) before deciding to resubmit
elif final["status"] in ("done", "completed"):
    print(final["applied"])
```

## Idempotent training submission

`rl.train` is a POST, and the SDK never retries a POST: after a timeout or a
dropped connection you cannot tell whether Horizon accepted the job. Pass a
stable `idempotency_key` to make the resubmission safe:

```python
key = "replay-gsm8k-2026-11-17"       # choose once, persist with your run record

try:
    job = h.rl.train(datasets=["gsm8k-train"], idempotency_key=key)
except (ntropi.APITimeoutError, ntropi.APIConnectionError):
    # acknowledgement lost: resume with the SAME key and the SAME arguments
    job = h.rl.train(datasets=["gsm8k-train"], idempotency_key=key)

final = job.wait()
```

The contract:

- `idempotency_key` is keyword-only and optional. A supplied value is sent
  unmodified in the JSON body as `idempotency_key`; when it is omitted (or
  `None`) the field is absent and the request body is exactly what it was
  before.
- The key identifies one intended training run. Generate it once, store it
  before the first attempt, and reuse that exact value for every resubmission
  of that run, including from a restarted process. A new key is a new run.
- Reuse the key only with the same arguments. Deduplication is performed by
  Horizon, not by the SDK; the SDK only carries the key.
- Resubmitting is always an explicit call you make. Neither `train`, `wait()`
  nor `stream()` replays a submission, including after `outcome_unknown`.
- If you still hold the job id, `h.jobs.get(job_id)` resumes waiting or
  streaming without submitting anything.

The async client is identical: `await ah.rl.train(..., idempotency_key=key)`.
