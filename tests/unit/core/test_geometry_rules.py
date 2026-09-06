from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from shapely.geometry import Polygon

from ekisqa.context import ValidationContext
from ekisqa.model import CompensationFeature, Severity
from ekisqa.profiles.base import ProfileReferenceConfig, StateProfile
from ekisqa.profiles.registry import default_registry
from ekisqa.register_data import ReferenceData
from ekisqa.rules.core import GEOMETRY_RULES
from ekisqa.rules.core.geometry import (
    ExteriorRingOrientation,
    InteriorRingsWithinExterior,
    MinimumAreaThreshold,
    NoDuplicateConsecutiveVertices,
    NoDuplicatePolygons,
    NonZeroArea,
    NoOverlapWithinDataset,
    NoSelfIntersection,
    RingClosure,
)
from ekisqa.rules.registry import CoreRuleRegistry, StageRunner

CHECK_DATE = date(2026, 1, 1)

VALID_SQUARE = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
BOWTIE = Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])
HOLE_OUTSIDE_SHELL = Polygon(
    [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)],
    [[(20, 20), (25, 20), (25, 25), (20, 25), (20, 20)]],
)
ZERO_AREA = Polygon([(0, 0), (10, 0), (20, 0), (0, 0)])
DUPLICATE_VERTEX = Polygon([(0, 0), (5, 0), (5, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
CLOCKWISE_SQUARE = Polygon([(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)])
TINY_SQUARE = Polygon([(0, 0), (0.5, 0), (0.5, 0.5), (0, 0.5), (0, 0)])
OVERLAPPING_SQUARE = Polygon([(5, 5), (15, 5), (15, 15), (5, 15), (5, 5)])
DISJOINT_SQUARE = Polygon([(100, 100), (110, 100), (110, 110), (100, 110), (100, 100)])


def _compensation(compensation_id: str, geometry) -> CompensationFeature:
    return CompensationFeature(compensation_id=compensation_id, geometry=geometry)


def _ctx(compensations=(), land_code="ZZ"):
    return SimpleNamespace(
        compensations=list(compensations),
        interventions=[],
        reference=ReferenceData(),
        ekis_register=None,
        check_date=CHECK_DATE,
        land_code=land_code,
    )


def test_geom01_ring_closure_passes_valid_geometry() -> None:
    rule = RingClosure()
    feature = _compensation("K-1", VALID_SQUARE)

    assert rule.check(feature, _ctx()) == []


def test_geom01_ring_closure_flags_unclosed_ring_reason() -> None:
    rule = RingClosure()
    feature = _compensation("K-1", VALID_SQUARE)

    with patch(
        "ekisqa.rules.core.geometry.explain_validity",
        return_value="Ring is not closed[0 0]",
    ):
        findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "GEOM-01"
    assert findings[0].severity == Severity.ERROR


def test_geom02_no_self_intersection_passes_valid_geometry() -> None:
    rule = NoSelfIntersection()
    feature = _compensation("K-1", VALID_SQUARE)

    assert rule.check(feature, _ctx()) == []


def test_geom02_no_self_intersection_flags_bowtie() -> None:
    rule = NoSelfIntersection()
    feature = _compensation("K-1", BOWTIE)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "GEOM-02"


def test_geom03_interior_rings_within_exterior_passes_valid_geometry() -> None:
    rule = InteriorRingsWithinExterior()
    feature = _compensation("K-1", VALID_SQUARE)

    assert rule.check(feature, _ctx()) == []


def test_geom03_interior_rings_within_exterior_flags_hole_outside_shell() -> None:
    rule = InteriorRingsWithinExterior()
    feature = _compensation("K-1", HOLE_OUTSIDE_SHELL)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "GEOM-03"


def test_geom04_non_zero_area_passes_valid_geometry() -> None:
    rule = NonZeroArea()
    feature = _compensation("K-1", VALID_SQUARE)

    assert rule.check(feature, _ctx()) == []


def test_geom04_non_zero_area_flags_degenerate_polygon() -> None:
    rule = NonZeroArea()
    feature = _compensation("K-1", ZERO_AREA)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "GEOM-04"


def test_geom05_no_duplicate_consecutive_vertices_passes_valid_geometry() -> None:
    rule = NoDuplicateConsecutiveVertices()
    feature = _compensation("K-1", VALID_SQUARE)

    assert rule.check(feature, _ctx()) == []


def test_geom05_no_duplicate_consecutive_vertices_flags_repeated_point() -> None:
    rule = NoDuplicateConsecutiveVertices()
    feature = _compensation("K-1", DUPLICATE_VERTEX)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "GEOM-05"


def test_geom06_exterior_ring_orientation_passes_ccw_geometry() -> None:
    rule = ExteriorRingOrientation()
    feature = _compensation("K-1", VALID_SQUARE)

    assert rule.check(feature, _ctx()) == []


def test_geom06_exterior_ring_orientation_flags_clockwise_exterior() -> None:
    rule = ExteriorRingOrientation()
    feature = _compensation("K-1", CLOCKWISE_SQUARE)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "GEOM-06"
    assert findings[0].severity == Severity.WARNING


def test_geom07_minimum_area_threshold_passes_large_geometry() -> None:
    rule = MinimumAreaThreshold()
    feature = _compensation("K-1", VALID_SQUARE)

    assert rule.check(feature, _ctx()) == []


def test_geom07_minimum_area_threshold_flags_sliver() -> None:
    rule = MinimumAreaThreshold()
    feature = _compensation("K-1", TINY_SQUARE)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "GEOM-07"
    assert findings[0].severity == Severity.WARNING


def test_geom08_no_duplicate_polygons_passes_distinct_geometries() -> None:
    rule = NoDuplicatePolygons()
    feature = _compensation("K-1", VALID_SQUARE)
    other = _compensation("K-2", DISJOINT_SQUARE)

    assert rule.check(feature, _ctx([feature, other])) == []


def test_geom08_no_duplicate_polygons_flags_identical_geometry() -> None:
    rule = NoDuplicatePolygons()
    feature = _compensation("K-1", VALID_SQUARE)
    duplicate = _compensation("K-2", Polygon(VALID_SQUARE.exterior.coords))

    findings = rule.check(feature, _ctx([feature, duplicate]))

    assert len(findings) == 1
    assert findings[0].rule_id == "GEOM-08"
    assert findings[0].observed_value == "K-2"


def test_geom09_no_overlap_within_dataset_passes_disjoint_geometries() -> None:
    rule = NoOverlapWithinDataset()
    feature = _compensation("K-1", VALID_SQUARE)
    other = _compensation("K-2", DISJOINT_SQUARE)

    assert rule.check(feature, _ctx([feature, other])) == []


def test_geom09_no_overlap_within_dataset_flags_overlapping_geometry() -> None:
    rule = NoOverlapWithinDataset()
    feature = _compensation("K-1", VALID_SQUARE)
    other = _compensation("K-2", OVERLAPPING_SQUARE)

    findings = rule.check(feature, _ctx([feature, other]))

    assert len(findings) == 1
    assert findings[0].rule_id == "GEOM-09"
    assert findings[0].severity == Severity.WARNING


class _NoOpSchemaAdapter:
    def parse(self, path):
        raise NotImplementedError("not used by this test")


def _synthetic_profile() -> StateProfile:
    return StateProfile(
        land_code="ZZ",
        land_name="Synthetic",
        crs="EPSG:4326",
        schema_adapter=_NoOpSchemaAdapter(),
        reference=ProfileReferenceConfig(),
    )


def test_core_rules_produce_identical_findings_under_synthetic_and_brandenburg_profiles() -> (
    None
):
    core_registry = CoreRuleRegistry(rules=[rule_cls() for rule_cls in GEOMETRY_RULES])
    compensations = [
        _compensation("K-1", VALID_SQUARE),
        _compensation("K-2", BOWTIE),
    ]

    synthetic_context = ValidationContext(
        profile=_synthetic_profile(),
        compensations=compensations,
        interventions=[],
        check_date=CHECK_DATE,
    )
    brandenburg_context = ValidationContext(
        profile=default_registry().resolve("BB"),
        compensations=compensations,
        interventions=[],
        check_date=CHECK_DATE,
    )

    synthetic_findings = StageRunner(core_registry).run(synthetic_context)
    brandenburg_findings = StageRunner(core_registry).run(brandenburg_context)

    core_rule_ids = {rule_cls.id for rule_cls in GEOMETRY_RULES}

    def _core_fired(findings):
        return sorted(
            (f.rule_id, f.feature_id) for f in findings if f.rule_id in core_rule_ids
        )

    assert _core_fired(synthetic_findings) == _core_fired(brandenburg_findings)
    assert _core_fired(synthetic_findings) != []
