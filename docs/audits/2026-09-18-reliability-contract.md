# SDK reliability contract update

Automatic retries now apply only to GET, HEAD and OPTIONS. POST, PUT, PATCH and DELETE execute once, including after a read timeout or 503 response. Callers must reconcile an ambiguous write result before deliberately resubmitting it; no server idempotency guarantee is implied.

Horizon SuiteRun.run_at accepts integer millisecond timestamps and historical string timestamps. The wire value is preserved. Previously an otherwise successful suite execution could raise during result parsing.

Regression coverage includes synchronous and asynchronous mutation failures, read retries, and real timestamp types. No credentials are needed for the tests.
