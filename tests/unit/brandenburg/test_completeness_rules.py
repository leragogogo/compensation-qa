from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from shapely.geometry import Point, Polygon

from ekisqa.model import CompensationFeature, InterventionFeature, Severity
from ekisqa.profiles.brandenburg.rules.completeness import (
    ApprovalDate,
    CaseReferenceEingriff,
    CaseReferenceKompensation,
    LegalBasis,
    MeasureType,
    PermittingAuthority,
    RegistrationScopePlausibility,
    SpatialGeometryEingriff,
    SpatialGeometryKompensation,
)
from ekisqa.register_data import ReferenceData

CHECK_DATE = date(2026, 1, 1)
VALID_SQUARE = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
VALID_POINT = Point(400050, 5800050)


def _compensation(compensation_id: str, **kwargs) -> CompensationFeature:
    kwargs.setdefault("geometry", VALID_SQUARE)
    return CompensationFeature(compensation_id=compensation_id, **kwargs)


def _intervention(intervention_id: str, **kwargs) -> InterventionFeature:
    kwargs.setdefault("geometry", VALID_POINT)
    return InterventionFeature(intervention_id=intervention_id, **kwargs)


def _ctx(land_code="BB"):
    return SimpleNamespace(
        compensations=[],
        interventions=[],
        reference=ReferenceData(),
        ekis_register=None,
        check_date=CHECK_DATE,
        land_code=land_code,
    )


def test_complete01_kompensation_passes_present_geometry() -> None:
    rule = SpatialGeometryKompensation()
    feature = _compensation("K-1")

    assert rule.check(feature, _ctx()) == []


def test_complete01_kompensation_flags_missing_geometry() -> None:
    rule = SpatialGeometryKompensation()
    feature = _compensation("K-1", geometry=None)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "COMPLETE-01"
    assert findings[0].severity == Severity.ERROR


def test_complete01_kompensation_flags_empty_geometry() -> None:
    rule = SpatialGeometryKompensation()
    feature = _compensation("K-1", geometry=Polygon())

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "COMPLETE-01"


def test_complete01_eingriff_passes_present_geometry() -> None:
    rule = SpatialGeometryEingriff()
    feature = _intervention("E-1")

    assert rule.check(feature, _ctx()) == []


def test_complete01_eingriff_flags_missing_geometry() -> None:
    rule = SpatialGeometryEingriff()
    feature = _intervention("E-1", geometry=None)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "COMPLETE-01"


def test_complete02_permitting_authority_passes_present_value() -> None:
    rule = PermittingAuthority()
    feature = _intervention("E-1", approval_authority="Landkreis Potsdam-Mittelmark")

    assert rule.check(feature, _ctx()) == []


def test_complete02_permitting_authority_flags_missing_value() -> None:
    rule = PermittingAuthority()
    feature = _intervention("E-1", approval_authority=None)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "COMPLETE-02"


def test_complete03_kompensation_passes_present_case_reference() -> None:
    rule = CaseReferenceKompensation()
    feature = _compensation("K-1", case_reference="AZ-2026-001")

    assert rule.check(feature, _ctx()) == []


def test_complete03_kompensation_flags_missing_case_reference() -> None:
    rule = CaseReferenceKompensation()
    feature = _compensation("K-1", case_reference="")

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "COMPLETE-03"


def test_complete03_eingriff_passes_present_case_reference() -> None:
    rule = CaseReferenceEingriff()
    feature = _intervention("E-1", case_reference="AZ-2026-001")

    assert rule.check(feature, _ctx()) == []


def test_complete03_eingriff_flags_missing_case_reference() -> None:
    rule = CaseReferenceEingriff()
    feature = _intervention("E-1", case_reference=None)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "COMPLETE-03"


def test_complete04_approval_date_passes_present_date() -> None:
    rule = ApprovalDate()
    feature = _intervention("E-1", approval_date=date(2026, 3, 1))

    assert rule.check(feature, _ctx()) == []


def test_complete04_approval_date_flags_missing_date() -> None:
    rule = ApprovalDate()
    feature = _intervention("E-1", approval_date=None)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "COMPLETE-04"


def test_complete05_measure_type_passes_present_value() -> None:
    rule = MeasureType()
    feature = _compensation("K-1", compensation_type="Realkompensation")

    assert rule.check(feature, _ctx()) == []


def test_complete05_measure_type_flags_missing_value() -> None:
    rule = MeasureType()
    feature = _compensation("K-1", compensation_type=None)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "COMPLETE-05"


def test_complete06_legal_basis_passes_present_value() -> None:
    rule = LegalBasis()
    feature = _intervention("E-1", legal_basis="BImSchG")

    assert rule.check(feature, _ctx()) == []


def test_complete06_legal_basis_flags_missing_value() -> None:
    rule = LegalBasis()
    feature = _intervention("E-1", legal_basis=None)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "COMPLETE-06"
    assert findings[0].severity == Severity.WARNING


def test_complete07_registration_scope_plausibility_flags_baugb() -> None:
    rule = RegistrationScopePlausibility()
    feature = _intervention("E-1", legal_basis="BauGB")

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "COMPLETE-07"
    assert findings[0].severity == Severity.WARNING
    assert findings[0].feature_id == "E-1"


def test_complete07_registration_scope_plausibility_flags_bbgbo() -> None:
    rule = RegistrationScopePlausibility()
    feature = _intervention("E-1", legal_basis="BbgBO")

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "COMPLETE-07"


def test_complete07_registration_scope_plausibility_passes_other_legal_basis() -> None:
    rule = RegistrationScopePlausibility()
    feature = _intervention("E-1", legal_basis="BImSchG")

    assert rule.check(feature, _ctx()) == []
