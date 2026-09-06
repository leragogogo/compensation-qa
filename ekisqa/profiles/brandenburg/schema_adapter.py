from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import pyogrio
from shapely.geometry import MultiPolygon
from shapely.geometry.base import BaseGeometry

from ekisqa.model import CompensationFeature, Finding, InterventionFeature, Severity

BRANDENBURG_CRS = "EPSG:25833"

INTERVENTION_LAYER_NAMES = ("Eingriff", "EKIS_Eingriff", "EKIS:Eingriff")
COMPENSATION_LAYER_NAMES = ("Kompensation", "EKIS_Kompensation", "EKIS:Kompensation")

_PRIMARY_EXTENSIONS = (".shp", ".gml")

_COMPENSATION_FIELD_MAP: dict[str, str] = {
    "Kompensation_ID": "compensation_id",
    "Kompensati": "compensation_id",
    "Art_der_Kompensation": "compensation_type",
    "Art_der_Ko": "compensation_type",
    "Vorhabensbezeichnung": "project_name",
    "Vorhabensb": "project_name",
    "Aktenzeichen_der_Zulassungsbehoerde": "case_reference",
    "Aktenzeich": "case_reference",
    "Bezeichnung_der_Kompensation": "compensation_name",
    "Bezeichnun": "compensation_name",
    "Bezeichnung_des_Flaechenpools": "area_pool_name",
    "Bezeichn_1": "area_pool_name",
    "Eingriff_ID": "intervention_id",
    "Eingriff_I": "intervention_id",
}

_INTERVENTION_FIELD_MAP: dict[str, str] = {
    "Eingriff_ID": "intervention_id",
    "Eingriff_I": "intervention_id",
    "Vorhabenskategorie": "project_category",
    "Vorhabensk": "project_category",
    "Vorhabensart": "project_type",
    "Vorhabensa": "project_type",
    "Vorhabensbezeichnung": "project_name",
    "Vorhabensb": "project_name",
    "Kategorie_VT": "category_vt",
    "Kategorie_": "category_vt",
    "Kategorie_ZB": "category_zb",
    "Kategori_1": "category_zb",
    "Zulassungsbehoerde": "approval_authority",
    "Zulassungs": "approval_authority",
    "Aktenzeichen_der_Zulassungsbehoerde": "case_reference",
    "Aktenzeich": "case_reference",
    "Weiteres_Aktenzeichen": "additional_case_reference",
    "Weiteres_A": "additional_case_reference",
    "Genehmigungsdatum": "approval_date",
    "Genehmigun": "approval_date",
    "Landkreis_oder_kreisfreie_Stadt": "district",
    "Landkreis_": "district",
    "Rechtsgrundlage": "legal_basis",
    "Rechtsgrun": "legal_basis",
    "Kurzbemerkung": "remarks",
    "Kurzbemerk": "remarks",
}


class BrandenburgSchemaAdapter:
    def parse(
        self, path: Path
    ) -> tuple[list[CompensationFeature], list[InterventionFeature]]:
        path = Path(path)
        sources = _locate_sources(path)

        intervention_frame = _read_layer(*sources["Eingriff"])
        compensation_frame = _read_layer(*sources["Kompensation"])

        interventions = [
            _row_to_intervention(row)
            for row in intervention_frame.to_dict(orient="records")
        ]
        intervention_by_case_reference: dict[str, InterventionFeature] = {}
        for intervention in interventions:
            if intervention.case_reference:
                intervention_by_case_reference.setdefault(
                    intervention.case_reference, intervention
                )

        compensations = [
            row_to_compensation(row)
            for row in compensation_frame.to_dict(orient="records")
        ]
        for compensation in compensations:
            if compensation.case_reference:
                compensation.linked_intervention = intervention_by_case_reference.get(
                    compensation.case_reference
                )

        return compensations, interventions


