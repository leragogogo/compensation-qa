from __future__ import annotations

from ekisqa.model import CompensationFeature, Finding, InterventionFeature, Severity
from ekisqa.rules.base import DatasetRef, Rule, RuleContext


class KompensationReferencesExistingEingriff(Rule):
    id = "REF-01"
    category = "ReferentialIntegrity"
    scope = "state"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 6

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if feature.linked_intervention is not None:
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                feature_id=feature.compensation_id,
                land_code=ctx.land_code,
                explanation="Eingriff_ID is not an ID of an existing intervention record",
                triggered_field="intervention_id",
                observed_value=feature.intervention_id,
            )
        ]


class AuthorityCompetenceCheck(Rule):
    id = "REF-02"
    category = "ReferentialIntegrity"
    scope = "state"
    entity = "intervention"
    severity = Severity.WARNING
    stage = 8
    required_datasets = (DatasetRef("district_boundaries"),)

    def check(self, feature: InterventionFeature, ctx: RuleContext) -> list[Finding]:
        if feature.category_zb != "Landkreis":
            return []
        if feature.geometry is None or not feature.district:
            return []

        boundaries = ctx.reference.loaded["district_boundaries"]
        codes = {code.strip() for code in feature.district.split(";") if code.strip()}
        matched = [boundaries[code] for code in codes if code in boundaries]
        if not matched:
            return []
        if any(feature.geometry.within(boundary) for boundary in matched):
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                feature_id=feature.intervention_id,
                land_code=ctx.land_code,
                explanation=(
                    f"Eingriff point does not lie within the declared districts"
                    f"{feature.district!r}"
                ),
                triggered_field="district",
                observed_value=feature.district,
            )
        ]


class UniqueRecordIdentifier(Rule):
    id = "REF-03"
    category = "ReferentialIntegrity"
    scope = "state"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 6

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if feature.compensation_id is None:
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=None,
                    land_code=ctx.land_code,
                    explanation="Kompensation_ID is missing",
                    triggered_field="compensation_id",
                )
            ]
        for other in ctx.compensations:
            if (
                other is not feature
                and other.compensation_id == feature.compensation_id
            ):
                return [
                    Finding(
                        rule_id=self.id,
                        severity=self.severity,
                        feature_id=feature.compensation_id,
                        land_code=ctx.land_code,
                        explanation="Kompensation_ID is duplicated across the dataset",
                        triggered_field="compensation_id",
                        observed_value=feature.compensation_id,
                    )
                ]
        return []


REFERENTIAL_INTEGRITY_RULES: tuple[type[Rule], ...] = (
    KompensationReferencesExistingEingriff,
    AuthorityCompetenceCheck,
    UniqueRecordIdentifier,
)
