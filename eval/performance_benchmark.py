from __future__ import annotations

import argparse
import csv
import time
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import geopandas as gpd
from shapely.geometry import Point, Polygon

from ekisqa.context import ValidationContext
from ekisqa.profiles.registry import default_registry
from ekisqa.reference.manager import ReferenceDataManager
from ekisqa.reports.geo_writer import write_geojson, write_geopackage
from ekisqa.reports.html_writer import write_html
from ekisqa.reports.json_writer import write_json
from ekisqa.reports.metadata import ReportMetadata
from ekisqa.rules.core import CORE_RULES
from ekisqa.rules.registry import CoreRuleRegistry, StageRunner

CRS = "EPSG:25833"
_ORIGIN_X, _ORIGIN_Y = 400000.0, 5800000.0
_SPACING = 200.0


def _make_pair_gpkg(path: Path, n: int) -> Path:
    interventions = []
    compensations = []
    cols = max(1, int(n**0.5))
    for i in range(n):
        row, col = divmod(i, cols)
        x = _ORIGIN_X + col * _SPACING
        y = _ORIGIN_Y + row * _SPACING
        case_ref = f"AZ-BENCH-{i:04d}"
        interventions.append(
            {
                "Eingriff_ID": [f"E-{i}"],
                "Vorhabenskategorie": ["BImSchG"],
                "Vorhabensart": ["Windenergieanlage"],
                "Vorhabensbezeichnung": ["Benchmark"],
                "Kategorie_VT": ["Neubau"],
                "Kategorie_ZB": ["Landkreis"],
                "Zulassungsbehoerde": ["Landkreis Potsdam-Mittelmark"],
                "Aktenzeichen_der_Zulassungsbehoerde": [case_ref],
                "Weiteres_Aktenzeichen": [None],
                "Genehmigungsdatum": ["2026-03-01"],
                "Landkreis_oder_kreisfreie_Stadt": ["PM"],
                "Rechtsgrundlage": ["BImSchG"],
                "Kurzbemerkung": [None],
                "geometry": [Point(x - 30, y - 30)],
            }
        )
        compensations.append(
            {
                "Kompensation_ID": [f"K-{i}"],
                "Art_der_Kompensation": ["Realkompensation"],
                "Vorhabensbezeichnung": ["Benchmark"],
                "Aktenzeichen_der_Zulassungsbehoerde": [case_ref],
                "Bezeichnung_der_Kompensation": [f"Flaeche {i}"],
                "Bezeichnung_des_Flaechenpools": [None],
                "Eingriff_ID": [None],
                "geometry": [
                    Polygon(
                        [
                            (x, y),
                            (x + 100, y),
                            (x + 100, y + 100),
                            (x, y + 100),
                            (x, y),
                        ]
                    )
                ],
            }
        )

    def _to_gdf(rows: list[dict]) -> gpd.GeoDataFrame:
        merged: dict[str, list] = {}
        for row in rows:
            for key, value in row.items():
                merged.setdefault(key, []).extend(value)
        return gpd.GeoDataFrame(merged, crs=CRS)

    _to_gdf(interventions).to_file(path, layer="Eingriff", driver="GPKG")
    _to_gdf(compensations).to_file(path, layer="Kompensation", driver="GPKG")
    return path


def _time(fn, *args, **kwargs):
    t0 = time.monotonic()
    result = fn(*args, **kwargs)
    return result, time.monotonic() - t0


