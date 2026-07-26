# ntropi — Python SDK + runtime for the Entropi stack

**Status:** revised plan (v2), for review. **Date:** 2026-07-25.

A single Python library to **run and operate** the three services from Python —
the orchestrator (**nbot**), the RL-eval/observability backend (**Horizon**), and
the chat-app gateway (**NBotWeb / webkit**). `import ntropi`, spin up the stack (or
connect to a running one), work with configs/projects/sessions, and each service
is live as its normal self — Horizon's web UI included.

---

## 0. The core reframing — it's a runtime, not just a client

`ntropi` is **two layers**:

1. **Runtime / lifecycle** — start, connect to, and stop each service from Python.
   `ntropi.Stack(...).start()` launches nbot + Horizon (+ optionally webkit),
   waits for health, and returns operation clients. When you start Horizon this
   way it is the *real* Horizon: its web UI is live on its port, you open it on
   your platform as normal. The SDK just launched and wired it.
2. **Client / operations** — typed clients to drive each running service (the
   HTTP surfaces below).

So a program reads:

```python
import ntropi

# launch the stack for a project (or .connect() to already-running services)
with ntropi.Stack(project="/path/to/proj") as stack:
    stack.nbot.wait_ready()               # nbot serve up (control.json + health)
    stack.horizon.open()                  # http://localhost:8848 — live UI
    s = stack.nbot.sessions.create()
    stack.nbot.tasks.submit("...", session=s)
    run = stack.horizon.suites.run("gsm8k-test", eval=True)
# context exit stops what ntropi started; connected (not started) services are left alone
```

