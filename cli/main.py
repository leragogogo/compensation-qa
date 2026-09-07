from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from typing import Annotated

import pyogrio.errors
import typer

from ekisqa.context import ValidationContext
from ekisqa.model import Severity
from ekisqa.profiles.registry import UnknownProfileError, default_registry
from ekisqa.reference.manager import ReferenceDataManager
from ekisqa.reports.geo_writer import write_geojson, write_geopackage
from ekisqa.reports.html_writer import write_html
from ekisqa.reports.json_writer import write_json
from ekisqa.reports.metadata import ReportMetadata
from ekisqa.rules.core import CORE_RULES
from ekisqa.rules.registry import CoreRuleRegistry, StageRunner

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
            help="Where to place the report.",
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
    try:
        profile = default_registry().resolve(state)
    except UnknownProfileError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    try:
        compensations, interventions = profile.schema_adapter.parse(file)
    except (FileNotFoundError, ValueError, pyogrio.errors.DataSourceError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    if check_date_str:
        try:
            check_date = date.fromisoformat(check_date_str)
        except ValueError as exc:
            typer.echo(f"Invalid --check-date: {check_date_str!r}", err=True)
            raise typer.Exit(code=2) from exc
    else:
        check_date = datetime.now(UTC).date()

    core_rules = [rule_cls() for rule_cls in CORE_RULES]

    if rules:
        requested = {name.strip() for name in rules.split(",") if name.strip()}
        available = {rule.category for rule in [*core_rules, *profile.rule_pack]}
        unknown = requested - available
        if unknown:
            noun = "category" if len(unknown) == 1 else "categories"
            typer.echo(
                f"Unknown rule {noun}: {', '.join(sorted(unknown))}. "
                f"Available: {', '.join(sorted(available))}",
                err=True,
            )
            raise typer.Exit(code=2)
        core_rules = [rule for rule in core_rules if rule.category in requested]
        profile = replace(
            profile,
            rule_pack=[
                rule for rule in profile.rule_pack if rule.category in requested
            ],
        )

    ekis_register = None
    if live_register:
        if profile.register_client is None:
            typer.echo(
                f"--live-register requested but {state} has no register client configured; "
                "skipping.",
                err=True,
            )
        else:
            ekis_register = profile.register_client.fetch()

    context = ValidationContext(
        profile=profile,
        compensations=compensations,
        interventions=interventions,
        check_date=check_date,
        reference=ReferenceDataManager(profile).load(),
        ekis_register=ekis_register,
    )

    findings = StageRunner(CoreRuleRegistry(rules=core_rules)).run(context)
    active_rules = [*core_rules, *profile.rule_pack]

    metadata = ReportMetadata(
        land_code=profile.land_code,
        check_date=check_date,
        register_fetch_timestamp=(
            ekis_register.fetch_timestamp if ekis_register else None
        ),
    )

    _write_report(
        format,
        findings,
        compensations,
        interventions,
        active_rules,
        metadata,
        profile.crs,
        output,
    )

    error_count = sum(1 for f in findings if f.severity == Severity.ERROR)
    warning_count = sum(1 for f in findings if f.severity == Severity.WARNING)
    info_count = sum(1 for f in findings if f.severity == Severity.INFO)
    typer.echo(
        f"{len(findings)} findings: {error_count} errors, {warning_count} warnings, "
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
    if output is None:
        typer.echo(f"--output is required for --format {format.value}.", err=True)
        raise typer.Exit(code=2)

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
