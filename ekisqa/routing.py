from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ekisqa.model import CompensationFeature, InterventionFeature


@dataclass(frozen=True, slots=True)
class AxisCondition:
    axis: str
    values: frozenset[str]


@dataclass(frozen=True, slots=True)
class AxisFlags:
    flags: dict[str, Any]

    def satisfies(self, condition: AxisCondition | None) -> bool:
        if condition is None:
            return True
        return self.flags.get(condition.axis) in condition.values


@runtime_checkable
class AxisDefinitions(Protocol):
    def evaluate(
        self, record: CompensationFeature | InterventionFeature
    ) -> dict[str, Any]: ...


class RoutingPreCheck:
    def __init__(self, axis_definitions: AxisDefinitions | None) -> None:
        self._axis_definitions = axis_definitions

    def resolve(self, record: CompensationFeature | InterventionFeature) -> AxisFlags:
        if self._axis_definitions is None:
            return AxisFlags(flags={})
        return AxisFlags(flags=self._axis_definitions.evaluate(record))

    def applies(
        self,
        condition: AxisCondition | None,
        record: CompensationFeature | InterventionFeature,
    ) -> bool:
        return self.resolve(record).satisfies(condition)
