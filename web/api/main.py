from __future__ import annotations

import base64
import json
import tempfile
from datetime import date
from pathlib import Path
from typing import Annotated, Any

import geopandas as gpd
import pyogrio.errors
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ekisqa.model import CompensationFeature, InterventionFeature, Severity
from ekisqa.pipeline import ValidationRun, run_validation
from ekisqa.profiles.registry import UnknownProfileError, default_registry
from ekisqa.reference.manager import ReferenceDataManager
from ekisqa.reports.geo_writer import (
    group_findings_by_feature,
    qa_columns,
    write_geojson,
    write_geopackage,
)
from ekisqa.reports.html_writer import write_html
from ekisqa.reports.json_writer import write_json
from ekisqa.reports.metadata import index_rules

app = FastAPI(title="EKIS QA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/lands")
def list_lands() -> dict[str, list[str]]:
    return {"land_codes": default_registry().land_codes()}


@app.get("/api/reference/status")
def reference_status(state: str = "BB") -> dict[str, Any]:
    try:
        profile = default_registry().resolve(state)
    except UnknownProfileError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    status = ReferenceDataManager(profile).status()
    return {
        "land_code": state,
        "cached": [name for name, ok in status.items() if ok],
        "missing": [name for name, ok in status.items() if not ok],
    }


@app.post("/api/reference/update")
def update_reference(state: str = "BB") -> dict[str, Any]:
    try:
        profile = default_registry().resolve(state)
    except UnknownProfileError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    written = ReferenceDataManager(profile).update()
    return {"land_code": state, "written": written}


@app.post("/api/validate")
async def validate(
    file: Annotated[UploadFile, File()],
    state: Annotated[str, Form()] = "BB",
    check_date_str: Annotated[str | None, Form(alias="check_date")] = None,
    live_register: Annotated[bool, Form()] = False,
) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".gpkg"):
        raise HTTPException(status_code=400, detail="Only .gpkg uploads are supported.")

    check_date: date | None = None
    if check_date_str:
        try:
            check_date = date.fromisoformat(check_date_str)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid check_date: {check_date_str!r}"
            ) from exc

    with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        run = run_validation(
            file=tmp_path, state=state, check_date=check_date, live_register=live_register
        )
    except UnknownProfileError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError, pyogrio.errors.DataSourceError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    return _build_response(run)


def _build_response(run: ValidationRun) -> dict[str, Any]:
    payload = json.loads(write_json(run.findings, run.metadata))

    summary = {
        "error": sum(1 for f in run.findings if f.severity == Severity.ERROR),
        "warning": sum(1 for f in run.findings if f.severity == Severity.WARNING),
        "info": sum(1 for f in run.findings if f.severity == Severity.INFO),
    }

    rule_index = index_rules(run.rules)
    comp_by_feature = group_findings_by_feature(
        run.findings, rule_index, "compensation"
    )
    int_by_feature = group_findings_by_feature(run.findings, rule_index, "intervention")

    with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as tmp:
        gpkg_path = Path(tmp.name)
    try:
        write_geopackage(
            run.compensations,
            run.interventions,
            run.findings,
            run.rules,
            run.metadata,
            run.profile.crs,
            gpkg_path,
        )
        gpkg_base64 = base64.b64encode(gpkg_path.read_bytes()).decode("ascii")
    finally:
        gpkg_path.unlink(missing_ok=True)

    return {
        "land_code": payload["land_code"],
        "check_date": payload["check_date"],
        "register_fetch_timestamp": payload["register_fetch_timestamp"],
        "live_register_skipped": run.live_register_skipped,
        "summary": summary,
        "findings": payload["findings"],
        "map": {
            "kompensation": _map_feature_collection(
                run.compensations, "compensation_id", comp_by_feature, run.profile.crs
            ),
            "eingriff": _map_feature_collection(
                run.interventions, "intervention_id", int_by_feature, run.profile.crs
            ),
        },
        "reports": {
            "html": write_html(run.findings, run.rules, run.metadata),
            "geojson": write_geojson(
                run.compensations,
                run.interventions,
                run.findings,
                run.rules,
                run.metadata,
                run.profile.crs,
            ),
            "gpkg_base64": gpkg_base64,
        },
    }


def _map_feature_collection(
    features: list[CompensationFeature] | list[InterventionFeature],
    id_field: str,
    findings_by_feature: dict[str, list],
    crs: str,
) -> dict[str, Any]:
    rows = []
    for feature in features:
        if feature.geometry is None:
            continue
        feature_id = getattr(feature, id_field)
        row = qa_columns(feature_id, findings_by_feature)
        row["feature_id"] = feature_id
        row["geometry"] = feature.geometry
        rows.append(row)

    if not rows:
        return {"type": "FeatureCollection", "features": []}

    gdf = gpd.GeoDataFrame(rows, crs=crs).to_crs("EPSG:4326")
    return json.loads(gdf.to_json())
