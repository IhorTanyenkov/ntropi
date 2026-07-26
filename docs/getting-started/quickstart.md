# Quickstart

A ten-minute path from nothing to a running, observable turn — and a chat app on
top. Every snippet is real 0.5.0 API.

## 1. Define a node

Write a project's `node.toml` from Python — no hand-editing. A node is bound to a
project directory (`<project>/.nconfig/node.toml`).

```python
import ntropi

cfg = ntropi.nbot.Config.create("/my/project", node_id="rtx")
cfg.pool.add(
    "gemma",
    endpoint="https://api.infercom.ai/v1",
    model="gemma-4-31B-it",
    api_key="env:INFERCOM_APIKEY",   # a reference, never an inlined secret
    modalities=["image_in"],
)
cfg.set_rl("thompson").set_network(encrypt=True)
cfg.save()
```

See [Develop](../guides/develop.md) for the full config surface.

## 2. Launch the stack

```python
stack = ntropi.launch("/my/project", with_web=True)   # nbot + Horizon + gateway
print(stack.nbot.health())
# Horizon UI is live on :8848, the chat gateway on :8080
```

The returned [`Stack`](../concepts/clients.md#the-stack) owns the processes it
started and stops them on `close()`. Prefer a context manager:

```python
with ntropi.launch("/my/project") as stack:
    ...
```

Already have services running? Use [`connect`](../concepts/clients.md#connect)
instead — it starts nothing:

```python
stack = ntropi.connect(nbot_url="http://127.0.0.1:9991",
                       horizon_url="http://127.0.0.1:8848")
```

## 3. Inspect the pool

```python
c = stack.nbot   # a ntropi.nbot.Client
for m in c.pool.list():
    print(m.id, m.capacity, m.modalities)
```

## 4. Run and stream a turn

```python
for ev in c.tasks.stream("Plot the data in report.csv", new_session=True):
    if ev.is_token:
        print(ev.text, end="")
    elif ev.type == "artifact":
        print(f"\n[produced {ev.name}]")
```

Or block for the whole result:

```python
result = c.tasks.submit("What is 12 * 13?")
print(result.response)
```

## 5. Chat (native or OpenAI-compatible)

```python
# native ephemeral session
c.chat.send("Hello", new_session=True)

# drop-in OpenAI-compatible facade
c.chat.completions.create(
    model="nbot",  # "nbot"/"auto" routes; a real adapter id pins
    messages=[{"role": "user", "content": "hi"}],
)
```

## 6. Teach — freeze learning for a clean eval

```python
c.rl.set_learning(False)              # eval-freeze: no train/eval leakage
print(c.routing.policies()["active"])
# ... run your evaluation ...
c.rl.set_learning(True)               # resume online learning
```

Train the policy on logged experience through Horizon:

```python
job = stack.horizon.rl.train(datasets=["gsm8k-train"], reset=True)
print(job.wait()["applied"])
```

## 7. From the shell

```bash
ntropi launch ./my-project --web
ntropi pool --project ./my-project
ntropi chat "summarise report.csv" --project ./my-project
ntropi rl-learning off --project ./my-project
```

## Where to go next

- [Architecture](../concepts/architecture.md) — the mental model
- [Build a chat app](../guides/chat-apps.md) — the `ntropi.web` gateway
- [Sovereign deployment](../guides/sovereign.md) — no external calls, in-jurisdiction
- [Reference](../reference/nbot.md) — every resource and method
