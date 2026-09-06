from __future__ import annotations

from ekisqa.model import CompensationFeature, Finding, InterventionFeature, Severity
from ekisqa.rules.base import Rule, RuleContext


def _is_blank(value: str | None) -> bool:
    return value is None or value.strip() == ""


def _is_blank_geometry(geometry) -> bool:
    return geometry is None or geometry.is_empty


class SpatialGeometryKompensation(Rule):
    id = "COMPLETE-01"
    category = "Completeness"
    scope = "state"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 3

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if _is_blank_geometry(feature.geometry):
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation="Shape is missing or empty",
                    triggered_field="geometry",
                )
            ]
        return []


class SpatialGeometryEingriff(Rule):
    id = "COMPLETE-01"
    category = "Completeness"
    scope = "state"
    entity = "intervention"
    severity = Severity.ERROR
    stage = 3

    def check(self, feature: InterventionFeature, ctx: RuleContext) -> list[Finding]:
        if _is_blank_geometry(feature.geometry):
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.intervention_id,
                    land_code=ctx.land_code,
                    explanation="Shape is missing or empty",
                    triggered_field="geometry",
                )
            ]
        return []


class PermittingAuthority(Rule):
    id = "COMPLETE-02"
    category = "Completeness"
    scope = "state"
    entity = "intervention"
    severity = Severity.ERROR
    stage = 3

    def check(self, feature: InterventionFeature, ctx: RuleContext) -> list[Finding]:
        if _is_blank(feature.approval_authority):
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.intervention_id,
                    land_code=ctx.land_code,
                    explanation="Zulassungsbehoerde is missing",
                    triggered_field="approval_authority",
                )
            ]
        return []


class CaseReferenceKompensation(Rule):
    id = "COMPLETE-03"
    category = "Completeness"
    scope = "state"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 3

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if _is_blank(feature.case_reference):
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation="Aktenzeichen_der_Zulassungsbehoerde is missing",
                    triggered_field="case_reference",
                )
            ]
        return []


class CaseReferenceEingriff(Rule):
    id = "COMPLETE-03"
    category = "Completeness"
    scope = "state"
    entity = "intervention"
    severity = Severity.ERROR
    stage = 3

    def check(self, feature: InterventionFeature, ctx: RuleContext) -> list[Finding]:
        if _is_blank(feature.case_reference):
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.intervention_id,
                    land_code=ctx.land_code,
                    explanation="Aktenzeichen_der_Zulassungsbehoerde is missing",
                    triggered_field="case_reference",
                )
            ]
        return []


class ApprovalDate(Rule):
    id = "COMPLETE-04"
    category = "Completeness"
    scope = "state"
    entity = "intervention"
    severity = Severity.ERROR
    stage = 3

    def check(self, feature: InterventionFeature, ctx: RuleContext) -> list[Finding]:
        if feature.approval_date is None:
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.intervention_id,
                    land_code=ctx.land_code,
                    explanation="Genehmigungsdatum is missing or not a valid date",
                    triggered_field="approval_date",
                )
            ]
        return []


class MeasureType(Rule):
    id = "COMPLETE-05"
    category = "Completeness"
    scope = "state"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 3

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if _is_blank(feature.compensation_type):
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation="Art_der_Kompensation is missing",
                    triggered_field="compensation_type",
                )
            ]
        return []


class LegalBasis(Rule):
    id = "COMPLETE-06"
    category = "Completeness"
    scope = "state"
    entity = "intervention"
    severity = Severity.WARNING
    stage = 3

    def check(self, feature: InterventionFeature, ctx: RuleContext) -> list[Finding]:
        if _is_blank(feature.legal_basis):
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.intervention_id,
                    land_code=ctx.land_code,
                    explanation="Rechtsgrundlage is missing",
                    triggered_field="legal_basis",
                )
            ]
        return []


_SCOPE_PLAUSIBILITY_LEGAL_BASES = frozenset({"BauGB", "BbgBO"})


class RegistrationScopePlausibility(Rule):
    id = "COMPLETE-07"
    category = "Completeness"
    scope = "state"
    entity = "intervention"
    severity = Severity.WARNING
    stage = 3

    def check(self, feature: InterventionFeature, ctx: RuleContext) -> list[Finding]:
        if feature.legal_basis not in _SCOPE_PLAUSIBILITY_LEGAL_BASES:
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                feature_id=feature.intervention_id,
                land_code=ctx.land_code,
                explanation=(
                    "Rechtsgrundlage indicates BauGB/BbgBO. A warning to confirm this is "
                    "still a subject to EKIS registration obligation"
                ),
                triggered_field="legal_basis",
            )
        ]


COMPLETENESS_RULES: tuple[type[Rule], ...] = (
    SpatialGeometryKompensation,
    SpatialGeometryEingriff,
    PermittingAuthority,
    CaseReferenceKompensation,
    CaseReferenceEingriff,
    ApprovalDate,
    MeasureType,
    LegalBasis,
    RegistrationScopePlausibility,
)
