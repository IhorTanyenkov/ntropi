# Changelog

All notable changes to ntropi are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versioning is
[SemVer](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/IhorTanyenkov/ntropi/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/IhorTanyenkov/ntropi/releases/tag/v0.2.0
[0.1.0]: https://github.com/IhorTanyenkov/ntropi/releases/tag/v0.1.0
