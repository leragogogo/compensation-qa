from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from shapely.geometry import Polygon

from ekisqa.model import CompensationFeature
from ekisqa.profiles.brandenburg.rules.geometric_semantic import (
    PolygonWithinBrandenburg,
)
from ekisqa.register_data import ReferenceData

CHECK_DATE = date(2026, 1, 1)

BRANDENBURG_BOUNDARY = Polygon([(0, 0), (1000, 0), (1000, 1000), (0, 1000), (0, 0)])
INSIDE_POLYGON = Polygon([(100, 100), (200, 100), (200, 200), (100, 200), (100, 100)])
OUTSIDE_POLYGON = Polygon(
    [(2000, 2000), (2100, 2000), (2100, 2100), (2000, 2100), (2000, 2000)]
)


def _compensation(compensation_id: str, geometry) -> CompensationFeature:
    return CompensationFeature(compensation_id=compensation_id, geometry=geometry)


def _ctx(land_code="BB"):
    return SimpleNamespace(
        compensations=[],
        interventions=[],
        reference=ReferenceData(loaded={"state_boundary": BRANDENBURG_BOUNDARY}),
        ekis_register=None,
        check_date=CHECK_DATE,
        land_code=land_code,
    )


def test_geosem01_passes_polygon_inside_boundary() -> None:
    rule = PolygonWithinBrandenburg()
    feature = _compensation("K-1", INSIDE_POLYGON)

    assert rule.check(feature, _ctx()) == []


def test_geosem01_flags_polygon_outside_boundary() -> None:
    rule = PolygonWithinBrandenburg()
    feature = _compensation("K-1", OUTSIDE_POLYGON)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "GEOSEM-01"
