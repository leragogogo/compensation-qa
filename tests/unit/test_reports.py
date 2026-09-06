from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, Polygon

from ekisqa.model import CompensationFeature, Finding, InterventionFeature, Severity
from ekisqa.reports.geo_writer import write_geojson, write_geopackage
from ekisqa.reports.html_writer import write_html
from ekisqa.reports.json_writer import write_json
from ekisqa.reports.metadata import ReportMetadata
from ekisqa.rules.base import Rule

CRS = "EPSG:25833"


class _StubGeomRule(Rule):
    id = "GEOM-01"
    category = "Geometry"
    scope = "core"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 1

    def check(self, feature, ctx):
        return []


class _StubLegalBasisRule(Rule):
    id = "COMPLETE-06"
    category = "Completeness"
    scope = "state"
    entity = "intervention"
    severity = Severity.WARNING
    stage = 3

    def check(self, feature, ctx):
        return []


RULES = [_StubGeomRule(), _StubLegalBasisRule()]

COMPENSATIONS = [
    CompensationFeature(
        compensation_id="K-1",
        geometry=Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]),
        compensation_type="Realkompensation",
    ),
    CompensationFeature(
        compensation_id="K-2",
        geometry=Polygon([(50, 50), (60, 50), (60, 60), (50, 60), (50, 50)]),
        compensation_type="Realkompensation",
    ),
]

INTERVENTIONS = [
    InterventionFeature(
        intervention_id="E-1",
        geometry=Point(5, 5),
        legal_basis=None,
        approval_date=date(2026, 3, 1),
    ),
]

FINDINGS = [
    Finding(
        rule_id="GEOM-01",
        severity=Severity.ERROR,
        feature_id="K-1",
        land_code="BB",
        explanation="Ring is not closed: Self-intersection[0 0]",
        triggered_field="geometry",
        observed_value="Self-intersection[0 0]",
    ),
    Finding(
        rule_id="COMPLETE-06",
        severity=Severity.WARNING,
        feature_id="E-1",
        land_code="BB",
        explanation="Rechtsgrundlage is missing",
        triggered_field="legal_basis",
        observed_value=None,
    ),
]

METADATA = ReportMetadata(
    land_code="BB",
    check_date=date(2026, 1, 1),
    register_fetch_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
)


def test_write_json_includes_metadata_and_findings() -> None:
    output = write_json(FINDINGS, METADATA)
    payload = json.loads(output)

    assert payload["land_code"] == "BB"
    assert payload["check_date"] == "2026-01-01"
    assert payload["register_fetch_timestamp"] == "2026-01-01T12:00:00+00:00"
    assert len(payload["findings"]) == 2
    assert payload["findings"][0]["rule_id"] == "GEOM-01"
    assert payload["findings"][0]["severity"] == "Error"


def test_write_json_handles_no_register_timestamp() -> None:
    metadata = ReportMetadata(land_code="BB", check_date=date(2026, 1, 1))

    payload = json.loads(write_json([], metadata))

    assert payload["register_fetch_timestamp"] is None
    assert payload["findings"] == []


def test_write_html_is_standalone_with_no_external_resources() -> None:
    html = write_html(FINDINGS, RULES, METADATA)

    assert "<script" not in html
    assert "<link" not in html
    assert "http://" not in html
    assert "https://" not in html


def test_write_html_surfaces_required_fields_per_finding() -> None:
    html = write_html(FINDINGS, RULES, METADATA)

    assert "GEOM-01" in html
    assert "Error" in html
    assert ">core<" in html
    assert "K-1" in html
    assert "Ring is not closed" in html

    assert "COMPLETE-06" in html
    assert ">state<" in html
    assert "Rechtsgrundlage is missing" in html
    assert "legal_basis" in html


def test_write_html_includes_run_metadata() -> None:
    html = write_html(FINDINGS, RULES, METADATA)

    assert "BB" in html
    assert "2026-01-01T12:00:00" in html


def test_write_html_handles_no_findings() -> None:
    html = write_html([], RULES, METADATA)

    assert "No findings" in html


def test_write_geopackage_adds_qa_columns_to_both_layers(tmp_path: Path) -> None:
    path = tmp_path / "report.gpkg"

    write_geopackage(COMPENSATIONS, INTERVENTIONS, FINDINGS, RULES, METADATA, CRS, path)

    kompensation = gpd.read_file(path, layer="Kompensation")
    eingriff = gpd.read_file(path, layer="Eingriff")

    k1 = kompensation.set_index("compensation_id").loc["K-1"]
    k2 = kompensation.set_index("compensation_id").loc["K-2"]
    assert k1["qa_status"] == "Error"
    assert k1["qa_errors"] == "GEOM-01"
    assert k1["qa_warnings"] == ""
    assert k2["qa_status"] == "OK"
    assert k2["qa_errors"] == ""

    e1 = eingriff.set_index("intervention_id").loc["E-1"]
    assert e1["qa_status"] == "Warning"
    assert e1["qa_warnings"] == "COMPLETE-06"

    assert (kompensation["land_code"] == "BB").all()


def test_write_geojson_returns_two_feature_collections_with_qa_columns() -> None:
    result = write_geojson(COMPENSATIONS, INTERVENTIONS, FINDINGS, RULES, METADATA, CRS)

    assert set(result) == {"kompensation", "eingriff"}

    kompensation = json.loads(result["kompensation"])
    assert kompensation["type"] == "FeatureCollection"
    properties_by_id = {
        f["properties"]["compensation_id"]: f["properties"]
        for f in kompensation["features"]
    }
    assert properties_by_id["K-1"]["qa_status"] == "Error"
    assert properties_by_id["K-2"]["qa_status"] == "OK"

    eingriff = json.loads(result["eingriff"])
    assert eingriff["features"][0]["properties"]["qa_status"] == "Warning"
    assert eingriff["features"][0]["properties"]["approval_date"] == "2026-03-01"
