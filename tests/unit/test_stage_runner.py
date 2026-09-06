from __future__ import annotations

from datetime import date
from pathlib import Path

from ekisqa.context import ValidationContext
from ekisqa.model import CompensationFeature, InterventionFeature, Severity
from ekisqa.profiles.base import ProfileReferenceConfig, StateProfile
from ekisqa.profiles.brandenburg.schema_adapter import BrandenburgSchemaAdapter
from ekisqa.profiles.registry import default_registry
from ekisqa.register_data import ReferenceData
from ekisqa.rules.base import DatasetRef, Rule
from ekisqa.rules.registry import CoreRuleRegistry, StageRunner
from tests.fixtures import builders

CHECK_DATE = date(2026, 1, 1)


class _NoOpSchemaAdapter:
    def parse(self, path: Path) -> tuple[list, list]:
        raise NotImplementedError("not used by StageRunner tests")


def _synthetic_profile(**overrides) -> StateProfile:
    defaults = {
        "land_code": "ZZ",
        "land_name": "Synthetic",
        "crs": "EPSG:4326",
        "schema_adapter": _NoOpSchemaAdapter(),
        "rule_pack": [],
        "register_client": None,
        "reference": ProfileReferenceConfig(),
    }
    defaults.update(overrides)
    return StateProfile(**defaults)


def _context(
    profile, compensations=(), interventions=(), **overrides
) -> ValidationContext:
    defaults = {
        "profile": profile,
        "compensations": list(compensations),
        "interventions": list(interventions),
        "check_date": CHECK_DATE,
    }
    defaults.update(overrides)
    return ValidationContext(**defaults)


def _compensation(compensation_id: str, **kwargs) -> CompensationFeature:
    return CompensationFeature(compensation_id=compensation_id, geometry=None, **kwargs)


def _intervention(intervention_id: str, **kwargs) -> InterventionFeature:
    return InterventionFeature(intervention_id=intervention_id, geometry=None, **kwargs)


def test_valid_record_produces_no_error_or_warning_findings_for_brandenburg(
    tmp_path: Path,
) -> None:
    intervention, compensation = builders.make_valid_pair()
    path = builders.write_gpkg(tmp_path / "data.gpkg", intervention, compensation)

    profile = default_registry().resolve("BB")
    compensations, interventions = BrandenburgSchemaAdapter().parse(path)
    context = _context(
        profile, compensations, interventions, check_date=date(2026, 6, 1)
    )

    findings = StageRunner(CoreRuleRegistry()).run(context)

    assert [f for f in findings if f.severity != Severity.INFO] == []
    assert {f.rule_id for f in findings} == {
        "GEOSEM-01",
        "REF-02",
        "SPATIAL-01",
        "SPATIAL-03",
        "SPATIAL-04",
    }


def test_empty_registry_returns_no_findings_for_synthetic_profile() -> None:
    context = _context(_synthetic_profile())

    findings = StageRunner(CoreRuleRegistry()).run(context)

    assert findings == []


class _RecordsCompensationIds(Rule):
    id = "STUB-COMP"
    category = "X"
    scope = "state"
    entity = "compensation"
    severity = Severity.INFO
    stage = 1

    def __init__(self) -> None:
        self.seen: list[str] = []

    def check(self, feature, ctx):
        self.seen.append(feature.compensation_id)
        return []


class _RecordsInterventionIds(Rule):
    id = "STUB-INT"
    category = "X"
    scope = "state"
    entity = "intervention"
    severity = Severity.INFO
    stage = 1

    def __init__(self) -> None:
        self.seen: list[str] = []

    def check(self, feature, ctx):
        self.seen.append(feature.intervention_id)
        return []


def test_rule_only_sees_records_of_its_declared_entity_type() -> None:
    comp_rule = _RecordsCompensationIds()
    int_rule = _RecordsInterventionIds()
    profile = _synthetic_profile(rule_pack=[comp_rule, int_rule])
    context = _context(
        profile,
        compensations=[_compensation("K-1")],
        interventions=[_intervention("E-1")],
    )

    StageRunner(CoreRuleRegistry()).run(context)

    assert comp_rule.seen == ["K-1"]
    assert int_rule.seen == ["E-1"]


