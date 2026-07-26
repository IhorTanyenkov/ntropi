# The CLI

`ntropi` is a command-line front door over the same clients the SDK exposes —
launch the stack, inspect the pool, run a turn, drive a command, toggle learning,
activate a license. It ships in the optional `cli` extra.

```bash
pip install "ntropi[cli]"
```

## Targeting a node

Most commands accept `--project/-p` (a project directory, auto-discovers the URL)
or `--url/-u` (an explicit base URL), plus `--token` when the control API is
secured. With neither, the current directory is used as the project.

## Commands

```bash
ntropi version                                  # print the ntropi version

ntropi launch ./my-project --web                # start nbot (+ Horizon, + web), keep running
ntropi launch ./my-project --no-horizon         # nbot only

ntropi health   --project ./my-project          # node health (+ license status)
ntropi pool     --project ./my-project          # the live model pool

ntropi chat "summarise report.csv" -p ./my-project        # one streamed turn
ntropi chat "…" -p ./my-project --no-stream               # block for the full reply

ntropi command /rl --project ./my-project       # run any slash-command

ntropi rl-learning       -p ./my-project        # show the learning state
ntropi rl-learning off   -p ./my-project        # freeze (for a clean eval)
ntropi rl-learning on    -p ./my-project        # resume

ntropi license NBOT-XXXX-XXXX-XXXX              # store an operator key
```

## Launch and hold

`ntropi launch` starts the services, prints their URLs, and stays in the
foreground until you press `Ctrl-C`, at which point it stops everything it
started:

```console
$ ntropi launch ./my-project --web
nbot     http://127.0.0.1:33681
horizon  http://127.0.0.1:8848
web      http://127.0.0.1:8080
running — Ctrl-C to stop
```

## Anything not covered

The CLI is intentionally small — a convenience layer. For the full surface, drop
into Python with the same clients; see the [reference](../reference/nbot.md).
