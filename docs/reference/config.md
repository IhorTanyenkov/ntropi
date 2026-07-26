# Reference — `Config`

`ntropi.nbot.Config` reads and writes a project's `node.toml`. It is file-based
and independent of any running server. See the [Develop](../guides/develop.md)
guide for a walkthrough.

## Construction

```python
Config(project, *, data=None)          # load <project>/.nconfig/node.toml (empty if absent)
Config.create(project, *, node_id="node")   # minimal config: loopback control, empty pool
```

## Properties & core methods

| Member | Purpose |
|---|---|
| `data` | the underlying dict |
| `pool` | the `[[llm]]` pool editor (`PoolConfig`) |
| `control` | the `[node.control]` table |
| `set(section, key, value)` | set under a dotted section (escape hatch) |
| `save() -> Path` | write back to `node.toml` |

## `pool` — `PoolConfig`

```python
cfg.pool.add(model_id, *, endpoint, model, type="openai_compat",
             capacity=8.0, n_ctx=None, api_key=None, modalities=None, tags=None)
cfg.pool.list()
cfg.pool.get(model_id)
cfg.pool.remove(model_id)
```

## Typed section setters

Fluent setters return the `Config`; `add_*` methods return the entry and are
idempotent by their key (shown below).

| Method | Writes | Key |
|---|---|---|
| `set_node(*, id=None, listen=None, log_level=None, chrome_path=None)` | `[node]` | — |
| `set_security(*, allowed_paths=None, peer_secret=None)` | `[node.security]` | — |
| `set_license(*, key=None, license_server=None)` | `[license]` | — |
| `set_network(*, encrypt=None, search_relay=None)` | `[network]` | — |
| `set_rl(policy)` | `[rl]` | — |
| `set_runtime(*, max_bg_agents_per_prompt=None, max_recursion_depth=None, blueprint_autoselect=None)` | `[runtime]` | — |
| `set_trace(prompts)` | `[trace]` | — |
| `add_connector(name, *, base_url, type="http", description=None, auth="none", token=None, header_name=None, timeout_s=None)` | `[[connector]]` | `name` |
| `add_peer(address, *, trusted=False, pubkey=None)` | `[[peers]]` | `address` |
| `add_satellite(id, command, *, working_dir=None, autostart=False, ready_port=None, ready_log=None, ready_cmd=None, max_restarts=None)` | `[[satellite]]` | `id` |

!!! warning "Satellites need an id"
    The node loads a `[[satellite]]` only when **both** `id` and `command` are
    present — `add_satellite` requires both.

## Secret convention

Any secret field (`api_key`, `token`, `peer_secret`, license `key`) accepts a raw
value or an `env:VAR_NAME` reference. Prefer the reference form — `Config` never
inlines a secret it was given as a reference, and secrets in TOML are read by the
node at load time.

## Sections not covered by a typed setter

Use `set()` with a dotted section. The node also parses: `[node.compute]`,
`[node.research]`, `[node.nat]`, `[node.relay]`, `[control]` fields
(`chat_session_ttl_seconds`, `chat_reaper_interval_seconds`), `[ranker]`, and
`[[llm]]` extras (`model_path`, `mmproj_path`, `n_gpu_layers`, `extra_body`,
`gonka_address`).

```python
cfg.set("node.compute", "enabled", True)
cfg.set("node.research", "max_searches_per_job", 8)
cfg.set("ranker", "budget_chars", 4000)
```
