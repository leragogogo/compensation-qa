from __future__ import annotations

from ekisqa.model import CompensationFeature, Finding, Severity
from ekisqa.rules.base import DatasetRef, Rule, RuleContext

_FLAECHENPOOL_TYPE = "Flächenpoolkompensation"


class FlaechenpoolConsistency(Rule):
    id = "SPATIAL-02"
    category = "SpatialLegalConstraints"
    scope = "state"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 9

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        is_pool_type = feature.compensation_type == _FLAECHENPOOL_TYPE
        has_pool_name = bool(feature.area_pool_name and feature.area_pool_name.strip())

        if is_pool_type and not has_pool_name:
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation=(
                        "Art_der_Kompensation is Flächenpoolkompensation but "
                        "Bezeichnung_des_Flaechenpools is missing"
                    ),
                    triggered_field="area_pool_name",
                )
            ]
        if has_pool_name and not is_pool_type:
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation=(
                        "Bezeichnung_des_Flaechenpools is populated but Art_der_Kompensation "
                        f"is {feature.compensation_type} and not Flächenpoolkompensation"
                    ),
                    triggered_field="compensation_type",
                    observed_value=feature.compensation_type,
                )
            ]
        return []


class ProtectedAreaIntersection(Rule):
    id = "SPATIAL-04"
    category = "SpatialLegalConstraints"
    scope = "state"
    entity = "compensation"
    severity = Severity.WARNING
    stage = 9
    required_datasets = (DatasetRef("protected_areas"),)

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if feature.geometry is None:
            return []
        for area in ctx.reference.loaded["protected_areas"]:
            if feature.geometry.intersects(area):
                return [
                    Finding(
                        rule_id=self.id,
                        severity=self.severity,
                        feature_id=feature.compensation_id,
                        land_code=ctx.land_code,
                        explanation=(
                            "Compensation polygon intersects a Naturschutzgebiet or Nationalpark."
                            "Verify the parcel"
                        ),
                        triggered_field="geometry",
                    )
                ]
        return []


SPATIAL_LEGAL_CONSTRAINTS_RULES: tuple[type[Rule], ...] = (
    FlaechenpoolConsistency,
    ProtectedAreaIntersection,
)
