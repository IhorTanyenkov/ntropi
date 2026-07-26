# Changelog

All notable changes to ntropi are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versioning is
[SemVer](https://semver.org/).

## [Unreleased]
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

[Unreleased]: https://github.com/IhorTanyenkov/ntropi/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/IhorTanyenkov/ntropi/releases/tag/v0.1.0
