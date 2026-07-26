# Connect — connectors, blueprints, mesh

The "connect" surface wires the node to the outside world and to other nodes:
external systems as connectors, proven methods as blueprints, autonomous work as
agents/satellites, and other nodes as a mesh.

## Connectors — external systems as tools

A connector is a configured external HTTP system the node can probe and invoke.
Declare them in [config](develop.md#typed-sections) with `add_connector`, then
drive them at runtime:

```python
c.connectors.list()                       # configured connectors
c.connectors.test("jira", path="/rest/api/2/myself")
c.connectors.call("jira", "GET /rest/api/2/issue/PROJ-1")
```

`call` takes an `"METHOD /path [body]"` instruction; `test` accepts either an
`input` or a `path` and returns a truncated probe result.

## Blueprints — custom business operations

Blueprints are followable-but-mutable recipe sequences that capture a business's
own methods. They are listable, runnable, importable, and mesh-shareable.

```python
c.blueprints.list()
c.blueprints.get("kyc-check")                       # the full blueprint object
c.blueprints.run("kyc-check", {"customer_id": "42"})   # params: str -> str
c.blueprints.import_(shared_blueprint_json)         # body IS the blueprint
```

A run returns `{ok, id, steps}` where each step is `{tool, success, output}`.

## Agents & satellites

*Agents* are autonomous LLM loops running in the background; *satellites* are
managed long-running processes (declared in config, e.g. a ComfyUI server).

```python
c.agents.list()                 # [{id, state}, …]
c.agents.get("a-1")             # full agent detail incl. digest/response
c.agents.stop("a-1")

c.satellites.list()
c.satellites.output("comfy")    # {ok, id, output}
c.satellites.stop("comfy")
```

## Knowledge base

Ingest documents, list them, download, and forget.

```python
c.kb.ingest([{"name": "policy.pdf", "content_base64": "…"}])
c.kb.list()                     # [{id, name, kind, mime, size, …}]
data = c.kb.file("kb-123")      # raw bytes
c.kb.delete("kb-123")
```

## Research

Deep-research jobs (search → fetch → cross-check → cited report).

```python
c.research.list()               # [{id, status, question, sources, …}]
c.research.get("r-1")           # detail incl. report + sources
```

## Mesh

Nodes federate into one pool. Mesh operations are exposed through the typed
command namespace (they return the node's human-readable output):

```python
c.command.mesh("connect tcp://10.0.0.2:5555")
c.command.peers()
c.command.add_nbot("10.0.0.3:9991")
c.command.nbots()
```

Add peers declaratively in config with `cfg.add_peer(...)` so they are present at
startup. See [Develop](develop.md#typed-sections).
