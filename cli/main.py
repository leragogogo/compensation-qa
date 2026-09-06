from __future__ import annotations

import typer

from ekisqa.profiles.registry import UnknownProfileError, default_registry
from ekisqa.reference.manager import ReferenceDataManager

app = typer.Typer(help="EKIS QA command-line tools.")


@app.callback()
def _main() -> None: ...


@app.command("update-reference")
def update_reference(
    state: str = typer.Option(..., "--state", help="Land code."),
    all_: bool = typer.Option(
        False, "--all", help="Fetch every configured reference dataset."
    ),
) -> None:
    if not all_:
        raise typer.BadParameter("Pass --all.")

    try:
        profile = default_registry().resolve(state)
    except UnknownProfileError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    written = ReferenceDataManager(profile).update()
    if not written:
        typer.echo(f"No reference datasets configured for {state}.")
        raise typer.Exit(code=1)
    for name in written:
        typer.echo(f"Wrote reference/{state}/{name}.gpkg")


if __name__ == "__main__":
    app()
