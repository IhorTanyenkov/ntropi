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


## External evaluation suites

A suite whose cases are run and graded by your own harness can be stored in
Horizon as immutable evidence (schema `horizon.external_eval/v1`): the suite
pins each case's exact request plus the source and scorer digests, and each
imported run keeps every request, visible response, HTTP status, native session
id and grade. Horizon never runs these cases; its own runner is refused for
them.

```python
import json
import ntropi
from ntropi.evals import ExternalHarness, session_log_verifier

horizon = ntropi.horizon.Client("http://127.0.0.1:8848")
stored = horizon.suites.import_suite(definition)["record"]       # idempotent

node = ntropi.nbot.Client("http://127.0.0.1:<isolated-port>", timeout=900)
harness = ExternalHarness(
    suite={**definition, "definition_sha256": stored["definition_sha256"]},
    run_id="my-run-2026-11-18",
    send=node.chat.completions.send_exact,                       # exact bytes, one attempt
    grade=my_grader,                                             # (case, receipt) -> grades
    checkpoint_dir="checkpoints",
    verify_session=session_log_verifier("<isolated-project>/.nconfig/logs"),
)
record = harness.run(statement="New run on an isolated node.")
horizon.suites.import_run(definition["id"], record)              # 409 if run_id is reused
```

Point the harness only at a node nobody else is using: each case opens a new
session there, and the node's own learning runs as configured. The harness
sends nothing but the pinned requests, each at most once per run.

A case is marked as dispatched before it is sent. If the process dies, or the
receipt cannot be saved, after that point, the case's outcome is unknown: the
harness never sends it again, and `run()` raises `UnresolvedDispatch` naming
it. Resolve it with `harness.adopt(case_id, status=..., response_body=...,
note=...)` when the response can be recovered from another record, or with
`harness.abandon(case_id, reason=...)` to record it as unknown, or start a new
run under a new `run_id`. `harness.pending()` lists unresolved cases. See
`eval/refund_benchmark/refund_eval.py` in the Horizon repository for a complete
adapter around an archived benchmark and its original grader.
