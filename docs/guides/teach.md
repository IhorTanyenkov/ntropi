# Teach — RL & evaluation

The node learns its routing policy online, on your own traffic. ntropi gives you
the controls to steer that learning, evaluate cleanly, and train on logged
experience through Horizon.

## The eval-freeze toggle

Online learning must be **frozen** during evaluation, or the act of measuring
leaks into the policy. `client.rl` on the node controls this.

```python
c = stack.nbot

c.rl.set_learning(False)          # freeze — no train/eval leakage
# ... run your benchmark / A-B / comparison ...
c.rl.set_learning(True)           # resume

c.rl.learning()                   # {ok, learning, notes_learning}
```

The freeze covers both the routing policy and the second (notes) bandit.

## Feedback and outcomes

Attach retroactive signals to a turn — for example from a user's follow-up, or an
objective check your app runs after the fact.

```python
c.rl.feedback("s-123", "positive")          # or "negative"
c.rl.env_outcome("s-123", goal_met=True, score=0.9)
```

## Checkpoints & versions

```python
c.rl.checkpoint(note="before campaign X")
versions = c.rl.versions()                  # list of saved versions
c.rl.rollback(2)                            # restore a version
c.rl.save()                                 # persist current state
c.rl.reset()                                # cold-start the policy
```

Export/import the learned state (policy-defined; some policies are not
exportable):

```python
snapshot = c.rl.export()
c.rl.import_(snapshot, save=True)
```

## Replay logged experience

Feed logged `(state, action, reward)` outcomes back through the policy:

```python
c.rl.replay(outcomes=my_outcomes, reset=False, save=True)
```

## Training through Horizon

Horizon is the eval/observability backend. It drives a live node to train and
grade, returning long-running work as a [`Job`](../reference/horizon.md#jobs).

### Offline replay training

```python
h = stack.horizon
job = h.rl.train(datasets=["gsm8k-train"], reset=True)
final = job.wait()
print(final["applied"])
```

### Environment training (run a task N times)

```python
job = h.rl.env_train(prompt="Solve: 12 * 13", iterations=20, eval=True)
for point in job.stream():                  # live trajectory as it grows
    print(point["iter"], point.get("reward"))
```

### Suites, datasets, judge

```python
h.suites.create("gsm8k")
h.suites.add_cases("gsm8k", [{"input": "2+2", "expected": "4"}])
run = h.suites.run("gsm8k", eval=True, judge={"model": "auto"})
print(run["passed"], run["total"])

h.datasets.import_samples(name="prod", kind="rl", samples=my_samples)
h.datasets.merge(["prod", "gsm8k-train"], min_feedback=1)
```

!!! tip "Freeze during suite runs"
    `suites.run(..., eval=True)` freezes learning for the duration of the run so
    scores are comparable and nothing leaks.
