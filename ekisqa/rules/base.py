from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import ClassVar, Literal, Protocol, runtime_checkable

from ekisqa.model import CompensationFeature, Finding, InterventionFeature, Severity
from ekisqa.register_data import ReferenceData, RegisterSnapshot
from ekisqa.routing import AxisCondition, AxisFlags

RuleScope = Literal["core", "state"]

RuleEntity = Literal["compensation", "intervention"]


@dataclass(frozen=True, slots=True)
class DatasetRef:
    dataset_name: str


@runtime_checkable
class RuleContext(Protocol):
    compensations: list[CompensationFeature]
    interventions: list[InterventionFeature]
    reference: ReferenceData
    ekis_register: RegisterSnapshot | None
    axis_flags: AxisFlags | None
    check_date: date

    @property
    def land_code(self) -> str: ...


class Rule(ABC):
    id: ClassVar[str]
    category: ClassVar[str]
    scope: ClassVar[RuleScope]
    entity: ClassVar[RuleEntity]
    severity: ClassVar[Severity]
    stage: ClassVar[int]
    axis_condition: ClassVar[AxisCondition | None] = None
    required_datasets: ClassVar[tuple[DatasetRef, ...]] = ()
    requires_linked_intervention: ClassVar[bool] = False

    @abstractmethod
    def check(
        self,
        feature: CompensationFeature | InterventionFeature,
        ctx: RuleContext,
    ) -> list[Finding]:
        """Return every Finding this rule produces against a given parcel."""
        ...
