from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

from shapely.geometry import Polygon
from shapely.strtree import STRtree

from ekisqa.model import CompensationFeature
from ekisqa.profiles.brandenburg.rules.spatial_legal_constraints import (
    FlaechenpoolConsistency,
    NearDuplicateDetection,
    NoOverlapWithRegister,
    ProtectedAreaIntersection,
)
from ekisqa.register_data import ReferenceData, RegisterSnapshot

CHECK_DATE = date(2026, 1, 1)
VALID_SQUARE = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
NSG_POLYGON = Polygon([(5, 5), (15, 5), (15, 15), (5, 15), (5, 5)])
DISJOINT_NSG = Polygon([(500, 500), (510, 500), (510, 510), (500, 510), (500, 500)])


def _compensation(compensation_id: str, **kwargs) -> CompensationFeature:
    kwargs.setdefault("geometry", VALID_SQUARE)
    return CompensationFeature(compensation_id=compensation_id, **kwargs)


def _register(features) -> RegisterSnapshot:
    return RegisterSnapshot(
        land_code="BB",
        features=list(features),
        fetch_timestamp=datetime.now(UTC),
        index=STRtree([f.geometry for f in features]),
    )


def _ctx(reference=None, ekis_register=None, land_code="BB"):
    return SimpleNamespace(
        compensations=[],
        interventions=[],
        reference=reference if reference is not None else ReferenceData(),
        ekis_register=ekis_register,
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


REGISTER_SQUARE = Polygon([(0, 0), (20, 0), (20, 20), (0, 20), (0, 0)])
REGISTER_ENTRY = _compensation(
    "REG-1", geometry=REGISTER_SQUARE, intervention_id="E-100"
)


def test_spatial01_passes_disjoint_submission() -> None:
    rule = NoOverlapWithRegister()
    submission = _compensation(
        "K-1",
        geometry=Polygon([(1000, 1000), (1010, 1000), (1010, 1010), (1000, 1010)]),
        intervention_id="E-999",
    )

    findings = rule.check(submission, _ctx(ekis_register=_register([REGISTER_ENTRY])))

    assert findings == []


def test_spatial01_passes_small_overlap_below_threshold() -> None:
    rule = NoOverlapWithRegister()
    submission = _compensation(
        "K-1",
        geometry=Polygon([(19, 0), (39, 0), (39, 20), (19, 20)]),
        intervention_id="E-999",
    )

    findings = rule.check(submission, _ctx(ekis_register=_register([REGISTER_ENTRY])))

    assert findings == []


def test_spatial01_passes_overlap_with_same_intervention() -> None:
    rule = NoOverlapWithRegister()
    submission = _compensation("K-1", geometry=REGISTER_SQUARE, intervention_id="E-100")

    findings = rule.check(submission, _ctx(ekis_register=_register([REGISTER_ENTRY])))

    assert findings == []


def test_spatial01_flags_significant_overlap_with_different_intervention() -> None:
    rule = NoOverlapWithRegister()
    submission = _compensation("K-1", geometry=REGISTER_SQUARE, intervention_id="E-999")

    findings = rule.check(submission, _ctx(ekis_register=_register([REGISTER_ENTRY])))

    assert len(findings) == 1
    assert findings[0].rule_id == "SPATIAL-01"
    assert findings[0].observed_value == "REG-1"


def test_spatial01_handles_missing_register_gracefully() -> None:
    rule = NoOverlapWithRegister()
    submission = _compensation("K-1", geometry=REGISTER_SQUARE, intervention_id="E-999")

    assert rule.check(submission, _ctx(ekis_register=None)) == []


def test_spatial03_flags_near_identical_geometry_different_intervention() -> None:
    rule = NearDuplicateDetection()
    submission = _compensation(
        "K-1",
        geometry=Polygon([(1, 0), (21, 0), (21, 20), (1, 20)]),
        intervention_id="E-999",
    )

    findings = rule.check(submission, _ctx(ekis_register=_register([REGISTER_ENTRY])))

    assert len(findings) == 1
    assert findings[0].rule_id == "SPATIAL-03"
    assert findings[0].observed_value == "REG-1"


def test_spatial03_passes_near_identical_geometry_same_intervention() -> None:
    rule = NearDuplicateDetection()
    submission = _compensation(
        "K-1",
        geometry=Polygon([(1, 0), (21, 0), (21, 20), (1, 20)]),
        intervention_id="E-100",
    )

    findings = rule.check(submission, _ctx(ekis_register=_register([REGISTER_ENTRY])))

    assert findings == []


def test_spatial03_passes_spatially_close_but_area_ratio_out_of_range() -> None:
    rule = NearDuplicateDetection()
    submission = _compensation(
        "K-1",
        geometry=Polygon(
            [(4, 0), (16, 0), (20, 4), (20, 16), (16, 20), (4, 20), (0, 16), (0, 4)]
        ),
        intervention_id="E-999",
    )

    findings = rule.check(submission, _ctx(ekis_register=_register([REGISTER_ENTRY])))

    assert findings == []


def test_spatial03_passes_distant_geometry() -> None:
    rule = NearDuplicateDetection()
    submission = _compensation(
        "K-1",
        geometry=Polygon([(1000, 1000), (1020, 1000), (1020, 1020), (1000, 1020)]),
        intervention_id="E-999",
    )

    findings = rule.check(submission, _ctx(ekis_register=_register([REGISTER_ENTRY])))

    assert findings == []


def test_spatial03_handles_missing_register_gracefully() -> None:
    rule = NearDuplicateDetection()
    submission = _compensation("K-1", geometry=REGISTER_SQUARE, intervention_id="E-999")

    assert rule.check(submission, _ctx(ekis_register=None)) == []
