from __future__ import annotations

from ekisqa.model import CompensationFeature, Finding, InterventionFeature, Severity
from ekisqa.rules.base import Rule, RuleContext


class CompensationAreaGeometryType(Rule):
    id = "TECH-02"
    category = "TechnicalDelivery"
    scope = "state"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 4

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        geom_type = feature.geometry.geom_type if feature.geometry is not None else None
        if geom_type not in ("Polygon", "MultiPolygon"):
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation=f"Geometry type is {geom_type!r}, expected Polygon or MultiPolygon",
                    triggered_field="geometry",
                    observed_value=geom_type,
                )
            ]
        return []


class InterventionGeometryType(Rule):
    id = "TECH-03"
    category = "TechnicalDelivery"
    scope = "state"
    entity = "intervention"
    severity = Severity.ERROR
    stage = 4

    def check(self, feature: InterventionFeature, ctx: RuleContext) -> list[Finding]:
        geom_type = feature.geometry.geom_type if feature.geometry is not None else None
        if geom_type != "Point":
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.intervention_id,
                    land_code=ctx.land_code,
                    explanation=f"Geometry type is {geom_type!r}, expected Point",
                    triggered_field="geometry",
                    observed_value=geom_type,
                )
            ]
        return []


TECHNICAL_DELIVERY_RULES: tuple[type[Rule], ...] = (
    CompensationAreaGeometryType,
    InterventionGeometryType,
)
