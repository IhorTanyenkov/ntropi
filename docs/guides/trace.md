# Trace — observe a turn

Everything the node does is inspectable data. You can watch a turn live, read the
route it took, walk the plan, and inspect the artifacts it produced.

## Stream a turn as typed events

```python
for ev in c.tasks.stream("Analyse report.csv and chart the trend", new_session=True):
    if ev.type == "status":
        print("·", ev.kind, ev.text)
    elif ev.is_token:
        print(ev.text, end="")
    elif ev.type == "artifact":
        print(f"\n[artifact {ev.name} ({ev.size} bytes)]")
    elif ev.is_done:
        print("\n[done] session", ev.session_id)
```

Native frames are `status`, `token`, `artifact`, and `done`. The blocking form
returns a `TaskResult` with `response`, `produced`, `ingested`, `files`, and
`trace`.

## The plan and the route

```python
c.plan()                        # the current execution plan (panels/steps tree)
c.routing.policies()            # {active, policies, action_space, state_space}
c.trace.get()                   # current prompt-trace verbosity
c.trace.set("full")             # off | meta | full
c.autonomy()                    # autonomy levels/state
```

## Sessions

```python
for s in c.sessions.list():
    print(s.id, s.msg_count, s.updated_at)

session = c.sessions.get("s-123")
for msg in session.messages:
    print(msg.role, msg.content)
```

## Artifacts

The node records provenance for what it produces and derives.

```python
graph = c.artifacts.graph()     # {ok, artifacts} — the provenance graph
```

## The prompt registry

Inspect and override control-plane prompts.

```python
c.prompts.list(model="gemma")                   # effective prompts for a model
c.prompts.set("router", template="…", scope="model:gemma")
c.prompts.delete("router", model="gemma")
```

## Deep observability with Horizon

For traces, decomposition graphs, grades, and a live web UI, use Horizon — it
reads the node's on-disk logs.

```python
h = stack.horizon
h.sessions.list()
h.sessions.trace("s-123")       # the full turn trace
h.sessions.graph("s-123")       # the decomposition graph
h.sessions.stats()
```

When Horizon is launched from Python its web UI is live on its port — the same
Horizon you would open in a browser.