def check_crs(
    path: Path, land_code: str, expected_crs: str = BRANDENBURG_CRS
) -> list[Finding]:
    path = Path(path)
    sources = _locate_sources(path)
    findings: list[Finding] = []
    for feature_name, source in sources.items():
        frame = _read_layer(*source)
        observed = str(frame.crs) if frame.crs is not None else None
        if observed != expected_crs:
            findings.append(
                Finding(
                    rule_id="TECH-01",
                    severity=Severity.ERROR,
                    feature_id=None,
                    land_code=land_code,
                    explanation=f"{feature_name} layer CRS is {observed!r}, expected {expected_crs!r}",
                    triggered_field="crs",
                    observed_value=observed,
                )
            )
    return findings


def _locate_sources(path: Path) -> dict[str, tuple[Path, str | None]]:
    if path.is_dir():
        return {
            "Eingriff": (_find_sibling_file(path, "Eingriff"), None),
            "Kompensation": (_find_sibling_file(path, "Kompensation"), None),
        }
    if path.suffix.lower() == ".gpkg":
        available = _list_layers(path)
        return {
            "Eingriff": (path, _match_layer(available, INTERVENTION_LAYER_NAMES, path)),
            "Kompensation": (
                path,
                _match_layer(available, COMPENSATION_LAYER_NAMES, path),
            ),
        }
    directory = path.parent
    suffix = path.suffix
    return {
        "Eingriff": (_find_sibling_file(directory, "Eingriff", suffix), None),
        "Kompensation": (_find_sibling_file(directory, "Kompensation", suffix), None),
    }


def _find_sibling_file(path: Path, feature: str, suffix: str | None = None) -> Path:
    candidates = sorted(path.glob(f"{feature}*"))
    allowed_suffixes = (suffix.lower(),) if suffix else _PRIMARY_EXTENSIONS
    candidates = [c for c in candidates if c.suffix.lower() in allowed_suffixes]
    exact = [c for c in candidates if c.stem == feature]
    if exact:
        return exact[0]
    if candidates:
        return candidates[0]
    raise FileNotFoundError(f"No {feature} layer found in {path} ")


def _list_layers(path: Path) -> list[str]:
    return [str(name) for name, _ in pyogrio.list_layers(path)]


def _match_layer(available: list[str], candidates: tuple[str, ...], path: Path) -> str:
    for name in candidates:
        if name in available:
            return name
    raise ValueError(
        f"{path}: expected a layer named one of {candidates}, found {available!r}"
    )


def _read_layer(path: Path, layer: str | None) -> gpd.GeoDataFrame:
    return gpd.read_file(path, layer=layer, engine="pyogrio")


def _map_fields(
    attrs: dict[str, Any], field_map: dict[str, str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    known: dict[str, Any] = {}
    extra: dict[str, Any] = {}
    for raw_name, value in attrs.items():
        model = field_map.get(raw_name)
        if model:
            known[model] = _clean(value)
        else:
            extra[raw_name] = value
    return known, extra


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value[:10]).date()
        except ValueError:
            return None
    return None


def _row_to_intervention(row: dict[str, Any]) -> InterventionFeature:
    geometry = row.pop("geometry", None)
    known, extra = _map_fields(row, _INTERVENTION_FIELD_MAP)
    intervention_id = known.pop("intervention_id", None)
    known["approval_date"] = _parse_date(known.get("approval_date"))
    return InterventionFeature(
        intervention_id=str(intervention_id) if intervention_id else None,
        geometry=geometry,
        extra=extra,
        **known,
    )


def _as_multipolygon(geometry: BaseGeometry | None) -> BaseGeometry | None:
    if geometry is not None and geometry.geom_type == "Polygon":
        return MultiPolygon([geometry])
    return geometry


def row_to_compensation(row: dict[str, Any]) -> CompensationFeature:
    geometry = _as_multipolygon(row.pop("geometry", None))
    known, extra = _map_fields(row, _COMPENSATION_FIELD_MAP)
    compensation_id = known.pop("compensation_id", None)
    return CompensationFeature(
        compensation_id=str(compensation_id) if compensation_id else None,
        geometry=geometry,
        extra=extra,
        **known,
    )
