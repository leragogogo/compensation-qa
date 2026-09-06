from __future__ import annotations

from ekisqa.model import Finding, InterventionFeature, Severity
from ekisqa.rules.base import Rule, RuleContext


class ApprovalDateNotInFuture(Rule):
    id = "TEMPORAL-01"
    category = "Temporal"
    scope = "state"
    entity = "intervention"
    severity = Severity.ERROR
    stage = 5

    def check(self, feature: InterventionFeature, ctx: RuleContext) -> list[Finding]:
        if feature.approval_date is None or feature.approval_date <= ctx.check_date:
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                feature_id=feature.intervention_id,
                land_code=ctx.land_code,
                explanation=(
                    f"Genehmigungsdatum {feature.approval_date} is after the check date {ctx.check_date}"
                ),
                triggered_field="approval_date",
                observed_value=str(feature.approval_date),
            )
        ]


TEMPORAL_RULES: tuple[type[Rule], ...] = (ApprovalDateNotInFuture,)
