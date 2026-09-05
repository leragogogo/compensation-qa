from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

from ekisqa.model import CompensationFeature, InterventionFeature
from ekisqa.profiles.base import StateProfile
from ekisqa.register_data import ReferenceData, RegisterSnapshot
from ekisqa.routing import AxisFlags


@dataclass(frozen=True, slots=True)
class ValidationContext:
    profile: StateProfile
    compensations: list[CompensationFeature]
    interventions: list[InterventionFeature]
    check_date: date
    reference: ReferenceData = field(default_factory=ReferenceData)
    ekis_register: RegisterSnapshot | None = None
    axis_flags: AxisFlags | None = None

    @property
    def land_code(self) -> str:
        return self.profile.land_code

    def for_record(self, axis_flags: AxisFlags) -> ValidationContext:
        return replace(self, axis_flags=axis_flags)