def benchmark_scenario(
    state: str, n: int, live_register: bool, tmpdir: Path
) -> dict[str, float]:
    profile = default_registry().resolve(state)
    fixture_path = tmpdir / f"n{n}.gpkg"
    if not fixture_path.exists():
        _make_pair_gpkg(fixture_path, n)

    timings: dict[str, float] = {}

    (compensations, interventions), timings["parse"] = _time(
        profile.schema_adapter.parse, fixture_path
    )
    reference, timings["reference_load"] = _time(ReferenceDataManager(profile).load)

    ekis_register = None
    timings["register_fetch"] = 0.0
    if live_register and profile.register_client is not None:
        ekis_register, timings["register_fetch"] = _time(profile.register_client.fetch)

    context = ValidationContext(
        profile=profile,
        compensations=compensations,
        interventions=interventions,
        check_date=datetime.now(UTC).date(),
        reference=reference,
        ekis_register=ekis_register,
    )
    core_rules = [rule_cls() for rule_cls in CORE_RULES]
    findings, timings["rules"] = _time(
        StageRunner(CoreRuleRegistry(rules=core_rules)).run, context
    )
    active_rules = [*core_rules, *profile.rule_pack]
    metadata = ReportMetadata(
        land_code=profile.land_code,
        check_date=context.check_date,
        register_fetch_timestamp=(
            ekis_register.fetch_timestamp if ekis_register else None
        ),
    )

    _, timings["report_json"] = _time(write_json, findings, metadata)
    _, timings["report_html"] = _time(write_html, findings, active_rules, metadata)
    _, timings["report_geojson"] = _time(
        write_geojson,
        compensations,
        interventions,
        findings,
        active_rules,
        metadata,
        profile.crs,
    )
    gpkg_out = tmpdir / f"n{n}_report.gpkg"
    _, timings["report_gpkg"] = _time(
        write_geopackage,
        compensations,
        interventions,
        findings,
        active_rules,
        metadata,
        profile.crs,
        gpkg_out,
    )
    gpkg_out.unlink(missing_ok=True)

    timings["total"] = sum(v for k, v in timings.items() if k != "total")
    timings["_findings_count"] = float(len(findings))
    return timings


def full_register_timings(csv_path: Path) -> dict[str, float] | None:
    """Read item 1's per-rule timings back out of its CSV output.

    full_register_run.py writes one "_fetch" row holding the register
    fetch time, plus one row per rule with its own "seconds" column --
    summing those gives the total rule-execution time.
    """
    if not csv_path.exists():
        return None
    fetch_s = 0.0
    rules_s = 0.0
    with csv_path.open(newline="") as f:
        for row in csv.DictReader(f):
            seconds = float(row["seconds"]) if row["seconds"] else 0.0
            if row["rule_id"] == "_fetch":
                fetch_s = seconds
            else:
                rules_s += seconds
    return {
        "register_fetch": fetch_s,
        "rules": rules_s,
        "total": fetch_s + rules_s,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--state", default="BB")
    parser.add_argument("--sizes", type=int, nargs="+", default=[1, 50])
    parser.add_argument(
        "--out", type=Path, default=Path("eval/results/performance_benchmark.csv")
    )
    parser.add_argument(
        "--full-register-csv",
        type=Path,
        default=Path("eval/results/full_register_findings.csv"),
    )
    args = parser.parse_args()

    rows = []
    with TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        for n in args.sizes:
            for live in (False, True):
                print(f"Benchmarking N={n}, live_register={live}...")
                timings = benchmark_scenario(args.state, n, live, tmpdir)
                scenario = f"n={n}, live_register={live}"
                for phase, seconds in timings.items():
                    if phase.startswith("_"):
                        continue
                    rows.append(
                        {
                            "scenario": scenario,
                            "phase": phase,
                            "seconds": round(seconds, 4),
                        }
                    )

    full_reg = full_register_timings(args.full_register_csv)
    if full_reg:
        scenario = "n=17774 (register-only, dataset-level rules, no report gen)"
        for phase, seconds in full_reg.items():
            rows.append(
                {"scenario": scenario, "phase": phase, "seconds": round(seconds, 2)}
            )
    else:
        print(
            f"Note: {args.full_register_csv} not found -- run eval/full_register_run.py first "
            "to include the full-register comparison point."
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["scenario", "phase", "seconds"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {args.out}")

    print(f"\n{'scenario':<48}{'phase':<18}{'seconds':>10}")
    for row in rows:
        print(f"{row['scenario']:<48}{row['phase']:<18}{row['seconds']:>10}")


if __name__ == "__main__":
    main()
