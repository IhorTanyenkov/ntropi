# Architecture

## The stack

ntropi is a client and runtime for three cooperating services. You can use one,
two, or all three, and each is reachable on its own or through a
[`Stack`](clients.md#the-stack).

```
                    ┌─────────────────────────────────────────┐
   your Python  ──▶ │  ntropi                                  │
   or the CLI       │   ├─ ntropi.nbot     → nbot node         │
                    │   ├─ ntropi.horizon  → Horizon backend   │
                    │   └─ ntropi.web      → NBotWeb gateway   │
                    └─────────────────────────────────────────┘
                                │              │            │
                        HTTP control     /api/*       /api/v1/*
                                ▼              ▼            ▼
                            ┌───────┐    ┌─────────┐  ┌──────────┐
                            │ nbot  │◀───│ Horizon │  │ NBotWeb  │──▶ nbot
                            │ node  │    │  (eval) │  │ (gateway)│
                            └───────┘    └─────────┘  └──────────┘
```

- **nbot** is the cognitive-compute node. It decomposes work, routes each part
  across a model pool, runs tools/agents/satellites, and learns. `ntropi.nbot`
  wraps its control API and command surface.
- **Horizon** reads the node's logs and drives a live node to train, grade, and
  benchmark. `ntropi.horizon` wraps its `/api/*` surface; long jobs come back as
  a [`Job`](../reference/horizon.md#jobs).
- **NBotWeb** is a FastAPI gateway with its own web server for building chat
  apps: auth/RBAC, channel adapters, an admin plane, and a proxy to the node.
  `ntropi.web` wraps its `/api/v1/*` surface.

## The cognitive pool

nbot is **model-agnostic**. It assembles a *pool* of fungible models sourced from
wherever they run — local GGUF, any OpenAI-compatible endpoint, or peer nodes on
a mesh — and treats them as interchangeable compute. High-fidelity capability
**emerges** from decomposition, routing, and composition rather than from any one
large model.

That is why "orchestration" is only one layer. The node also exposes:

- **Three execution layers** — *tools* (atomic), *agents* (autonomous LLM loops),
  *satellites* (managed long-running processes).
- **Blueprints** — followable-but-mutable recipe sequences that capture a
  business's own methods.
- **A mesh** — nodes federating into one pool across machines, teams, or orgs.
- **Everything registered and observable** — the node can reason over its own
  live resources, and you can inspect every one.

ntropi surfaces all of this as typed resources; see the
[`ntropi.nbot` reference](../reference/nbot.md).

## Where computation happens

ntropi holds no model and performs no inference. It is a control-plane client:
every method is an HTTP call to a service that does the work. This is what makes
a fully **local, air-gapped** deployment possible — the SDK adds no external
dependency of its own. See [Sovereign deployment](../guides/sovereign.md).

## Design shape

Each service client follows the same structure:

- A `Client` and an identical `AsyncClient` (see [Sync & async](async.md)).
- **Resource groups** as attributes (`client.pool`, `client.rl`, `client.chat`, …)
  holding typed methods over one area.
- A shared HTTP core with auth, retry-with-backoff on idempotent failures, and a
  typed [error hierarchy](../reference/errors.md).
- Structured, load-bearing responses as pydantic models; the long tail returns
  plain dicts (tolerant of new server fields).
