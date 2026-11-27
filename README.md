<p align="center">
  <strong style="font-size:1.6em">ntropi</strong><br>
  The Python SDK for the Entropi stack: <b>nbot</b>, <b>Horizon</b> and the platform.
</p>

<p align="center">
  <a href="https://pypi.org/project/ntropi/"><img alt="PyPI" src="https://img.shields.io/pypi/v/ntropi"></a>
  <a href="https://github.com/IhorTanyenkov/ntropi/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/IhorTanyenkov/ntropi/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="mypy strict" src="https://img.shields.io/badge/mypy-strict-blue">
  <img alt="License" src="https://img.shields.io/badge/license-source--available-lightgrey">
</p>

```bash
pip install ntropi
```

```python
import ntropi

node = ntropi.nbot.Client(project="/my/project")      # finds the running node
for event in node.tasks.stream("Summarise report.csv", new_session=True):
    if event.is_token:
        print(event.text, end="")
```

## What it is

[nbot](https://platform.entropi.ai/download) is a cognitive-compute node: it plans, routes and executes work with the models you choose, on hardware you control. [Horizon](https://horizon.entropi.ai) is its fleet, trace, eval and RL-training backend. ntropi is the typed Python layer over both, sync and async, plus a runtime that can launch them.

| Package | Covers |
| --- | --- |
| `ntropi.nbot` | tasks and chat, the model pool, sessions, projects, files, agents, satellites, blueprints, connectors, the OpenAI-compatible facade, every slash command as a typed method |
| `ntropi.horizon` | suites, datasets, grades and judges, RL training and routing policies, prompt optimisation, traces |
| `ntropi.launch` | start nbot and Horizon for a project from Python, or attach to running ones |

Everything speaks the same versioned HTTP API the services expose, with Pydantic models on both sides. The SDK never sits in the request path: it is a client, not a proxy.

## Getting started

1. Install nbot and get a license key at [platform.entropi.ai](https://platform.entropi.ai). Every key starts on the Free plan.
2. `pip install ntropi` (add `"ntropi[cli]"` for the `ntropi` command).
3. Point a client at a project directory or a URL:

```python
import ntropi

# a node you started yourself
node = ntropi.nbot.Client(project="/my/project")
print(node.health())

# or by address, with the platform key
node = ntropi.nbot.Client("http://127.0.0.1:52817", token="env:NBOT_LICENSE_KEY")

# Horizon
hz = ntropi.horizon.Client("http://127.0.0.1:8848")
run = hz.suites.run(suite_id="humaneval-20")
print(run.rate, run.passed, "/", run.total)
```

The same calls are available as `ntropi.nbot.AsyncClient` and `ntropi.horizon.AsyncClient`.

### Define a node from Python

```python
cfg = ntropi.nbot.Config.create("/my/project", node_id="rtx")
cfg.pool.add("gemma", endpoint="https://api.infercom.ai/v1",
             model="gemma-4-31B-it", api_key="env:INFERCOM_APIKEY")
cfg.set_rl("thompson").set_security(allowed_paths=["/data"])
cfg.save()
```

### Launch the stack

```python
stack = ntropi.launch("/my/project", horizon=True)   # nbot + Horizon on :8848
stack.nbot.chat("hello")
stack.stop()
```

### From the shell

```bash
pip install "ntropi[cli]"
ntropi launch ./my-project
ntropi pool --project ./my-project
ntropi chat "summarise report.csv" --project ./my-project
```

## Documentation

- [SDK overview](https://platform.entropi.ai/docs?doc=sdk-overview), [installation](https://platform.entropi.ai/docs?doc=installation), [quickstart](https://platform.entropi.ai/docs?doc=sdk-quickstart)
- [`ntropi.nbot` reference](https://platform.entropi.ai/docs?doc=nbot), [`ntropi.horizon` reference](https://platform.entropi.ai/docs?doc=horizon), [errors](https://platform.entropi.ai/docs?doc=errors)
- [Changelog](CHANGELOG.md)

The `docs/` directory in this repository is the source of those pages (`mkdocs serve` renders it locally with `pip install "ntropi[docs]"`).

## Compatibility

| ntropi | nbot API | Horizon |
| --- | --- | --- |
| 0.8.x | 1.3 and later (same major) | 0.8.4 and later |

The SDK reads the node's `api_version` on connect and refuses a different major version with a clear error.

## Development

```bash
git clone https://github.com/IhorTanyenkov/ntropi.git && cd ntropi
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,cli]"
pytest -q            # offline test suite, no services needed
ruff check src tests && mypy src
```

Releases are tagged `vX.Y.Z`; the release workflow publishes to PyPI and mirrors the wheel on the platform's own index.

## License

Source-available, see [LICENSE](LICENSE). You can read, audit and use the SDK under an Entropi license; redistribution and derived packages need written permission. Contributions are welcome as pull requests.

Contact: [it@entropi.ai](mailto:it@entropi.ai)
