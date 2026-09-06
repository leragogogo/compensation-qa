from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from ekisqa.model import CompensationFeature, InterventionFeature, Severity
from ekisqa.profiles.brandenburg.rules.domain_validity import (
    AktenzeichenFormatEingriff,
    AktenzeichenFormatKompensation,
    MeasureTypeControlledVocabulary,
)
from ekisqa.register_data import ReferenceData

CHECK_DATE = date(2026, 1, 1)


def _compensation(compensation_id: str, **kwargs) -> CompensationFeature:
    return CompensationFeature(compensation_id=compensation_id, geometry=None, **kwargs)


def _intervention(intervention_id: str, **kwargs) -> InterventionFeature:
    return InterventionFeature(intervention_id=intervention_id, geometry=None, **kwargs)


def _ctx(land_code="BB"):
    return SimpleNamespace(
        compensations=[],
        interventions=[],
        reference=ReferenceData(),
        ekis_register=None,
        check_date=CHECK_DATE,
        land_code=land_code,
    )


def test_domain01_passes_realkompensation() -> None:
    rule = MeasureTypeControlledVocabulary()
    feature = _compensation("K-1", compensation_type="Realkompensation")

    assert rule.check(feature, _ctx()) == []


def test_domain01_passes_flaechenpoolkompensation() -> None:
    rule = MeasureTypeControlledVocabulary()
    feature = _compensation("K-1", compensation_type="Flächenpoolkompensation")

    assert rule.check(feature, _ctx()) == []


def test_domain01_ignores_null_value() -> None:
    rule = MeasureTypeControlledVocabulary()
    feature = _compensation("K-1", compensation_type=None)

    assert rule.check(feature, _ctx()) == []


def test_domain01_flags_value_outside_vocabulary() -> None:
    rule = MeasureTypeControlledVocabulary()
    feature = _compensation("K-1", compensation_type="Ausgleichsmaßnahme")

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "DOMAIN-01"
    assert findings[0].severity == Severity.ERROR
    assert findings[0].observed_value == "Ausgleichsmaßnahme"


def test_domain02_kompensation_passes_short_aktenzeichen() -> None:
    rule = AktenzeichenFormatKompensation()
    feature = _compensation("K-1", case_reference="AZ-2026-001")

    assert rule.check(feature, _ctx()) == []


def test_domain02_kompensation_ignores_null_aktenzeichen() -> None:
    rule = AktenzeichenFormatKompensation()
    feature = _compensation("K-1", case_reference=None)

    assert rule.check(feature, _ctx()) == []


def test_domain02_kompensation_flags_aktenzeichen_over_50_chars() -> None:
    rule = AktenzeichenFormatKompensation()
    feature = _compensation("K-1", case_reference="A" * 51)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "DOMAIN-02"
    assert findings[0].feature_id == "K-1"


def test_domain02_eingriff_passes_short_aktenzeichen() -> None:
    rule = AktenzeichenFormatEingriff()
    feature = _intervention("E-1", case_reference="AZ-2026-001")

    assert rule.check(feature, _ctx()) == []


def test_domain02_eingriff_flags_aktenzeichen_over_50_chars() -> None:
    rule = AktenzeichenFormatEingriff()
    feature = _intervention("E-1", case_reference="A" * 51)

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "DOMAIN-02"
    assert findings[0].feature_id == "E-1"
