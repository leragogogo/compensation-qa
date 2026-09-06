from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from shapely.geometry import Polygon

from ekisqa.model import CompensationFeature
from ekisqa.profiles.brandenburg.rules.spatial_legal_constraints import (
    FlaechenpoolConsistency,
    ProtectedAreaIntersection,
)
from ekisqa.register_data import ReferenceData

CHECK_DATE = date(2026, 1, 1)
VALID_SQUARE = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
NSG_POLYGON = Polygon([(5, 5), (15, 5), (15, 15), (5, 15), (5, 5)])
DISJOINT_NSG = Polygon([(500, 500), (510, 500), (510, 510), (500, 510), (500, 500)])


def _compensation(compensation_id: str, **kwargs) -> CompensationFeature:
    kwargs.setdefault("geometry", VALID_SQUARE)
    return CompensationFeature(compensation_id=compensation_id, **kwargs)


def _ctx(reference=None, land_code="BB"):
    return SimpleNamespace(
        compensations=[],
        interventions=[],
        reference=reference if reference is not None else ReferenceData(),
        ekis_register=None,
        axis_flags=None,
        check_date=CHECK_DATE,
        land_code=land_code,
    )


def test_spatial02_passes_realkompensation_without_pool_name() -> None:
    rule = FlaechenpoolConsistency()
    feature = _compensation(
        "K-1", compensation_type="Realkompensation", area_pool_name=None
    )

    assert rule.check(feature, _ctx()) == []


def test_spatial02_passes_flaechenpoolkompensation_with_pool_name() -> None:
    rule = FlaechenpoolConsistency()
    feature = _compensation(
        "K-1", compensation_type="Flächenpoolkompensation", area_pool_name="Pool Nord"
    )

    assert rule.check(feature, _ctx()) == []


def test_spatial02_flags_flaechenpoolkompensation_without_pool_name() -> None:
    rule = FlaechenpoolConsistency()
    feature = _compensation(
        "K-1", compensation_type="Flächenpoolkompensation", area_pool_name=None
    )

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "SPATIAL-02"


def test_spatial02_flags_pool_name_on_non_flaechenpool_record() -> None:
    rule = FlaechenpoolConsistency()
    feature = _compensation(
        "K-1", compensation_type="Realkompensation", area_pool_name="Pool Nord"
    )

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "SPATIAL-02"
    assert findings[0].observed_value == "Realkompensation"


def _g04_ctx():
    return _ctx(reference=ReferenceData(loaded={"protected_areas": [NSG_POLYGON]}))


def test_spatial04_passes_disjoint_polygon() -> None:
    rule = ProtectedAreaIntersection()
    feature = _compensation(
        "K-1", geometry=Polygon([(50, 50), (60, 50), (60, 60), (50, 60), (50, 50)])
    )

    assert rule.check(feature, _g04_ctx()) == []


def test_spatial04_flags_intersecting_polygon() -> None:
    rule = ProtectedAreaIntersection()
    feature = _compensation("K-1", geometry=VALID_SQUARE)

    findings = rule.check(feature, _g04_ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "SPATIAL-04"
