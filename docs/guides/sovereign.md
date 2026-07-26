# Sovereign deployment

Because a node and its pool run inside your own infrastructure, a deployment can
be constrained so that **no prompt, document, or trace ever leaves it** — and no
external model API is ever called. This is what makes ntropi usable in closed and
regulated environments: banks running KYC/AML in place, health and public-sector
data that cannot cross a jurisdiction, a mesh that lives inside one datacenter.

ntropi is a control-plane client that adds no external dependency of its own, so
it does not compromise an air-gapped node.

## Constrain the pool to local models

Point every `[[llm]]` entry at models that run inside the enclave — local GGUF or
in-datacenter endpoints — and omit any external API. With no external adapter in
the pool, there are **no external LLM calls**.

```python
cfg = ntropi.nbot.Config.create("/secure/project", node_id="dc-1")
cfg.pool.add("local-llama", type="llama_cpp",
             endpoint="http://127.0.0.1:8081/v1", model="llama-3.3-70b")
cfg.pool.add("peer", type="openai_compat",
             endpoint="http://10.0.0.2:9991/v1", model="mesh")   # in-datacenter peer
cfg.save()
```

## Fix data residency and access

```python
cfg.set_security(allowed_paths=["/secure/data"])   # filesystem allow-list
cfg.set_network(encrypt=True)                        # ZMQ CURVE between peers
cfg.set_trace(prompts="full")                        # keep full local traces
```

- **Data isolation, not just residency** — regulated data never leaves the
  enclave.
- **Full local traces** — the operator sees every decision and every byte; nothing
  phones home.

## Per-jurisdiction routing policy

A deployment can be constrained to its approved models and nodes, and its routing
policy is learned **per environment** — so each jurisdiction optimises within its
own constraints. Inspect and pin the active policy:

```python
c.routing.policies()          # active + available policies, action/state space
c.routing.set_policy("thompson")
```

## Licensing offline

Even a self-hosted node authorises itself. Store the operator key; the node
validates on start and daily, with an offline grace window.

```python
ntropi.nbot.activate("NBOT-XXXX-XXXX-XXXX")
c.auth.status()               # {enforced, licensed, operator, plan, grace_days_left}
```

## A worked shape — KYC in place

```python
# a dedicated node inside the bank's datacenter, no egress
cfg = ntropi.nbot.Config.create("/bank/kyc", node_id="kyc-dc")
cfg.pool.add("local", type="llama_cpp",
             endpoint="http://127.0.0.1:8081/v1", model="llama-3.3-70b")
cfg.set_security(allowed_paths=["/bank/customer-data"])
cfg.set_license(key="env:NBOT_LICENSE_KEY")
cfg.save()

stack = ntropi.launch("/bank/kyc")
c = stack.nbot
c.blueprints.run("kyc-check", {"customer_id": "42"})   # runs against the local pool
```

Every decision is logged locally; the model pool never reaches beyond the walls.

## Building the app layer air-gapped

The [NBotWeb gateway](chat-apps.md) is a self-contained FastAPI app and can run
inside the same enclave, giving a chat UI, RBAC, and API keys without any
external service. Point it at the local node with `serve_web` or its admin
settings.
