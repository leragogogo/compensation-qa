from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from shapely.geometry import Point, Polygon

from ekisqa.model import CompensationFeature, InterventionFeature
from ekisqa.profiles.brandenburg.rules.referential_integrity import (
    AuthorityCompetenceCheck,
    KompensationReferencesExistingEingriff,
    UniqueRecordIdentifier,
)
from ekisqa.register_data import ReferenceData

CHECK_DATE = date(2026, 1, 1)
VALID_SQUARE = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])

PM_BOUNDARY = Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)])
HVL_BOUNDARY = Polygon([(200, 0), (300, 0), (300, 100), (200, 100), (200, 0)])
DISTRICT_BOUNDARIES = {"PM": PM_BOUNDARY, "HVL": HVL_BOUNDARY}


def _compensation(compensation_id, **kwargs) -> CompensationFeature:
    kwargs.setdefault("geometry", VALID_SQUARE)
    return CompensationFeature(compensation_id=compensation_id, **kwargs)


def _intervention(intervention_id, **kwargs) -> InterventionFeature:
    kwargs.setdefault("geometry", Point(50, 50))
    return InterventionFeature(intervention_id=intervention_id, **kwargs)


def _ctx(compensations=(), reference=None, land_code="BB"):
    return SimpleNamespace(
        compensations=list(compensations),
        interventions=[],
        reference=reference if reference is not None else ReferenceData(),
        ekis_register=None,
        check_date=CHECK_DATE,
        land_code=land_code,
    )


def test_ref01_passes_when_linked() -> None:
    rule = KompensationReferencesExistingEingriff()
    feature = _compensation("K-1", linked_intervention=_intervention("E-1"))

    assert rule.check(feature, _ctx()) == []


def test_ref01_flags_missing_link() -> None:
    rule = KompensationReferencesExistingEingriff()
    feature = _compensation("K-1", linked_intervention=None)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "REF-01"


def test_ref03_passes_unique_id() -> None:
    rule = UniqueRecordIdentifier()
    feature = _compensation("K-1")
    other = _compensation("K-2")

    assert rule.check(feature, _ctx([feature, other])) == []


def test_ref03_flags_missing_id() -> None:
    rule = UniqueRecordIdentifier()
    feature = _compensation(None)

    findings = rule.check(feature, _ctx([feature]))

    assert len(findings) == 1
    assert findings[0].rule_id == "REF-03"


def test_ref03_flags_duplicate_id() -> None:
    rule = UniqueRecordIdentifier()
    feature = _compensation("K-1")
    duplicate = _compensation("K-1")

    findings = rule.check(feature, _ctx([feature, duplicate]))

    assert len(findings) == 1
    assert findings[0].rule_id == "REF-03"
    assert findings[0].feature_id == "K-1"


def _f02_ctx():
    return _ctx(
        reference=ReferenceData(loaded={"district_boundaries": DISTRICT_BOUNDARIES})
    )


def test_ref02_passes_point_within_declared_district() -> None:
    rule = AuthorityCompetenceCheck()
    feature = _intervention(
        "E-1", category_zb="Landkreis", district="PM", geometry=Point(50, 50)
    )

    assert rule.check(feature, _f02_ctx()) == []


def test_ref02_flags_point_outside_declared_district() -> None:
    rule = AuthorityCompetenceCheck()
    feature = _intervention(
        "E-1", category_zb="Landkreis", district="PM", geometry=Point(250, 50)
    )

    findings = rule.check(feature, _f02_ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "REF-02"


def test_ref02_handles_semicolon_separated_multi_district() -> None:
    rule = AuthorityCompetenceCheck()
    feature = _intervention(
        "E-1", category_zb="Landkreis", district="PM;HVL", geometry=Point(250, 50)
    )

    assert rule.check(feature, _f02_ctx()) == []


def test_ref02_skips_non_landkreis_authority() -> None:
    rule = AuthorityCompetenceCheck()
    feature = _intervention(
        "E-1", category_zb="Land", district="PM", geometry=Point(9999, 9999)
    )

    assert rule.check(feature, _f02_ctx()) == []


def test_ref02_skips_when_crosswalk_has_no_matching_code() -> None:
    rule = AuthorityCompetenceCheck()
    feature = _intervention(
        "E-1",
        category_zb="Landkreis",
        district="UNKNOWN-CODE",
        geometry=Point(9999, 9999),
    )

    assert rule.check(feature, _f02_ctx()) == []
