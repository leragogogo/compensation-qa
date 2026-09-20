from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from pathlib import Path

from ekisqa.context import ValidationContext
from ekisqa.model import CompensationFeature, Finding, InterventionFeature
from ekisqa.profiles.base import StateProfile
from ekisqa.profiles.registry import ProfileRegistry, default_registry
from ekisqa.reference.manager import ReferenceDataManager
from ekisqa.reports.metadata import ReportMetadata
from ekisqa.rules.base import Rule
from ekisqa.rules.core import CORE_RULES
from ekisqa.rules.registry import CoreRuleRegistry, StageRunner


class UnknownRuleCategoryError(ValueError):
    def __init__(self, unknown: set[str], available: set[str]) -> None:
        self.unknown = unknown
        self.available = available
        noun = "category" if len(unknown) == 1 else "categories"
        super().__init__(
            f"Unknown rule {noun}: {', '.join(sorted(unknown))}. "
            f"Available: {', '.join(sorted(available))}"
        )


@dataclass(frozen=True, slots=True)
class ValidationRun:
    profile: StateProfile
    compensations: list[CompensationFeature]
    interventions: list[InterventionFeature]
    findings: list[Finding]
    rules: list[Rule]
    check_date: date
    metadata: ReportMetadata
    live_register_skipped: bool = field(default=False)


def run_validation(
    file: Path,
    state: str = "BB",
    rules: str | None = None,
    check_date: date | None = None,
    live_register: bool = False,
    registry: ProfileRegistry | None = None,
) -> ValidationRun:
    profile = (registry or default_registry()).resolve(state)

    compensations, interventions = profile.schema_adapter.parse(file)

    resolved_check_date = check_date or datetime.now(UTC).date()

    core_rules = [rule_cls() for rule_cls in CORE_RULES]

    if rules:
        requested = {name.strip() for name in rules.split(",") if name.strip()}
        available = {rule.category for rule in [*core_rules, *profile.rule_pack]}
        unknown = requested - available
        if unknown:
            raise UnknownRuleCategoryError(unknown, available)
        core_rules = [rule for rule in core_rules if rule.category in requested]
        profile = replace(
            profile,
            rule_pack=[
                rule for rule in profile.rule_pack if rule.category in requested
            ],
        )

    ekis_register = None
    live_register_skipped = False
    if live_register:
        if profile.register_client is None:
            live_register_skipped = True
        else:
            ekis_register = profile.register_client.fetch()

    context = ValidationContext(
        profile=profile,
        compensations=compensations,
        interventions=interventions,
        check_date=resolved_check_date,
        reference=ReferenceDataManager(profile).load(),
        ekis_register=ekis_register,
    )

    findings = StageRunner(CoreRuleRegistry(rules=core_rules)).run(context)
    active_rules = [*core_rules, *profile.rule_pack]

    metadata = ReportMetadata(
        land_code=profile.land_code,
        check_date=resolved_check_date,
        register_fetch_timestamp=(
            ekis_register.fetch_timestamp if ekis_register else None
        ),
    )

    return ValidationRun(
        profile=profile,
        compensations=compensations,
        interventions=interventions,
        findings=findings,
        rules=active_rules,
        check_date=resolved_check_date,
        metadata=metadata,
        live_register_skipped=live_register_skipped,
    )
