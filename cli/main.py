from __future__ import annotations

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Annotated

import pyogrio.errors
import typer

from ekisqa.model import Severity
from ekisqa.pipeline import run_validation
from ekisqa.profiles.registry import UnknownProfileError, default_registry
from ekisqa.reference.manager import ReferenceDataManager
from ekisqa.reports.geo_writer import write_geojson, write_geopackage
from ekisqa.reports.html_writer import write_html
from ekisqa.reports.json_writer import write_json
from ekisqa.reports.metadata import ReportMetadata

app = typer.Typer(help="EKIS QA command-line tool.")


class ReportFormat(str, Enum):
    JSON = "json"
    HTML = "html"
    GPKG = "gpkg"
    GEOJSON = "geojson"


@app.callback()
def _main() -> None: ...


@app.command("update-reference")
def update_reference(
    state: Annotated[str, typer.Option("--state", help="Land code.")],
    all_: Annotated[
        bool, typer.Option("--all", help="Fetch every configured reference dataset.")
    ] = False,
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


@app.command("validate")
def validate(
    file: Annotated[
        Path,
        typer.Option(
            "--file",
            help="Dataset to validate (.gpkg, directory, or shapefile).",
        ),
    ],
    state: Annotated[str, typer.Option("--state", help="Land code.")] = "BB",
    rules: Annotated[
        str | None,
        typer.Option("--rules", help="Rule categories to run (default: all)."),
    ] = None,
    format: Annotated[
        ReportFormat, typer.Option("--format", help="Report format.")
    ] = ReportFormat.JSON,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Where to write the report. Required for gpkg/geojson; "
            "for json/html, defaults to stdout.",
        ),
    ] = None,
    check_date_str: Annotated[
        str | None,
        typer.Option("--check-date", help="ISO date (YYYY-MM-DD). Defaults to today."),
    ] = None,
    live_register: Annotated[
        bool,
        typer.Option(
            "--live-register",
            help="Fetch the live EKIS register before validating.",
        ),
    ] = False,
) -> None:
    check_date = None
    if check_date_str:
        try:
            check_date = date.fromisoformat(check_date_str)
        except ValueError as exc:
            typer.echo(f"Invalid --check-date: {check_date_str!r}", err=True)
            raise typer.Exit(code=2) from exc

    try:
        run = run_validation(
            file=file,
            state=state,
            rules=rules,
            check_date=check_date,
            live_register=live_register,
        )
    except UnknownProfileError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    except (FileNotFoundError, ValueError, pyogrio.errors.DataSourceError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    if run.live_register_skipped:
        typer.echo(
            f"--live-register requested but {state} has no register client configured; "
            "skipping.",
            err=True,
        )

    _write_report(
        format,
        run.findings,
        run.compensations,
        run.interventions,
        run.rules,
        run.metadata,
        run.profile.crs,
        output,
    )

    error_count = sum(1 for f in run.findings if f.severity == Severity.ERROR)
    warning_count = sum(1 for f in run.findings if f.severity == Severity.WARNING)
    info_count = sum(1 for f in run.findings if f.severity == Severity.INFO)
    typer.echo(
        f"{len(run.findings)} finding(s): {error_count} error(s), {warning_count} warning(s), "
        f"{info_count} info.",
        err=True,
    )
    raise typer.Exit(code=1 if error_count else 0)


def _write_report(
    format: ReportFormat,
    findings,
    compensations,
    interventions,
    rules,
    metadata: ReportMetadata,
    crs: str,
    output: Path | None,
) -> None:
    if format in (ReportFormat.JSON, ReportFormat.HTML):
        content = (
            write_json(findings, metadata)
            if format == ReportFormat.JSON
            else write_html(findings, rules, metadata)
        )
        if output is None:
            typer.echo(content)
        else:
            output.write_text(content)
            typer.echo(f"Wrote {output}", err=True)
        return

    if output is None:
        typer.echo(f"--output is required for --format {format.value}.", err=True)
        raise typer.Exit(code=2)

    if format == ReportFormat.GPKG:
        write_geopackage(
            compensations, interventions, findings, rules, metadata, crs, output
        )
        typer.echo(f"Wrote {output}", err=True)
        return

    result = write_geojson(compensations, interventions, findings, rules, metadata, crs)
    kompensation_path = output.with_name(f"{output.stem}.kompensation.geojson")
    eingriff_path = output.with_name(f"{output.stem}.eingriff.geojson")
    kompensation_path.write_text(result["kompensation"])
    eingriff_path.write_text(result["eingriff"])
    typer.echo(f"Wrote {kompensation_path}", err=True)
    typer.echo(f"Wrote {eingriff_path}", err=True)


if __name__ == "__main__":
    app()
