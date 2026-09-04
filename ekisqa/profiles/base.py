from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from shapely.strtree import STRtree

    from ekisqa.model import CompensationFeature, InterventionFeature
    from ekisqa.rules.base import Rule


@runtime_checkable
class SchemaAdapter(Protocol):
    def parse(
        self, path: Path
    ) -> tuple[list[CompensationFeature], list[InterventionFeature]]:
        """Read a file and return joined Compensation and Intervention features."""
        ...


@runtime_checkable
class RegisterClientProtocol(Protocol):
    """Live access to a compensation register to check double allocation."""

    def fetch(self) -> RegisterSnapshot: ...


@dataclass(slots=True)
class RegisterSnapshot:
    land_code: str
    features: list[CompensationFeature]
    fetch_timestamp: datetime
    index: STRtree | None = None


@runtime_checkable
class AxisDefinitions(Protocol):
    def evaluate(self, compensation: CompensationFeature) -> dict[str, Any]:
        """Return this record's axis flags."""
        ...


@dataclass(slots=True)
class ProfileReferenceConfig:
    """Declares where a profile's reference datasets come from."""

    state_boundary_source: str | None = None
    district_boundary_source: str | None = None
    district_crosswalk: dict[str, str] | None = None
    protected_areas_source: str | None = None


@dataclass(slots=True)
class StateProfile:
    """One land's complete protocol: schema, rules, axes, reference data."""

    land_code: str
    land_name: str
    crs: str
    schema_adapter: SchemaAdapter
    rule_pack: list[Rule] = field(default_factory=list)
    axis_definitions: AxisDefinitions | None = None
    register_client: RegisterClientProtocol | None = None
    reference: ProfileReferenceConfig = field(default_factory=ProfileReferenceConfig)