class _RecordsOrder(Rule):
    category = "X"
    scope = "state"
    entity = "intervention"
    severity = Severity.INFO

    def __init__(self, id_: str, stage: int, log: list[str]) -> None:
        self.id = id_
        self.stage = stage
        self._log = log

    def check(self, feature, ctx):
        self._log.append(self.id)
        return []


def test_rules_run_in_stage_order_not_declaration_order() -> None:
    log: list[str] = []
    late = _RecordsOrder("LATE", stage=9, log=log)
    early = _RecordsOrder("EARLY", stage=1, log=log)
    profile = _synthetic_profile(rule_pack=[late, early])
    context = _context(profile, interventions=[_intervention("E-1")])

    StageRunner(CoreRuleRegistry()).run(context)

    assert log == ["EARLY", "LATE"]


class _RequiresLinkedInterventionRule(Rule):
    id = "STUB-LINKED"
    category = "X"
    scope = "state"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 1
    requires_linked_intervention = True

    def __init__(self) -> None:
        self.seen: list[str] = []

    def check(self, feature, ctx):
        self.seen.append(feature.compensation_id)
        return []


def test_requires_linked_intervention_skips_unjoined_records_with_info_finding() -> (
    None
):
    rule = _RequiresLinkedInterventionRule()
    profile = _synthetic_profile(rule_pack=[rule])
    context = _context(
        profile,
        compensations=[
            _compensation("K-1", linked_intervention=_intervention("E-1")),
            _compensation("K-2", linked_intervention=None),
        ],
    )

    findings = StageRunner(CoreRuleRegistry()).run(context)

    assert rule.seen == ["K-1"]
    skipped = [f for f in findings if f.rule_id == "STUB-LINKED"]
    assert len(skipped) == 1
    assert skipped[0].severity == Severity.INFO
    assert skipped[0].feature_id is None
    assert "linked intervention" in skipped[0].explanation


class _RequiresReferenceDatasetRule(Rule):
    id = "STUB-REFERENCE"
    category = "X"
    scope = "state"
    entity = "intervention"
    severity = Severity.INFO
    stage = 1
    required_datasets = (DatasetRef("bb_boundary"),)

    def check(self, feature, ctx):
        raise AssertionError("must not run without the required reference dataset")


def test_missing_reference_dataset_produces_info_finding_instead_of_running() -> None:
    profile = _synthetic_profile(rule_pack=[_RequiresReferenceDatasetRule()])
    context = _context(profile, interventions=[_intervention("E-1")])

    findings = StageRunner(CoreRuleRegistry()).run(context)

    assert len(findings) == 1
    assert findings[0].rule_id == "STUB-REFERENCE"
    assert findings[0].severity == Severity.INFO
    assert "bb_boundary" in findings[0].explanation


class _RunsIfReferenceLoaded(Rule):
    id = "STUB-REFERENCE-OK"
    category = "X"
    scope = "state"
    entity = "intervention"
    severity = Severity.INFO
    stage = 1
    required_datasets = (DatasetRef("bb_boundary"),)

    def __init__(self) -> None:
        self.ran = False

    def check(self, feature, ctx):
        self.ran = True
        return []


def test_loaded_reference_dataset_lets_rule_run() -> None:
    rule = _RunsIfReferenceLoaded()
    profile = _synthetic_profile(rule_pack=[rule])
    context = _context(
        profile,
        interventions=[_intervention("E-1")],
        reference=ReferenceData(loaded={"bb_boundary": object()}),
    )

    findings = StageRunner(CoreRuleRegistry()).run(context)

    assert rule.ran is True
    assert findings == []


class _RequiresEkisRegisterRule(Rule):
    id = "STUB-REGISTER"
    category = "X"
    scope = "state"
    entity = "compensation"
    severity = Severity.INFO
    stage = 1
    required_datasets = (DatasetRef("ekis_register"),)

    def check(self, feature, ctx):
        raise AssertionError("must not run without an EKIS register snapshot")


def test_missing_ekis_register_produces_info_finding_instead_of_running() -> None:
    profile = _synthetic_profile(rule_pack=[_RequiresEkisRegisterRule()])
    context = _context(profile, compensations=[_compensation("K-1")])

    findings = StageRunner(CoreRuleRegistry()).run(context)

    assert len(findings) == 1
    assert findings[0].rule_id == "STUB-REGISTER"
    assert findings[0].severity == Severity.INFO
    assert "ekis_register" in findings[0].explanation
