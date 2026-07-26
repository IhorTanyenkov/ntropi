# Reference — errors

Every error the SDK raises descends from `ntropi.NtropiError`, so one `except`
catches everything from the stack.

```python
import ntropi

try:
    stack.horizon.suites.run("gsm8k")
except ntropi.UpstreamUnavailable:
    ...   # Horizon is up, but no nbot serve is reachable
except ntropi.APIError as exc:
    print(exc.status, exc.payload)
except ntropi.NtropiError:
    ...   # anything else from ntropi
```

## Hierarchy

```
NtropiError
├── APIConnectionError          # could not reach the service (DNS, refused, reset)
│   └── APITimeoutError         # the request exceeded its timeout
├── APIError                    # reached the service, but it returned an error
│   ├── BadRequest              # 400
│   ├── AuthenticationError     # 401
│   ├── PermissionDenied        # 403
│   ├── NotFoundError           # 404
│   ├── UnprocessableEntity     # 422
│   ├── RateLimitError          # 429
│   ├── InternalServerError     # 5xx
│   └── UpstreamUnavailable     # 502/503 — a service is up but its upstream is not
└── ServiceStartError           # a process ntropi spawned did not become healthy in time
```

## `APIError` fields

`APIError` (and its subclasses) carry:

- `status: int | None` — the HTTP status code.
- `payload: Any` — the parsed JSON error body when the service returned one, else
  the raw text.

## Two stack-specific errors

- **`UpstreamUnavailable`** — a Horizon live call returned 502/503 because no nbot
  serve was reachable. It is broken out (not folded into generic 5xx) precisely
  because callers routinely need to catch exactly this and start or wait for the
  node.
- **`ServiceStartError`** — raised by [`launch`](../concepts/clients.md#launch) /
  `serve_*` when a spawned binary does not become healthy within its start
  timeout (or exits during startup, or cannot be found on `PATH`).

## Retries

Idempotent failures (`408, 409, 429, 500, 502, 503, 504`) are retried
automatically with exponential backoff before the error surfaces — shared by both
the sync and async clients, so behaviour never diverges.
