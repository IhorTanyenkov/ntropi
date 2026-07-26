# Sync & async

Every client has an identical asynchronous twin. The surface is the same — same
resources, same method names, same arguments — you just `await` calls and iterate
streams with `async for`.

## The twins

| Sync | Async |
|---|---|
| `ntropi.nbot.Client` | `ntropi.nbot.AsyncClient` |
| `ntropi.horizon.Client` | `ntropi.horizon.AsyncClient` |
| `ntropi.web.Client` | `ntropi.web.AsyncClient` |

## Usage

```python
import ntropi

async with ntropi.nbot.AsyncClient(project="/my/project") as ac:
    await ac.tasks.submit("hello")
    print(await ac.rl.learning())

    async for ev in ac.tasks.stream("stream this", new_session=True):
        if ev.is_token:
            print(ev.text, end="")
```

Horizon jobs have an async form too — `rl.train` / `rl.env_train` return an
`AsyncJob` you can `await job.wait()` or `async for point in job.stream()`:

```python
async with ntropi.horizon.AsyncClient("http://127.0.0.1:8848") as ah:
    job = await ah.rl.env_train(prompt="do X", iterations=5)
    async for point in job.stream():
        print(point["reward"])
```

The web gateway is the same:

```python
async with ntropi.web.AsyncClient("http://127.0.0.1:8080") as aw:
    await aw.tasks.submit("hi", new_session=True)
    async for ev in aw.chat.stream("hello"):
        ...
```

## Notes

- Sync clients: `with client: ...` / `client.close()`. Async clients:
  `async with client: ...` / `await client.aclose()`.
- Retry-with-backoff, auth, and the typed [error hierarchy](../reference/errors.md)
  are shared by both twins, so behaviour never drifts between them.
- Streaming uses the services' native server-sent events; the sync form yields an
  iterator, the async form an async iterator.
