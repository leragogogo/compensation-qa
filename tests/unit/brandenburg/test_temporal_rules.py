from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

from ekisqa.model import InterventionFeature
from ekisqa.profiles.brandenburg.rules.temporal import ApprovalDateNotInFuture
from ekisqa.register_data import ReferenceData

CHECK_DATE = date(2026, 1, 1)


def _intervention(intervention_id: str, **kwargs) -> InterventionFeature:
    return InterventionFeature(intervention_id=intervention_id, geometry=None, **kwargs)


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


def test_temporal01_passes_past_date() -> None:
    rule = ApprovalDateNotInFuture()
    feature = _intervention("E-1", approval_date=CHECK_DATE - timedelta(days=1))

    assert rule.check(feature, _ctx()) == []


def test_temporal01_passes_check_date_itself() -> None:
    rule = ApprovalDateNotInFuture()
    feature = _intervention("E-1", approval_date=CHECK_DATE)

    assert rule.check(feature, _ctx()) == []


def test_temporal01_ignores_missing_date() -> None:
    rule = ApprovalDateNotInFuture()
    feature = _intervention("E-1", approval_date=None)

    assert rule.check(feature, _ctx()) == []


def test_temporal01_flags_future_date() -> None:
    rule = ApprovalDateNotInFuture()
    feature = _intervention("E-1", approval_date=CHECK_DATE + timedelta(days=1))

    findings = rule.check(feature, _ctx())

    assert len(findings) == 1
    assert findings[0].rule_id == "TEMPORAL-01"
    assert findings[0].feature_id == "E-1"
