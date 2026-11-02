# Streaming error contract qualification

Baseline: `acd50a8`, SDK version `0.7.0`. The unmodified offline suite passed
96 tests. This audit used synthetic HTTP transports, no provider calls or license
changes.

## Reproduced issue

The five synchronous and five asynchronous native/gateway streaming surfaces
bypassed the shared transport. A 401 response raised `httpx.HTTPStatusError`,
and a timeout raised `httpx.ReadTimeout`, escaping a caller's documented
`except ntropi.NtropiError` recovery path. All 20 new startup-error regression
cases failed against the baseline.

## Fix and retest

Streaming now uses shared synchronous/asynchronous transport context managers.
HTTP errors preserve their status and body in the SDK exception hierarchy;
transport failures map to `APIConnectionError` or `APITimeoutError`. Streaming
requests execute once. An interruption after a token preserves the delivered
token, closes the response, and raises without replaying the request.

Run from this repository with its development dependencies installed:

```bash
python -m pytest -q
ruff check src/ntropi/_base.py src/ntropi/nbot/resources.py src/ntropi/nbot/resources_async.py src/ntropi/web/resources.py src/ntropi/web/resources_async.py tests/test_streaming_errors.py
```

Result on October 29: **118 tests passed** in 5.92 seconds; changed-file lint
passed. The two partial-stream regressions verify response closure and exactly
one request. These are deterministic transport tests, not current NBot provider,
license, model-quality, trace-completeness or production deployment acceptance.
