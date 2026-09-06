from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from shapely.geometry import LineString, Point, Polygon

from ekisqa.model import CompensationFeature, InterventionFeature
from ekisqa.profiles.brandenburg.rules.technical_delivery import (
    CompensationAreaGeometryType,
    InterventionGeometryType,
)
from ekisqa.register_data import ReferenceData

CHECK_DATE = date(2026, 1, 1)
VALID_SQUARE = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
VALID_POINT = Point(400050, 5800050)


def _compensation(compensation_id: str, geometry) -> CompensationFeature:
    return CompensationFeature(compensation_id=compensation_id, geometry=geometry)


def _intervention(intervention_id: str, geometry) -> InterventionFeature:
    return InterventionFeature(intervention_id=intervention_id, geometry=geometry)


def _ctx(land_code="BB"):
    return SimpleNamespace(
        compensations=[],
        interventions=[],
        reference=ReferenceData(),
        ekis_register=None,
        axis_flags=None,
        check_date=CHECK_DATE,
        land_code=land_code,
    )


def test_tech02_passes_polygon_geometry() -> None:
    rule = CompensationAreaGeometryType()
    feature = _compensation("K-1", VALID_SQUARE)

    assert rule.check(feature, _ctx()) == []


def test_tech02_flags_point_geometry() -> None:
    rule = CompensationAreaGeometryType()
    feature = _compensation("K-1", VALID_POINT)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "TECH-02"
    assert findings[0].observed_value == "Point"


def test_tech02_flags_missing_geometry() -> None:
    rule = CompensationAreaGeometryType()
    feature = _compensation("K-1", None)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "TECH-02"
    assert findings[0].observed_value is None


def test_tech03_passes_point_geometry() -> None:
    rule = InterventionGeometryType()
    feature = _intervention("E-1", VALID_POINT)

    assert rule.check(feature, _ctx()) == []


def test_tech03_flags_line_geometry() -> None:
    rule = InterventionGeometryType()
    feature = _intervention("E-1", LineString([(0, 0), (1, 1)]))

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "TECH-03"
    assert findings[0].observed_value == "LineString"


def test_tech03_flags_missing_geometry() -> None:
    rule = InterventionGeometryType()
    feature = _intervention("E-1", None)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "TECH-03"
