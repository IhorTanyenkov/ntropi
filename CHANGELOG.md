# Changelog

All notable changes to ntropi are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versioning is
[SemVer](https://semver.org/).

## [Unreleased]
### Added
- `nbot` `chat.completions.send_exact(body)` (sync and async) posts exact bytes
  once and returns an `HTTPReceipt` with the status, the whole response body, a
  safe header subset and monotonic elapsed time. Nothing is added to the body
  (unlike `create`, which adds `stream:false`), an error status does not raise
  and a transport failure is a receipt with `status=None`.
- Horizon `suites.import_suite`, `suites.import_run` and `suites.get_run`
  (sync and async) for external suites (`horizon.external_eval/v1`). Imports
  are idempotent; a different record under an existing id raises the new
  `ConflictError` (HTTP 409).
- `ntropi.evals.ExternalHarness`: runs a stored external suite once per case
  with durable checkpoints, reports a native session only after its node log
  is found, grades with the caller's grader and returns a `new_run` record. It
  sends no feedback and does not change the node's learning.
- Horizon `rl.train` (sync and async) accepts a keyword-only
  `idempotency_key`, forwarded verbatim in the request body. Reuse the same key
  to resubmit safely after a lost acknowledgement; omitting it leaves the
  request unchanged.
### Changed
- `Job` / `AsyncJob` `wait()` and `stream()` treat Horizon's `outcome_unknown`
  status as terminal. `wait()` returns the unknown document as-is; nothing is
  reported as success and nothing is resubmitted.

## [0.8.0] — 2026-11-02
### Added
- **Published.** `pip install ntropi` — the release workflow builds the wheel
  and sdist on every `v*` tag, publishes them to PyPI and mirrors them on
  `platform.entropi.ai/pip/`.
- `ntropi[gateway]` extra (alias `web`) declares the `nbot-gateway` dependency
  for the renamed gateway; `launch --web` prefers the `nbot-gateway` console
  script and falls back to `nbot-web`.
### Fixed
- Streaming failures now raise the same `NtropiError` subclasses as request
  failures, so a dropped or erroring stream is handled by the error contract
  instead of surfacing a raw transport exception.
- Automatic retries now apply only to GET, HEAD and OPTIONS. POST, PUT, PATCH
  and DELETE execute once, including after a read timeout or 503.
- Horizon `SuiteRun.run_at` accepts integer millisecond timestamps as well as
  string timestamps, so a successful suite run no longer fails in parsing.

## [0.7.0] — 2026-08-10
### Added
- `NTROPI_API_KEY` — one platform key authenticates to both nbot and Horizon.

## [0.6.0] — 2026-07-31
### Added — Horizon completed as a training framework
- **Prompt optimization** — `horizon.prompts.optimize(prompt_id, suite_id, …)`
  proposes variants, scores them on a suite, and deploys the best (typed
  `PromptOptimization` with `.trials`, `.best_label`, `.deployed`); plus the
  versioned prompt registry: `list / get / deploy / versions / runs / revert / delete`.
- **Routing** — `horizon.routing.policies()` (typed `RoutingPolicies` — active,
  policies, action/state space), `set_policy()`, and `rl.aggregate(by=…)`.
- **Grades & judge** — `horizon.grades.grade(...)` / `.judge(...)` (typed `Grade`
  / `JudgeVerdict`) that feed the policy.
- **Review queue** — `horizon.review` (sample / queue / grade / judge /
  judge_batch / clear / delete) for curating graded data.
- **Trainers** — `horizon.trainers` (list / create / get / jobs / train / delete),
  the offline dataset-training path (typed `TrainerRun`).
- **RL controls** — `rl.rollback / export / import_ / schema / dataset`; `rl.train`
  gains a `dataset=` bucket; `rl.env_train` gains `expect / dataset_id /
  enqueue_ungraded`.
- **Datasets & sessions** — `datasets.from_session / coverage / enrich / version /
  delete`; `sessions.diff / feedback`.
### Changed
- `suites.run(...)` now returns a typed **`SuiteRun`** (`.rate`, `.passed`,
  `.total`, `.results`) instead of a raw dict — attribute access over indexing.

## [0.5.0] — 2026-07-26
### Added
- **Async parity across all three components** — `horizon.AsyncClient` and its
  resource twins, plus `AsyncJob` (async poll/wait/stream). Every component now
  ships sync **and** async.
- **Typed `Config` sections** — `set_license`, `set_network`, `set_security`,
  `set_rl`, `set_runtime`, `set_trace`, `set_node`, and `add_connector` /
  `add_peer` / `add_satellite` (idempotent by key) — define a sovereign/mesh node
  from Python without hand-editing TOML.
- **ntropi CLI** (optional `cli` extra, `ntropi` console script): `launch`,
  `pool`, `chat`, `command`, `health`, `rl-learning`, `license`, `version`.

## [0.4.0] — 2026-07-26
### Added
- **nbot structured surface fully typed** — the *teach/trace/connect* endpoints
  that were text-only or unwrapped now have typed resources (sync + async):
  `client.rl` (node policy — incl. the `learning` eval-freeze toggle, feedback,
  replay, checkpoint, versions, rollback, save, env_outcome, export/import,
  reset), `blueprints`, `kb` (+binary), `research`, `artifacts`, `prompts`,
  `notes`, `connectors`, `routing`, `agents`, `satellites`, `trace`, `files`,
  `manifesto`, plus `plan()` / `autonomy()`.
- Command namespace gains `rl_reset`, `whoami`, `license`, `allow_restricted`,
  `init`, `satellite`.

## [0.3.0] — 2026-07-26
### Added
- **ntropi.web to full parity** — `Client`/`AsyncClient` over the NBotWeb
  gateway: auth (google/logout/me), tasks + ephemeral chat (blocking + SSE), the
  read surfaces (projects/sessions/kb/agents/satellites/artifacts/blueprints/
  files/mesh), channel adapters, and the admin plane (API keys, RBAC users,
  settings/restart); `command()`, `mcp()`, and raw `proxy()`.
- **`serve_web`** launches the gateway pointed at the started nbot; `launch()`
  gains `with_web=`.
- `BaseClient.content()` for binary downloads.

## [0.2.0] — 2026-07-26
### Added
- **ntropi.horizon** — suites, sessions/traces, datasets, RL train/env-train with
  a first-class `Job` (poll/wait/stream trajectory/pause-resume-stop).
- **Runtime launch** — `ntropi.launch(project)` starts nbot (+ Horizon) from
  Python, health-gated; the Stack stops only what it started.
- **Typed command namespace** — every nbot slash-command is a method on
  `client.command` (no string passthrough; a bare string is a message).
- **ntropi.nbot.auth** — `activate(key)` stores a license key for nbot;
  `client.auth.status()` reports the node's license state from `/v1/health`.
- CI green on Python 3.10–3.13.


- Horizon client + live launch, runtime `Stack.start()`, nbot control-plane depth.

## [0.1.0] — 2026-07-25
### Added
- **Foundation** — sync + async `BaseClient` twins (httpx, auth schemes, retry +
  backoff, typed error mapping); `NtropiError` hierarchy incl. `UpstreamUnavailable`
  and `ServiceStartError`; process runtime (`ServiceProcess`, binary discovery);
  `Stack` + `connect()`.
- **ntropi.nbot** — the full node basics, sync and async:
  - config: typed `node.toml` read/write, `pool.add/remove` (`Config`).
  - projects, sessions, `tasks.submit`/`tasks.stream` (typed native events).
  - chat + OpenAI-compatible `chat.completions.create`/`.stream`, `models.list`.
  - callable `command` namespace — `command("/x")` and typed `command.pool()`.
- Service shells for `ntropi.horizon` and `ntropi.web` (health + auth).
- Tooling: ruff, mypy `--strict`, pytest (respx); CI on 3.10–3.13.

[Unreleased]: https://github.com/IhorTanyenkov/ntropi/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/IhorTanyenkov/ntropi/releases/tag/v0.6.0
[0.5.0]: https://github.com/IhorTanyenkov/ntropi/releases/tag/v0.5.0
[0.4.0]: https://github.com/IhorTanyenkov/ntropi/releases/tag/v0.4.0
[0.3.0]: https://github.com/IhorTanyenkov/ntropi/releases/tag/v0.3.0
[0.2.0]: https://github.com/IhorTanyenkov/ntropi/releases/tag/v0.2.0
[0.1.0]: https://github.com/IhorTanyenkov/ntropi/releases/tag/v0.1.0
