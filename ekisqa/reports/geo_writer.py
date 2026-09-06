from __future__ import annotations

from collections.abc import Iterable
from dataclasses import fields
from datetime import date
from pathlib import Path
from typing import Any

import geopandas as gpd

from ekisqa.model import CompensationFeature, Finding, InterventionFeature, Severity
from ekisqa.reports.metadata import ReportMetadata, index_rules
from ekisqa.rules.base import Rule

_EXCLUDED_ATTRIBUTE_FIELDS = {"geometry", "extra", "linked_intervention"}


def _feature_attributes(
    feature: CompensationFeature | InterventionFeature,
) -> dict[str, Any]:
    return {
        f.name: getattr(feature, f.name)
        for f in fields(feature)
        if f.name not in _EXCLUDED_ATTRIBUTE_FIELDS
    }


def _group_findings_by_feature(
    findings: list[Finding], rule_index: dict[str, Rule], entity: str
) -> dict[str, list[Finding]]:
    grouped: dict[str, list[Finding]] = {}
    for finding in findings:
        rule = rule_index.get(finding.rule_id)
        if rule is None or rule.entity != entity or finding.feature_id is None:
            continue
        grouped.setdefault(finding.feature_id, []).append(finding)
    return grouped


def _qa_columns(
    feature_id: str | None, findings_by_feature: dict[str, list[Finding]]
) -> dict:
    matching = findings_by_feature.get(feature_id, []) if feature_id else []
    errors = sorted({f.rule_id for f in matching if f.severity == Severity.ERROR})
    warnings = sorted({f.rule_id for f in matching if f.severity == Severity.WARNING})
    status = "Error" if errors else "Warning" if warnings else "OK"
    return {
        "qa_status": status,
        "qa_errors": ";".join(errors),
        "qa_warnings": ";".join(warnings),
    }


def _build_geodataframe(
    features: Iterable[CompensationFeature | InterventionFeature],
    id_field: str,
    findings_by_feature: dict[str, list[Finding]],
    metadata: ReportMetadata,
    crs: str,
) -> gpd.GeoDataFrame:
    rows = []
    for feature in features:
        row = _feature_attributes(feature)
        row.update(_qa_columns(getattr(feature, id_field), findings_by_feature))
        row["land_code"] = metadata.land_code
        row["geometry"] = feature.geometry
        rows.append(row)
    return gpd.GeoDataFrame(rows, crs=crs)


def _augmented_frames(
    compensations: list[CompensationFeature],
    interventions: list[InterventionFeature],
    findings: list[Finding],
    rules: Iterable[Rule],
    metadata: ReportMetadata,
    crs: str,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    rule_index = index_rules(rules)
    comp_findings = _group_findings_by_feature(findings, rule_index, "compensation")
    int_findings = _group_findings_by_feature(findings, rule_index, "intervention")

    compensation_gdf = _build_geodataframe(
        compensations, "compensation_id", comp_findings, metadata, crs
    )
    intervention_gdf = _build_geodataframe(
        interventions, "intervention_id", int_findings, metadata, crs
    )
    return compensation_gdf, intervention_gdf


def write_geopackage(
    compensations: list[CompensationFeature],
    interventions: list[InterventionFeature],
    findings: list[Finding],
    rules: Iterable[Rule],
    metadata: ReportMetadata,
    crs: str,
    path: Path | str,
) -> None:
    compensation_gdf, intervention_gdf = _augmented_frames(
        compensations, interventions, findings, rules, metadata, crs
    )
    compensation_gdf.to_file(path, layer="Kompensation", driver="GPKG")
    intervention_gdf.to_file(path, layer="Eingriff", driver="GPKG")


def _json_safe(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    geometry_column = gdf.geometry.name
    for column in gdf.columns:
        if column == geometry_column:
            continue
        if gdf[column].map(lambda v: isinstance(v, date)).any():
            gdf[column] = gdf[column].map(
                lambda v: v.isoformat() if isinstance(v, date) else v
            )
    return gdf


def write_geojson(
    compensations: list[CompensationFeature],
    interventions: list[InterventionFeature],
    findings: list[Finding],
    rules: Iterable[Rule],
    metadata: ReportMetadata,
    crs: str,
) -> dict[str, str]:
    compensation_gdf, intervention_gdf = _augmented_frames(
        compensations, interventions, findings, rules, metadata, crs
    )
    return {
        "kompensation": _json_safe(compensation_gdf).to_json(),
        "eingriff": _json_safe(intervention_gdf).to_json(),
    }
