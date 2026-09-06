from __future__ import annotations

from ekisqa.context import ValidationContext
from ekisqa.model import Finding, Severity
from ekisqa.rules.base import DatasetRef, Rule


class CoreRuleRegistry:
    def __init__(self, rules: list[Rule] | None = None) -> None:
        self._rules = list(rules) if rules else []

    def rules(self) -> list[Rule]:
        return list(self._rules)


class StageRunner:
    """Runs the rule pack once per record, and returns every Finding."""

    def __init__(self, core_registry: CoreRuleRegistry | None = None) -> None:
        self._core_registry = core_registry or CoreRuleRegistry()

    def run(self, context: ValidationContext) -> list[Finding]:
        rules = sorted(
            [*self._core_registry.rules(), *context.profile.rule_pack],
            key=lambda rule: (rule.stage, rule.id),
        )

        findings: list[Finding] = []
        for rule in rules:
            records = (
                context.compensations
                if rule.entity == "compensation"
                else context.interventions
            )
            for record in records:
                findings.extend(self._check_one(rule, record, context))
        return findings

    def _check_one(self, rule: Rule, record, context: ValidationContext) -> list[Finding]:
        if (
            rule.entity == "compensation"
            and rule.requires_linked_intervention
            and record.linked_intervention is None
        ):
            return [self._skipped(rule, context, "no linked intervention")]

        missing = self._missing_datasets(rule.required_datasets, context)
        if missing:
            return [self._skipped(rule, context, f"{', '.join(missing)} not available")]

        return rule.check(record, context)

    @staticmethod
    def _missing_datasets(
        required: tuple[DatasetRef, ...], context: ValidationContext
    ) -> list[str]:
        missing = []
        for ref in required:
            loaded = (
                context.ekis_register is not None
                if ref.dataset_name == "ekis_register"
                else context.reference.has(ref.dataset_name)
            )
            if not loaded:
                missing.append(ref.dataset_name)
        return missing

    @staticmethod
    def _skipped(rule: Rule, context: ValidationContext, reason: str) -> Finding:
        return Finding(
            rule_id=rule.id,
            severity=Severity.INFO,
            feature_id=None,
            land_code=context.land_code,
            explanation=f"Skipped {rule.id}: {reason}.",
        )
