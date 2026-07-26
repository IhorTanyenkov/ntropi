"""``ntropi`` command-line front door — the dev tool from the shell.

A thin CLI over the same clients the SDK exposes: launch the stack, inspect the
pool, run a turn, drive a command, toggle learning, activate a license. It needs
the ``cli`` extra (``pip install 'ntropi[cli]'``); :func:`main` prints a friendly
message if Typer is missing.

    ntropi launch ./my-project --web
    ntropi pool --project ./my-project
    ntropi chat "summarise report.csv" --project ./my-project
"""

import json
import sys
import time
from typing import Annotated, Any, cast

import ntropi


def _build_app() -> Any:
    """Construct the Typer app (imported lazily so the SDK has no hard CLI dep)."""
    import typer

    app = typer.Typer(add_completion=False, help="ntropi — operate the Entropi stack from the shell.")

    ProjectOpt = Annotated[str | None, typer.Option("--project", "-p", help="Project directory.")]
    UrlOpt = Annotated[str | None, typer.Option("--url", "-u", help="Explicit nbot base URL.")]
    TokenOpt = Annotated[str | None, typer.Option("--token", help="Control-API bearer token.")]

    def client(project: str | None, url: str | None, token: str | None) -> ntropi.nbot.Client:
        if not project and not url:
            project = "."
        return ntropi.nbot.Client(url, project=project, token=token)

    def dump(obj: object) -> str:
        return json.dumps(obj, indent=2, ensure_ascii=False)

    @app.command()
    def version() -> None:
        """Print the ntropi version."""
        typer.echo(ntropi.__version__)

    @app.command()
    def health(project: ProjectOpt = None, url: UrlOpt = None, token: TokenOpt = None) -> None:
        """Show the node's health (and license status if enforced)."""
        with client(project, url, token) as c:
            typer.echo(dump(c.health()))

    @app.command()
    def pool(project: ProjectOpt = None, url: UrlOpt = None, token: TokenOpt = None) -> None:
        """List the live model pool."""
        with client(project, url, token) as c:
            for m in c.pool.list():
                mods = ",".join(m.modalities) or "-"
                typer.echo(f"{m.id:<28} node={m.node:<10} cap={m.capacity:<5} load={m.load:<5} {mods}")

    @app.command()
    def command(
        text: Annotated[str, typer.Argument(help="Slash-command, e.g. '/rl' or '/pool'.")],
        project: ProjectOpt = None,
        url: UrlOpt = None,
        token: TokenOpt = None,
    ) -> None:
        """Run an interactive slash-command and print its output."""
        line = text if text.startswith("/") else f"/{text}"
        with client(project, url, token) as c:
            resp = c._http.request("POST", "/v1/command", json={"command": line})
            typer.echo(resp.get("output", "") if isinstance(resp, dict) else str(resp))

    @app.command()
    def chat(
        prompt: Annotated[str, typer.Argument(help="The message to send.")],
        project: ProjectOpt = None,
        url: UrlOpt = None,
        token: TokenOpt = None,
        stream: Annotated[bool, typer.Option(help="Stream tokens as they arrive.")] = True,
    ) -> None:
        """Send one chat turn to the node."""
        with client(project, url, token) as c:
            if stream:
                for ev in c.chat.stream(prompt, new_session=True):
                    if ev.is_token and ev.text:
                        typer.echo(ev.text, nl=False)
                typer.echo("")
            else:
                typer.echo(c.chat.send(prompt, new_session=True).response)

    @app.command(name="rl-learning")
    def rl_learning(
        state: Annotated[str | None, typer.Argument(help="'on', 'off', or omit to show.")] = None,
        project: ProjectOpt = None,
        url: UrlOpt = None,
        token: TokenOpt = None,
    ) -> None:
        """Show or set the node's online-learning (eval-freeze) toggle."""
        with client(project, url, token) as c:
            if state is None:
                typer.echo(dump(c.rl.learning()))
            else:
                typer.echo(dump(c.rl.set_learning(state.lower() in ("on", "true", "1"))))

    @app.command(name="license")
    def license_cmd(
        key: Annotated[str, typer.Argument(help="The operator license key.")],
    ) -> None:
        """Store a license key where the node reads it (~/.nbot/license.json)."""
        path = ntropi.nbot.activate(key)
        typer.echo(f"stored license key at {path}")

    @app.command()
    def launch(
        project: Annotated[str, typer.Argument(help="Project directory to launch.")],
        web: Annotated[bool, typer.Option(help="Also start the NBotWeb gateway.")] = False,
        no_horizon: Annotated[bool, typer.Option("--no-horizon", help="Skip Horizon.")] = False,
        token: TokenOpt = None,
    ) -> None:
        """Start nbot (+ Horizon, + web) for a project and keep it running."""
        stack = cast("ntropi.Stack", ntropi.launch(
            project, token=token, with_horizon=not no_horizon, with_web=web
        ))
        for name, svc in (("nbot", stack.nbot), ("horizon", stack.horizon), ("web", stack.web)):
            if svc is not None:
                typer.echo(f"{name:<8} {svc._config.base_url}")
        typer.echo("running — Ctrl-C to stop")
        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            typer.echo("\nstopping…")
        finally:
            stack.close()

    return app


def main() -> None:
    """Console-script entry point."""
    try:
        import typer  # noqa: F401
    except ModuleNotFoundError:
        print("The ntropi CLI needs the 'cli' extra:  pip install 'ntropi[cli]'", file=sys.stderr)
        raise SystemExit(1) from None
    app = _build_app()
    app()