**Two entry modes, one API:**
- `ntropi.Stack(project=..., start=[...])` — ntropi *spawns* the services it owns.
- `ntropi.Stack.connect(nbot_url=..., horizon_url=..., web_url=...)` — attach to
  services already running (a shared box, docker, a colleague's node).

`.start()` returns the same clients as `.connect()`; downstream code is identical.

---

## 1. How each service is launched / used

| Service | What it is | How ntropi runs it |
|---|---|---|
| **nbot** | C++ orchestrator binary (`nbot serve`) | subprocess: `nbot serve -c <project>/.nconfig/node.toml`; wait for `control.json` + `GET /v1/health`. Bearer-token client bound to the discovered `base_url`. |
| **Horizon** | C++ eval/observability binary (`nbot-horizon`) with a web UI | subprocess: `nbot-horizon --project <p> --port <n>`; wait for `GET /api/health`. UI live on the port — "see it like normal Horizon." X-API-Key client. |
| **webkit / NBotWeb** | Python FastAPI chat-app gateway, **its own web server**, proxies nbot, integrations (telegram/whatsapp/MCP/adapters), auth/RBAC | it's already Python, so `ntropi[web]` depends on `nbot-web` and runs it — either **in-process** (uvicorn in a thread from `create_app()`) or a managed subprocess — configured to point at the nbot instance ntropi started. |

- **Binary discovery** (nbot, Horizon): explicit path arg → `NTROPI_NBOT_BIN` /
  `NTROPI_HORIZON_BIN` → PATH (`nbot`, `nbot-horizon`) → error with a clear "not
  found / install or set the path" message. ntropi never bundles the C++ binaries.
- **webkit's role, generally:** it is the *front door for building chat
  applications*. ntropi's job is to make "nbot up → webkit up, pointed at it →
  integrations configured" a few lines, so a developer builds their chat app /
  bot on top. Because it owns a web server, `ntropi.web` both **launches** it and
  gives a **client** to its `/api/v1/*` for programmatic control (users, keys,
  projects, adapters).

---

## 2. Config & project management (first-class in v0.1)

"Working with configs, projects" is a real surface, not just clients. ntropi
reads/writes the project's `.nconfig/`:

- **Projects:** create/select/list project dirs; a project is a `.nconfig/` +
  `node.toml`. `stack.projects.create(path)`, `stack.projects.use(path)`.
  (Note: nbot's active project is *instance-global* — ntropi surfaces that plainly
  and switches via the command path.)
- **Config:** typed access to `node.toml` — the model pool (`[[llm]]` add/remove/
  edit), `[node.control]`, `[node.security]`, connectors, `[node.compute]`. So a
  Python program can define its pool and launch nbot against it without hand-
  editing TOML. `stack.config.pool.add(id=..., endpoint=..., model=..., api_key="env:...")`.
- **Sessions:** create/list/load/delete; submit turns against a session; stream.

This is the bulk of v0.1 alongside the runtime.

---

## 3. Package architecture

```
ntropi/
  __init__.py          Stack, Client, AsyncClient, exceptions, __version__
  _base.py             BaseClient — httpx, auth, retries/backoff, discovery
  _runtime.py          ServiceProcess (spawn/health-wait/stop), Stack, connect()
  _config.py           node.toml / .nconfig read-write, pool + connector helpers
  _streaming.py        Stream[T]/AsyncStream[T], typed SSE events
  _jobs.py             Job — .wait()/.stream()/.pause()/.resume()/.stop()
  _exceptions.py       error hierarchy
  nbot/                orchestrator: runtime + tasks, chat, completions, models,
                       pool, routing, rl, connectors, projects, sessions, kb,
                       files, agents, satellites, blueprints, notes, prompts, trace, plan
  horizon/             eval/obs: runtime + suites, datasets, rl(train/env_train),
                       sessions(traces/replay/diff), grades, judge, review, jobs, trainers, live
  web/                 chat-app gateway: runtime(launch NBotWeb) + auth, projects,
                       sessions, admin, adapters(telegram/whatsapp/mcp)
  types/               shared pydantic v2 models
```

Composition: one top-level `Stack`/`Client` with three sub-clients
(`stack.nbot.*`, `stack.horizon.*`, `stack.web.*`), each usable standalone and
each carrying its own runtime handle. Sync **and** async twins throughout
(`ntropi.Stack` / `ntropi.AsyncStack`) — you asked for both.

Two surfaces on nbot (Fireworks/OpenRouter/Sakana-Fugu pattern):
- **OpenAI-compatible façade** — `stack.nbot.chat.completions.create(...)` →
  `/v1/chat/completions`, drop-in for existing `openai`-client code; routing intent
  via `extra_body`.
- **Native observable surface** — `stack.nbot.tasks.stream(...)` yielding typed
  `status`/`token`/`artifact`/`done` events; RL router, plans, traces as
  first-class objects. Fugu hides routing; we expose it — that's the differentiator.

---

## 4. Design conventions

- **Sync + async twins** over one generic `BaseClient` (Anthropic/OpenAI pattern).
- **Per-service auth + discovery:** nbot Bearer (auto-discover `control.json`);
  Horizon `X-API-Key` (+ admin token); webkit its own key/session. Env:
  `NTROPI_NBOT_URL/_TOKEN/_BIN`, `NTROPI_HORIZON_URL/_KEY/_ADMIN_TOKEN/_BIN`,
  `NTROPI_WEB_URL/_KEY`.
- **`Job` first-class** — Horizon train/env_train/replay + nbot rl/replay return
  `{job_id, status_url}`; one `Job` with `.wait()/.stream()/.pause()/.resume()/.stop()`.
- **Streaming:** typed event union; native frames + OpenAI chunks.
- **Typed pydantic v2** + `extra_body`/`extra_headers` escape hatches.
- **Errors:** `NtropiError` → connection/timeout/auth(401)/forbidden(403)/
  notfound(404)/unprocessable(422)/ratelimit(429)/badrequest(400)/server(5xx) +
  distinct **`UpstreamUnavailable`(502/503)** (Horizon 502s when no nbot serve) +
  **`ServiceStartError`** (a spawned process failed health-wait).
- **Retries:** 2× exponential on connection + 408/409/429/≥500.
- **Response metadata** exposes the route/model that actually served the turn.
- **Packaging:** `httpx`+`pydantic` core; extras `ntropi[web]` (pulls `nbot-web`),
  `ntropi[cli]`. Python ≥3.10. hatchling, ruff, mypy, pytest + respx.

---

## 5. Where webkit sits (it already has a client to extract)

NBotWeb contains `HttpNBotGateway` (typed async nbot `/v1/*` client) + a downstream
`NBotWebClient`. `ntropi.nbot` is the generalization of `HttpNBotGateway`; the SDK
sits **below** the gateway. Phase-4 (not day 1): NBotWeb depends on `ntropi.nbot`,
its gateway becomes a thin adapter keeping only auth/RBAC/link-injection — one
client contract, no duplication. Until then NBotWeb runs untouched and
`ntropi.web` just launches + drives it.

---

## 6. Phased roadmap

- **Phase 0 — scaffold + runtime.** Repo, pyproject, `BaseClient`, `_runtime`
  (spawn/health-wait/stop, `Stack`, `connect`), binary discovery, errors, CI.
- **Phase 1 — nbot basics (the v0.1 cut).** Runtime start/connect; config/project
  management (pool, node.toml); sessions create/list/load; tasks submit + stream
  (typed events); chat + OpenAI-compat completions + models; pool/status. The
  "launch nbot from Python, configure it, run and observe a session" loop.
- **Phase 2 — Horizon basics (in v0.1 too).** Runtime start (UI live); connect;
  suites run, sessions/traces read, datasets, rl train + env_train with `Job`
  live-trajectory. "Start Horizon from Python, see it on my platform, drive evals."
- **Phase 3 — nbot control plane.** rl full, routing, connectors, blueprints,
  agents/satellites, notes, prompts, trace, plan.
- **Phase 4 — Horizon depth + web.** grades/judge/review/trainers; `ntropi.web`
  launch + client; fold NBotWeb onto `ntropi.nbot`.
- **Phase 5 — DX.** `ntropi` CLI, docs/examples, pagination/retry polish, publish.

**v0.1 = Phases 0–2:** launch nbot **and** Horizon from Python, manage config/
projects/sessions, run+observe, drive a basic eval, Horizon UI live. That is the
smallest thing that matches "I see it on my platform like normal."

---

## 7. New decisions this raises (need your call)

1. **webkit launch mode:** in-process (uvicorn thread from `create_app()`) or
   managed subprocess (`nbot-web`)? In-process is simpler to wire and share
   config; subprocess isolates it. Recommend **in-process by default, subprocess
   opt-in.**
2. **Binary dependency:** ntropi requires `nbot`/`nbot-horizon` installed on PATH
   (or path set). OK? (No bundling of C++ binaries.)
3. **Does `Stack` own teardown?** Recommend: ntropi stops only what it *started*;
   `connect()`-ed services are never stopped on exit.
4. Third package name still `ntropi.web` (vs `.gateway`) — keeping `web` unless you say otherwise.
