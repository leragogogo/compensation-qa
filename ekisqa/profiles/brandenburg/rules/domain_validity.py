from __future__ import annotations

from ekisqa.model import CompensationFeature, Finding, InterventionFeature, Severity
from ekisqa.rules.base import Rule, RuleContext

_ALLOWED_COMPENSATION_TYPES = frozenset({"Realkompensation", "Flächenpoolkompensation"})
_AKTENZEICHEN_MAX_LENGTH = 50


class MeasureTypeControlledVocabulary(Rule):
    id = "DOMAIN-01"
    category = "DomainValidity"
    scope = "state"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 2

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        value = feature.compensation_type
        if not value or value in _ALLOWED_COMPENSATION_TYPES:
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                feature_id=feature.compensation_id,
                land_code=ctx.land_code,
                explanation=f"Art_der_Kompensation {value} is not a recognised EKIS value",
                triggered_field="compensation_type",
                observed_value=value,
            )
        ]


class AktenzeichenFormatKompensation(Rule):
    id = "DOMAIN-02"
    category = "DomainValidity"
    scope = "state"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 2

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if (
            feature.case_reference
            and len(feature.case_reference) > _AKTENZEICHEN_MAX_LENGTH
        ):
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation=(
                        f"Aktenzeichen_der_Zulassungsbehoerde is "
                        f"{len(feature.case_reference)} characters, exceeds the "
                        f"{_AKTENZEICHEN_MAX_LENGTH}-character EKIS schema limit"
                    ),
                    triggered_field="case_reference",
                    observed_value=feature.case_reference,
                )
            ]
        return []


class AktenzeichenFormatEingriff(Rule):
    id = "DOMAIN-02"
    category = "DomainValidity"
    scope = "state"
    entity = "intervention"
    severity = Severity.ERROR
    stage = 2

    def check(self, feature: InterventionFeature, ctx: RuleContext) -> list[Finding]:
        if (
            feature.case_reference
            and len(feature.case_reference) > _AKTENZEICHEN_MAX_LENGTH
        ):
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.intervention_id,
                    land_code=ctx.land_code,
                    explanation=(
                        f"Aktenzeichen_der_Zulassungsbehoerde is "
                        f"{len(feature.case_reference)} characters, exceeds the "
                        f"{_AKTENZEICHEN_MAX_LENGTH}-character EKIS schema limit"
                    ),
                    triggered_field="case_reference",
                    observed_value=feature.case_reference,
                )
            ]
        return []


DOMAIN_VALIDITY_RULES: tuple[type[Rule], ...] = (
    MeasureTypeControlledVocabulary,
    AktenzeichenFormatKompensation,
    AktenzeichenFormatEingriff,
)
