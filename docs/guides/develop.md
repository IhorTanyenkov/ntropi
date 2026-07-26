# Develop — define a node from Python

`ntropi.nbot.Config` reads and writes a project's `node.toml` so you can define a
node's model pool, routing, security, and mesh entirely from code — then
[launch](../concepts/clients.md#launch) a node against it. It is file-based and
bound to a project directory (`<project>/.nconfig/node.toml`); it does not need a
running server.

Credentials stay as **references** (`api_key="env:INFERCOM_APIKEY"`) — the module
never inlines a secret into the file.

## Create and save

```python
import ntropi

cfg = ntropi.nbot.Config.create("/my/project", node_id="rtx")
# ... mutate ...
cfg.save()   # writes /my/project/.nconfig/node.toml
```

`Config.create` gives a minimal config: a loopback control server on a dynamic
port and an empty pool. To edit an existing file, construct directly:

```python
cfg = ntropi.nbot.Config("/my/project")   # loads node.toml if present
```

## The model pool

The declared pool is `[[llm]]` — what a launched node will load. It is distinct
from the *live* pool you read with `client.pool.list()`.

```python
cfg.pool.add(
    "gemma",
    endpoint="https://api.infercom.ai/v1",
    model="gemma-4-31B-it",
    type="openai_compat",          # native | ollama | llama_cpp | tensorrt | anthropic | openai | openai_compat | gonka | mock
    api_key="env:INFERCOM_APIKEY",
    capacity=8.0,
    n_ctx=131072,
    modalities=["image_in"],       # opt-in capabilities
    tags=["vision", "fast"],
)

cfg.pool.list()          # the configured entries
cfg.pool.get("gemma")
cfg.pool.remove("gemma")
```

## Typed sections

Beyond the pool, the sovereignty- and mesh-relevant sections have typed setters.
Setters are fluent (they return the `Config`); the `add_*` methods return the
entry they wrote and are idempotent by key.

```python
cfg.set_node(log_level="info", chrome_path="/usr/bin/chromium")
cfg.set_security(allowed_paths=["/data", "/models"], peer_secret="env:PEER")
cfg.set_license(key="env:NBOT_LICENSE_KEY",
                license_server="https://horizon.nbotchat.app")
cfg.set_network(encrypt=True, search_relay=False)   # ZMQ CURVE + search relay
cfg.set_rl("thompson")                               # thompson | epsilon
cfg.set_runtime(max_recursion_depth=4, blueprint_autoselect=True)
cfg.set_trace(prompts="meta")                        # off | meta | full

cfg.add_connector("jira", base_url="https://jira.example",
                  auth="bearer", token="env:JIRA")
cfg.add_peer("tcp://10.0.0.2:5555", trusted=True, pubkey="…")
cfg.add_satellite("comfy", "python main.py", working_dir="/opt/comfy",
                  autostart=True, ready_port=8188)   # id AND command required
```

!!! note "Escape hatch"
    For any key not covered by a typed setter, use `cfg.set("section", "key",
    value)` — it accepts a dotted section (e.g. `"node.compute"`). See the
    [Config reference](../reference/config.md) for the complete section list.

## Then launch

```python
stack = ntropi.launch("/my/project")
print(stack.nbot.pool.list())
```
