from __future__ import annotations

from ekisqa.model import CompensationFeature, Finding, Severity
from ekisqa.rules.base import DatasetRef, Rule, RuleContext


class PolygonWithinBrandenburg(Rule):
    id = "GEOSEM-01"
    category = "GeometricSemantic"
    scope = "state"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 7
    required_datasets = (DatasetRef("state_boundary"),)

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if feature.geometry is None:
            return []
        boundary = ctx.reference.loaded["state_boundary"]
        if not feature.geometry.disjoint(boundary):
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                feature_id=feature.compensation_id,
                land_code=ctx.land_code,
                explanation="Polygon is located outside the Brandenburg state boundary",
                triggered_field="geometry",
            )
        ]


GEOMETRIC_SEMANTIC_RULES: tuple[type[Rule], ...] = (PolygonWithinBrandenburg,)
